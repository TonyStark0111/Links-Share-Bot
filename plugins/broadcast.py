import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from helper_func import is_owner_or_admin
from database.database import (
    get_global_groups, add_global_group, remove_global_group,
    get_global_channels, add_global_channel, remove_global_channel
)

# Store active sessions
broadcast_sessions = {}

# ============ COMMAND HANDLERS ============

@Client.on_message(filters.command("grp_broadcast") & filters.private & is_owner_or_admin)
async def group_broadcast_menu(client: Client, message: Message):
    """Show list of groups to choose from"""
    await show_broadcast_menu(client, message, chat_type="group")

@Client.on_message(filters.command("channel_broadcast") & filters.private & is_owner_or_admin)
async def channel_broadcast_menu(client: Client, message: Message):
    """Show list of channels to choose from"""
    await show_broadcast_menu(client, message, chat_type="channel")

# ============ CORE MENU FUNCTION ============

async def show_broadcast_menu(client: Client, message: Message, chat_type: str):
    """Display paginated list of groups or channels with checkboxes"""
    user_id = message.from_user.id
    
    # Get appropriate list from database
    if chat_type == "group":
        items = await get_global_groups()
        item_name = "groups"
    else:
        items = await get_global_channels()
        item_name = "channels"
    
    if not items:
        await message.reply(
            f"❌ No {item_name} in global list.\n\n"
            f"{'Groups are automatically added when someone sends a message in the group.' if chat_type == 'group' else 'Use /addchannel to add channels.'}\n\n"
            f"Or add manually using:\n"
            f"/add{chat_type} -1001234567890"
        )
        return
    
    # Store session
    broadcast_sessions[user_id] = {
        "type": chat_type,
        "items": items,
        "page": 0,
        "selected_items": [],
        "awaiting_content": False,
        "content_msg": None,
        "broadcast_all": False,
        "awaiting_input": False
    }
    
    await show_item_list(client, message, user_id)

async def show_item_list(client: Client, message: Message, user_id: int, edit: bool = True):
    """Display paginated list with checkboxes"""
    session = broadcast_sessions.get(user_id)
    if not session:
        return
    
    chat_type = session["type"]
    items = session["items"]
    page = session["page"]
    per_page = 10
    total_pages = (len(items) + per_page - 1) // per_page
    
    start = page * per_page
    end = start + per_page
    page_items = items[start:end]
    
    buttons = []
    
    # Add item buttons with checkboxes
    for item_id in page_items:
        try:
            chat = await client.get_chat(item_id)
            title = chat.title[:35] + ".." if len(chat.title) > 35 else chat.title
            
            # Show member count for groups
            if chat_type == "group":
                member_count = getattr(chat, 'members_count', '?')
                display = f"{title} ({member_count})"
            else:
                display = title
            
            is_selected = item_id in session["selected_items"]
            checkbox = "✅" if is_selected else "⬜"
            
            buttons.append([InlineKeyboardButton(
                f"{checkbox} {display}",
                callback_data=f"bc_toggle_{chat_type}_{item_id}"
            )])
        except Exception:
            buttons.append([InlineKeyboardButton(
                f"⚠️ Unknown ({item_id})",
                callback_data=f"bc_toggle_{chat_type}_{item_id}"
            )])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"bc_page_prev_{chat_type}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"bc_page_next_{chat_type}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Action buttons
    action_buttons = []
    if session["selected_items"]:
        action_buttons.append(InlineKeyboardButton(
            f"📢 Broadcast to Selected ({len(session['selected_items'])})",
            callback_data=f"bc_broadcast_selected_{chat_type}"
        ))
    action_buttons.append(InlineKeyboardButton(
        f"📢 Broadcast to ALL {chat_type.upper()}s ({len(items)})",
        callback_data=f"bc_broadcast_all_{chat_type}"
    ))
    action_buttons.append(InlineKeyboardButton("❌ Cancel", callback_data=f"bc_cancel_{chat_type}"))
    buttons.append(action_buttons)
    
    # Management buttons
    buttons.append([
        InlineKeyboardButton(f"➕ Add {chat_type.capitalize()}", callback_data=f"bc_add_{chat_type}"),
        InlineKeyboardButton(f"🗑️ Remove {chat_type.capitalize()}", callback_data=f"bc_remove_{chat_type}"),
        InlineKeyboardButton("🔄 Refresh", callback_data=f"bc_refresh_{chat_type}")
    ])
    
    # Create message text
    selected_count = len(session["selected_items"])
    text = f"**📡 SELECT {chat_type.upper()}S TO BROADCAST**\n\n"
    text += f"Selected: **{selected_count}** {chat_type}(s)\n"
    text += f"Total: **{len(items)}** {chat_type}(s)\n\n"
    text += f"Page **{page + 1}** of **{total_pages}**\n\n"
    text += "⬜ = Not selected | ✅ = Selected\n"
    text += "Click on an item to select/unselect it.\n\n"
    text += "After selecting, click **'Broadcast to Selected'** or **'Broadcast to ALL'**."
    
    if chat_type == "group":
        text += "\n\n💡 **Tip:** Groups are auto-added when users message the bot."
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if edit and hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=reply_markup)
    else:
        if edit:
            await message.edit_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)

