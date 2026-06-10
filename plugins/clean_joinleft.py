# plugins/clean_joinleft.py

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from database.database import set_clean_joinleft, get_clean_joinleft
from helper_func import is_owner_or_admin

@Client.on_message(filters.group & (filters.new_chat_members | filters.left_chat_member))
async def clean_joinleft(client: Client, message: Message):
    """Delete join/left messages if enabled in the group."""
    chat_id = message.chat.id

    # Check if feature is enabled for this chat
    if not await get_clean_joinleft(chat_id):
        return

    # Check if bot can delete messages
    bot_member = await client.get_chat_member(chat_id, (await client.get_me()).id)
    if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return  # Bot can't delete

    # Check if bot has delete permission
    if bot_member.status == ChatMemberStatus.ADMINISTRATOR and not bot_member.can_delete_messages:
        return

    # Delete the join/left message
    try:
        await message.delete()
        print(f"Deleted join/left message in {chat_id} from {message.from_user.id if message.from_user else 'unknown'}")
    except Exception as e:
        print(f"Failed to delete join/left message in {chat_id}: {e}")


@Client.on_message(filters.command("cleanjoin") & filters.group & is_owner_or_admin)
async def toggle_clean_joinleft(client: Client, message: Message):
    """Toggle the auto-delete feature for this group (admin only)."""
    chat_id = message.chat.id
    if len(message.command) == 2:
        arg = message.command[1].lower()
        if arg in ["on", "off"]:
            enabled = (arg == "on")
            await set_clean_joinleft(chat_id, enabled)
            status = "enabled ✅" if enabled else "disabled ❌"
            await message.reply_text(f"Auto-deletion of join/left messages is now {status}.")
            return
    # If no valid argument, show current status
    current = await get_clean_joinleft(chat_id)
    status = "enabled ✅" if current else "disabled ❌"
    await message.reply_text(
        f"Current status: {status}\n"
        f"Usage: `/cleanjoin on` or `/cleanjoin off`",
        parse_mode="markdown"
    )
