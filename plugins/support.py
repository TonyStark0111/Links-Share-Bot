from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user, support_messages_collection


# =========================
# DATABASE FUNCTIONS
# =========================

async def save_mapping(admin_id: int, forwarded_msg_id: int, user_id: int):
    try:
        await support_messages_collection.update_one(
            {
                "admin_id": admin_id,
                "forwarded_msg_id": forwarded_msg_id
            },
            {
                "$set": {
                    "user_id": user_id
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"save_mapping error: {e}")


async def get_user_id(admin_id: int, forwarded_msg_id: int):
    try:
        doc = await support_messages_collection.find_one(
            {
                "admin_id": admin_id,
                "forwarded_msg_id": forwarded_msg_id
            }
        )

        if doc:
            return doc["user_id"]

        return None

    except Exception as e:
        print(f"get_user_id error: {e}")
        return None


# =========================
# USER -> ADMIN
# =========================

@Bot.on_message(
    filters.private
    & ~filters.command(["start"])
)
async def forward_to_admin(client: Bot, message: Message):

    if not message.from_user:
        return

    user = message.from_user
    user_id = user.id

    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return

    await add_user(user_id)

    username = (
        f"@{user.username}"
        if user.username
        else "No Username"
    )

    mention = (
        f'<a href="tg://user?id={user_id}">{user.first_name}</a>'
    )

    dc_id = getattr(user, "dc_id", "Unknown")

    header = (
        f"📨 <b>New Support Message</b>\n\n"
        f"👤 <b>Name:</b> {user.first_name or ''} {user.last_name or ''}\n"
        f"♀️ <b>Mention:</b> {mention}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🪪 <b>DM ID:</b> <code>tg://user?id={user_id}</code>\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🌎 <b>DC:</b> {dc_id}"
    )

    for admin_id in SUPPORT_ADMINS:
        try:

            info_msg = await client.send_message(
                chat_id=admin_id,
                text=header,
                parse_mode="html",
                disable_web_page_preview=True
            )

            await save_mapping(
                admin_id,
                info_msg.id,
                user_id
            )

            copied_msg = await message.copy(admin_id)

            await save_mapping(
                admin_id,
                copied_msg.id,
                user_id
            )

        except Exception as e:
            print(
                f"Failed sending support message "
                f"to {admin_id}: {e}"
            )

    try:
        await message.reply_text(
            "✅ Your message has been sent to support."
        )
    except:
        pass


# =========================
# ADMIN -> USER
# =========================

@Bot.on_message(
    filters.private
    & filters.reply
)
async def reply_to_user(client: Bot, message: Message):

    if not message.from_user:
        return

    admin_id = message.from_user.id

    if (
        admin_id not in SUPPORT_ADMINS
        and admin_id != OWNER_ID
    ):
        return

    replied_message = message.reply_to_message

    if not replied_message:
        return

    user_id = await get_user_id(
        admin_id,
        replied_message.id
    )

    if not user_id:
        return

    try:

        # TEXT
        if message.text:

            await client.send_message(
                chat_id=user_id,
                text=f"💬 Support Reply\n\n{message.text}"
            )

        # ALL MEDIA
        else:
            await message.copy(user_id)

        await message.reply_text(
            f"✅ Reply sent to user {user_id}"
        )

    except Exception as e:

        await message.reply_text(
            f"❌ Failed to send reply\n\n{e}"
        )