# ============ CALLBACK HANDLERS ============

@Client.on_callback_query(filters.regex(r"^bc_(toggle|page_prev|page_next|broadcast_selected|broadcast_all|cancel|add|remove|refresh|confirm_remove|back_to_list|start_broadcast)_"))
async def broadcast_callback(client: Client, query: CallbackQuery):
    data = query.data
    parts = data.split("_")
    action = parts[1]
    chat_type = parts[2] if len(parts) > 2 else None
    
    user_id = query.from_user.id
    session = broadcast_sessions.get(user_id)
    
    if not session and action not in ["confirm_remove", "start_broadcast"]:
        await query.answer("Session expired. Use /grp_broadcast or /channel_broadcast again.", show_alert=True)
        await query.message.delete()
        return
    
    # Handle toggle selection
    if action == "toggle" and chat_type:
        item_id = int(parts[3])
        if item_id in session["selected_items"]:
            session["selected_items"].remove(item_id)
        else:
            session["selected_items"].append(item_id)
        await show_item_list(client, query.message, user_id)
        await query.answer()
    
    # Handle pagination
    elif action == "page_prev" and chat_type:
        session["page"] -= 1
        await show_item_list(client, query.message, user_id)
        await query.answer()
    
    elif action == "page_next" and chat_type:
        session["page"] += 1
        await show_item_list(client, query.message, user_id)
        await query.answer()
    
    # Handle refresh
    elif action == "refresh" and chat_type:
        if chat_type == "group":
            session["items"] = await get_global_groups()
        else:
            session["items"] = await get_global_channels()
        await show_item_list(client, query.message, user_id)
        await query.answer(f"{chat_type.capitalize()} list refreshed!", show_alert=True)
    
    # Handle broadcast selected
    elif action == "broadcast_selected" and chat_type:
        if not session["selected_items"]:
            await query.answer(f"No {chat_type}s selected! Select at least one.", show_alert=True)
            return
        session["broadcast_all"] = False
        session["awaiting_content"] = True
        await query.message.edit_text(
            f"**📢 BROADCAST TO SELECTED {chat_type.upper()}S**\n\n"
            f"Selected: **{len(session['selected_items'])}**\n\n"
            f"IDs:\n"
            + "\n".join(f"`{iid}`" for iid in session["selected_items"][:10])
            + (f"\n... and {len(session['selected_items']) - 10} more" if len(session["selected_items"]) > 10 else "")
            + f"\n\n**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Handle broadcast all
    elif action == "broadcast_all" and chat_type:
        session["broadcast_all"] = True
        session["awaiting_content"] = True
        await query.message.edit_text(
            f"**📢 BROADCAST TO ALL {chat_type.upper()}S**\n\n"
            f"Total: **{len(session['items'])}**\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Handle cancel
    elif action == "cancel" and chat_type:
        if user_id in broadcast_sessions:
            del broadcast_sessions[user_id]
        await query.message.edit_text("❌ Broadcast cancelled.")
        await query.answer()
    
    # Handle add item
    elif action == "add" and chat_type:
        await query.message.edit_text(
            f"**➕ ADD NEW {chat_type.upper()}**\n\n"
            f"Send the {chat_type} ID to add:\n"
            f"Example: `-1001234567890`\n\n"
            f"Or send the username: `@{chat_type}username`\n\n"
            f"Make sure bot is {'member' if chat_type == 'group' else 'admin'} in that {chat_type}.\n\n"
            f"Send `/cancel` to abort."
        )
        session["awaiting_input"] = True
        await query.answer()
    
    # Handle remove item
    elif action == "remove" and chat_type:
        items = session["items"]
        if not items:
            await query.answer(f"No {chat_type}s to remove!", show_alert=True)
            return
        
        buttons = []
        for item_id in items:
            try:
                chat = await client.get_chat(item_id)
                title = chat.title[:30] + ".." if len(chat.title) > 30 else chat.title
                buttons.append([InlineKeyboardButton(
                    f"❌ {title}",
                    callback_data=f"bc_confirm_remove_{chat_type}_{item_id}"
                )])
            except Exception:
                buttons.append([InlineKeyboardButton(
                    f"❌ Unknown ({item_id})",
                    callback_data=f"bc_confirm_remove_{chat_type}_{item_id}"
                )])
        
        buttons.append([InlineKeyboardButton("◀️ Back to List", callback_data=f"bc_back_to_list_{chat_type}")])
        
        await query.message.edit_text(
            f"**🗑️ REMOVE {chat_type.upper()}**\n\nClick on an item to remove it from broadcast list:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
    
    # Handle confirm remove
    elif action == "confirm_remove" and chat_type:
        item_id = int(parts[3])
        if chat_type == "group":
            success = await remove_global_group(item_id)
        else:
            success = await remove_global_channel(item_id)
        
        if success:
            # Update session items
            if chat_type == "group":
                session["items"] = await get_global_groups()
            else:
                session["items"] = await get_global_channels()
            if item_id in session["selected_items"]:
                session["selected_items"].remove(item_id)
            await query.answer(f"✅ {chat_type.capitalize()} {item_id} removed!", show_alert=True)
            await show_item_list(client, query.message, user_id)
        else:
            await query.answer(f"Failed to remove {chat_type}!", show_alert=True)
    
    # Handle back to list
    elif action == "back_to_list" and chat_type:
        await show_item_list(client, query.message, user_id)
        await query.answer()
    
    # Handle start broadcast
    elif action == "start_broadcast" and chat_type:
        await start_broadcast_execution(client, query)

# ============ HANDLE TEXT INPUT (ADD ITEM OR CONTENT) ============

@Client.on_message(filters.private & ~filters.command(["cancel", "grp_broadcast", "channel_broadcast"]))
async def handle_broadcast_input(client: Client, message: Message):
    user_id = message.from_user.id
    session = broadcast_sessions.get(user_id)
    
    if not session:
        return
    
    chat_type = session["type"]
    
    # Handle adding item via ID/username
    if session.get("awaiting_input"):
        input_text = message.text.strip()
        
        try:
            if input_text.startswith("-100") or input_text.lstrip("-").isdigit():
                item_id = int(input_text)
            elif input_text.startswith("@"):
                chat = await client.get_chat(input_text)
                item_id = chat.id
            else:
                await message.reply(f"❌ Invalid format. Send {chat_type} ID or username.\nExample: `-1001234567890` or `@{chat_type}`")
                return
            
            # Add to database
            if chat_type == "group":
                success = await add_global_group(item_id)
            else:
                success = await add_global_channel(item_id)
            
            if success:
                # Update session
                if chat_type == "group":
                    session["items"] = await get_global_groups()
                else:
                    session["items"] = await get_global_channels()
                session["awaiting_input"] = False
                await message.reply(f"✅ {chat_type.capitalize()} `{item_id}` added successfully!")
                await show_item_list(client, message, user_id)
            else:
                await message.reply(f"❌ Failed to add {chat_type}. It may already exist.")
                session["awaiting_input"] = False
                await show_item_list(client, message, user_id)
        except Exception as e:
            await message.reply(f"❌ Error: {e}\nMake sure bot is {'member' if chat_type == 'group' else 'admin'} in that {chat_type}.")
            session["awaiting_input"] = False
            await show_item_list(client, message, user_id)
        return
    
    # Handle broadcast content
    if session.get("awaiting_content"):
        session["content_msg"] = message
        session["awaiting_content"] = False
        
        if session["broadcast_all"]:
            targets = session["items"]
            target_desc = f"ALL {len(targets)} {chat_type}s"
        else:
            targets = session["selected_items"]
            target_desc = f"{len(targets)} selected {chat_type}s"
        
        confirm_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Start Broadcast", callback_data=f"bc_start_broadcast_{chat_type}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f"bc_cancel_{chat_type}")],
            [InlineKeyboardButton("◀️ Back to List", callback_data=f"bc_back_to_list_{chat_type}")]
        ])
        
        await message.reply(
            f"**📢 BROADCAST READY**\n\n"
            f"Target: {target_desc}\n\n"
            f"Content received!\n\n"
            f"**Do you want to start the broadcast?**",
            reply_markup=confirm_buttons
        )
        return

