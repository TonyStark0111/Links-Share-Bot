import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user

# Store mapping: admin_id -> {forwarded_msg_id: user_id}
# Also store in database for persistence
from database.database import support_messages_collection

async def save_mapping(admin_id: int, forwarded_msg_id: int, user_id: int):
    """Save mapping to database"""
    try:
        await support_messages_collection.update_one(
            {"admin_id": admin_id, "forwarded_msg_id": forwarded_msg_id},
            {"$set": {"user_id": user_id, "admin_id": admin_id, "forwarded_msg_id": forwarded_msg_id}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving mapping: {e}")

async def get_user_id(admin_id: int, forwarded_msg_id: int):
    """Get user_id from mapping"""
    try:
        doc = await support_messages_collection.find_one(
            {"admin_id": admin_id, "forwarded_msg_id": forwarded_msg_id}
        )
        return doc["user_id"] if doc else None
    except Exception as e:
        print(f"Error getting mapping: {e}")
        return None

@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admin(client: Bot, message: Message):
    """Forward any user message to all admins"""
    user = message.from_user
    user_id = user.id
    
    # Add to database
    await add_user(user_id)
    
    # Don't forward admin messages
    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return
    
    # Prepare user info
    user_info = f"""
<b>📨 New Message from User</b>

<b>User ID:</b> <code>{user_id}</code>
<b>Name:</b> {user.first_name or ''} {user.last_name or ''}
<b>Username:</b> @{user.username} if user.username else 'No username'
<b>DC ID:</b> {user.dc_id or 'Unknown'}

<b>Message:</b>
{message.text or message.caption or 'Media message'}
"""
    
    # Send to each admin
    for admin_id in SUPPORT_ADMINS:
        try:
            # Send message to admin
            sent = await client.send_message(
                admin_id,
                user_info,
                parse_mode="HTML"
            )
            
            # Store mapping so admin can reply
            await save_mapping(admin_id, sent.id, user_id)
            
            # If media, forward separately
            if message.media:
                await message.copy(admin_id)
                
        except Exception as e:
            print(f"Failed to send to admin {admin_id}: {e}")
    
    # Acknowledge user
    try:
        await message.reply(
            "✅ Your message has been forwarded to our support team. You will receive a reply shortly.",
            parse_mode="HTML"
        )
    except:
        pass

@Bot.on_message(filters.private & filters.reply)
async def reply_to_user(client: Bot, message: Message):
    """When admin replies to forwarded message, send to user"""
    admin_id = message.from_user.id
    
    # Check if sender is admin
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return
    
    # Get the message they replied to
    replied_msg = message.reply_to_message
    if not replied_msg:
        return
    
    # Get user_id from mapping
    user_id = await get_user_id(admin_id, replied_msg.id)
    
    if not user_id:
        await message.reply("❌ Could not find the original user. The mapping may have expired.")
        return
    
    # Send reply to user
    reply_text = message.text or message.caption
    try:
        if reply_text:
            await client.send_message(
                user_id,
                f"<b>📨 Reply from Support:</b>\n\n{reply_text}",
                parse_mode="HTML"
            )
            await message.reply(f"✅ Reply sent to user <code>{user_id}</code>")
        elif message.media:
            await message.copy(user_id)
            await message.reply(f"✅ Media forwarded to user <code>{user_id}</code>")
    except Exception as e:
        await message.reply(f"❌ Failed to send: {e}")
