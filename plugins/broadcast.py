import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
from helper_func import is_owner_or_admin
from database.database import (
    get_global_groups, add_global_group, remove_global_group,
    get_global_channels, add_global_channel, remove_global_channel
)

# Store user sessions
user_data = {}

# ============ GROUP BROADCAST ============

@Client.on_message(filters.command("grp_broadcast") & filters.private & is_owner_or_admin)
async def grp_broadcast_cmd(client: Client, message: Message):
    groups = await get_global_groups()
    
    if not groups:
        await message.reply("❌ No groups found.\n\nAdd a group with: /addgroup 96022547")
        return
    
    user_data[message.from_user.id] = {
        "type": "group",
        "items": groups,
        "selected": set(),
        "step": "menu"
    }
    
    await send_menu(client, message.chat.id, message.from_user.id)

# ============ CHANNEL BROADCAST ============

@Client.on_message(filters.command("channel_broadcast") & filters.private & is_owner_or_admin)
async def channel_broadcast_cmd(client: Client, message: Message):
    channels = await get_global_channels()
    
    if not channels:
        await message.reply("❌ No channels found.\n\nAdd a channel with: /addchannel 96022547")
        return
    
    user_data[message.from_user.id] = {
        "type": "channel",
        "items": channels,
        "selected": set(),
        "step": "menu"
    }
    
    await send_menu(client, message.chat.id, message.from_user.id)

# ============ SEND MENU ============

