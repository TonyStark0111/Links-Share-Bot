import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from helper_func import is_owner_or_admin
from database.database import (
    get_global_groups, add_global_group, remove_global_group,
    get_global_channels, add_global_channel, remove_global_channel
)

# Store sessions
user_sessions = {}

def fix_id(id_value):
    id_str = str(id_value).strip()
    if id_str.startswith('-'):
        return int(id_str)
    try:
        num = int(id_str)
        if num > 0:
            return int(f"-100{num}")
        return num
    except:
        return id_value

# ============ MAIN BROADCAST COMMANDS ============

@Client.on_message(filters.command("grp_broadcast") & filters.private & is_owner_or_admin)
async def grp_broadcast_cmd(client: Client, message: Message):
    await show_broadcast_list(client, message, "group")

@Client.on_message(filters.command("channel_broadcast") & filters.private & is_owner_or_admin)
async def channel_broadcast_cmd(client: Client, message: Message):
    await show_broadcast_list(client, message, "channel")

async def show_broadcast_list(client: Client, message: Message, chat_type: str):
    user_id = message.from_user.id
    
    # Get items from database
    if chat_type == "group":
        items = await get_global_groups()
    else:
        items = await get_global_channels()
    
    if not items:
        await message.reply(
            f"❌ No {chat_type}s in list.\n\n"
            f"Use /add{chat_type} 96022547 to add."
        )
        return
    
    # Create session
    user_sessions[user_id] = {
        "type": chat_type,
        "items": items,
        "selected": set(),
        "page": 0,
        "step": "menu",  # menu, waiting_content, waiting_add
        "send_all": False,
        "content_msg": None
    }
    
    await send_menu(client, message.chat.id, user_id)

async def send_menu(client: Client, chat_id: int, user_id: int, edit_msg_id: int = None):
    session = user_sessions.get(user_id)
    if not session:
        return
    
    items = session["items"]
    page = session["page"]
    per_page = 10
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    start = page * per_page
    end = start + per_page
    page_items = items[start:end]
    
    buttons = []
    
    # Add items with checkboxes
    for item_id in page_items:
        try:
            chat = await client.get_chat(item_id)
            name = chat.title[:35]
        except Exception:
            name = f"Unknown ({item_id})"
        
        is_selected = "✅" if item_id in session["selected"] else "⬜"
        buttons.append([InlineKeyboardButton(f"{is_selected} {name}", callback_data=f"bc_toggle_{session['type']}_{item_id}")])
    
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"bc_prev_{session['type']}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"bc_next_{session['type']}"))
    if nav_row:
        buttons.append(nav_row)
    
    # Action buttons
    action_row = []
    if session["selected"]:
        action_row.append(InlineKeyboardButton(f"📢 Send Selected ({len(session['selected'])})", callback_data=f"bc_selected_{session['type']}"))
    action_row.append(InlineKeyboardButton(f"📢 Send ALL ({len(items)})", callback_data=f"bc_all_{session['type']}"))
    action_row.append(InlineKeyboardButton("❌ Cancel", callback_data=f"bc_cancel_{session['type']}"))
    buttons.append(action_row)
    
    # Management
    buttons.append([
        InlineKeyboardButton("➕ Add", callback_data=f"bc_add_{session['type']}"),
        InlineKeyboardButton("🗑️ Remove", callback_data=f"bc_remove_{session['type']}"),
        InlineKeyboardButton("🔄 Refresh", callback_data=f"bc_refresh_{session['type']}")
    ])
    
    text = f"**📡 SELECT {session['type'].upper()}S TO BROADCAST**\n\n"
    text += f"Selected: **{len(session['selected'])}** | Total: **{len(items)}**\n"
    text += f"Page **{page + 1}** of **{total_pages}**\n\n"
    text += "⬜ = Not selected | ✅ = Selected\n"
    text += "Click on an item to select/unselect it.\n\n"
    text += "After selecting, click **'Send Selected'** or **'Send ALL'**."
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if edit_msg_id:
        try:
            await client.edit_message_text(chat_id, edit_msg_id, text, reply_markup=reply_markup)
        except:
            msg = await client.send_message(chat_id, text, reply_markup=reply_markup)
            session["menu_msg_id"] = msg.id
            session["menu_chat_id"] = chat_id
    else:
        if "menu_msg_id" in session:
            try:
                await client.edit_message_text(session["menu_chat_id"], session["menu_msg_id"], text, reply_markup=reply_markup)
            except:
                msg = await client.send_message(chat_id, text, reply_markup=reply_markup)
                session["menu_msg_id"] = msg.id
                session["menu_chat_id"] = chat_id
        else:
            msg = await client.send_message(chat_id, text, reply_markup=reply_markup)
            session["menu_msg_id"] = msg.id
            session["menu_chat_id"] = chat_id

