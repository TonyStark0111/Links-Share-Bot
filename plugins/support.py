import asyncio
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user, save_support_mapping, get_user_id_by_forwarded_msg

@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admin(client: Bot, message: Message):
    """Forward user message (text or media) to all admins as a single message with user info in caption."""
    user = message.from_user
    user_id = user.id

    await add_user(user_id)

    # Don't forward messages from admins themselves
    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return

    # Prepare user info block (plain text, no HTML)
    username = f"@{user.username}" if user.username else "No username"
    user_info = (
        f"📨 New message from user\n\n"
        f"ID: `{user_id}`\n"
        f"Name: {user.first_name or ''} {user.last_name or ''}\n"
        f"Username: {username}\n"
        f"DC: {user.dc_id or 'Unknown'}\n"
    )

    # Add user's message content
    if message.text:
        user_info += f"\nMessage:\n{message.text}"
    elif message.caption:
        user_info += f"\nCaption:\n{message.caption}"

    # Send a single message to each admin
    for admin_id in SUPPORT_ADMINS:
        try:
            if message.media:
                # Send the media with user_info as caption
                sent = await message.copy(
                    admin_id,
                    caption=user_info,
                    parse_mode=None  # avoid parse errors
                )
            else:
                # Send text message with user_info as text
                sent = await client.send_message(admin_id, user_info)

            # Store mapping: admin_id, sent message id -> user_id
            await save_support_mapping(admin_id, sent.id, user_id)

        except Exception as e:
            print(f"Failed to forward to admin {admin_id}: {e}")

    # Acknowledge user
    try:
        await message.reply(
            "✅ Your message has been forwarded to support. You'll receive a reply here."
        )
    except:
        pass


@Bot.on_message(filters.private & filters.reply)
async def reply_to_user(client: Bot, message: Message):
    """When admin replies to a forwarded message, send the reply back to original user."""
    admin_id = message.from_user.id

    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return

    replied_msg = message.reply_to_message
    if not replied_msg:
        return

    # Get original user from mapping
    user_id = await get_user_id_by_forwarded_msg(admin_id, replied_msg.id)
    if not user_id:
        await message.reply("❌ Could not find the original user. Make sure you replied to the message containing user info.")
        return

    # Send reply to user
    reply_text = message.text or message.caption
    try:
        if reply_text:
            await client.send_message(
                user_id,
                f"📨 Reply from Support:\n\n{reply_text}"
            )
            await message.reply(f"✅ Reply sent to user `{user_id}`")
        elif message.media:
            await message.copy(user_id)
            await message.reply(f"✅ Media sent to user `{user_id}`")
    except Exception as e:
        await message.reply(f"❌ Failed to send: {e}")
