import asyncio
import base64
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from helper_func import is_owner_or_admin
from database.database import (
    get_global_channels, add_global_channel, remove_global_channel,
    save_encoded_link, get_channel_by_encoded_link, get_original_link,
    save_invite_link, get_current_invite_link, get_link_creation_time
)
from bot import Bot
from config import OWNER_ID

# Store temporary data for pagination
temp_data = {}

# ============ CHANNEL MANAGEMENT ============

@Bot.on_message(filters.command("addch") & filters.private & is_owner_or_admin)
async def add_channel_cmd(client: Bot, message: Message):
    """Add a channel to the bot (auto adds -100 prefix)"""
    if len(message.command) != 2:
        await message.reply("Usage: `/addch 96022547` or `/addch -10096022547`")
        return
    
    input_id = message.command[1]
    try:
        if input_id.isdigit():
            channel_id = int(f"-100{input_id}")
            await message.reply(f"🔄 Auto-converted `{input_id}` → `{channel_id}`")
        else:
            channel_id = int(input_id)
        
        # Try to get chat to verify bot is admin
        try:
            chat = await client.get_chat(channel_id)
            member = await client.get_chat_member(channel_id, (await client.get_me()).id)
            if member.status not in ["administrator", "creator"]:
                await message.reply(f"❌ Bot is not admin in {chat.title}. Please add bot as admin first.")
                return
        except Exception as e:
            await message.reply(f"❌ Cannot access channel. Make sure bot is admin.\nError: {e}")
            return
        
        if await add_global_channel(channel_id):
            # Generate encoded link for the channel
            encoded = await save_encoded_link(channel_id)
            await message.reply(
                f"✅ **Channel Added Successfully!**\n\n"
                f"**Name:** {chat.title}\n"
                f"**ID:** `{channel_id}`\n"
                f"**Encoded Link:** `{encoded}`\n\n"
                f"Use this link in your posts: `https://t.me/{client.username}?start={encoded}`"
            )
        else:
            await message.reply("❌ Failed to add channel. It may already exist.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@Bot.on_message(filters.command("delch") & filters.private & is_owner_or_admin)
async def del_channel_cmd(client: Bot, message: Message):
    """Remove a channel from the bot"""
    if len(message.command) != 2:
        await message.reply("Usage: `/delch -10096022547`")
        return
    
    try:
        channel_id = int(message.command[1])
        if await remove_global_channel(channel_id):
            await message.reply(f"✅ Channel `{channel_id}` removed successfully.")
        else:
            await message.reply("❌ Channel not found.")
    except:
        await message.reply("Invalid channel ID.")

@Bot.on_message(filters.command("channels") & filters.private & is_owner_or_admin)
async def list_channels_cmd(client: Bot, message: Message):
    """Show all connected channels as buttons (paginated)"""
    channels = await get_global_channels()
    if not channels:
        await message.reply("❌ No channels found.\n\nAdd channels with: `/addch 96022547`")
        return
    
    user_id = message.from_user.id
    temp_data[user_id] = {"channels": channels, "page": 0}
    
    loading = await message.reply("🔄 Loading channels...")
    await send_channel_list(client, message.chat.id, user_id, loading.id)

async def send_channel_list(client: Bot, chat_id: int, user_id: int, edit_msg_id: int = None):
    session = temp_data.get(user_id)
    if not session:
        return
    
    channels = session["channels"]
    page = session["page"]
    per_page = 10
    total_pages = (len(channels) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_channels = channels[start:end]
    
    buttons = []
    for cid in page_channels:
        try:
            chat = await client.get_chat(cid)
            name = chat.title[:35]
            buttons.append([InlineKeyboardButton(f"📢 {name}", callback_data=f"ch_info_{cid}")])
        except:
            buttons.append([InlineKeyboardButton(f"⚠️ Unknown ({cid})", callback_data=f"ch_info_{cid}")])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data="ch_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data="ch_next"))
    if nav:
        buttons.append(nav)
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="ch_close")])
    
    text = f"**📡 Your Channels (Page {page+1}/{total_pages})**\n\n"
    text += f"Total: {len(channels)} channels\n"
    text += "Click on a channel to see its invite link."
    
    try:
        await client.edit_message_text(chat_id, edit_msg_id, text, reply_markup=InlineKeyboardMarkup(buttons))
    except:
        msg = await client.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))
        temp_data[user_id]["msg_id"] = msg.id

@Bot.on_callback_query(filters.regex(r"^(ch_|ch_info_)"))
async def channel_callbacks(client: Bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    if data == "ch_prev":
        if user_id in temp_data:
            temp_data[user_id]["page"] -= 1
            await send_channel_list(client, query.message.chat.id, user_id, query.message.id)
        await query.answer()
    
    elif data == "ch_next":
        if user_id in temp_data:
            temp_data[user_id]["page"] += 1
            await send_channel_list(client, query.message.chat.id, user_id, query.message.id)
        await query.answer()
    
    elif data == "ch_close":
        if user_id in temp_data:
            del temp_data[user_id]
        await query.message.delete()
        await query.answer()
    
    elif data.startswith("ch_info_"):
        channel_id = int(data.split("_")[2])
        try:
            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                expire_date=datetime.now() + timedelta(minutes=10),
                creates_join_request=False
            )
            link = invite.invite_link
            
            encoded = base64.urlsafe_b64encode(str(channel_id).encode()).decode()
            start_link = f"https://t.me/{client.username}?start={encoded}"
            
            await query.message.reply(
                f"**Channel Invite Link**\n\n"
                f"**Direct Join Link:**\n{link}\n\n"
                f"**Bot Share Link:**\n{start_link}\n\n"
                f"⚠️ Link expires in 10 minutes."
            )
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)
        await query.answer()

