import asyncio
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user

# Simple in-memory store
reply_map = {}

@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admin(client: Bot, message: Message):
    user = message.from_user
    user_id = user.id
    await add_user(user_id)

    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return

    # Build info text
    username = f"@{user.username}" if user.username else "No username"
    msg_text = message.text or message.caption or "📎 Media (no caption)"
    info = f"""**📨 New message from user**

ID: `{user_id}`
Name: {user.first_name or ''}
Username: {username}
DC: {user.dc_id or '?'}

**Message:**\n{msg_text}"""

    for admin_id in SUPPORT_ADMINS:
        try:
            if message.media:
                sent = await message.copy(admin_id, caption=info, parse_mode="Markdown")
            else:
                sent = await client.send_message(admin_id, info, parse_mode="Markdown")
            # Store mapping: (admin_id, sent_message_id) -> user_id
            reply_map[(admin_id, sent.id)] = user_id
            print(f"✅ MAPPING SAVED: admin={admin_id}, msg_id={sent.id} -> user={user_id}")
        except Exception as e:
            print(f"❌ Failed to send to admin {admin_id}: {e}")

    await message.reply("✅ Your message has been forwarded to support. You'll receive a reply here.")


@Bot.on_message(filters.private & filters.reply)
async def reply_to_user(client: Bot, message: Message):
    admin_id = message.from_user.id
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return

    replied_msg = message.reply_to_message
    if not replied_msg:
        return

    print(f"🔍 Admin {admin_id} replied to msg_id={replied_msg.id}")
    print(f"📋 Current reply_map: {reply_map}")

    # Lookup user
    user_id = reply_map.get((admin_id, replied_msg.id))
    if not user_id:
        await message.reply(
            "❌ Could not find original user.\n\n"
            "Make sure you're replying to the **exact message** that contains the user's info (ID, name, etc.)"
        )
        return

    # Send reply
    reply_text = message.text or message.caption
    try:
        if reply_text:
            await client.send_message(user_id, f"**📨 Reply from Support:**\n\n{reply_text}", parse_mode="Markdown")
            await message.reply(f"✅ Reply sent to user `{user_id}`")
        elif message.media:
            await message.copy(user_id)
            await message.reply(f"✅ Media sent to user `{user_id}`")
    except Exception as e:
        await message.reply(f"❌ Failed: {e}")