# ============ CALLBACK HANDLER ============

@Client.on_callback_query()
async def handle_broadcast_callback(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    # Only handle our broadcast callbacks
    if not data.startswith("bc_"):
        return
    
    session = user_sessions.get(user_id)
    if not session:
        await query.answer("Session expired! Use /grp_broadcast or /channel_broadcast again.", show_alert=True)
        await query.message.delete()
        return
    
    parts = data.split("_")
    action = parts[1]
    chat_type = parts[2] if len(parts) > 2 else None
    
    # ========== TOGGLE SELECTION ==========
    if action == "toggle" and chat_type:
        item_id = int(parts[3])
        if item_id in session["selected"]:
            session["selected"].remove(item_id)
        else:
            session["selected"].add(item_id)
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer()
    
    # ========== PAGINATION ==========
    elif action == "prev" and chat_type:
        session["page"] -= 1
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer()
    
    elif action == "next" and chat_type:
        session["page"] += 1
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer()
    
    # ========== REFRESH ==========
    elif action == "refresh" and chat_type:
        if chat_type == "group":
            session["items"] = await get_global_groups()
        else:
            session["items"] = await get_global_channels()
        session["selected"] = set()
        session["page"] = 0
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer("List refreshed!", show_alert=True)
    
    # ========== SEND TO SELECTED ==========
    elif action == "selected" and chat_type:
        if not session["selected"]:
            await query.answer("No items selected! Click on items to select them.", show_alert=True)
            return
        session["send_all"] = False
        session["step"] = "waiting_content"
        await query.message.edit_text(
            f"**📢 BROADCAST TO SELECTED {chat_type.upper()}S**\n\n"
            f"Selected: **{len(session['selected'])}**\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # ========== SEND TO ALL ==========
    elif action == "all" and chat_type:
        session["send_all"] = True
        session["step"] = "waiting_content"
        await query.message.edit_text(
            f"**📢 BROADCAST TO ALL {chat_type.upper()}S**\n\n"
            f"Total: **{len(session['items'])}**\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # ========== CANCEL ==========
    elif action == "cancel" and chat_type:
        if user_id in user_sessions:
            del user_sessions[user_id]
        await query.message.edit_text("❌ Broadcast cancelled.")
        await query.answer()
    
    # ========== ADD ITEM ==========
    elif action == "add" and chat_type:
        session["step"] = "waiting_add"
        await query.message.edit_text(
            f"**➕ ADD NEW {chat_type.upper()}**\n\n"
            f"Send the {chat_type} ID to add:\n"
            f"Example: `96022547` (auto adds -100 prefix)\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # ========== REMOVE ITEM - SHOW LIST ==========
    elif action == "remove" and chat_type:
        items = session["items"]
        if not items:
            await query.answer(f"No {chat_type}s to remove!", show_alert=True)
            return
        
        buttons = []
        for item_id in items:
            try:
                chat = await client.get_chat(item_id)
                name = chat.title[:30]
            except Exception:
                name = f"Unknown ({item_id})"
            buttons.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"bc_remove_confirm_{chat_type}_{item_id}")])
        
        buttons.append([InlineKeyboardButton("◀️ Back to List", callback_data=f"bc_back_{chat_type}")])
        
        await query.message.edit_text(
            f"**🗑️ REMOVE {chat_type.upper()}**\n\nClick on an item to remove it:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
    
    # ========== CONFIRM REMOVE ==========
    elif action == "remove_confirm" and chat_type:
        item_id = int(parts[3])
        if chat_type == "group":
            await remove_global_group(item_id)
            session["items"] = await get_global_groups()
        else:
            await remove_global_channel(item_id)
            session["items"] = await get_global_channels()
        session["selected"].discard(item_id)
        session["page"] = 0
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer(f"✅ {chat_type.capitalize()} removed!", show_alert=True)
    
    # ========== BACK TO MENU ==========
    elif action == "back" and chat_type:
        session["step"] = "menu"
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer()
    
    # ========== CONFIRM BROADCAST ==========
    elif action == "confirm" and chat_type:
        await execute_broadcast(client, query)

# ========== HANDLE TEXT INPUTS ==========

@Client.on_message(filters.private & ~filters.command(["cancel", "grp_broadcast", "channel_broadcast"]))
async def handle_user_input(client: Client, message: Message):
    user_id = message.from_user.id
    session = user_sessions.get(user_id)
    
    if not session:
        return
    
    chat_type = session["type"]
    
    # Handle adding new ID
    if session.get("step") == "waiting_add":
        try:
            input_text = message.text.strip()
            if input_text.isdigit():
                item_id = int(f"-100{input_text}")
                await message.reply(f"🔄 Auto-converted `{input_text}` → `{item_id}`")
            else:
                item_id = int(input_text)
            
            if chat_type == "group":
                success = await add_global_group(item_id)
            else:
                success = await add_global_channel(item_id)
            
            if success:
                if chat_type == "group":
                    session["items"] = await get_global_groups()
                else:
                    session["items"] = await get_global_channels()
                session["step"] = "menu"
                await message.reply(f"✅ {chat_type.capitalize()} `{item_id}` added!")
                await send_menu(client, message.chat.id, user_id)
            else:
                await message.reply(f"❌ Failed to add. It may already exist.")
                session["step"] = "menu"
                await send_menu(client, message.chat.id, user_id)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            session["step"] = "menu"
            await send_menu(client, message.chat.id, user_id)
        return
    
    # Handle broadcast content
    if session.get("step") == "waiting_content":
        session["content_msg"] = message
        session["step"] = "confirm"
        
        targets = session["items"] if session["send_all"] else list(session["selected"])
        
        confirm_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Start Broadcast", callback_data=f"bc_confirm_{chat_type}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f"bc_cancel_{chat_type}")],
            [InlineKeyboardButton("◀️ Back to List", callback_data=f"bc_back_{chat_type}")]
        ])
        
        await message.reply(
            f"**📢 BROADCAST READY**\n\n"
            f"Target: {'ALL' if session['send_all'] else 'SELECTED'} {len(targets)} {chat_type}(s)\n\n"
            f"Content received!\n\n"
            f"**Do you want to start the broadcast?**",
            reply_markup=confirm_buttons
        )
        return

