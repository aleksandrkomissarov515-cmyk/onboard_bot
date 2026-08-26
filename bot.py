import os
import subprocess
import sys

# ========== АВТОМАТИЧЕСКАЯ УСТАНОВКА ЗАВИСИМОСТЕЙ ==========
def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--no-cache-dir"])
        print("✅ Все зависимости установлены!")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка установки зависимостей: {e}")
        return False

# Проверяем и устанавливаем зависимости при первом запуске
if not os.path.exists(".deps_installed"):
    print("📦 Устанавливаю зависимости...")
    if install_requirements():
        with open(".deps_installed", "w") as f:
            f.write("installed")
    else:
        print("❌ Не удалось установить зависимости. Проверьте requirements.txt")

# ========== ОСНОВНЫЕ ИМПОРТЫ ==========
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

# Пытаемся импортировать Pillow (если не установлена — будет ошибка, но мы уже установили)
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("⚠️ Pillow не установлена. Функция сертификатов будет недоступна.")

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ ОШИБКА: Токен не найден! Проверьте файл .env")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ID АДМИНИСТРАТОРА ==========
ADMIN_ID = 470740095

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
    if not PILLOW_AVAILABLE:
        return None
    
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((200, 100), "СЕРТИФИКАТ", fill=(0, 0, 0), font=font)
    draw.text((100, 200), f"Настоящий сертификат подтверждает, что", fill=(0, 0, 0), font=font_small)
    draw.text((100, 250), f"{name}", fill=(0, 0, 255), font=font)
    draw.text((100, 320), f"успешно прошёл адаптацию в проекте!", fill=(0, 0, 0), font=font_small)
    draw.text((100, 370), f"Дней: {days}/7 | Оценка уверенности: {rating}/5", fill=(0, 0, 0), font=font_small)
    draw.text((100, 420), f"Дата: {datetime.now().strftime('%d.%m.%Y')}", fill=(0, 0, 0), font=font_small)
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

# ========== КОМАНДЫ ==========

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
        text += f"{status} {name} — День {u[2]}/7\n"
    await message.answer(text, parse_mode="Markdown")

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
    writer.writerow(["ID", "Имя", "День", "Оценка", "Завершено", "Дата начала"])
    for u in users:
        writer.writerow(list(u))
    output.seek(0)
    await message.answer_document(
        types.BufferedInputFile(output.getvalue().encode('utf-8'), filename="report.csv"),
        caption="📊 Отчёт"
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
        text = f"🏠 Главное меню, {user['name']}!"
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
        "🔐 **Админ-панель**",
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
        await callback.message.answer("👋 Напиши своё имя!")
        await callback.answer()
        return
    text = f"👤 **{user['name']}**\n{get_progress_bar(user.get('day', 0))}"
    await callback.message.delete()
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

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
        text += f"{status} {name} — День {u[2]}/7\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ========== КНОПКИ ГЛАВНОГО МЕНЮ ==========

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
    await callback.message.answer(f"🗺️ {user['name']}, выбери день:", reply_markup=days_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq")
async def handle_faq(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("❓ Выбери вопрос:", reply_markup=faq_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "mentor")
async def handle_mentor(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("🆘 Свяжись с ментором: @mentor", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "contacts")
async def handle_contacts(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("👥 Контакты:\n@username", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "resources")
async def handle_resources(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📚 Ресурсы:\n[ссылка]", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "help")
async def handle_help(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("📋 Используй кнопки!", reply_markup=back_to_menu_keyboard())
    await callback.answer()

# ========== ДНИ ==========

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
        1: "📅 День 1: Знакомство с компанией",
        2: "📅 День 2: Обзор проекта",
        3: "📅 День 3: Инструменты",
        4: "📅 День 4: Процессы",
        5: "📅 День 5: Первая задача",
        6: "📅 День 6: Обратная связь",
        7: "📅 День 7: Итоги 🎉"
    }
    
    await callback.message.delete()
    await callback.message.answer(days_info.get(day_num, "❌ День не найден"))
    await callback.message.answer(f"{get_progress_bar(user.get('day', 0))}")
    
    await callback.message.answer(
        f"📊 Оцени сложность дня {day_num}:",
        reply_markup=difficulty_keyboard(day_num)
    )
    
    if day_num == 7:
        await callback.message.answer("📊 Пройди опрос!", reply_markup=survey_keyboard())
    
    await callback.message.answer("🔙 Назад:", reply_markup=back_to_guide_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("diff_"))
async def handle_difficulty(callback: types.CallbackQuery):
    await callback.message.answer(f"✅ Оценено!")
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
    
    report = f"📊 {user['name']} завершил адаптацию! Оценка: {rating}/5"
    await bot.send_message(chat_id=ADMIN_ID, text=report)
    
    # Генерируем сертификат, если Pillow доступна
    if PILLOW_AVAILABLE:
        cert = generate_certificate(user['name'], user.get('day', 0), rating)
        if cert:
            await callback.message.answer_document(
                types.BufferedInputFile(cert.getvalue(), filename="certificate.png"),
                caption="🎓 Сертификат!"
            )
    
    await callback.message.delete()
    await callback.message.answer(f"🎉 Спасибо, {user['name']}!", reply_markup=main_menu_keyboard(user_id))
    await callback.answer()

# ========== FAQ ==========

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
    await callback.message.answer(faq_info.get(faq_num, "❌ Не найден"))
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
    
    await message.answer("😊 Используй кнопки!", reply_markup=main_menu_keyboard(user_id))

# ========== ЗАПУСК ==========

async def main():
    print("🤖 Бот Onboard AI запущен!")
    print("✅ Все функции активны!")
    print(f"👤 Администратор: {ADMIN_ID}")
    print(f"📦 Pillow доступна: {PILLOW_AVAILABLE}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
