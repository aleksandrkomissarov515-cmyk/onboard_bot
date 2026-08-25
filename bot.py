import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ХРАНИЛИЩЕ ДАННЫХ ==========
user_data = {}  # {user_id: {"name": str, "day": int, "quiz": bool, "survey": bool}}

# ID чата для отчётов (ЗАМЕНИТЕ НА РЕАЛЬНЫЙ)
REPORT_CHAT_ID = -1001234567890

# ========== ГЛАВНОЕ МЕНЮ ==========

def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗺️ План адаптации", callback_data="guide"),
        InlineKeyboardButton(text="❓ FAQ", callback_data="faq")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Контакты", callback_data="contacts"),
        InlineKeyboardButton(text="📚 Ресурсы", callback_data="resources")
    )
    builder.row(
        InlineKeyboardButton(text="🆘 Связаться с ментором", callback_data="mentor"),
        InlineKeyboardButton(text="📋 Помощь", callback_data="help")
    )
    return builder.as_markup()

def days_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(1, 8):
        builder.add(InlineKeyboardButton(text=f"📅 День {i}", callback_data=f"day_{i}"))
    builder.adjust(4)
    return builder.as_markup()

def faq_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=f"❓ Вопрос {i}", callback_data=f"faq_{i}"))
    builder.adjust(3)
    return builder.as_markup()

def back_to_guide_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к плану", callback_data="guide")]
    ])

def back_to_faq_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к FAQ", callback_data="faq")]
    ])

def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu")]
    ])

def quiz_keyboard(quiz_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data=f"quiz_{quiz_id}_1"),
         InlineKeyboardButton(text="2️⃣", callback_data=f"quiz_{quiz_id}_2"),
         InlineKeyboardButton(text="3️⃣", callback_data=f"quiz_{quiz_id}_3")]
    ])

def survey_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 ⭐", callback_data="survey_1"),
         InlineKeyboardButton(text="2 ⭐⭐", callback_data="survey_2"),
         InlineKeyboardButton(text="3 ⭐⭐⭐", callback_data="survey_3"),
         InlineKeyboardButton(text="4 ⭐⭐⭐⭐", callback_data="survey_4"),
         InlineKeyboardButton(text="5 ⭐⭐⭐⭐⭐", callback_data="survey_5")]
    ])

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_progress_bar(day):
    filled = min(day, 7)
    empty = 7 - filled
    bar = "█" * filled + "░" * empty
    percent = round((filled / 7) * 100)
    return f"📊 Прогресс: {bar} {percent}%"

def get_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"name": None, "day": 0, "quiz": False, "survey": False}
    return user_data[user_id]

def ask_name_if_needed(callback: types.CallbackQuery, action_callback):
    """Проверяет, есть ли имя. Если нет — просит представиться."""
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    if not user["name"]:
        # Удаляем предыдущее сообщение
        try:
            await callback.message.delete()
        except:
            pass
        
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и мы продолжим! 🚀"
        )
        await callback.answer()
        return False
    
    return True

# ========== КОМАНДА /start ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    # Всегда показываем главное меню с кнопками
    welcome_text = """
👋 Привет! Я — Onboard AI, твой цифровой наставник.

🔥 Используй кнопки ниже, чтобы начать адаптацию!

💡 Если ты здесь впервые — просто нажми на любую кнопку, и я попрошу представиться.
"""
    
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())

# ========== ОБРАБОТЧИК ЛЮБЫХ ТЕКСТОВЫХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_any_text(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    # Если имя ещё не введено — сохраняем
    if not user["name"]:
        user["name"] = message.text.strip()
        welcome_text = f"""
🎉 Отлично, {user["name"]}! Я запомнил тебя.

Теперь я буду твоим проводником в мире проекта.

📅 Нажми "План адаптации", чтобы начать!
"""
        await message.answer(welcome_text, reply_markup=main_menu_keyboard())
        return
    
    # Если имя уже есть — отправляем в главное меню
    await message.answer(
        f"😊 {user['name']}, я работаю только по кнопкам!\n\nИспользуй меню ниже 👇",
        reply_markup=main_menu_keyboard()
    )