# ============ LINKS COMMAND ============

@Bot.on_message(filters.command("links") & filters.private & is_owner_or_admin)
async def show_links_cmd(client: Bot, message: Message):
    """Show all channel links as text (paginated)"""
    channels = await get_global_channels()
    if not channels:
        await message.reply("No channels found.")
        return
    
    user_id = message.from_user.id
    temp_data[user_id] = {"channels": channels, "page": 0, "mode": "links"}
    
    loading = await message.reply("🔄 Generating links...")
    await send_links_list(client, message.chat.id, user_id, loading.id)

async def send_links_list(client: Bot, chat_id: int, user_id: int, edit_msg_id: int = None):
    session = temp_data.get(user_id)
    if not session or session.get("mode") != "links":
        return
    
    channels = session["channels"]
    page = session["page"]
    per_page = 5
    total_pages = (len(channels) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_channels = channels[start:end]
    
    text = f"**🔗 Channel Links (Page {page+1}/{total_pages})**\n\n"
    for cid in page_channels:
        try:
            chat = await client.get_chat(cid)
            invite = await client.create_chat_invite_link(
                chat_id=cid,
                expire_date=datetime.now() + timedelta(minutes=10),
                creates_join_request=False
            )
            link = invite.invite_link
            text += f"**{chat.title}**\n`{link}`\n\n"
        except Exception as e:
            text += f"**Unknown ({cid})**\nError: {e}\n\n"
    
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data="links_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data="links_next"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="links_close")])
    
    try:
        await client.edit_message_text(chat_id, edit_msg_id, text, reply_markup=InlineKeyboardMarkup(buttons))
    except:
        msg = await client.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))
        temp_data[user_id]["msg_id"] = msg.id

@Bot.on_callback_query(filters.regex(r"^links_(prev|next|close)$"))
async def links_callbacks(client: Bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    if data == "links_prev":
        if user_id in temp_data and temp_data[user_id].get("mode") == "links":
            temp_data[user_id]["page"] -= 1
            await send_links_list(client, query.message.chat.id, user_id, query.message.id)
        await query.answer()
    
    elif data == "links_next":
        if user_id in temp_data and temp_data[user_id].get("mode") == "links":
            temp_data[user_id]["page"] += 1
            await send_links_list(client, query.message.chat.id, user_id, query.message.id)
        await query.answer()
    
    elif data == "links_close":
        if user_id in temp_data:
            del temp_data[user_id]
        await query.message.delete()
        await query.answer()

# ============ REQLINK COMMAND ============

@Bot.on_message(filters.command("reqlink") & filters.private & is_owner_or_admin)
async def show_reqlinks_cmd(client: Bot, message: Message):
    """Show all request links for channels (paginated)"""
    channels = await get_global_channels()
    if not channels:
        await message.reply("No channels found.")
        return
    
    user_id = message.from_user.id
    temp_data[user_id] = {"channels": channels, "page": 0, "mode": "reqlinks"}
    
    loading = await message.reply("🔄 Generating request links...")
    await send_reqlinks_list(client, message.chat.id, user_id, loading.id)

async def send_reqlinks_list(client: Bot, chat_id: int, user_id: int, edit_msg_id: int = None):
    session = temp_data.get(user_id)
    if not session or session.get("mode") != "reqlinks":
        return
    
    channels = session["channels"]
    page = session["page"]
    per_page = 5
    total_pages = (len(channels) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_channels = channels[start:end]
    
    text = f"**📝 Request Links (Page {page+1}/{total_pages})**\n\n"
    for cid in page_channels:
        try:
            chat = await client.get_chat(cid)
            invite = await client.create_chat_invite_link(
                chat_id=cid,
                expire_date=datetime.now() + timedelta(minutes=10),
                creates_join_request=True
            )
            link = invite.invite_link
            
            encoded = base64.urlsafe_b64encode(str(cid).encode()).decode()
            start_link = f"https://t.me/{client.username}?start=req_{encoded}"
            
            text += f"**{chat.title}**\nInvite: `{link}`\nBot Link: `{start_link}`\n\n"
        except Exception as e:
            text += f"**Unknown ({cid})**\nError: {e}\n\n"
    
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data="req_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data="req_next"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="req_close")])
    
    try:
        await client.edit_message_text(chat_id, edit_msg_id, text, reply_markup=InlineKeyboardMarkup(buttons))
    except:
        msg = await client.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))
        temp_data[user_id]["msg_id"] = msg.id

