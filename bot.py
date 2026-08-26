import os
import asyncio
import logging
import sqlite3
import csv
from datetime import datetime
from io import BytesIO, StringIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import gspread
from google.oauth2.service_account import Credentials

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен не найден! Проверьте файл .env")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ID АДМИНИСТРАТОРА ==========
ADMIN_ID = 470740095

# ========== GOOGLE SHEETS ==========
def init_google_sheets():
    """Подключение к Google Sheets"""
    try:
        if not os.path.exists("credentials.json"):
            print("❌ Файл credentials.json не найден!")
            return None
        
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets", 
                    "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        sheet = client.open("Onboard AI - Статистика").sheet1
        print("✅ Подключение к Google Sheets установлено!")
        return sheet
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        return None

def sync_to_google_sheets():
    """Отправляет все данные в Google Sheets"""
    try:
        sheet = init_google_sheets()
        if not sheet:
            return "❌ Не удалось подключиться к Google Sheets. Проверьте credentials.json"
        
        users = get_all_users()
        if not users:
            return "📊 Нет данных для синхронизации."
        
        sheet.clear()
        sheet.append_row(["ID", "Имя", "День", "Оценка", "Завершено", "Дата начала", "Дата завершения"])
        
        for u in users:
            sheet.append_row(list(u))
        
        return f"✅ Данные синхронизированы с Google Sheets! ({len(users)} записей)"
    except Exception as e:
        return f"❌ Ошибка синхронизации: {e}"

# ========== БАЗА ДАННЫХ ==========
DB_FILE = "onboard.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            day INTEGER DEFAULT 0,
            rating INTEGER,
            completed BOOLEAN DEFAULT 0,
            start_date TEXT,
            completed_date TEXT,
            last_activity TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "name": row[1],
            "day": row[2],
            "rating": row[3],
            "completed": bool(row[4]),
            "start_date": row[5],
            "completed_date": row[6],
            "last_activity": row[7]
        }
    return None

def save_user_data(user_id, data):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users (user_id, name, day, rating, completed, start_date, completed_date, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(user_id),
        data.get("name"),
        data.get("day", 0),
        data.get("rating"),
        1 if data.get("completed") else 0,
        data.get("start_date"),
        data.get("completed_date"),
        data.get("last_activity")
    ))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY start_date DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

# ========== КЛАВИАТУРЫ ==========

def main_menu_keyboard(user_id=None):
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
    builder.row(
        InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")
    )
    if user_id == ADMIN_ID:
        builder.row(
            InlineKeyboardButton(text="🔐 Админ-панель", callback_data="admin_panel")
        )
    return builder.as_markup()

def admin_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📥 Экспорт Excel", callback_data="admin_export")],
        [InlineKeyboardButton(text="🔄 Синхронизация Google Sheets", callback_data="admin_sync")],
        [InlineKeyboardButton(text="📋 Список сотрудников", callback_data="admin_users")]
    ])

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

def survey_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 ⭐", callback_data="survey_1"),
         InlineKeyboardButton(text="2 ⭐⭐", callback_data="survey_2"),
         InlineKeyboardButton(text="3 ⭐⭐⭐", callback_data="survey_3"),
         InlineKeyboardButton(text="4 ⭐⭐⭐⭐", callback_data="survey_4"),
         InlineKeyboardButton(text="5 ⭐⭐⭐⭐⭐", callback_data="survey_5")]
    ])

def difficulty_keyboard(day):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 😰", callback_data=f"diff_{day}_1"),
         InlineKeyboardButton(text="2 😟", callback_data=f"diff_{day}_2"),
         InlineKeyboardButton(text="3 😐", callback_data=f"diff_{day}_3"),
         InlineKeyboardButton(text="4 🙂", callback_data=f"diff_{day}_4"),
         InlineKeyboardButton(text="5 😊", callback_data=f"diff_{day}_5")]
    ])

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_progress_bar(day):
    filled = min(day, 7)
    empty = 7 - filled
    bar = "█" * filled + "░" * empty
    percent = round((filled / 7) * 100)
    return f"📊 Прогресс: {bar} {percent}%"

def is_admin(user_id):
    return user_id == ADMIN_ID

