import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from helper_func import is_owner_or_admin
from database.database import (
    get_global_groups, add_global_group, remove_global_group,
    get_global_channels, add_global_channel, remove_global_channel
)

broadcast_sessions = {}

def fix_id(id_value):
    """Convert ID to proper Telegram format with -100 prefix if needed"""
    id_str = str(id_value).strip()
    # If it's already negative, return as is
    if id_str.startswith('-'):
        return int(id_str)
    # If it's a positive number, assume it needs -100 prefix
    try:
        num = int(id_str)
        if num > 0:
            return int(f"-100{num}")
        return num
    except:
        return id_value

@Client.on_message(filters.command("grp_broadcast") & filters.private & is_owner_or_admin)
async def group_broadcast_menu(client: Client, message: Message):
    await show_broadcast_menu(client, message, "group")

@Client.on_message(filters.command("channel_broadcast") & filters.private & is_owner_or_admin)
async def channel_broadcast_menu(client: Client, message: Message):
    await show_broadcast_menu(client, message, "channel")

async def show_broadcast_menu(client: Client, message: Message, chat_type: str):
    user_id = message.from_user.id
    
    if chat_type == "group":
        items = await get_global_groups()
    else:
        items = await get_global_channels()
    
    if not items:
        await message.reply(
            f"❌ No {chat_type}s in list.\n\n"
            f"Use /add{chat_type} 96022547 (auto adds -100 prefix)\n"
            f"Or /add{chat_type} -10096022547"
        )
        return
    
    # Send new menu message
    menu_msg = await message.reply("Loading menu...")
    
    broadcast_sessions[user_id] = {
        "type": chat_type,
        "items": items,
        "selected": set(),
        "page": 0,
        "menu_msg_id": menu_msg.id,
        "menu_chat_id": menu_msg.chat.id,
        "awaiting_content": False,
        "awaiting_add": False,
        "send_all": False,
        "content_msg": None
    }
    
    await render_menu(client, user_id)

