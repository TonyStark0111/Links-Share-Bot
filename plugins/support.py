from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user, save_support_mapping, get_user_id_by_forwarded_msg, delete_support_mapping

# Forward user messages to admins
@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admin(client: Bot, message: Message):
    user = message.from_user
    user_id = user.id
    
    # Add user to database
    await add_user(user_id)
    
    # Don't forward messages from admins themselves
    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return
    
    # Prepare message text for admin
    username = f"@{user.username}" if user.username else "No username"
    msg_text = f"""
📨 NEW MESSAGE FROM USER

ID: {user_id}
Name: {user.first_name or ''}
Username: {username}
DC ID: {user.dc_id or 'Unknown'}

Message:
{message.text or '📎 Media message attached below'}

---
💡 Reply to this message to send a reply back to the user
"""
    
    # Send to each admin
    for admin_id in SUPPORT_ADMINS:
        try:
            # Send the info message
            sent = await client.send_message(admin_id, msg_text)
            
            # Save mapping so admin can reply
            await save_support_mapping(admin_id, sent.id, user_id)
            
            # If there's media, forward it separately
            if message.media:
                await message.copy(admin_id)
                
        except Exception as e:
            print(f"Failed to send to admin {admin_id}: {e}")
    
    # Acknowledge the user
    try:
        await message.reply("✅ Your message has been forwarded to our support team. You will receive a reply here.")
    except:
        pass

# Handle admin replies to forwarded messages
@Bot.on_message(filters.private & filters.reply)
async def admin_reply_to_user(client: Bot, message: Message):
    admin_id = message.from_user.id
    
    # Check if sender is an admin
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return
    
    # Get the message they replied to
    replied_msg = message.reply_to_message
    if not replied_msg:
        return
    
    # Get original user ID from the mapping
    user_id = await get_user_id_by_forwarded_msg(admin_id, replied_msg.id)
    
    if not user_id:
        await message.reply("❌ Cannot find original user. Use /reply command instead.")
        return
    
    # Send the reply to the user
    reply_text = message.text or message.caption
    try:
        if reply_text:
            await client.send_message(user_id, f"📨 SUPPORT REPLY:\n\n{reply_text}")
            await message.reply(f"✅ Reply sent to user `{user_id}`")
        elif message.media:
            await message.copy(user_id)
            await message.reply(f"✅ Media sent to user `{user_id}`")
    except Exception as e:
        await message.reply(f"❌ Failed to send: {e}")

# Direct reply command for admins: /reply 821215952 Hello user!
@Bot.on_message(filters.command("reply") & filters.private)
async def direct_reply_command(client: Bot, message: Message):
    admin_id = message.from_user.id
    
    # Check if sender is an admin
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return await message.reply("❌ You are not authorized to use this command.")
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("📝 **Usage:** `/reply 821215952 Your message here`")
    
    try:
        user_id = int(parts[1])
        text = parts[2]
        await client.send_message(user_id, f"📨 SUPPORT REPLY:\n\n{text}")
        await message.reply(f"✅ Message sent to user `{user_id}`")
    except ValueError:
        await message.reply("❌ Invalid user ID. Use numbers only.")
    except Exception as e:
        await message.reply(f"❌ Failed: {e}")

# Check support system status
@Bot.on_message(filters.command("support") & filters.private)
async def support_status_command(client: Bot, message: Message):
    admin_id = message.from_user.id
    
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return await message.reply("Contact support for help. Use /start")
    
    # Format admin list
    admin_list = "\n".join([f"• `{aid}`" for aid in SUPPORT_ADMINS])
    
    await message.reply(f"""
✅ **Support System Active**

**Admins receiving user messages:**
{admin_list}

**How to reply:**
1. Reply directly to any forwarded message
2. Or use: `/reply <user_id> <message>`

**Status:** Online and monitoring
""")
