import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

# ======================= НАСТРОЙКИ =======================
BOT_TOKEN = "8822608059:AAGIt8tu0IcXOQ_RJIUsQ0PZZe7h-BuZFFY"
GROUP_ID = -5568247151
# =========================================================

logging.basicConfig(level=logging.WARNING)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
router = Router()
dp.include_router(router)
message_to_user: dict[int, int] = {}
banned_users: set[int] = set()


WELCOME_TEXT = (
    "Приветствую, оставьте пожалуйста свою заявку детально распишите: "
    "какую рекламу вы хотите, что за продукт, @username для связи"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id in banned_users:
        await message.answer("Менеджер заблокировал вам использование бота.")
        return
    await message.answer(WELCOME_TEXT)


# ---------- Сообщения от пользователей в боте ----------
@router.message(F.chat.type == "private")
async def handle_user_message(message: Message):
    user = message.from_user
    if user.id in banned_users:
        await message.answer("Менеджер заблокировал вам использование бота.")
        return

    username = f"@{user.username}" if user.username else "без username"
    header = f"Сообщение от {username} (ID: {user.id}):\n\n"

    if message.text:
        sent = await bot.send_message(
            chat_id=GROUP_ID,
            text=header + message.text,
        )
        message_to_user[sent.message_id] = user.id
    else:
        caption = header + (message.caption or "")
        sent = await message.copy_to(chat_id=GROUP_ID, caption=caption)
        message_to_user[sent.message_id] = user.id

    await message.answer("Ваша заявка отправлена менеджеру. Ожидайте ответа.")


# ---------- Ответ менеджера в группе (реплай на сообщение бота) ----------
@router.message(F.chat.id == GROUP_ID, F.reply_to_message)
async def handle_manager_reply(message: Message):
    replied = message.reply_to_message

    if replied.from_user is None or replied.from_user.id != bot.id:
        return

    user_id = message_to_user.get(replied.message_id)
    if not user_id:
        return

    text = message.text or message.caption or ""

    if text.startswith("/ban"):
        # Извлекаем причину
        parts = text.split(maxsplit=1)
        reason = parts[1].strip() if len(parts) > 1 else "причина не указана"

        banned_users.add(user_id)

        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "Менеджер заблокировал вам использование бота "
                    f"по причине: {reason}"
                ),
            )
        except Exception as e:
            await message.reply(f"Пользователь забанен, но уведомление не доставлено: {e}")
            return

        await message.reply(f"Пользователь {user_id} забанен. Причина: {reason}")
        return

    # ---------- /unban ------------
    if text.startswith("/unban"):
        if user_id in banned_users:
            banned_users.discard(user_id)
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="Менеджер снял с вас блокировку. Можете снова отправлять заявки.",
                )
            except Exception:
                pass
            await message.reply(f"Пользователь {user_id} разбанен.")
        else:
            await message.reply(f"Пользователь {user_id} не в бане.")
        return

    # ---------- Обычный ответ ----------
    reply_text = f"Ответ от менеджера:\n\n{text}"

    try:
        await bot.send_message(chat_id=user_id, text=reply_text)
        await message.reply("Ответ отправлен.")
    except Exception as e:
        await message.reply(f"Не удалось отправить ответ: {e}")


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())