async def render_menu(client: Client, user_id: int):
    session = broadcast_sessions.get(user_id)
    if not session:
        return
    
    items = session["items"]
    page = session["page"]
    per_page = 10
    total_pages = (len(items) + per_page - 1) // per_page
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
        
        is_selected = item_id in session["selected"]
        checkbox = "✅" if is_selected else "⬜"
        buttons.append([InlineKeyboardButton(f"{checkbox} {name}", callback_data=f"broad_toggle_{session['type']}_{item_id}")])
    
    # Navigation buttons
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"broad_prev_{session['type']}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"broad_next_{session['type']}"))
    if nav:
        buttons.append(nav)
    
    # Action buttons
    action_row = []
    if session["selected"]:
        action_row.append(InlineKeyboardButton(f"📢 Send to Selected ({len(session['selected'])})", callback_data=f"broad_selected_{session['type']}"))
    action_row.append(InlineKeyboardButton(f"📢 Send to ALL ({len(items)})", callback_data=f"broad_all_{session['type']}"))
    action_row.append(InlineKeyboardButton("❌ Cancel", callback_data=f"broad_cancel_{session['type']}"))
    buttons.append(action_row)
    
    # Management buttons
    buttons.append([
        InlineKeyboardButton("➕ Add", callback_data=f"broad_add_{session['type']}"),
        InlineKeyboardButton("🗑️ Remove", callback_data=f"broad_remove_{session['type']}"),
        InlineKeyboardButton("🔄 Refresh", callback_data=f"broad_refresh_{session['type']}")
    ])
    
    text = f"**📡 SELECT {session['type'].upper()}S TO BROADCAST**\n\n"
    text += f"Selected: **{len(session['selected'])}** | Total: **{len(items)}**\n"
    text += f"Page **{page + 1}** of **{total_pages}**\n\n"
    text += "⬜ = Not selected | ✅ = Selected\n"
    text += "Click on an item to select/unselect it.\n\n"
    text += "After selecting, click **'Send to Selected'** or **'Send to ALL'**."
    
    try:
        await client.edit_message_text(
            session["menu_chat_id"],
            session["menu_msg_id"],
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        print(f"Render error: {e}")

# Main callback handler
@Client.on_callback_query()
async def broadcast_callback(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    # Check if this is a broadcast callback
    if not data.startswith("broad_"):
        return
    
    session = broadcast_sessions.get(user_id)
    if not session:
        await query.answer("Session expired. Use /grp_broadcast or /channel_broadcast again.", show_alert=True)
        await query.message.delete()
        return
    
    parts = data.split("_")
    action = parts[1]
    chat_type = parts[2] if len(parts) > 2 else None
    
    # Toggle selection
    if action == "toggle" and chat_type:
        item_id = int(parts[3])
        if item_id in session["selected"]:
            session["selected"].remove(item_id)
        else:
            session["selected"].add(item_id)
        await render_menu(client, user_id)
        await query.answer()
    
    # Pagination
    elif action == "prev" and chat_type:
        session["page"] -= 1
        await render_menu(client, user_id)
        await query.answer()
    
    elif action == "next" and chat_type:
        session["page"] += 1
        await render_menu(client, user_id)
        await query.answer()
    
    # Refresh
    elif action == "refresh" and chat_type:
        if chat_type == "group":
            session["items"] = await get_global_groups()
        else:
            session["items"] = await get_global_channels()
        session["selected"] = set()
        session["page"] = 0
        await render_menu(client, user_id)
        await query.answer("List refreshed!", show_alert=True)
    
    # Send to selected
    elif action == "selected" and chat_type:
        if not session["selected"]:
            await query.answer("No items selected! Click on items to select them.", show_alert=True)
            return
        session["send_all"] = False
        session["awaiting_content"] = True
        await query.message.edit_text(
            f"**📢 BROADCAST TO SELECTED {chat_type.upper()}S**\n\n"
            f"Selected: **{len(session['selected'])}**\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Send to all
    elif action == "all" and chat_type:
        session["send_all"] = True
        session["awaiting_content"] = True
        await query.message.edit_text(
            f"**📢 BROADCAST TO ALL {chat_type.upper()}S**\n\n"
            f"Total: **{len(session['items'])}**\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Cancel session
    elif action == "cancel" and chat_type:
        if user_id in broadcast_sessions:
            del broadcast_sessions[user_id]
        await query.message.edit_text("❌ Broadcast cancelled.")
        await query.answer()
    
    # Add item
    elif action == "add" and chat_type:
        session["awaiting_add"] = True
        await query.message.edit_text(
            f"**➕ ADD NEW {chat_type.upper()}**\n\n"
            f"Send the {chat_type} ID to add:\n"
            f"Example: `96022547` (auto adds -100 prefix)\n"
            f"Or: `-10096022547`\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Remove item - show list
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
            buttons.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"broad_remove_confirm_{chat_type}_{item_id}")])
        
        buttons.append([InlineKeyboardButton("◀️ Back to List", callback_data=f"broad_back_{chat_type}")])
        
        await query.message.edit_text(
            f"**🗑️ REMOVE {chat_type.upper()}**\n\nClick on an item to remove it:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
    
    # Confirm remove
    elif action == "remove_confirm" and chat_type:
        item_id = int(parts[3])
        if chat_type == "group":
            await remove_global_group(item_id)
        else:
            await remove_global_channel(item_id)
        
        # Refresh items
        if chat_type == "group":
            session["items"] = await get_global_groups()
        else:
            session["items"] = await get_global_channels()
        session["selected"].discard(item_id)
        session["page"] = 0
        await render_menu(client, user_id)
        await query.answer(f"✅ {chat_type.capitalize()} removed!", show_alert=True)
    
    # Back to main menu
    elif action == "back" and chat_type:
        await render_menu(client, user_id)
        await query.answer()

# Handle text input (add ID or content)
@Client.on_message(filters.private & ~filters.command(["cancel", "grp_broadcast", "channel_broadcast"]))
async def handle_broadcast_input(client: Client, message: Message):
    user_id = message.from_user.id
    session = broadcast_sessions.get(user_id)
    
    if not session:
        return
    
    chat_type = session["type"]
    
    # Handle adding new ID
    if session.get("awaiting_add"):
        try:
            input_text = message.text.strip()
            
            # Auto-fix ID with -100 prefix
            if input_text.isdigit() or (input_text.lstrip('-').isdigit() and not input_text.startswith('-100')):
                # Convert positive number to -100 prefix format
                clean_id = input_text.lstrip('-')
                item_id = int(f"-100{clean_id}")
                await message.reply(f"🔄 Auto-converted `{input_text}` → `{item_id}`")
            elif input_text.startswith("-100") or input_text.startswith("-"):
                item_id = int(input_text)
            else:
                await message.reply(f"❌ Invalid format. Send numeric ID like `96022547` or `-10096022547`")
                return
            
            if chat_type == "group":
                success = await add_global_group(item_id)
            else:
                success = await add_global_channel(item_id)
            
            if success:
                # Refresh items
                if chat_type == "group":
                    session["items"] = await get_global_groups()
                else:
                    session["items"] = await get_global_channels()
                session["awaiting_add"] = False
                await message.reply(f"✅ {chat_type.capitalize()} `{item_id}` added!")
                await render_menu(client, user_id)
            else:
                await message.reply(f"❌ Failed to add {chat_type}. It may already exist.")
                session["awaiting_add"] = False
                await render_menu(client, user_id)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            session["awaiting_add"] = False
            await render_menu(client, user_id)
        return
    
    # Handle broadcast content
    if session.get("awaiting_content"):
        session["content_msg"] = message
        session["awaiting_content"] = False
        
        targets = session["items"] if session["send_all"] else list(session["selected"])
        confirm_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Start Broadcast", callback_data=f"broad_confirm_{chat_type}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f"broad_cancel_{chat_type}")],
            [InlineKeyboardButton("◀️ Back to List", callback_data=f"broad_back_{chat_type}")]
        ])
        
        await message.reply(
            f"**📢 BROADCAST READY**\n\n"
            f"Target: {'ALL' if session['send_all'] else 'SELECTED'} {len(targets)} {chat_type}(s)\n\n"
            f"Content received!\n\n"
            f"**Do you want to start the broadcast?**",
            reply_markup=confirm_buttons
        )
        return

