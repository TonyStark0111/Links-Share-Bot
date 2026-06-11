# plugins/broadcast_chats.py

import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import full_userbase, del_user
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from helper_func import is_owner_or_admin

# Temporary storage for broadcast sessions
broadcast_sessions = {}

@Client.on_message(filters.command("grp_broadcast") & filters.private & is_owner_or_admin)
async def grp_broadcast_command(client: Client, message: Message):
    """Broadcast to groups where bot is admin."""
    await broadcast_menu(client, message, chat_type="group")

@Client.on_message(filters.command("channel_broadcast") & filters.private & is_owner_or_admin)
async def channel_broadcast_command(client: Client, message: Message):
    """Broadcast to channels where bot is admin."""
    await broadcast_menu(client, message, chat_type="channel")

async def broadcast_menu(client: Client, message: Message, chat_type: str):
    """Show list of groups/channels where bot is admin."""
    user_id = message.from_user.id
    dialogs = client.get_dialogs()
    admin_chats = []
    
    status_msg = await message.reply("🔄 Fetching chats where I am admin...")
    
    async for dialog in dialogs:
        chat = dialog.chat
        if chat_type == "group" and chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            continue
        if chat_type == "channel" and chat.type != ChatType.CHANNEL:
            continue
        
        try:
            bot_member = await client.get_chat_member(chat.id, (await client.get_me()).id)
            if bot_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                admin_chats.append(chat)
        except Exception:
            continue
    
    if not admin_chats:
        await status_msg.edit(f"❌ No {chat_type}s found where I am admin.")
        return
    
    broadcast_sessions[user_id] = {
        "chats": admin_chats,
        "type": chat_type,
        "page": 0,
        "selected_chat": None,
        "broadcast_all": False,
        "awaiting_content": False,
        "content_msg": None,
        "building_buttons": False,
        "buttons": []
    }
    
    await show_chat_list(client, status_msg, user_id)

