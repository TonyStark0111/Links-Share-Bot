# +++ Modified By [telegram username: @Codeflix_Bots
import os
import asyncio
from config import *
from pyrogram import Client, filters
from pyrogram.types import Message, User, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, ChatAdminRequired, RPCError
from database.database import (
    set_approval_off, is_approval_off, 
    add_admin, remove_admin, list_admins, 
    add_group, remove_group, get_groups,
    add_global_group, remove_global_group, get_global_groups,
    add_global_channel, remove_global_channel, get_global_channels
)

# ============ ADMIN MANAGEMENT ============

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

# ============ GLOBAL GROUP MANAGEMENT (for broadcast) ============

@Client.on_message(filters.command("addgroup") & filters.user(OWNER_ID))
async def add_global_group_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/addgroup group_id</code>\nExample: <code>/addgroup -1001234567890</code>")
    gid = int(message.command[1])
    success = await add_global_group(gid)
    if success:
        total = len(await get_global_groups())
        await message.reply_text(f"✅ Group <code>{gid}</code> added to global broadcast list.\nTotal groups: {total}")
    else:
        await message.reply_text(f"❌ Failed to add group <code>{gid}</code>.")

@Client.on_message(filters.command("delgroup") & filters.user(OWNER_ID))
async def del_global_group_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/delgroup group_id</code>")
    gid = int(message.command[1])
    success = await remove_global_group(gid)
    if success:
        total = len(await get_global_groups())
        await message.reply_text(f"✅ Group <code>{gid}</code> removed from global broadcast list.\nTotal groups: {total}")
    else:
        await message.reply_text(f"❌ Failed to remove group <code>{gid}</code>.")

@Client.on_message(filters.command("listgroups") & filters.user(OWNER_ID))
async def list_global_groups_command(client, message: Message):
    groups = await get_global_groups()
    if not groups:
        return await message.reply_text("No groups in global broadcast list.\n\nGroups are auto-added when users message the bot.\nOr add manually with /addgroup")
    
    text = "<b>📡 Global Broadcast Groups:</b>\n\n"
    for gid in groups:
        try:
            chat = await client.get_chat(gid)
            member_count = getattr(chat, 'members_count', '?')
            text += f"• {chat.title}\n  <code>{gid}</code> | Members: {member_count}\n\n"
        except Exception:
            text += f"• Unknown Group\n  <code>{gid}</code>\n\n"
    
    if len(text) > 4000:
        await message.reply_text("Too many groups! Use /grp_broadcast menu instead.")
    else:
        await message.reply_text(text)

# ============ GLOBAL CHANNEL MANAGEMENT (for broadcast) ============

@Client.on_message(filters.command("addchannel") & filters.user(OWNER_ID))
async def add_global_channel_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/addchannel channel_id</code>\nExample: <code>/addchannel -1001234567890</code>")
    cid = int(message.command[1])
    success = await add_global_channel(cid)
    if success:
        total = len(await get_global_channels())
        await message.reply_text(f"✅ Channel <code>{cid}</code> added to global broadcast list.\nTotal channels: {total}")
    else:
        await message.reply_text(f"❌ Failed to add channel <code>{cid}</code>.")

@Client.on_message(filters.command("delchannel") & filters.user(OWNER_ID))
async def del_global_channel_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/delchannel channel_id</code>")
    cid = int(message.command[1])
    success = await remove_global_channel(cid)
    if success:
        total = len(await get_global_channels())
        await message.reply_text(f"✅ Channel <code>{cid}</code> removed from global broadcast list.\nTotal channels: {total}")
    else:
        await message.reply_text(f"❌ Failed to remove channel <code>{cid}</code>.")

@Client.on_message(filters.command("listchannels") & filters.user(OWNER_ID))
async def list_global_channels_command(client, message: Message):
    channels = await get_global_channels()
    if not channels:
        return await message.reply_text("No channels in global broadcast list.\n\nAdd channels with /addchannel")
    
    text = "<b>📡 Global Broadcast Channels:</b>\n\n"
    for cid in channels:
        try:
            chat = await client.get_chat(cid)
            text += f"• {chat.title}\n  <code>{cid}</code>\n\n"
        except Exception:
            text += f"• Unknown Channel\n  <code>{cid}</code>\n\n"
    
    if len(text) > 4000:
        await message.reply_text("Too many channels! Use /channel_broadcast menu instead.")
    else:
        await message.reply_text(text)

# ============ LEGACY GROUP MANAGEMENT (for old system - kept for compatibility) ============

@Client.on_message(filters.command("addoldgroup") & filters.user(OWNER_ID))
async def add_group_command_legacy(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/addoldgroup group_id</code>\nExample: <code>/addoldgroup -1001234567890</code>")
    gid = int(message.command[1])
    success = await add_group(gid)
    if success:
        await message.reply_text(f"✅ Group <code>{gid}</code> added to legacy broadcast list.")
    else:
        await message.reply_text(f"❌ Failed to add group <code>{gid}</code>.")

@Client.on_message(filters.command("deloldgroup") & filters.user(OWNER_ID))
async def del_group_command_legacy(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/deloldgroup group_id</code>")
    gid = int(message.command[1])
    success = await remove_group(gid)
    if success:
        await message.reply_text(f"✅ Group <code>{gid}</code> removed from legacy broadcast list.")
    else:
        await message.reply_text(f"❌ Failed to remove group <code>{gid}</code>.")

@Client.on_message(filters.command("listoldgroups") & filters.user(OWNER_ID))
async def list_groups_command_legacy(client, message: Message):
    groups = await get_groups()
    if not groups:
        return await message.reply_text("No groups in legacy database.")
    text = "<b>📋 Legacy Stored Groups:</b>\n" + "\n".join([f"<code>{g}</code>" for g in groups])
    await message.reply_text(text)

# ============ AUTO-APPROVAL MANAGEMENT ============

@Client.on_message(filters.command("approveoff") & filters.user(OWNER_ID))
async def approve_off_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/approveoff {channel_id}</code>")
    channel_id = int(message.command[1])
    success = await set_approval_off(channel_id, True)
    if success:
        await message.reply_text(f"✅ Auto-approval is now <b>OFF</b> for channel <code>{channel_id}</code>.")
    else:
        await message.reply_text(f"❌ Failed to set auto-approval OFF for channel <code>{channel_id}</code>.")

@Client.on_message(filters.command("approveon") & filters.user(OWNER_ID))
async def approve_on_command(client, message: Message):
    if len(message.command) != 2 or not message.command[1].lstrip("-").isdigit():
        return await message.reply_text("Usage: <code>/approveon {channel_id}</code>")
    channel_id = int(message.command[1])
    success = await set_approval_off(channel_id, False)
    if success:
        await message.reply_text(f"✅ Auto-approval is now <b>ON</b> for channel <code>{channel_id}</code>.")
    else:
        await message.reply_text(f"❌ Failed to set auto-approval ON for channel <code>{channel_id}</code>.")