# ========== ОБРАБОТЧИКИ КНОПОК ==========

@dp.callback_query(lambda c: c.data == "menu")
async def handle_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    await callback.message.delete()
    
    if not user["name"]:
        text = "👋 Давай познакомимся! Напиши своё имя."
    else:
        text = f"🏠 Главное меню, {user['name']}!\n\n{get_progress_bar(user['day'])}"
    
    await callback.message.answer(text, reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "guide")
async def handle_guide(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    # Если имени нет — просим представиться
    if not user["name"]:
        await callback.message.delete()
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и мы начнём адаптацию! 🚀"
        )
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer(
        f"🗺️ {user['name']}, выбери день:",
        reply_markup=days_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq")
async def handle_faq(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    if not user["name"]:
        await callback.message.delete()
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и я отвечу на все вопросы! 🚀"
        )
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer("❓ Выбери вопрос:", reply_markup=faq_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "mentor")
async def handle_mentor(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    await callback.message.delete()
    
    if not user["name"]:
        mentor_text = """
👋 Привет! Для начала давай познакомимся.

Напиши своё имя, и я свяжу тебя с ментором! 🆘
"""
        await callback.message.answer(mentor_text)
        await callback.answer()
        return
    
    mentor_text = f"""
🆘 {user['name']}, не переживай! Я помогу тебе.

Можешь связаться с ментором напрямую:
@mentor_username

Или напиши в общий чат:
@chat_username

Ты не один! 💪
"""
    await callback.message.answer(mentor_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "contacts")
async def handle_contacts(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    if not user["name"]:
        await callback.message.delete()
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и я покажу контакты команды! 👥"
        )
        await callback.answer()
        return
    
    await callback.message.delete()
    contacts_text = """
👥 Ключевые люди:

🟢 Руководитель — @username
🟡 Тимлид — @username
🔵 Ментор — @username
🟣 DevOps — @username
"""
    await callback.message.answer(contacts_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "resources")
async def handle_resources(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    if not user["name"]:
        await callback.message.delete()
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и я покажу все полезные ресурсы! 📚"
        )
        await callback.answer()
        return
    
    await callback.message.delete()
    resources_text = """
📚 Ресурсы:

📁 Документация — [ссылка]
📊 Jira — [ссылка]
💬 Чат — [ссылка]
"""
    await callback.message.answer(resources_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "help")
async def handle_help(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    if not user["name"]:
        await callback.message.delete()
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и я покажу, как работает бот! 📋"
        )
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer(
        "📋 Используй кнопки меню для навигации!",
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()

# ========== ДНИ С ВИКТОРИНОЙ ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("day_"))
async def handle_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    day_num = int(callback.data.split("_")[1])
    
    user["day"] = max(user["day"], day_num)
    
    days_info = {
        1: "📅 **День 1: Знакомство**\n\n✅ Познакомиться с командой\n✅ Получить доступы\n✅ Установить ПО",
        2: "📅 **День 2: Обзор проекта**\n\n✅ Изучить цели\n✅ Понять свою роль\n✅ Посмотреть статус",
        3: "📅 **День 3: Инструменты**\n\n✅ Изучить стек\n✅ Настроить окружение\n✅ Запустить проект",
        4: "📅 **День 4: Процессы**\n\n✅ Как планируем задачи\n✅ Как делаем ревью\n✅ Как тестируем",
        5: "📅 **День 5: Первая задача**\n\n✅ Взять задачу\n✅ Выполнить её\n✅ Отправить на проверку",
        6: "📅 **День 6: Обратная связь**\n\n✅ Обсудить впечатления\n✅ Задать вопросы\n✅ Получить фидбек",
        7: "📅 **День 7: Итоги**\n\n✅ Подвести итоги\n✅ Обсудить план\n✅ Чувствовать себя уверенно 💪"
    }
    
    await callback.message.delete()
    await callback.message.answer(days_info.get(day_num, "❌ День не найден"), parse_mode="Markdown")
    await callback.message.answer(f"{get_progress_bar(user['day'])}")
    
    if day_num < 7:
        await callback.message.answer("🧠 **Викторина:** Ответь на вопрос!", parse_mode="Markdown")
        await ask_quiz(callback.message, day_num)
    else:
        await callback.message.answer("📊 **Ты прошёл всю адаптацию! 🎉**\n\nОтветь на несколько вопросов.", parse_mode="Markdown")
        await ask_survey(callback.message)
    
    await callback.message.answer("🔙 Вернуться к плану:", reply_markup=back_to_guide_keyboard())
    await callback.answer()

# ========== ВИКТОРИНА ==========

async def ask_quiz(message: Message, day: int):
    quizzes = {
        1: {"question": "Что нужно сделать в первый день?", "correct": 1},
        2: {"question": "Что важно изучить во второй день?", "correct": 1},
        3: {"question": "Что нужно сделать в третий день?", "correct": 1},
        4: {"question": "Что такое код-ревью?", "correct": 1},
        5: {"question": "Что делать с первой задачей?", "correct": 1},
        6: {"question": "Зачем нужна обратная связь?", "correct": 1},
    }
    
    quiz = quizzes.get(day)
    if not quiz:
        return
    
    await message.answer(f"🧠 **{quiz['question']}**", parse_mode="Markdown", reply_markup=quiz_keyboard(day))

@dp.callback_query(lambda c: c.data and c.data.startswith("quiz_"))
async def handle_quiz(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    day = int(parts[1])
    answer = int(parts[2])
    
    quizzes = {1: {"correct": 1}, 2: {"correct": 1}, 3: {"correct": 1}, 4: {"correct": 1}, 5: {"correct": 1}, 6: {"correct": 1}}
    correct = quizzes.get(day, {}).get("correct")
    
    if answer == correct:
        await callback.message.answer("✅ **Правильно! Отлично!** 🎉", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ **Неправильно. Попробуй ещё раз!**", parse_mode="Markdown")
    
    await callback.answer()

# ========== ОПРОС ==========

async def ask_survey(message: Message):
    await message.answer("📊 **Оцени уверенность в проекте (1–5):**", parse_mode="Markdown", reply_markup=survey_keyboard())

@dp.callback_query(lambda c: c.data and c.data.startswith("survey_"))
async def handle_survey(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    rating = int(callback.data.split("_")[1])
    
    user["survey"] = True
    
    report = f"""
📊 **Отчёт об адаптации**

👤 Сотрудник: {user['name']}
📅 Дней пройдено: {user['day']}/7
⭐ Оценка уверенности: {rating}/5
📆 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
    
    try:
        await bot.send_message(chat_id=REPORT_CHAT_ID, text=report, parse_mode="Markdown")
    except:
        print("❌ Не удалось отправить отчёт в чат")
    
    await callback.message.delete()
    await callback.message.answer(f"""
📊 **Спасибо за обратную связь, {user['name']}!**

Твоя оценка: {rating}/5 ⭐

Ты прошёл полный курс адаптации! 🎉
""", reply_markup=main_menu_keyboard())
    await callback.answer()

# ========== FAQ ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("faq_"))
async def handle_faq_callback(callback: types.CallbackQuery):
    faq_num = int(callback.data.split("_")[1])
    faq_info = {
        1: "❓ Где взять доступы?\n\nОбратись к наставнику или тимлиду.",
        2: "❓ Как настроить окружение?\n\nВсё в документации: [ссылка]",
        3: "❓ Кто мой наставник?\n\n@mentor_username",
        4: "❓ Где документы?\n\nNotion/Confluence: [ссылка]",
        5: "❓ Когда встречи?\n\nDaily в 10:00 по Москве"
    }
    await callback.message.delete()
    await callback.message.answer(faq_info.get(faq_num, "❌ Вопрос не найден"))
    await callback.message.answer("🔙 Назад:", reply_markup=back_to_faq_keyboard())
    await callback.answer()

# ========== ЗАПУСК ==========

async def main():
    print("🤖 Бот Onboard AI запущен!")
    print("✅ Работает только через кнопки!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
