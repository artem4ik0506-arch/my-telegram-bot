import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# === НАЛАШТУВАННЯ ===
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"  # Токен від BotFather
ADMIN_GROUP_ID = -1001234567890  # ID вашої спільної групи з другом

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Текст-попередження для ефекту "сну" на Render
SLEEP_WARNING = "\n\n_⏳ (Повідомлення може зайняти трохи часу, тому що сервер може переходити в режим сну)_"

# Словники для збереження активних сесій
active_chats = {}       # user_id -> admin_id
admin_active_chats = {} # admin_id -> user_id

# Клавіатура для адміна під час розмови
admin_finish_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Завершити чат")]],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 **Добрий день! Вас вітає Допомога 7-В!** 🎓✨\n\n"
        "Напишіть, з чим вам допомогти, або подайте ідею 💡 — і незабаром адміністратор вам відповість!"
        + SLEEP_WARNING,
        parse_mode="Markdown"
    )

@dp.message(F.text == "❌ Завершити чат")
async def finish_chat_admin(message: types.Message):
    admin_id = message.from_user.id
    if admin_id in admin_active_chats:
        user_id = admin_active_chats[admin_id]
        
        # Видаляємо зв'язок
        del admin_active_chats[admin_id]
        if user_id in active_chats:
            del active_chats[user_id]
        
        # Сповіщаємо обох
        await message.answer("✅ Чат успішно завершено.", reply_markup=types.ReplyKeyboardRemove())
        await bot.send_message(
            user_id, 
            "✨ Адміністратор завершив діалог. Дякуємо за звернення! Якщо знадобиться ще допомога — просто напишіть сюди знову."
            + SLEEP_WARNING,
            parse_mode="Markdown"
        )
    else:
        await message.answer("У вас немає активного чату.")

@dp.callback_query(F.data.startswith("claim_"))
async def claim_chat(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    admin_id = callback.from_user.id

    if user_id in active_chats and active_chats[user_id] is not None:
        await callback.answer("⚠️ Цей чат уже хтось взяв!", show_alert=True)
        return

    # Фіксуємо діалог
    active_chats[user_id] = admin_id
    admin_active_chats[admin_id] = user_id

    await callback.answer("Ви взяли це звернення!")
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ **Взято в роботу адміном:** {callback.from_user.full_name}"
    )

    # Пишемо адміну в приват
    await bot.send_message(
        admin_id,
        f"🤝 Ви розпочали діалог із користувачем (`ID: {user_id}`).\n"
        f"Усі ваші наступні повідомлення будуть пересилатися йому.\n"
        f"Щоб закрити чат, натисніть кнопку нижче 👇",
        reply_markup=admin_finish_kb
    )
    
    # Сповіщаємо користувача
    await bot.send_message(
        user_id, 
        "👨‍💻 Адміністратор підключився до чату і готовий спілкуватися!" + SLEEP_WARNING,
        parse_mode="Markdown"
    )

@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # Якщо пише адмін в особисті боту під час активного чату
    if user_id in admin_active_chats:
        target_user_id = admin_active_chats[user_id]
        await bot.send_message(target_user_id, message.text)
        return

    # Якщо це звичайне повідомлення від користувача в особистих боту
    if message.chat.type == "private":
        # Якщо чат вже підключено до адміна
        if user_id in active_chats and active_chats[user_id] is not None:
            admin_id = active_chats[user_id]
            await bot.send_message(admin_id, f"📩 **Повідомлення від користувача:**\n{message.text}")
        else:
            # Якщо це нове звернення
            active_chats[user_id] = None
            
            await message.answer(
                "📥 **Ваше повідомлення надіслано адміністраторам!**\n"
                "Зачекайте, будь ласка, незабаром вони вам дадуть відповідь ⌛"
                + SLEEP_WARNING,
                parse_mode="Markdown"
            )

            # Формуємо інформацію про користувача
            username = f"@{message.from_user.username}" if message.from_user.username else "Не вказано"
            user_link = f"tg://user?id={user_id}"

            # Кнопка для адмінів у групі
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Взяти в роботу 💬", callback_data=f"claim_{user_id}")
            ]])

            await bot.send_message(
                ADMIN_GROUP_ID,
                f"📥 **Нове звернення!**\n\n"
                f"👤 **Користувач:** [{message.from_user.full_name}]({user_link})\n"
                f"🏷 **Юзернейм:** {username}\n"
                f"🆔 **ID:** `{user_id}`\n\n"
                f"💬 **Повідомлення:**\n{message.text}",
                reply_markup=kb,
                parse_mode="Markdown"
            )

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())