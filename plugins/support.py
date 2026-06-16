import asyncio
from pyrogram import filters
from pyrogram.types import Message
from bot import Bot
from config import SUPPORT_ADMINS, OWNER_ID
from database.database import add_user, support_messages_collection


# =========================
# DATABASE HELPERS
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
        data = await support_messages_collection.find_one(
            {
                "admin_id": admin_id,
                "forwarded_msg_id": forwarded_msg_id
            }
        )

        if data:
            return data["user_id"]

        return None

    except Exception as e:
        print(f"get_user_id error: {e}")
        return None


# =========================
# USER -> ADMIN
# =========================

@Bot.on_message(
    filters.private
    & ~filters.reply
    & ~filters.command(["start"])
)
async def forward_to_admin(client: Bot, message: Message):

    if not message.from_user:
        return

    user = message.from_user
    user_id = user.id

    await add_user(user_id)

    # Ignore admin messages
    if user_id in SUPPORT_ADMINS or user_id == OWNER_ID:
        return

    # Fetch full user info to get the Data Centre (DC) ID
    dc_id = "Unknown"
    try:
        full_user = await client.get_users(user_id)
        if full_user.dc_id:
            dc_id = f"{full_user.dc_id}"
    except Exception as e:
        print(f"Failed to fetch DC ID: {e}")

    username = f"@{user.username}" if user.username else "No Username"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    header = (
        f"📨 **New Support Message**\n\n"
        f"👤 **Name:** {full_name}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"🔗 **Username:** {username}\n"
        f"🪪 **DM iD:** [Link](tg://user?id={user_id})\n"
        f"🌎 **DC:** {dc_id}"
    )

    for admin_id in SUPPORT_ADMINS:
        try:
            # Send user info
            info_msg = await client.send_message(
                admin_id,
                header
            )

            await save_mapping(
                admin_id,
                info_msg.id,
                user_id
            )

            # Copy original message
            copied = await message.copy(admin_id)

            await save_mapping(
                admin_id,
                copied.id,
                user_id
            )

        except Exception as e:
            print(f"Failed sending to admin {admin_id}: {e}")

    try:
        await message.reply_text(
            "✅ Your message has been sent to support."
        )
    except:
        pass


# =========================
# ADMIN -> USER
# =========================

@Bot.on_message(filters.private & filters.reply)
async def reply_to_user(client: Bot, message: Message):

    if not message.from_user:
        return

    admin_id = message.from_user.id

    if admin_id not in SUPPORT_ADMINS and admin_id != OWNER_ID:
        return

    replied = message.reply_to_message

    if not replied:
        return

    user_id = await get_user_id(
        admin_id,
        replied.id
    )

    if not user_id:
        return

    try:

        # TEXT
        if message.text:
            await client.send_message(
                user_id,
                f"💬 Support Reply:\n\n{message.text}"
            )

        # PHOTO
        elif message.photo:
            await message.copy(user_id)

        # VIDEO
        elif message.video:
            await message.copy(user_id)

        # DOCUMENT
        elif message.document:
            await message.copy(user_id)

        # AUDIO
        elif message.audio:
            await message.copy(user_id)

        # VOICE
        elif message.voice:
            await message.copy(user_id)

        # STICKER
        elif message.sticker:
            await message.copy(user_id)

        # ANIMATION/GIF
        elif message.animation:
            await message.copy(user_id)

        # ANY OTHER MEDIA
        else:
            await message.copy(user_id)

        await message.reply_text(
            f"✅ Reply sent to user `{user_id}`"
        )

    except Exception as e:
        await message.reply_text(
            f"❌ Failed to send reply\n\n{e}"
        )
