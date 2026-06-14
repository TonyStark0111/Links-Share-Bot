import asyncio
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import (
    add_user, save_support_mapping, get_user_id_by_forwarded_msg,
    delete_support_mapping, is_admin
)

@Bot.on_message(filters.private & ~filters.command("start") & ~filters.me)
async def forward_to_admins(client: Bot, message: Message):
    user = message.from_user
    user_id = user.id

    # Add user to DB
    await add_user(user_id)

    # Don't forward messages from admins themselves
    if await is_admin(user_id) or user_id == OWNER_ID:
        return

    # Prepare user info block
    username = f"@{user.username}" if user.username else "No username"
    dc_id = user.dc_id if user.dc_id else "Unknown"
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    mention = user.mention

    info_block = (
        f"<b>📩 New message from user</b>\n"
        f"<b>ID:</b> <code>{user_id}</code>\n"
        f"<b>Name:</b> {first_name} {last_name}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>DC ID:</b> {dc_id}\n"
        f"<b>Mention:</b> {mention}\n"
        f"<b>Message:</b>\n"
        f"<blockquote>{message.text or message.caption or 'Media message'}</blockquote>"
    )

    # Send to every support admin
    for admin_id in SUPPORT_ADMINS:
        try:
            # Send info block to this admin
            forwarded_info = await client.send_message(
                chat_id=admin_id,
                text=info_block,
                parse_mode="HTML"
            )

            # Store mapping for this admin's forwarded message
            await save_support_mapping(admin_id, forwarded_info.id, user_id)

            # If message has media, forward it separately
            if message.media:
                await message.copy(admin_id)

        except Exception as e:
            print(f"Failed to forward to admin {admin_id}: {e}")

    # Notify user that message was sent (optional)
    try:
        await message.reply(
            "<i>Your message has been forwarded to the admins. You will receive a reply here.</i>",
            parse_mode="HTML"
        )
    except:
        pass

@Bot.on_message(filters.private & filters.reply & ~filters.me)
async def admin_reply_to_user(client: Bot, message: Message):
    """Handle replies from admins to forwarded messages."""
    admin_id = message.from_user.id

    # Only admins can reply
    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID and not await is_admin(admin_id):
        return

    replied_msg_id = message.reply_to_message_id
    user_id = await get_user_id_by_forwarded_msg(admin_id, replied_msg_id)

    if not user_id:
        # Not a tracked forward, ignore
        return

    # Admin's reply content
    reply_text = message.text or message.caption
    if reply_text:
        reply_with_header = f"<b>📨 Reply from Admin:</b>\n\n{reply_text}"
        try:
            await client.send_message(user_id, reply_with_header, parse_mode="HTML")
            await message.reply(f"<i>Reply sent to user <code>{user_id}</code>.</i>", parse_mode="HTML")
        except Exception as e:
            await message.reply(f"<i>Failed to send reply: {e}</i>", parse_mode="HTML")
            if "blocked" in str(e).lower():
                await delete_support_mapping(admin_id, replied_msg_id)
    elif message.media:
        # Forward media directly
        try:
            await message.copy(user_id)
            await message.reply(f"<i>Media forwarded to user <code>{user_id}</code>.</i>", parse_mode="HTML")
        except Exception as e:
            await message.reply(f"<i>Failed to send media: {e}</i>", parse_mode="HTML")
            if "blocked" in str(e).lower():
                await delete_support_mapping(admin_id, replied_msg_id)
    else:
        await message.reply("<i>No content to reply with.</i>", parse_mode="HTML")
