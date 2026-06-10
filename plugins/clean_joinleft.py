# plugins/clean_joinleft.py

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message
from database.database import get_global_clean_joinleft, set_global_clean_joinleft
from helper_func import is_owner_or_admin

@Client.on_message(filters.group & (filters.new_chat_members | filters.left_chat_member))
async def clean_joinleft(client: Client, message: Message):
    """Delete join/left messages globally if feature is enabled."""
    # Check global toggle
    if not await get_global_clean_joinleft():
        return

    chat_id = message.chat.id

    # Check if bot can delete messages
    try:
        bot_me = await client.get_me()
        bot_member = await client.get_chat_member(chat_id, bot_me.id)
        
        if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return

        if bot_member.status == ChatMemberStatus.ADMINISTRATOR and not bot_member.can_delete_messages:
            return

        # Delete the join/left message
        await message.delete()
        print(f"Deleted join/left message in {chat_id}")
    except Exception as e:
        print(f"Failed to delete join/left message in {chat_id}: {e}")


@Client.on_message(filters.private & filters.command("setcleanjoin") & is_owner_or_admin)
async def set_clean_joinleft_global(client: Client, message: Message):
    """Owner or admin command to globally enable/disable clean join/left."""
    if len(message.command) != 2:
        await message.reply_text(
            "<b>Usage:</b>\n"
            "<code>/setcleanjoin on</code> - Enable auto-deletion of join/left messages\n"
            "<code>/setcleanjoin off</code> - Disable auto-deletion",
            parse_mode="HTML"
        )
        return

    arg = message.command[1].lower()
    
    if arg == "on":
        await set_global_clean_joinleft(True)
        await message.reply_text(
            "✅ <b>Global clean join/left is now ENABLED</b>\n\n"
            "All join/left messages in groups will be deleted automatically.\n"
            "Note: Bot must be admin with delete permission in each group.",
            parse_mode="HTML"
        )
    elif arg == "off":
        await set_global_clean_joinleft(False)
        await message.reply_text(
            "❌ <b>Global clean join/left is now DISABLED</b>\n\n"
            "Join/left messages will stay in groups.",
            parse_mode="HTML"
        )
    else:
        await message.reply_text(
            "Invalid argument. Use <code>on</code> or <code>off</code>.",
            parse_mode="HTML"
        )
