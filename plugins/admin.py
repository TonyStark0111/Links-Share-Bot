# +++ Modified By [telegram username: @Codeflix_Bots
import os
import asyncio
from config import *
from pyrogram import Client, filters
from pyrogram.types import Message, User, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChatAdminRequired, RPCError
from database.database import set_approval_off, is_approval_off, add_admin, remove_admin, list_admins, add_group, remove_group, get_groups

@Client.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: <code>/addadmin {user_id}</code>")
    user_id = int(message.command[1])
    success = await add_admin(user_id)
    if success:
        await message.reply_text(f"✅ User <code>{user_id}</code> added as admin.")
    else:
        await message.reply_text(f"❌ Failed to add admin <code>{user_id}</code>.")

@Client.on_message(filters.command("deladmin") & filters.user(OWNER_ID))
async def del_admin_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].isdigit():
        return await message.reply_text("Usage: <code>/deladmin {user_id}</code>")
    user_id = int(message.command[1])
    success = await remove_admin(user_id)
    if success:
        await message.reply_text(f"✅ User <code>{user_id}</code> removed from admins.")
    else:
        await message.reply_text(f"❌ Failed to remove admin <code>{user_id}</code>.")

@Client.on_message(filters.command("admins") & filters.user(OWNER_ID))
async def list_admins_command(client, message: Message):
    admins = await list_admins()
    if not admins:
        return await message.reply_text("No admins found.")
    text = "<b>Admin User IDs:</b>\n" + "\n".join([f"<code>{uid}</code>" for uid in admins])
    await message.reply_text(text)


# ============ GROUP MANAGEMENT COMMANDS (NEW) ============

@Client.on_message(filters.command("addgroup") & filters.user(OWNER_ID))
async def add_group_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/addgroup group_id</code>\nExample: <code>/addgroup -1001234567890</code>")
    gid = int(message.command[1])
    success = await add_group(gid)
    if success:
        await message.reply_text(f"✅ Group <code>{gid}</code> added to broadcast list.")
    else:
        await message.reply_text(f"❌ Failed to add group <code>{gid}</code>.")

@Client.on_message(filters.command("delgroup") & filters.user(OWNER_ID))
async def del_group_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/delgroup group_id</code>")
    gid = int(message.command[1])
    success = await remove_group(gid)
    if success:
        await message.reply_text(f"✅ Group <code>{gid}</code> removed from broadcast list.")
    else:
        await message.reply_text(f"❌ Failed to remove group <code>{gid}</code>.")

@Client.on_message(filters.command("listgroups") & filters.user(OWNER_ID))
async def list_groups_command(client, message: Message):
    groups = await get_groups()
    if not groups:
        return await message.reply_text("No groups in database.")
    text = "<b>📋 Stored Groups:</b>\n" + "\n".join([f"<code>{g}</code>" for g in groups])
    await message.reply_text(text)
