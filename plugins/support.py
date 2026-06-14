import asyncio
import logging
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user, support_messages_collection

logger = logging.getLogger(__name__)

async def save_mapping(admin_id: int, forwarded_msg_id: int, user_id: int):
    """Save mapping to database with explicit error handling"""
    try:
        await support_messages_collection.update_one(
            {"admin_id": admin_id, "forwarded_msg_id": forwarded_msg_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving mapping to DB: {e}")

async def get_user_id(admin_id: int, forwarded_msg_id: int):
    """Get user_id from mapping"""
    try:
        doc = await support_messages_collection.find_one(
            {"admin_id": admin_id, "forwarded_msg_id": forwarded_msg_id}
        )
        return doc["user_id"] if doc else None
    except Exception as e:
        logger.error(f"Error getting mapping from DB: {e}")
        return None

@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admin(client: Bot, message: Message):
    """Forward any user message (Text or Media) to all admins seamlessly"""
    user = message.from_user
    if not user:
        return
        
    user_id = user.id
    
    # Add user to global metrics database
    await add_user(user_id)
    
    # Don't route messages if the sender is an admin/owner
    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return
    
    username = f"@{user.username}" if user.username else "No username"
    header_info = (
        f"📨 <b>New Message from User</b>\n\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Name:</b> {user.first_name or ''} {user.last_name or ''}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>DC ID:</b> {user.dc_id or 'Unknown'}\n"
        f"-----------------------------------------\n\n"
    )
    
    # Broadcast inbound ticket to all active support admins
    for admin_id in SUPPORT_ADMINS:
        try:
            if message.media:
                # Construct combined caption safely preserving formatting constraints
                original_caption = message.caption.html if message.caption else ""
                combined_caption = f"{header_info}<b>User Caption:</b>\n{original_caption}" if original_caption else header_info
                
                # Check for Telegram caption length limitations (Max 1024 characters)
                if len(combined_caption) > 1024:
                    # Send info bundle first, then send media separately 
                    info_msg = await client.send_message(chat_id=admin_id, text=header_info, parse_mode="html")
                    await save_mapping(admin_id, info_msg.id, user_id)
                    
                    media_msg = await message.copy(chat_id=admin_id)
                    await save_mapping(admin_id, media_msg.id, user_id)
                else:
                    # Native high-fidelity media forwarding with metadata integrated
                    media_msg = await message.copy(chat_id=admin_id, caption=combined_caption, parse_mode="html")
                    await save_mapping(admin_id, media_msg.id, user_id)
            else:
                # Regular text message routing workflow
                text_content = message.text.html if message.text else ""
                full_text = f"{header_info}<b>Message:</b>\n{text_content}"
                
                sent_msg = await client.send_message(chat_id=admin_id, text=full_text, parse_mode="html")
                await save_mapping(admin_id, sent_msg.id, user_id)
                
        except Exception as e:
            logger.error(f"Failed to route ticket to admin {admin_id}: {e}")
            
    # Acknowledge user ticket receipt securely
    try:
        await message.reply(
            "✅ <b>Your message has been forwarded to our support team. You will receive a reply shortly.</b>",
            parse_mode="html"
        )
    except Exception:
        pass

@Bot.on_message(filters.private & filters.reply)
async def reply_to_user(client: Bot, message: Message):
    """When an admin replies directly to any forwarded message layout, proxy it back to the client"""
    admin_id = message.from_user.id
    
    # Verify execution credentials
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return
    
    replied_msg = message.reply_to_message
    if not replied_msg:
        return
    
    # Fetch targeted user index using structural routing table mapping
    user_id = await get_user_id(admin_id, replied_msg.id)
    
    if not user_id:
        await message.reply("❌ <b>Could not locate the destination mapping for this message.</b>", parse_mode="html")
        return
    
    try:
        # Check if admin is returning native files/media formats or simple text
        if message.media:
            # Copy media natively to recipient while retaining admin text amendments
            original_caption = message.caption.html if message.caption else ""
            prefix = "📨 <b>Reply from Support:</b>\n\n"
            new_caption = f"{prefix}{original_caption}" if original_caption else prefix
            
            await message.copy(chat_id=user_id, caption=new_caption, parse_mode="html")
        else:
            # Routing text response back safely
            reply_text = message.text.html if message.text else ""
            await client.send_message(
                chat_id=user_id,
                text=f"📨 <b>Reply from Support:</b>\n\n{reply_text}",
                parse_mode="html"
            )
            
        await message.reply(f"✅ <b>Reply successfully routed to user:</b> <code>{user_id}</code>", parse_mode="html")
        
    except Exception as e:
        await message.reply(f"❌ <b>Failed to deliver message payload:</b>\n<code>{e}</code>", parse_mode="html")