# ============ BROADCAST EXECUTION WITH PROGRESS BAR ============

async def start_broadcast_execution(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    session = broadcast_sessions.get(user_id)
    
    if not session:
        await query.answer("Session expired!", show_alert=True)
        return
    
    content = session.get("content_msg")
    if not content:
        await query.answer("No content found!", show_alert=True)
        return
    
    chat_type = session["type"]
    
    # Get targets
    if session["broadcast_all"]:
        targets = session["items"]
        target_type = f"ALL {chat_type.upper()}S"
    else:
        targets = session["selected_items"]
        target_type = f"SELECTED {chat_type.upper()}S"
    
    if not targets:
        await query.answer("No targets selected!", show_alert=True)
        return
    
    total = len(targets)
    bar_length = 20
    
    # Initial progress message
    progress_bar = "○" * bar_length
    await query.message.edit_text(
        f"**🔄 {target_type} BROADCAST IN PROGRESS...**\n\n"
        f"<blockquote>⏳:</b> [{progress_bar}] <code>0%</code></blockquote>\n\n"
        f"**📊 Total:** `{total}`\n"
        f"**✅ Successful:** `0`\n"
        f"**❌ Failed:** `0`\n\n"
        f"<i>⛔ To stop: <b>/cancel</b></i>"
    )
    
    successful = 0
    failed = 0
    failed_list = []
    
    for i, target_id in enumerate(targets, 1):
        try:
            if content.media:
                await client.copy_message(target_id, content.chat.id, content.id)
            else:
                await client.send_message(target_id, content.text or content.caption)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                if content.media:
                    await client.copy_message(target_id, content.chat.id, content.id)
                else:
                    await client.send_message(target_id, content.text or content.caption)
                successful += 1
            except Exception:
                failed += 1
                failed_list.append(str(target_id))
        except Exception:
            failed += 1
            failed_list.append(str(target_id))
        
        # Update progress bar every 5 messages or at the end
        if i % 5 == 0 or i == total:
            percent = i / total
            percent_int = int(percent * 100)
            filled = int(percent * bar_length)
            progress_bar = "●" * filled + "○" * (bar_length - filled)
            
            await query.message.edit_text(
                f"**🔄 {target_type} BROADCAST IN PROGRESS...**\n\n"
                f"<blockquote>⏳:</b> [{progress_bar}] <code>{percent_int}%</code></blockquote>\n\n"
                f"**📊 Total:** `{total}`\n"
                f"**✅ Successful:** `{successful}`\n"
                f"**❌ Failed:** `{failed}`\n\n"
                f"<i>⛔ To stop: <b>/cancel</b></i>"
            )
    
    # Final status with full progress bar
    progress_bar = "●" * bar_length
    result_text = (
        f"**✅ {chat_type.upper()} BROADCAST COMPLETED ✅**\n\n"
        f"<blockquote>📊:</b> [{progress_bar}] <code>100%</code></blockquote>\n\n"
        f"**📊 Total {chat_type}s:** `{total}`\n"
        f"**✅ Successful:** `{successful}`\n"
        f"**❌ Failed:** `{failed}`"
    )
    
    if failed_list and len(failed_list) <= 10:
        result_text += f"\n\n**Failed {chat_type.capitalize()} IDs:**\n" + "\n".join(f"`{iid}`" for iid in failed_list)
    elif failed_list:
        result_text += f"\n\n**Failed:** `{len(failed_list)}` {chat_type}s (check logs)"
    
    await query.message.edit_text(result_text)
    
    # Cleanup session
    if user_id in broadcast_sessions:
        del broadcast_sessions[user_id]
    await query.answer("Broadcast completed!")

# ============ AUTO-ADD GROUPS (ONLY GROUPS, NOT CHANNELS) ============

@Client.on_message(filters.group)
async def auto_add_group_to_global(client: Client, message: Message):
    """Auto-add groups when bot receives any message"""
    await add_global_group(message.chat.id)
    print(f"Auto-added group {message.chat.id} to global broadcast list")

# ============ QUICK COMMANDS FOR ADMINS ============

@Client.on_message(filters.command("addgroup") & filters.private & is_owner_or_admin)
async def quick_add_group(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addgroup -1001234567890\nOr: /addgroup @groupusername")
    await quick_add_item(client, message, "group")

@Client.on_message(filters.command("addchannel") & filters.private & is_owner_or_admin)
async def quick_add_channel(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /addchannel -1001234567890\nOr: /addchannel @channelusername")
    await quick_add_item(client, message, "channel")

async def quick_add_item(client: Client, message: Message, item_type: str):
    input_text = message.command[1]
    try:
        if input_text.startswith("-100") or input_text.lstrip("-").isdigit():
            item_id = int(input_text)
        elif input_text.startswith("@"):
            chat = await client.get_chat(input_text)
            item_id = chat.id
        else:
            return await message.reply(f"Invalid format. Use ID or username.")
        
        if item_type == "group":
            success = await add_global_group(item_id)
        else:
            success = await add_global_channel(item_id)
        
        if success:
            await message.reply(f"✅ {item_type.capitalize()} `{item_id}` added to broadcast list.")
        else:
            await message.reply(f"❌ Failed to add {item_type}.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@Client.on_message(filters.command("delgroup") & filters.private & is_owner_or_admin)
async def quick_del_group(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /delgroup -1001234567890")
    await quick_del_item(client, message, "group")

@Client.on_message(filters.command("delchannel") & filters.private & is_owner_or_admin)
async def quick_del_channel(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /delchannel -1001234567890")
    await quick_del_item(client, message, "channel")

async def quick_del_item(client: Client, message: Message, item_type: str):
    try:
        item_id = int(message.command[1])
        if item_type == "group":
            success = await remove_global_group(item_id)
        else:
            success = await remove_global_channel(item_id)
        
        if success:
            await message.reply(f"✅ {item_type.capitalize()} `{item_id}` removed from broadcast list.")
        else:
            await message.reply(f"❌ {item_type.capitalize()} not found.")
    except ValueError:
        await message.reply(f"Invalid {item_type} ID.")

@Client.on_message(filters.command("listgroups") & filters.private & is_owner_or_admin)
async def list_groups_cmd(client: Client, message: Message):
    await list_items(client, message, "group")

@Client.on_message(filters.command("listchannels") & filters.private & is_owner_or_admin)
async def list_channels_cmd(client: Client, message: Message):
    await list_items(client, message, "channel")

async def list_items(client: Client, message: Message, item_type: str):
    if item_type == "group":
        items = await get_global_groups()
    else:
        items = await get_global_channels()
    
    if not items:
        return await message.reply(f"No {item_type}s in list.\n\nUse /add{item_type} to add.")
    
    text = f"**📡 Broadcast {item_type.upper()}S:**\n\n"
    for iid in items:
        try:
            chat = await client.get_chat(iid)
            if item_type == "group":
                member_count = getattr(chat, 'members_count', '?')
                text += f"• {chat.title}\n  `{iid}` | Members: {member_count}\n\n"
            else:
                text += f"• {chat.title}\n  `{iid}`\n\n"
        except:
            text += f"• Unknown {item_type}\n  `{iid}`\n\n"
    
    if len(text) > 4000:
        await message.reply(f"Too many {item_type}s! Use /{item_type}_broadcast menu instead.")
    else:
        await message.reply(text)

# ============ CANCEL COMMAND ============

@Client.on_message(filters.command("cancel") & filters.private & is_owner_or_admin)
async def cancel_broadcast_session(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in broadcast_sessions:
        del broadcast_sessions[user_id]
        await message.reply("❌ Broadcast session cancelled.")
    else:
        await message.reply("No active broadcast session.")