def generate_certificate(name, days, rating):
    try:
        img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
            font_small = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        draw.text((200, 100), "СЕРТИФИКАТ", fill=(0, 0, 0), font=font)
        draw.text((100, 200), "Настоящий сертификат подтверждает, что", fill=(0, 0, 0), font=font_small)
        draw.text((100, 250), f"{name}", fill=(0, 0, 255), font=font)
        draw.text((100, 320), "успешно прошёл адаптацию в проекте!", fill=(0, 0, 0), font=font_small)
        draw.text((100, 370), f"Дней: {days}/7 | Оценка уверенности: {rating}/5", fill=(0, 0, 0), font=font_small)
        draw.text((100, 420), f"Дата: {datetime.now().strftime('%d.%m.%Y')}", fill=(0, 0, 0), font=font_small)
        
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    except Exception as e:
        print(f"❌ Ошибка генерации сертификата: {e}")
        return None

# ========== КОМАНДА /start ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    if not user:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 **Новый сотрудник!**\n\n👤 {message.from_user.first_name}\n🆔 `{user_id}`",
            parse_mode="Markdown"
        )
    
    welcome_text = """
👋 Привет! Я — Onboard AI, твой цифровой наставник.

🔥 Используй кнопки ниже, чтобы начать адаптацию!
"""
    await message.answer(welcome_text, reply_markup=main_menu_keyboard(user_id))

# ========== КОМАНДА /admin ==========
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "🔐 **Админ-панель**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard()
    )

