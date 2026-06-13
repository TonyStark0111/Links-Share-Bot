from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot

@Bot.on_message(filters.command("menu") & filters.private)
async def show_menu(client: Bot, message: Message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Button 1", callback_data="btn_1")],
        [InlineKeyboardButton("Button 2", callback_data="btn_2")],
        [InlineKeyboardButton("Button 3", callback_data="btn_3")]
    ])
    await message.reply("Click any button:", reply_markup=buttons)

@Bot.on_callback_query()
async def handle_buttons(client: Bot, query: CallbackQuery):
    print(f"Received callback: {query.data}")
    await query.answer(f"You clicked: {query.data}", show_alert=True)