@Bot.on_callback_query(filters.regex(r"^req_(prev|next|close)$"))
async def reqlinks_callbacks(client: Bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    if data == "req_prev":
        if user_id in temp_data and temp_data[user_id].get("mode") == "reqlinks":
            temp_data[user_id]["page"] -= 1
            await send_reqlinks_list(client, query.message.chat.id, user_id, query.message.id)
        await query.answer()
    
    elif data == "req_next":
        if user_id in temp_data and temp_data[user_id].get("mode") == "reqlinks":
            temp_data[user_id]["page"] += 1
            await send_reqlinks_list(client, query.message.chat.id, user_id, query.message.id)
        await query.answer()
    
    elif data == "req_close":
        if user_id in temp_data:
            del temp_data[user_id]
        await query.message.delete()
        await query.answer()

# ============ BULKLINK COMMAND ============

@Bot.on_message(filters.command("bulklink") & filters.private & is_owner_or_admin)
async def bulk_link_cmd(client: Bot, message: Message):
    """Generate links for multiple channel IDs at once"""
    args = message.command[1:]
    if not args:
        await message.reply("Usage: `/bulklink -1001234567890 -1009876543210`\nOr: `/bulklink 96022547 96022548`")
        return
    
    channel_ids = []
    for arg in args:
        try:
            if arg.isdigit():
                cid = int(f"-100{arg}")
                await message.reply(f"🔄 Auto-converted `{arg}` → `{cid}`")
            else:
                cid = int(arg)
            channel_ids.append(cid)
        except:
            await message.reply(f"❌ Invalid ID: {arg}")
            return
    
    await message.reply(f"🔄 Generating links for {len(channel_ids)} channels...")
    
    result_text = "**🔗 Bulk Generated Links**\n\n"
    for cid in channel_ids:
        try:
            chat = await client.get_chat(cid)
            invite = await client.create_chat_invite_link(
                chat_id=cid,
                expire_date=datetime.now() + timedelta(minutes=10),
                creates_join_request=False
            )
            encoded = base64.urlsafe_b64encode(str(cid).encode()).decode()
            start_link = f"https://t.me/{client.username}?start={encoded}"
            result_text += f"**{chat.title}**\nInvite: `{invite.invite_link}`\nBot Link: `{start_link}`\n\n"
        except Exception as e:
            result_text += f"**ID {cid}**\nError: {e}\n\n"
    
    if len(result_text) > 4000:
        parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
        for part in parts:
            await message.reply(part)
    else:
        await message.reply(result_text)

# ============ STATS COMMAND ============

@Bot.on_message(filters.command("stats") & filters.private & filters.user(OWNER_ID))
async def stats_cmd(client: Bot, message: Message):
    from database.database import full_userbase
    from helper_func import get_readable_time
    
    users = await full_userbase()
    channels = await get_global_channels()
    now = datetime.now()
    delta = now - client.uptime
    uptime = get_readable_time(delta.seconds)
    
    await message.reply(
        f"**📊 Bot Statistics**\n\n"
        f"👥 **Users:** `{len(users)}`\n"
        f"📺 **Channels:** `{len(channels)}`\n"
        f"⏱️ **Uptime:** `{uptime}`\n"
        f"🤖 **Bot:** @{client.username}"
    )

# ============ HELP COMMAND ============

@Bot.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Bot, message: Message):
    help_text = """
**📚 LinkShareBot Help**

**Channel Management:**
/addch <id> - Add channel (auto -100 prefix)
/delch <id> - Remove channel
/channels - List all channels
/links - Show all channel links
/reqlink - Show request links
/bulklink <id1> <id2> - Generate multiple links

**Broadcast:**
/grp_broadcast - Broadcast to groups
/channel_broadcast - Broadcast to channels
/addgroup <id> - Add group to broadcast list
/addchannel <id> - Add channel to broadcast list
/listgroups - List broadcast groups
/listchannels - List broadcast channels
/cancel - Cancel broadcast

**Admin:**
/status - Bot status
/stats - Bot statistics
/broadcast - Message all users
/addadmin <id> - Add admin
/deladmin <id> - Remove admin
/admins - List admins

**Auto Approve:**
/reqtime <sec> - Set approval timer
/reqmode on/off - Toggle auto approval
/approveon <id> - Enable for channel
/approveoff <id> - Disable for channel
"""
    await message.reply(help_text)

# ============ ABOUT COMMAND ============

@Bot.on_message(filters.command("about") & filters.private)
async def about_cmd(client: Bot, message: Message):
    about_text = f"""
**🤖 About LinkShareBot**

**Version:** 2.0
**Creator:** [Yato](https://t.me/ProYato)
**Support:** @CodeflixSupport

A powerful Telegram bot to share channel links securely with auto-expiring invite links.

**Features:**
• Auto-expiring invite links (10 min)
• Request join links support
• Bulk link generation
• Force subscription
• Broadcast to groups/channels
• Auto-approve join requests

**Source:** [GitHub](https://github.com/yourusername/LinkShareBot)
"""
    await message.reply(about_text, disable_web_page_preview=True)