# ========== КОМАНДА /stats ==========
@dp.message(Command("stats"))
async def stats_command(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа.")
        return
    users = get_all_users()
    if not users:
        await message.answer("📊 Нет данных.")
        return
    text = "📊 **Статистика:**\n\n"
    for u in users:
        name = u[1] or "Без имени"
        status = "✅" if u[4] else "🔄"
        rating = u[3] or "—"
        text += f"{status} {name} — День {u[2]}/7, Оценка: {rating}/5\n"
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /export ==========
@dp.message(Command("export"))
async def export_command(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа.")
        return
    users = get_all_users()
    if not users:
        await message.answer("📊 Нет данных.")
        return
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Имя", "День", "Оценка", "Завершено", "Дата начала", "Дата завершения"])
    for u in users:
        writer.writerow(list(u))
    output.seek(0)
    await message.answer_document(
        types.BufferedInputFile(output.getvalue().encode('utf-8'), filename="report.csv"),
        caption="📊 Отчёт по адаптации"
    )

# ========== ОБРАБОТЧИКИ КНОПОК ==========

@dp.callback_query(lambda c: c.data == "menu")
async def handle_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    await callback.message.delete()
    if not user:
        text = "👋 Напиши своё имя."
    else:
        text = f"🏠 Главное меню, {user['name']}!\n\n{get_progress_bar(user.get('day', 0))}"
    await callback.message.answer(text, reply_markup=main_menu_keyboard(user_id))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_panel")
async def handle_admin_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("⛔ Нет доступа")
        return
    await callback.message.delete()
    await callback.message.answer(
        "🔐 **Админ-панель**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Напиши своё имя, чтобы создать профиль!")
        await callback.answer()
        return
    text = f"""
👤 **Личный кабинет**

Имя: {user['name']}
📅 Дней пройдено: {user.get('day', 0)}/7
{get_progress_bar(user.get('day', 0))}
⭐ Оценка уверенности: {user.get('rating') or '—'}/5
📆 Дата начала: {user.get('start_date') or '—'}
📆 Дата завершения: {user.get('completed_date') or '—'}
Статус: {'✅ Завершено' if user.get('completed') else '🔄 В процессе'}
"""
    await callback.message.delete()
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

# ========== АДМИН-КНОПКИ ==========

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    await stats_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_export")
async def admin_export_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    await export_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_sync")
async def admin_sync_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    result = sync_to_google_sheets()
    await callback.message.answer(result)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    users = get_all_users()
    if not users:
        await callback.message.answer("📋 Нет сотрудников")
        await callback.answer()
        return
    text = "📋 **Список сотрудников:**\n\n"
    for u in users:
        name = u[1] or "Без имени"
        status = "✅" if u[4] else "🔄"
        rating = u[3] or "—"
        text += f"{status} {name} — День {u[2]}/7, Оценка: {rating}/5\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ========== КНОПКИ ГЛАВНОГО МЕНЮ ==========

@dp.callback_query(lambda c: c.data == "guide")
async def handle_guide(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Привет! Для начала давай познакомимся.\n\nНапиши своё имя, и мы начнём адаптацию! 🚀")
        await callback.answer()
        return
    await callback.message.delete()
    await callback.message.answer(f"🗺️ {user['name']}, выбери день:", reply_markup=days_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq")
async def handle_faq(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Привет! Для начала давай познакомимся.\n\nНапиши своё имя, и я отвечу на все вопросы! 🚀")
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
    if not user:
        await callback.message.answer("👋 Привет! Для начала давай познакомимся.\n\nНапиши своё имя, и я свяжу тебя с ментором! 🆘")
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
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Привет! Для начала давай познакомимся.\n\nНапиши своё имя, и я покажу контакты команды! 👥")
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
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Привет! Для начала давай познакомимся.\n\nНапиши своё имя, и я покажу все полезные ресурсы! 📚")
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
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Привет! Для начала давай познакомимся.\n\nНапиши своё имя, и я покажу, как работает бот! 📋")
        await callback.answer()
        return
    await callback.message.delete()
    await callback.message.answer("📋 Используй кнопки меню для навигации!", reply_markup=back_to_menu_keyboard())
    await callback.answer()

# ========== ДНИ С ВИКТОРИНОЙ ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("day_"))
async def handle_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    day_num = int(callback.data.split("_")[1])
    
    if not user:
        user = {"name": None, "day": 0}
    
    user["day"] = max(user.get("day", 0), day_num)
    user["last_activity"] = datetime.now().isoformat()
    save_user_data(user_id, user)
    
    days_info = {
        1: "📅 **День 1: Знакомство с компанией**\n\n✅ Познакомиться с командой\n✅ Получить доступы\n✅ Установить ПО\n✅ Изучить структуру компании",
        2: "📅 **День 2: Обзор проекта**\n\n✅ Изучить цели и задачи\n✅ Понять свою роль\n✅ Посмотреть текущий статус\n✅ Изучить ключевые метрики",
        3: "📅 **День 3: Инструменты**\n\n✅ Изучить стек технологий\n✅ Настроить локальное окружение\n✅ Запустить проект локально\n✅ Изучить CI/CD",
        4: "📅 **День 4: Процессы**\n\n✅ Как планируем задачи\n✅ Как делаем ревью\n✅ Как тестируем\n✅ Как деплоим",
        5: "📅 **День 5: Первая задача**\n\n✅ Взять задачу\n✅ Выполнить её\n✅ Отправить на проверку\n✅ Получить фидбек",
        6: "📅 **День 6: Обратная связь**\n\n✅ Обсудить впечатления\n✅ Задать вопросы\n✅ Получить фидбек\n✅ Узнать зоны роста",
        7: "📅 **День 7: Итоги**\n\n✅ Подвести итоги недели\n✅ Обсудить план развития\n✅ Чувствовать себя уверенно 💪"
    }
    
    await callback.message.delete()
    await callback.message.answer(days_info.get(day_num, "❌ День не найден"), parse_mode="Markdown")
    await callback.message.answer(f"{get_progress_bar(user.get('day', 0))}")
    
    await callback.message.answer(
        f"📊 **Оцени сложность дня {day_num}:**\n\n1 — очень сложно\n5 — очень легко",
        parse_mode="Markdown",
        reply_markup=difficulty_keyboard(day_num)
    )
    
    if day_num < 7:
        await callback.message.answer("🧠 **Тест:** Ответь на 3 вопроса!", parse_mode="Markdown")
        await ask_quiz(callback.message, day_num)
    else:
        await callback.message.answer("📊 **Ты прошёл всю адаптацию! 🎉**\n\nОтветь на несколько вопросов.", parse_mode="Markdown")
        await ask_survey(callback.message)
    
    await callback.message.answer("🔙 Вернуться к плану:", reply_markup=back_to_guide_keyboard())
    await callback.answer()

# ========== ТЕСТ (3 вопроса) ==========

async def ask_quiz(message: Message, day: int):
    quizzes = {
        1: [
            {"question": "Что нужно сделать в первый день?", "options": ["Познакомиться с командой", "Написать код", "Уйти домой"], "correct": 1},
            {"question": "Кто твой наставник?", "options": ["@mentor", "Руководитель", "Коллега"], "correct": 1},
            {"question": "Где взять доступы?", "options": ["У наставника", "В интернете", "Нигде"], "correct": 1}
        ],
        2: [
            {"question": "Что важно изучить во второй день?", "options": ["Цели проекта", "Меню столовой", "Погоду"], "correct": 1},
            {"question": "Какую роль ты выполняешь?", "options": ["Разработчик", "Тестировщик", "Аналитик"], "correct": 1},
            {"question": "Где посмотреть статус проекта?", "options": ["В Jira", "В Notion", "В Telegram"], "correct": 1}
        ],
        3: [
            {"question": "Что нужно сделать в третий день?", "options": ["Настроить окружение", "Посмотреть кино", "Сделать ремонт"], "correct": 1},
            {"question": "Какой стек используется?", "options": ["Python", "Java", "JavaScript"], "correct": 1},
            {"question": "Где лежит код?", "options": ["GitHub", "GitLab", "Bitbucket"], "correct": 1}
        ],
        4: [
            {"question": "Что такое код-ревью?", "options": ["Проверка кода командой", "Написание кода", "Удаление кода"], "correct": 1},
            {"question": "Кто делает код-ревью?", "options": ["Тимлид", "Все разработчики", "Тестировщики"], "correct": 1},
            {"question": "Где происходит код-ревью?", "options": ["GitHub PR", "В чате", "На созвоне"], "correct": 1}
        ],
        5: [
            {"question": "Что делать с первой задачей?", "options": ["Выполнить и отправить", "Игнорировать", "Отложить"], "correct": 1},
            {"question": "Кому отправлять задачу?", "options": ["Наставнику", "Тимлиду", "Всем чатом"], "correct": 1},
            {"question": "Что делать после выполнения?", "options": ["Получить фидбек", "Забыть", "Уйти"], "correct": 1}
        ],
        6: [
            {"question": "Зачем нужна обратная связь?", "options": ["Чтобы улучшаться", "Чтобы обижаться", "Чтобы спорить"], "correct": 1},
            {"question": "Как часто нужно получать фидбек?", "options": ["Регулярно", "Раз в год", "Никогда"], "correct": 1},
            {"question": "Что делать с фидбеком?", "options": ["Работать над собой", "Игнорировать", "Спорить"], "correct": 1}
        ]
    }
    
    quiz = quizzes.get(day, [])
    if not quiz:
        return
    
    for i, q in enumerate(quiz, 1):
        text = f"**Вопрос {i}:** {q['question']}\n\n"
        for j, opt in enumerate(q['options'], 1):
            text += f"{j}. {opt}\n"
        await message.answer(text, parse_mode="Markdown", reply_markup=quiz_keyboard(i))

def quiz_keyboard(question_num):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data=f"quiz_{question_num}_1"),
         InlineKeyboardButton(text="2", callback_data=f"quiz_{question_num}_2"),
         InlineKeyboardButton(text="3", callback_data=f"quiz_{question_num}_3")]
    ])

@dp.callback_query(lambda c: c.data and c.data.startswith("quiz_"))
async def handle_quiz_answer(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    q_num = int(parts[1])
    answer = int(parts[2])
    
    if answer == 1:
        await callback.message.answer("✅ **Правильно!** 🎉", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ **Неправильно.** Правильный ответ: 1", parse_mode="Markdown")
    
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
    user["completed_date"] = datetime.now().isoformat()
    save_user_data(user_id, user)
    
    report = f"""
📊 **Отчёт об адаптации**

👤 Сотрудник: {user['name']}
📅 Дней пройдено: {user.get('day', 0)}/7
⭐ Оценка уверенности: {rating}/5
📆 Дата завершения: {user['completed_date']}
"""
    
    await bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode="Markdown")
    
    cert = generate_certificate(user['name'], user.get('day', 0), rating)
    if cert:
        await callback.message.answer_document(
            types.BufferedInputFile(cert.getvalue(), filename="certificate.png"),
            caption="🎓 **Ваш сертификат об окончании адаптации!**",
            parse_mode="Markdown"
        )
    
    sync_result = sync_to_google_sheets()
    print(f"📊 Результат синхронизации: {sync_result}")
    
    await callback.message.delete()
    await callback.message.answer(f"""
📊 **Спасибо за обратную связь, {user['name']}!**

Твоя оценка: {rating}/5 ⭐

Ты прошёл полный курс адаптации! 🎉
""", reply_markup=main_menu_keyboard(user_id))
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

# ========== ОБРАБОТЧИК ЛЮБЫХ ТЕКСТОВ ==========

@dp.message()
async def handle_any_text(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    
    if message.text and message.text.startswith('/'):
        await message.answer("❌ Неизвестная команда. Используй /help для списка команд.")
        return
    
    if not user:
        user = {"name": message.text.strip(), "day": 0, "start_date": datetime.now().isoformat()}
        save_user_data(user_id, user)
        await message.answer(f"🎉 Привет, {user['name']}!", reply_markup=main_menu_keyboard(user_id))
        return
    
    await message.answer(f"😊 {user['name']}, я работаю только по кнопкам!\n\nИспользуй меню ниже 👇", reply_markup=main_menu_keyboard(user_id))

# ========== ЗАПУСК ==========

async def main():
    print("🤖 Бот Onboard AI запущен!")
    print("✅ Все функции активны!")
    print(f"👤 Администратор: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