async def send_menu(client: Client, chat_id: int, user_id: int, edit_msg_id: int = None):
    session = user_data.get(user_id)
    if not session:
        return
    
    items = session["items"]
    item_type = session["type"]
    type_upper = item_type.upper()
    
    buttons = []
    
    for item_id in items:
        try:
            chat = await client.get_chat(item_id)
            name = chat.title[:30]
        except:
            name = f"ID: {item_id}"
        
        is_selected = "✅" if item_id in session["selected"] else "⬜"
        buttons.append([InlineKeyboardButton(f"{is_selected} {name}", callback_data=f"toggle_{item_id}")])
    
    selected_count = len(session["selected"])
    buttons.append([InlineKeyboardButton(f"📢 Send to Selected ({selected_count})", callback_data="send_selected")])
    buttons.append([InlineKeyboardButton(f"📢 Send to ALL ({len(items)})", callback_data="send_all")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    buttons.append([InlineKeyboardButton(f"➕ Add {item_type.capitalize()}", callback_data="add_item")])
    buttons.append([InlineKeyboardButton(f"🗑️ Remove {item_type.capitalize()}", callback_data="remove_item")])
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh")])
    
    text = f"**📡 SELECT {type_upper}S TO BROADCAST**\n\n"
    text += f"Selected: {selected_count} | Total: {len(items)}\n\n"
    text += "⬜ = Not selected | ✅ = Selected\n"
    text += "Click on an item to select/unselect it."
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if edit_msg_id:
        try:
            await client.edit_message_text(chat_id, edit_msg_id, text, reply_markup=reply_markup)
        except:
            msg = await client.send_message(chat_id, text, reply_markup=reply_markup)
            session["msg_id"] = msg.id
            session["chat_id"] = chat_id
    else:
        if "msg_id" in session:
            try:
                await client.edit_message_text(session["chat_id"], session["msg_id"], text, reply_markup=reply_markup)
            except:
                msg = await client.send_message(chat_id, text, reply_markup=reply_markup)
                session["msg_id"] = msg.id
                session["chat_id"] = chat_id
        else:
            msg = await client.send_message(chat_id, text, reply_markup=reply_markup)
            session["msg_id"] = msg.id
            session["chat_id"] = chat_id

# ============ CALLBACK HANDLER ============

@Client.on_callback_query(filters.regex(r"^broad_"))
async def broadcast_callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    
    # Check if user has session
    if user_id not in user_data:
        await query.answer("Session expired! Send /grp_broadcast or /channel_broadcast again.", show_alert=True)
        return
    
    session = user_data[user_id]
    item_type = session["type"]
    
    # Handle toggle selection
    if data.startswith("toggle_"):
        item_id = int(data.split("_")[1])
        if item_id in session["selected"]:
            session["selected"].remove(item_id)
            await query.answer("Removed from selection")
        else:
            session["selected"].add(item_id)
            await query.answer("Added to selection")
        
        await send_menu(client, query.message.chat.id, user_id)
        return
    
    # Handle send selected
    elif data == "send_selected":
        if not session["selected"]:
            await query.answer(f"No {item_type}s selected! Click on items to select them.", show_alert=True)
            return
        
        session["targets"] = list(session["selected"])
        session["step"] = "waiting_content"
        session["send_type"] = "selected"
        
        await query.message.edit_text(
            f"**📢 BROADCAST TO SELECTED {item_type.upper()}S**\n\n"
            f"Selected: {len(session['selected'])} {item_type}(s)\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Handle send all
    elif data == "send_all":
        session["targets"] = session["items"].copy()
        session["step"] = "waiting_content"
        session["send_type"] = "all"
        
        await query.message.edit_text(
            f"**📢 BROADCAST TO ALL {item_type.upper()}S**\n\n"
            f"Total: {len(session['items'])} {item_type}(s)\n\n"
            f"**Send me the message to broadcast.**\n"
            f"Supports: Text, Photos, Videos, Documents, etc.\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Handle cancel
    elif data == "cancel":
        del user_data[user_id]
        await query.message.edit_text("❌ Broadcast cancelled.")
        await query.answer()
    
    # Handle refresh
    elif data == "refresh":
        if item_type == "group":
            session["items"] = await get_global_groups()
        else:
            session["items"] = await get_global_channels()
        session["selected"] = set()
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer("List refreshed!", show_alert=True)
    
    # Handle add item
    elif data == "add_item":
        session["step"] = "waiting_add"
        await query.message.edit_text(
            f"**➕ ADD NEW {item_type.upper()}**\n\n"
            f"Send the {item_type} ID to add:\n"
            f"Example: `96022547` (auto adds -100 prefix)\n\n"
            f"Send `/cancel` to abort."
        )
        await query.answer()
    
    # Handle remove item
    elif data == "remove_item":
        items = session["items"]
        if not items:
            await query.answer(f"No {item_type}s to remove!", show_alert=True)
            return
        
        buttons = []
        for item_id in items:
            try:
                chat = await client.get_chat(item_id)
                name = chat.title[:25]
            except:
                name = f"ID: {item_id}"
            buttons.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"remove_confirm_{item_id}")])
        
        buttons.append([InlineKeyboardButton("◀️ Back", callback_data="back_to_menu")])
        
        await query.message.edit_text(
            f"**🗑️ REMOVE {item_type.upper()}**\n\nClick on an item to remove it:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await query.answer()
    
    # Handle confirm remove
    elif data.startswith("remove_confirm_"):
        item_id = int(data.split("_")[2])
        if item_type == "group":
            await remove_global_group(item_id)
            session["items"] = await get_global_groups()
        else:
            await remove_global_channel(item_id)
            session["items"] = await get_global_channels()
        session["selected"].discard(item_id)
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer(f"{item_type.capitalize()} removed!", show_alert=True)
    
    # Handle back to menu
    elif data == "back_to_menu":
        session["step"] = "menu"
        await send_menu(client, query.message.chat.id, user_id)
        await query.answer()
    
    # Handle confirm broadcast
    elif data == "confirm_broadcast":
        await execute_broadcast(client, query)

# ============ HANDLE USER INPUT ============

@Client.on_message(filters.private & ~filters.command(["cancel", "grp_broadcast", "channel_broadcast"]))
async def handle_input(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        return
    
    session = user_data[user_id]
    item_type = session["type"]
    
    # Handle adding new item
    if session.get("step") == "waiting_add":
        try:
            input_text = message.text.strip()
            if input_text.isdigit():
                item_id = int(f"-100{input_text}")
                await message.reply(f"🔄 Auto-converted `{input_text}` → `{item_id}`")
            else:
                item_id = int(input_text)
            
            if item_type == "group":
                success = await add_global_group(item_id)
            else:
                success = await add_global_channel(item_id)
            
            if success:
                if item_type == "group":
                    session["items"] = await get_global_groups()
                else:
                    session["items"] = await get_global_channels()
                session["step"] = "menu"
                await message.reply(f"✅ {item_type.capitalize()} `{item_id}` added!")
                await send_menu(client, message.chat.id, user_id)
            else:
                await message.reply(f"❌ Failed to add. {item_type.capitalize()} may already exist.")
                session["step"] = "menu"
                await send_menu(client, message.chat.id, user_id)
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
            session["step"] = "menu"
            await send_menu(client, message.chat.id, user_id)
        return
    
    # Handle broadcast content
    if session.get("step") == "waiting_content":
        session["content"] = message
        session["step"] = "confirm"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Start Broadcast", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="cancel")]
        ])
        
        await message.reply(
            f"**📢 BROADCAST READY**\n\n"
            f"Target: {'ALL' if session['send_type'] == 'all' else 'SELECTED'} {len(session['targets'])} {item_type}(s)\n\n"
            f"Content received!\n\n"
            f"**Do you want to start the broadcast?**",
            reply_markup=buttons
        )

# ============ EXECUTE BROADCAST ============

async def execute_broadcast(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    session = user_data.get(user_id)
    
    if not session:
        await query.answer("Session expired!", show_alert=True)
        return
    
    content = session.get("content")
    targets = session.get("targets", [])
    item_type = session["type"]
    
    if not content or not targets:
        await query.answer("No content or targets!", show_alert=True)
        return
    
    total = len(targets)
    await query.message.edit_text(f"🔄 Broadcasting to {total} {item_type}(s)...\n0/{total} completed.")
    
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
            except:
                failed += 1
                failed_list.append(str(target_id))
        except Exception as e:
            print(f"Error: {e}")
            failed += 1
            failed_list.append(str(target_id))
        
        if i % 5 == 0 or i == total:
            await query.message.edit_text(
                f"🔄 Broadcasting...\n"
                f"✅ Success: {successful}\n"
                f"❌ Failed: {failed}\n"
                f"{i}/{total} completed."
            )
    
    # Final result with progress bar
    bar_length = 20
    progress_bar = "●" * bar_length
    
    result = f"**✅ {item_type.upper()} BROADCAST COMPLETED ✅**\n\n"
    result += f"<blockquote>📊:</b> [{progress_bar}] <code>100%</code></blockquote>\n\n"
    result += f"**📊 Total {item_type}s:** `{total}`\n"
    result += f"**✅ Successful:** `{successful}`\n"
    result += f"**❌ Failed:** `{failed}`"
    
    if failed_list and len(failed_list) <= 10:
        result += f"\n\n**Failed IDs:**\n" + "\n".join(f"`{iid}`" for iid in failed_list)
    
    await query.message.edit_text(result)
    
    # Cleanup
    if user_id in user_data:
        del user_data[user_id]
    await query.answer("Broadcast completed!")

# ============ CANCEL COMMAND ============

@Client.on_message(filters.command("cancel") & filters.private & is_owner_or_admin)
async def cancel_broadcast(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
        await message.reply("❌ Broadcast session cancelled.")
    else:
        await message.reply("No active broadcast session.")

# ============ AUTO-ADD GROUPS ============

@Client.on_message(filters.group)
async def auto_add_group(client: Client, message: Message):
    await add_global_group(message.chat.id)

# ============ QUICK COMMANDS ============

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

@Client.on_message(filters.command("delgroup") & filters.private & is_owner_or_admin)
async def del_group_cmd(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("Usage: /delgroup -10096022547")
    try:
        gid = int(message.command[1])
        if await remove_global_group(gid):
            await message.reply(f"✅ Group removed.")
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
            await message.reply(f"✅ Channel removed.")
        else:
            await message.reply("❌ Not found.")
    except:
        await message.reply("Invalid ID.")
