import asyncio
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user

# Simple in-memory storage for mapping (more reliable than database for testing)
mapping = {}  # {(admin_id, forwarded_msg_id): user_id}

@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admin(client: Bot, message: Message):
    """Forward user message to all admins"""
    user = message.from_user
    user_id = user.id
    
    await add_user(user_id)
    
    # Don't forward admin messages
    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return
    
    # Prepare user info
    username = f"@{user.username}" if user.username else "No username"
    user_info = f"""
📨 **New message from user**

**ID:** `{user_id}`
**Name:** {user.first_name or ''} {user.last_name or ''}
**Username:** {username}
**DC:** {user.dc_id or 'Unknown'}

**Message:**
{message.text or message.caption or 'Media message'}
"""
    
    # Send to each admin
    for admin_id in SUPPORT_ADMINS:
        try:
            if message.media:
                # For media messages, send media with caption
                sent = await message.copy(
                    admin_id,
                    caption=user_info,
                    parse_mode="Markdown"
                )
            else:
                # For text messages
                sent = await client.send_message(
                    admin_id,
                    user_info,
                    parse_mode="Markdown"
                )
            
            # Store mapping in memory (more reliable)
            mapping[(admin_id, sent.id)] = user_id
            print(f"✅ Mapping stored: admin={admin_id}, msg_id={sent.id}, user={user_id}")
            
        except Exception as e:
            print(f"Failed to send to admin {admin_id}: {e}")
    
    # Acknowledge user
    try:
        await message.reply(
            "✅ Your message has been forwarded to support. You'll receive a reply here."
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
    user_id = mapping.get((admin_id, replied_msg.id))
    
    print(f"🔍 Looking for mapping: admin={admin_id}, msg_id={replied_msg.id}")
    print(f"📋 Current mappings: {mapping}")
    
    if not user_id:
        await message.reply(
            "❌ Could not find the original user.\n\n"
            "Make sure you are replying to the message that contains the user's info (ID, Name, etc.)"
        )
        return
    
    # Send reply to user
    reply_text = message.text or message.caption
    try:
        if reply_text:
            await client.send_message(
                user_id,
                f"📨 **Reply from Support:**\n\n{reply_text}",
                parse_mode="Markdown"
            )
            await message.reply(f"✅ Reply sent to user `{user_id}`")
            print(f"✅ Reply sent to user {user_id}")
        elif message.media:
            await message.copy(user_id)
            await message.reply(f"✅ Media sent to user `{user_id}`")
    except Exception as e:
        await message.reply(f"❌ Failed to send: {e}")
        print(f"Error sending reply: {e}")