# Confirm and execute broadcast
@Client.on_callback_query(filters.regex(r"^broad_confirm_"))
async def confirm_broadcast(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    session = broadcast_sessions.get(user_id)
    
    if not session:
        await query.answer("Session expired!", show_alert=True)
        return
    
    chat_type = session["type"]
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
    bar_length = 20
    
    # Initial progress
    progress_bar = "○" * bar_length
    await query.message.edit_text(
        f"**🔄 BROADCAST IN PROGRESS...**\n\n"
        f"<blockquote>⏳:</b> [{progress_bar}] <code>0%</code></blockquote>\n\n"
        f"**📊 Total:** `{total}`\n"
        f"**✅ Successful:** `0`\n"
        f"**❌ Failed:** `0`"
    )
    
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
        
        # Update progress every 5 messages
        if i % 5 == 0 or i == total:
            percent = i / total
            percent_int = int(percent * 100)
            filled = int(percent * bar_length)
            progress_bar = "●" * filled + "○" * (bar_length - filled)
            
            await query.message.edit_text(
                f"**🔄 BROADCAST IN PROGRESS...**\n\n"
                f"<blockquote>⏳:</b> [{progress_bar}] <code>{percent_int}%</code></blockquote>\n\n"
                f"**📊 Total:** `{total}`\n"
                f"**✅ Successful:** `{successful}`\n"
                f"**❌ Failed:** `{failed}`"
            )
    
    # Final result
    progress_bar = "●" * bar_length
    result_text = (
        f"**✅ BROADCAST COMPLETED ✅**\n\n"
        f"<blockquote>📊:</b> [{progress_bar}] <code>100%</code></blockquote>\n\n"
        f"**📊 Total {chat_type}s:** `{total}`\n"
        f"**✅ Successful:** `{successful}`\n"
        f"**❌ Failed:** `{failed}`"
    )
    
    if failed_list and len(failed_list) <= 10:
        result_text += f"\n\n**Failed IDs:**\n" + "\n".join(f"`{iid}`" for iid in failed_list)
    
    await query.message.edit_text(result_text)
    
    # Cleanup
    if user_id in broadcast_sessions:
        del broadcast_sessions[user_id]
    await query.answer("Broadcast completed!")

# Auto-add groups when bot receives any message
@Client.on_message(filters.group)
async def auto_add_group(client: Client, message: Message):
    await add_global_group(message.chat.id)

# Cancel command
@Client.on_message(filters.command("cancel") & filters.private & is_owner_or_admin)
async def cancel_broadcast(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in broadcast_sessions:
        del broadcast_sessions[user_id]
        await message.reply("❌ Broadcast session cancelled.")
    else:
        await message.reply("No active broadcast session.")

# Quick add commands with auto -100 prefix
@Client.on_message(filters.command("addgroup") & filters.private & is_owner_or_admin)
async def quick_add_group(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addgroup 96022547 (auto adds -100)\nOr: /addgroup -10096022547")
    try:
        input_id = message.command[1]
        # Auto-fix ID
        if input_id.isdigit():
            item_id = int(f"-100{input_id}")
            await message.reply(f"🔄 Auto-converted `{input_id}` → `{item_id}`")
        else:
            item_id = int(input_id)
        
        if await add_global_group(item_id):
            await message.reply(f"✅ Group `{item_id}` added.")
        else:
            await message.reply("❌ Failed to add.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@Client.on_message(filters.command("addchannel") & filters.private & is_owner_or_admin)
async def quick_add_channel(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addchannel 96022547 (auto adds -100)\nOr: /addchannel -10096022547")
    try:
        input_id = message.command[1]
        # Auto-fix ID
        if input_id.isdigit():
            item_id = int(f"-100{input_id}")
            await message.reply(f"🔄 Auto-converted `{input_id}` → `{item_id}`")
        else:
            item_id = int(input_id)
        
        if await add_global_channel(item_id):
            await message.reply(f"✅ Channel `{item_id}` added.")
        else:
            await message.reply("❌ Failed to add.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# List commands
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

# Delete commands
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