# ========== EXECUTE BROADCAST ==========

async def execute_broadcast(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    session = user_sessions.get(user_id)
    
    if not session:
        await query.answer("Session expired!", show_alert=True)
        return
    
    content = session.get("content_msg")
    if not content:
        await query.answer("No content found!", show_alert=True)
        return
    
    if session["send_all"]:
        targets = session["items"]
    else:
        targets = list(session["selected"])
    
    if not targets:
        await query.answer("No targets!", show_alert=True)
        return
    
    total = len(targets)
    await query.message.edit_text(f"🔄 Broadcasting to {total} targets...\n0/{total} completed.")
    
    successful = 0
    failed = 0
    failed_list = []
    
    for i, target_id in enumerate(targets, 1):
        try:
            if content.media:
                await content.copy(target_id)
            else:
                await client.send_message(target_id, content.text or content.caption)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                if content.media:
                    await content.copy(target_id)
                else:
                    await client.send_message(target_id, content.text or content.caption)
                successful += 1
            except Exception:
                failed += 1
                failed_list.append(str(target_id))
        except Exception:
            failed += 1
            failed_list.append(str(target_id))
        
        if i % 5 == 0 or i == total:
            await query.message.edit_text(f"🔄 Broadcasting...\n✅ Successful: {successful}\n❌ Failed: {failed}\n{i}/{total} completed.")
    
    result_text = f"**✅ BROADCAST COMPLETED**\n\nTotal: {total}\n✅ Successful: {successful}\n❌ Failed: {failed}"
    
    if failed_list and len(failed_list) <= 10:
        result_text += f"\n\n**Failed IDs:**\n" + "\n".join(f"`{iid}`" for iid in failed_list)
    
    await query.message.edit_text(result_text)
    
    # Cleanup session
    if user_id in user_sessions:
        del user_sessions[user_id]
    await query.answer("Broadcast completed!")

# ========== CANCEL COMMAND ==========

@Client.on_message(filters.command("cancel") & filters.private & is_owner_or_admin)
async def cancel_session(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await message.reply("❌ Broadcast session cancelled.")
    else:
        await message.reply("No active broadcast session.")

# ========== AUTO-ADD GROUPS ==========

@Client.on_message(filters.group)
async def auto_add_group(client: Client, message: Message):
    await add_global_group(message.chat.id)

# ========== QUICK COMMANDS ==========

@Client.on_message(filters.command("addgroup") & filters.private & is_owner_or_admin)
async def quick_add_group(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addgroup 96022547")
    try:
        input_id = message.command[1]
        if input_id.isdigit():
            item_id = int(f"-100{input_id}")
            await message.reply(f"🔄 Auto-converted `{input_id}` → `{item_id}`")
        else:
            item_id = int(input_id)
        if await add_global_group(item_id):
            await message.reply(f"✅ Group `{item_id}` added.")
        else:
            await message.reply("❌ Failed to add.")
    except:
        await message.reply("Invalid ID.")

@Client.on_message(filters.command("addchannel") & filters.private & is_owner_or_admin)
async def quick_add_channel(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addchannel 96022547")
    try:
        input_id = message.command[1]
        if input_id.isdigit():
            item_id = int(f"-100{input_id}")
            await message.reply(f"🔄 Auto-converted `{input_id}` → `{item_id}`")
        else:
            item_id = int(input_id)
        if await add_global_channel(item_id):
            await message.reply(f"✅ Channel `{item_id}` added.")
        else:
            await message.reply("❌ Failed to add.")
    except:
        await message.reply("Invalid ID.")

@Client.on_message(filters.command("delgroup") & filters.private & is_owner_or_admin)
async def del_group_cmd(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /delgroup -10096022547")
    try:
        gid = int(message.command[1])
        if await remove_global_group(gid):
            await message.reply(f"✅ Group `{gid}` removed.")
        else:
            await message.reply("❌ Not found.")
    except:
        await message.reply("Invalid ID.")

@Client.on_message(filters.command("delchannel") & filters.private & is_owner_or_admin)
async def del_channel_cmd(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /delchannel -10096022547")
    try:
        cid = int(message.command[1])
        if await remove_global_channel(cid):
            await message.reply(f"✅ Channel `{cid}` removed.")
        else:
            await message.reply("❌ Not found.")
    except:
        await message.reply("Invalid ID.")

@Client.on_message(filters.command("listgroups") & filters.private & is_owner_or_admin)
async def list_groups_cmd(client: Client, message: Message):
    items = await get_global_groups()
    if not items:
        return await message.reply("No groups.")
    text = "**📡 Groups:**\n"
    for iid in items:
        try:
            chat = await client.get_chat(iid)
            text += f"• {chat.title}\n  `{iid}`\n\n"
        except:
            text += f"• Unknown\n  `{iid}`\n\n"
    await message.reply(text)

@Client.on_message(filters.command("listchannels") & filters.private & is_owner_or_admin)
async def list_channels_cmd(client: Client, message: Message):
    items = await get_global_channels()
    if not items:
        return await message.reply("No channels.")
    text = "**📡 Channels:**\n"
    for iid in items:
        try:
            chat = await client.get_chat(iid)
            text += f"• {chat.title}\n  `{iid}`\n\n"
        except:
            text += f"• Unknown\n  `{iid}`\n\n"
    await message.reply(text)