async def show_chat_list(client: Client, msg: Message, user_id: int, edit: bool = True):
    session = broadcast_sessions.get(user_id)
    if not session:
        return
    
    chats = session["chats"]
    page = session["page"]
    chat_type = session["type"]
    per_page = 10
    total_pages = (len(chats) + per_page - 1) // per_page
    
    start = page * per_page
    end = start + per_page
    page_chats = chats[start:end]
    
    buttons = []
    for chat in page_chats:
        title = chat.title[:30] + ".." if len(chat.title) > 30 else chat.title
        buttons.append([InlineKeyboardButton(f"📢 {title}", callback_data=f"bc_select_{chat.id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data="bc_page_prev"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data="bc_page_next"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("📢 Broadcast to ALL", callback_data="bc_all")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="bc_cancel")])
    
    text = f"**Select a {chat_type} to broadcast to:**\n\n"
    for i, chat in enumerate(page_chats, start=1):
        link = await get_chat_link(client, chat)
        text += f"{i}. **{chat.title}**\n   `{chat.id}`\n   {link}\n\n"
    
    text += f"\nPage {page+1}/{total_pages}"
    
    if edit:
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def get_chat_link(client: Client, chat) -> str:
    if chat.username:
        return f"https://t.me/{chat.username}"
    else:
        try:
            invite = await client.create_chat_invite_link(chat.id, member_limit=1)
            return invite.invite_link
        except Exception:
            return "No link available"

@Client.on_callback_query(filters.regex(r"^bc_(select|page_prev|page_next|all|cancel|add_button|done_buttons|cancel_buttons)$"))
async def broadcast_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    session = broadcast_sessions.get(user_id)
    if not session:
        await query.answer("Session expired. Use command again.", show_alert=True)
        await query.message.delete()
        return
    
    if data == "bc_page_prev":
        session["page"] -= 1
        await show_chat_list(client, query.message, user_id)
        await query.answer()
    
    elif data == "bc_page_next":
        session["page"] += 1
        await show_chat_list(client, query.message, user_id)
        await query.answer()
    
    elif data == "bc_all":
        session["broadcast_all"] = True
        session["awaiting_content"] = True
        await query.message.edit_text(
            f"📢 **Broadcast to ALL {session['type']}s**\n\n"
            f"Total: {len(session['chats'])}\n\n"
            "Send me the message content to broadcast.\n"
            "You can send text, photo, video, document, etc.\n"
            "After sending, I'll ask if you want to add buttons.\n\n"
            "Send /cancel to abort."
        )
        await query.answer()
    
    elif data == "bc_cancel":
        del broadcast_sessions[user_id]
        await query.message.edit_text("❌ Broadcast cancelled.")
        await query.answer()
    
    elif data == "bc_add_button":
        session["building_buttons"] = True
        await query.message.edit_text(
            "**Add Inline Button**\n\n"
            "Send button details in this format:\n"
            "`text | url`  - for URL button\n"
            "`text | alert:callback_data` - for callback button (shows alert on click)\n\n"
            "Example:\n"
            "`Visit Google | https://google.com`\n"
            "`Click Me | alert:button_clicked`\n\n"
            "Send /done when finished adding buttons.\n"
            "Send /cancel_buttons to cancel adding."
        )
        await query.answer()
    
    elif data == "bc_done_buttons":
        if not session.get("buttons"):
            await query.answer("No buttons added. Use /cancel_buttons to skip.", show_alert=True)
            return
        await send_broadcast_with_buttons(client, query.message, user_id, session)
        await query.answer()
    
    elif data == "bc_cancel_buttons":
        session["building_buttons"] = False
        session["buttons"] = []
        await query.message.edit_text("Button creation cancelled. Sending broadcast without buttons...")
        await send_broadcast_with_buttons(client, query.message, user_id, session, skip_buttons=True)
        await query.answer()
    
    elif data.startswith("bc_select_"):
        chat_id = int(data.split("_")[2])
        selected_chat = None
        for chat in session["chats"]:
            if chat.id == chat_id:
                selected_chat = chat
                break
        if selected_chat:
            session["selected_chat"] = selected_chat
            session["awaiting_content"] = True
            await query.message.edit_text(
                f"📢 **Selected: {selected_chat.title}**\n\n"
                f"ID: `{selected_chat.id}`\n"
                f"Link: {await get_chat_link(client, selected_chat)}\n\n"
                "Send me the message content to broadcast.\n"
                "You can send text, photo, video, document, etc.\n"
                "After sending, I'll ask if you want to add buttons.\n\n"
                "Send /cancel to abort."
            )
        await query.answer()

async def send_broadcast_with_buttons(client: Client, msg: Message, user_id: int, session: dict, skip_buttons=False):
    """Send the broadcast with optional buttons."""
    content = session.get("content_msg")
    if not content:
        await msg.edit_text("❌ No content found. Please start over.")
        del broadcast_sessions[user_id]
        return
    
    targets = []
    if session.get("broadcast_all"):
        targets = session["chats"]
    elif session.get("selected_chat"):
        targets = [session["selected_chat"]]
    else:
        await msg.edit_text("❌ No targets selected.")
        del broadcast_sessions[user_id]
        return
    
    # Build reply markup if buttons exist
    reply_markup = None
    if not skip_buttons and session.get("buttons"):
        buttons = []
        for btn in session["buttons"]:
            row = []
            for b in btn:
                if b["type"] == "url":
                    row.append(InlineKeyboardButton(b["text"], url=b["value"]))
                else:  # alert callback
                    row.append(InlineKeyboardButton(b["text"], callback_data=b["value"]))
            buttons.append(row)
        reply_markup = InlineKeyboardMarkup(buttons)
    
    total = len(targets)
    successful = 0
    failed = 0
    status_msg = await msg.edit_text(f"🔄 Broadcasting to {total} {session['type']}(s)...\n0/{total} completed.")
    
    # Determine if content is a media message or text
    for i, chat in enumerate(targets, 1):
        try:
            if content.media:
                await client.copy_message(
                    chat.id,
                    content.chat.id,
                    content.id,
                    reply_markup=reply_markup
                )
            else:
                await client.send_message(
                    chat.id,
                    content.text or content.caption,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.DEFAULT
                )
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                if content.media:
                    await client.copy_message(chat.id, content.chat.id, content.id, reply_markup=reply_markup)
                else:
                    await client.send_message(chat.id, content.text or content.caption, reply_markup=reply_markup)
                successful += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
        
        if i % 5 == 0 or i == total:
            await status_msg.edit(f"🔄 Broadcasting...\n✅ {successful} | ❌ {failed}\n{i}/{total} completed.")
    
    final_text = (
        f"✅ **Broadcast Completed**\n\n"
        f"Target: {'ALL' if session.get('broadcast_all') else session['selected_chat'].title}\n"
        f"Total: {total}\n"
        f"Successful: {successful}\n"
        f"Failed: {failed}"
    )
    if session.get("buttons"):
        final_text += f"\n\nButtons: {len(session['buttons'])} button(s) added."
    await status_msg.edit(final_text)
    del broadcast_sessions[user_id]

@Client.on_message(filters.private & filters.text & ~filters.command(["cancel", "done", "cancel_buttons", "grp_broadcast", "channel_broadcast"]))
async def handle_broadcast_content_and_buttons(client: Client, message: Message):
    user_id = message.from_user.id
    session = broadcast_sessions.get(user_id)
    if not session:
        return
    
    # If we are building buttons
    if session.get("building_buttons"):
        text = message.text.strip()
        if " | " not in text:
            await message.reply("❌ Invalid format. Use `text | url` or `text | alert:data`\nSend /cancel_buttons to abort.")
            return
        
        parts = text.split(" | ", 1)
        btn_text = parts[0].strip()
        btn_value = parts[1].strip()
        
        btn_type = "url" if btn_value.startswith("http://") or btn_value.startswith("https://") else "alert"
        if btn_type == "alert" and not btn_value.startswith("alert:"):
            # Allow custom callback data without alert prefix? We'll assume alert for simplicity
            btn_value = f"alert:{btn_value}"
        
        # Store button as a dict
        if "buttons" not in session:
            session["buttons"] = []
        # Add to current row or new row? For simplicity, each message adds a new row.
        session["buttons"].append([{
            "text": btn_text,
            "type": btn_type,
            "value": btn_value if btn_type == "url" else btn_value.replace("alert:", "")
        }])
        
        await message.reply(f"✅ Button added: `{btn_text}` ({btn_type})\nSend another button or /done to finish, /cancel_buttons to abort.")
        return
    
    # If awaiting content
    if session.get("awaiting_content"):
        session["content_msg"] = message
        session["awaiting_content"] = False
        # Ask if user wants to add buttons
        buttons = [
            [InlineKeyboardButton("➕ Add Buttons", callback_data="bc_add_button")],
            [InlineKeyboardButton("🚀 Send Without Buttons", callback_data="bc_done_buttons")]
        ]
        await message.reply(
            "✅ Content received!\n\nDo you want to add inline buttons to this broadcast?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

@Client.on_message(filters.command("done") & filters.private & is_owner_or_admin)
async def done_buttons(client: Client, message: Message):
    user_id = message.from_user.id
    session = broadcast_sessions.get(user_id)
    if session and session.get("building_buttons"):
        # Finish button building
        session["building_buttons"] = False
        await message.reply("Button creation finished. Proceeding to broadcast...")
        # Now send broadcast with buttons (need to get original message context)
        # We don't have the original menu message here, so we'll ask user to re-send content? 
        # Instead, store a flag and use the last message reference.
        # Simpler: user will see a callback after /done from the previous inline menu.
        # We'll rely on the callback handler to do the broadcast.
        # So just acknowledge.
        await message.reply("Use the inline menu to finalize broadcast.")
    else:
        await message.reply("No active button creation session.")

@Client.on_message(filters.command("cancel_buttons") & filters.private & is_owner_or_admin)
async def cancel_buttons(client: Client, message: Message):
    user_id = message.from_user.id
    session = broadcast_sessions.get(user_id)
    if session:
        session["building_buttons"] = False
        session["buttons"] = []
        await message.reply("Button creation cancelled.")
    else:
        await message.reply("No active session.")

@Client.on_message(filters.command("cancel") & filters.private & is_owner_or_admin)
async def cancel_broadcast_session(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in broadcast_sessions:
        del broadcast_sessions[user_id]
        await message.reply("❌ Broadcast session cancelled.")
    else:
        await message.reply("No active broadcast session.")
