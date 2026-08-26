import os
import asyncio
import logging
import sqlite3
import csv
import threading
from datetime import datetime
from io import BytesIO, StringIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import gspread
from google.oauth2.service_account import Credentials

# ========== ЗАПУСК ВЕБ-СЕРВЕРА (ДАШБОРДА) В ОТДЕЛЬНОМ ПОТОКЕ ==========
def run_web_dashboard():
    """Запускает Flask-дашборд в отдельном потоке"""
    try:
        from app import app
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Ошибка запуска дашборда: {e}")

# Запускаем дашборд в фоновом потоке
threading.Thread(target=run_web_dashboard, daemon=True).start()
print("🌐 Веб-дашборд запускается...")

# ========== ОСТАЛЬНОЙ КОД БОТА ==========
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен не найден!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMIN_ID = 470740095
print(f"🔐 Администратор ID: {ADMIN_ID}")

user_quizzes = {}

DB_FILE = "onboard.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        day INTEGER DEFAULT 0,
        rating INTEGER,
        completed BOOLEAN DEFAULT 0,
        start_date TEXT,
        completed_date TEXT,
        last_activity TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        day INTEGER,
        total_correct INTEGER,
        total_questions INTEGER,
        date TEXT
    )""")
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

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
    cur.execute("""INSERT OR REPLACE INTO users (user_id, name, day, rating, completed, start_date, completed_date, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
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

def save_quiz_result(user_id, day, correct, total):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""INSERT INTO quiz_results (user_id, day, total_correct, total_questions, date)
        VALUES (?, ?, ?, ?, ?)""", (str(user_id), day, correct, total, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_quiz_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT SUM(total_correct), SUM(total_questions) FROM quiz_results WHERE user_id = ?", (str(user_id),))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return row[0], row[1]
    return 0, 0

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
        InlineKeyboardButton(text="🆘 Ментор", callback_data="mentor"),
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

def quiz_keyboard(day, q_num):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data=f"quiz_{day}_{q_num}_1"),
         InlineKeyboardButton(text="2️⃣", callback_data=f"quiz_{day}_{q_num}_2"),
         InlineKeyboardButton(text="3️⃣", callback_data=f"quiz_{day}_{q_num}_3")]
    ])

def get_progress_bar(day):
    filled = min(day, 7)
    empty = 7 - filled
    bar = "█" * filled + "░" * empty
    percent = round((filled / 7) * 100)
    return f"📊 Прогресс: {bar} {percent}%"

def is_admin(user_id):
    return user_id == ADMIN_ID

def sync_to_google_sheets():
    try:
        if not os.path.exists("credentials.json"):
            return "❌ credentials.json не найден"
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets", 
                    "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        sheet = client.open("Onboard AI - Статистика").sheet1
        users = get_all_users()
        if not users:
            return "📊 Нет данных"
        sheet.clear()
        sheet.append_row(["ID", "Имя", "День", "Оценка", "Завершено", "Дата начала", "Дата завершения"])
        for u in users:
            sheet.append_row(list(u))
        return f"✅ Синхронизировано! ({len(users)} записей)"
    except Exception as e:
        return f"❌ Ошибка: {e}"

def generate_certificate(name, days, rating):
    try:
        img = Image.new('RGB', (1400, 900), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except:
            try:
                font_big = ImageFont.truetype("arial.ttf", 70)
                font_medium = ImageFont.truetype("arial.ttf", 40)
                font_small = ImageFont.truetype("arial.ttf", 32)
            except:
                font_big = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
        
        draw.rectangle([20, 20, 1380, 880], outline=(0, 100, 200), width=5)
        draw.rectangle([40, 40, 1360, 860], outline=(0, 100, 200), width=2)
        
        draw.text((700, 70), "СЕРТИФИКАТ", fill=(0, 100, 200), font=font_big, anchor="mt")
        draw.line([250, 130, 1150, 130], fill=(0, 100, 200), width=3)
        
        draw.text((700, 200), "Настоящий сертификат подтверждает, что", fill=(50, 50, 50), font=font_medium, anchor="mt")
        draw.text((700, 300), name, fill=(0, 50, 150), font=font_big, anchor="mt")
        draw.text((700, 400), "успешно прошёл адаптацию в проекте!", fill=(50, 50, 50), font=font_medium, anchor="mt")
        draw.text((700, 500), f"Дней: {days}/7 | Оценка уверенности: {rating}/5", fill=(0, 100, 200), font=font_medium, anchor="mt")
        draw.text((700, 590), f"Дата: {datetime.now().strftime('%d.%m.%Y')}", fill=(100, 100, 100), font=font_medium, anchor="mt")
        draw.text((700, 700), "Onboard AI", fill=(150, 150, 150), font=font_medium, anchor="mt")
        draw.line([400, 760, 1000, 760], fill=(200, 200, 200), width=2)
        
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    except Exception as e:
        print(f"❌ Ошибка сертификата: {e}")
        return None

@dp.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    if not user:
        await bot.send_message(ADMIN_ID, f"🆕 Новый сотрудник: {message.from_user.first_name}")
    
    # Проверяем, есть ли видео
    video_path = "welcome.mp4"
    if os.path.exists(video_path):
        try:
            video = FSInputFile(video_path)
            await message.answer_video(
                video, 
                caption="👋 Привет! Я — Onboard AI, твой цифровой наставник!\n\nИспользуй кнопки ниже!",
                reply_markup=main_menu_keyboard(user_id)
            )
            return
        except:
            pass
    
    await message.answer(
        "👋 Привет! Я — Onboard AI, твой цифровой наставник!\n\nИспользуй кнопки ниже!",
        reply_markup=main_menu_keyboard(user_id)
    )

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("🔐 Админ-панель", reply_markup=admin_menu_keyboard())

@dp.message(Command("stats"))
async def stats_command(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return
    users = get_all_users()
    if not users:
        await message.answer("📊 Нет данных.")
        return
    text = "📊 Статистика:\n\n"
    for u in users:
        text += f"{'✅' if u[4] else '🔄'} {u[1]} — День {u[2]}/7\n"
    await message.answer(text)

@dp.message(Command("export"))
async def export_command(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return
    users = get_all_users()
    if not users:
        await message.answer("📊 Нет данных для экспорта.")
        return
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["ID", "Имя", "День", "Оценка", "Завершено", "Дата начала", "Дата завершения"])
    for u in users:
        completed = "Да" if u[4] else "Нет"
        writer.writerow([u[0], u[1], u[2], u[3] if u[3] else "—", completed, u[5] or "—", u[6] or "—"])
    output.seek(0)
    await message.answer_document(
        types.BufferedInputFile(output.getvalue().encode('utf-8-sig'), 
            filename=f"отчёт_адаптации_{datetime.now().strftime('%d.%m.%Y')}.csv"),
        caption="📊 Отчёт по адаптации"
    )

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
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer("🔐 Админ-панель", reply_markup=admin_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await stats_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_export")
async def admin_export_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await export_command(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    users = get_all_users()
    if not users:
        await callback.message.answer("📋 Нет сотрудников")
        await callback.answer()
        return
    text = "📋 Сотрудники:\n\n"
    for u in users:
        text += f"{'✅' if u[4] else '🔄'} {u[1]} — День {u[2]}/7\n"
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Напиши своё имя!")
        await callback.answer()
        return
    correct, total = get_quiz_stats(user_id)
    text = f"👤 {user['name']}\n{get_progress_bar(user.get('day', 0))}\n📊 Викторина: {correct}/{total} правильных ответов"
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "guide")
async def handle_guide(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    if not user:
        await callback.message.delete()
        await callback.message.answer("👋 Напиши своё имя!")
        await callback.answer()
        return
    await callback.message.delete()
    await callback.message.answer("🗺️ Выбери день:", reply_markup=days_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq")
async def handle_faq(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("❓ Выбери вопрос:", reply_markup=faq_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "mentor")
async def handle_mentor(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🆘 Ментор: @mentor", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "contacts")
async def handle_contacts(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("👥 Контакты: @username", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "resources")
async def handle_resources(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📚 Ресурсы: [ссылка]", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "help")
async def handle_help(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📋 Используй кнопки!", reply_markup=back_to_menu_keyboard())
    await callback.answer()

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
    
    days_text = {
        1: "📅 **День 1: Знакомство с компанией**\n\n✅ Познакомиться с командой\n✅ Получить доступы\n✅ Установить ПО",
        2: "📅 **День 2: Обзор проекта**\n\n✅ Изучить цели и задачи\n✅ Понять свою роль\n✅ Посмотреть статус",
        3: "📅 **День 3: Инструменты**\n\n✅ Изучить стек технологий\n✅ Настроить окружение\n✅ Запустить проект",
        4: "📅 **День 4: Процессы**\n\n✅ Как планируем задачи\n✅ Как делаем ревью\n✅ Как тестируем",
        5: "📅 **День 5: Первая задача**\n\n✅ Взять задачу\n✅ Выполнить её\n✅ Отправить на проверку",
        6: "📅 **День 6: Обратная связь**\n\n✅ Обсудить впечатления\n✅ Задать вопросы\n✅ Получить фидбек",
        7: "📅 **День 7: Итоги**\n\n✅ Подвести итоги\n✅ Обсудить план развития\n✅ Чувствовать себя уверенно 💪"
    }
    
    await callback.message.delete()
    await callback.message.answer(days_text.get(day_num, "❌ День не найден"), parse_mode="Markdown")
    await callback.message.answer(get_progress_bar(user.get('day', 0)))
    
    if day_num < 7:
        await callback.message.answer(f"📊 Оцени сложность дня {day_num}:", reply_markup=difficulty_keyboard(day_num))
        await asyncio.sleep(0.5)
        await callback.message.answer("🧠 Ответь на 3 вопроса!", parse_mode="Markdown")
        await ask_quiz(callback.message, day_num)
    
    if day_num == 7:
        await callback.message.answer("📊 Пройди опрос!", reply_markup=survey_keyboard())
    
    await callback.message.answer("🔙 Назад:", reply_markup=back_to_guide_keyboard())
    await callback.answer()

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
            {"question": "Какой стек технологий используется?", "options": ["Python", "Java", "JavaScript"], "correct": 1},
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
        await message.answer("❌ Вопросы для этого дня не найдены.")
        return
    user_id = message.chat.id
    if user_id not in user_quizzes:
        user_quizzes[user_id] = {}
    for i, q in enumerate(quiz, 1):
        user_quizzes[user_id][f"{day}_{i}"] = q["correct"]
        text = f"🧠 **Вопрос {i}:** {q['question']}\n\n"
        for j, opt in enumerate(q['options'], 1):
            text += f"{j}. {opt}\n"
        await message.answer(text, parse_mode="Markdown", reply_markup=quiz_keyboard(day, i))

@dp.callback_query(lambda c: c.data and c.data.startswith("quiz_"))
async def handle_quiz_answer(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        if len(parts) != 4:
            await callback.answer("❌ Неверный формат")
            return
        day = int(parts[1])
        q_num = int(parts[2])
        answer = int(parts[3])
        user_id = callback.from_user.id
        correct = user_quizzes.get(user_id, {}).get(f"{day}_{q_num}")
        if correct is None:
            await callback.message.answer("❌ Вопрос не найден.")
            await callback.answer()
            return
        if answer == correct:
            await callback.message.answer("✅ **Правильно!** 🎉", parse_mode="Markdown")
        else:
            await callback.message.answer(f"❌ **Неправильно.** Правильный ответ: {correct}", parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        print(f"❌ Ошибка викторины: {e}")
        await callback.answer("❌ Произошла ошибка")

@dp.callback_query(lambda c: c.data and c.data.startswith("diff_"))
async def handle_difficulty(callback: types.CallbackQuery):
    await callback.message.answer("✅ Оценено!")
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("survey_"))
async def handle_survey(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_data(user_id)
    rating = int(callback.data.split("_")[1])
    user["rating"] = rating
    user["completed"] = True
    user["completed_date"] = datetime.now().isoformat()
    save_user_data(user_id, user)
    
    correct = sum(1 for v in user_quizzes.get(user_id, {}).values() if v)
    total = len(user_quizzes.get(user_id, {}))
    save_quiz_result(user_id, 7, correct, total)
    
    await bot.send_message(ADMIN_ID, f"📊 {user['name']} завершил адаптацию!\nОценка: {rating}/5\nВикторина: {correct}/{total}")
    
    cert = generate_certificate(user['name'], user.get('day', 0), rating)
    if cert:
        await callback.message.answer_document(
            types.BufferedInputFile(cert.getvalue(), filename="certificate.png"),
            caption="🎓 Сертификат об окончании адаптации!"
        )
    else:
        await callback.message.answer("❌ Не удалось сгенерировать сертификат.")
    
    await callback.message.delete()
    await callback.message.answer(f"🎉 Спасибо, {user['name']}!", reply_markup=main_menu_keyboard(user_id))
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("faq_"))
async def handle_faq_callback(callback: types.CallbackQuery):
    faq_num = int(callback.data.split("_")[1])
    faq_info = {
        1: "❓ Доступы — у наставника.",
        2: "❓ Окружение — в документации.",
        3: "❓ Наставник — @mentor.",
        4: "❓ Документы — в Notion.",
        5: "❓ Daily в 10:00."
    }
    await callback.message.delete()
    await callback.message.answer(faq_info.get(faq_num, "❌"))
    await callback.message.answer("🔙 Назад:", reply_markup=back_to_faq_keyboard())
    await callback.answer()

@dp.message()
async def handle_any_text(message: Message):
    user_id = message.from_user.id
    user = get_user_data(user_id)
    if not user:
        user = {"name": message.text.strip(), "day": 0, "start_date": datetime.now().isoformat()}
        save_user_data(user_id, user)
        await message.answer(f"🎉 Привет, {user['name']}!", reply_markup=main_menu_keyboard(user_id))
        return
    await message.answer("😊 Используй кнопки!", reply_markup=main_menu_keyboard(user_id))

async def main():
    print("🤖 Бот Onboard AI запущен!")
    print("✅ Все функции активны!")
    print(f"👤 Администратор: {ADMIN_ID}")
    print("🌐 Веб-дашборд доступен по адресу: {PORT}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
