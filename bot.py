import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import json

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ID АДМИНИСТРАТОРА ==========
ADMIN_ID = 470740095  # ВАШ ID

# ========== ХРАНИЛИЩЕ ДАННЫХ ==========
DATA_FILE = "users_data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== КЛАВИАТУРЫ ==========

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
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {
            "name": None,
            "day": 0,
            "survey": False,
            "rating": None,
            "completed": False,
            "start_date": None,
            "completed_date": None
        }
    return data[user_id_str]

def save_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

# ========== КОМАНДА /start ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    welcome_text = """
👋 Привет! Я — Onboard AI, твой цифровой наставник.

🔥 Используй кнопки ниже, чтобы начать адаптацию!

💡 Если ты здесь впервые — просто нажми на любую кнопку, и я попрошу представиться.
"""
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())

# ========== КОМАНДА /stats (ТОЛЬКО ДЛЯ АДМИНА) ==========
@dp.message(Command("stats"))
async def stats_command(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, админ ли это
    if user_id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    
    data = load_data()
    
    if not data:
        await message.answer("📊 Нет данных о сотрудниках.")
        return
    
    total = len(data)
    completed = sum(1 for u in data.values() if u.get("completed", False))
    avg_rating = 0
    ratings = [u.get("rating", 0) for u in data.values() if u.get("rating")]
    if ratings:
        avg_rating = round(sum(ratings) / len(ratings), 1)
    
    stats_text = f"""
📊 **Статистика адаптации**

👥 Всего сотрудников: {total}
✅ Завершили адаптацию: {completed}
⭐ Средняя оценка уверенности: {avg_rating}/5

📋 **Список сотрудников:**
"""
    
    for user_id, u in data.items():
        name = u.get("name") or "Без имени"
        days = u.get("day", 0)
        status = "✅" if u.get("completed") else "🔄"
        rating = u.get("rating") or "—"
        stats_text += f"\n{status} {name} — День {days}/7, Оценка: {rating}/5"
    
    await message.answer(stats_text, parse_mode="Markdown")

# ========== ОБРАБОТЧИК ЛЮБЫХ ТЕКСТОВЫХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_any_text(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    if not user.get("name"):
        user["name"] = message.text.strip()
        user["start_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_user_data(user_id, user)
        
        welcome_text = f"""
🎉 Отлично, {user["name"]}! Я запомнил тебя.

Теперь я буду твоим проводником в мире проекта.

📅 Нажми "План адаптации", чтобы начать!
"""
        await message.answer(welcome_text, reply_markup=main_menu_keyboard())
        return
    
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
    
    if not user.get("name"):
        text = "👋 Давай познакомимся! Напиши своё имя."
    else:
        text = f"🏠 Главное меню, {user['name']}!\n\n{get_progress_bar(user.get('day', 0))}"
    
    await callback.message.answer(text, reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "guide")
async def handle_guide(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    
    if not user.get("name"):
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
    
    if not user.get("name"):
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
    
    if not user.get("name"):
        await callback.message.answer(
            "👋 Привет! Для начала давай познакомимся.\n\n"
            "Напиши своё имя, и я свяжу тебя с ментором! 🆘"
        )
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
    
    if not user.get("name"):
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
    
    if not user.get("name"):
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
    
    if not user.get("name"):
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
    
    user["day"] = max(user.get("day", 0), day_num)
    save_user_data(user_id, user)
    
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
    await callback.message.answer(f"{get_progress_bar(user.get('day', 0))}")
    
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
    
    user["rating"] = rating
    user["completed"] = True
    user["completed_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_user_data(user_id, user)
    
    report = f"""
📊 **Отчёт об адаптации**

👤 Сотрудник: {user['name']}
📅 Дней пройдено: {user.get('day', 0)}/7
⭐ Оценка уверенности: {rating}/5
📆 Дата завершения: {user['completed_date']}
"""
    
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode="Markdown")
    except:
        print("❌ Не удалось отправить отчёт админу")
    
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
    print("✅ Все функции активны!")
    print(f"👤 Администратор: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
