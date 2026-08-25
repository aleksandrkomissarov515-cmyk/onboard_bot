import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

# Загружаем переменные окружения (токен)
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КОМАНДА /start ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    welcome_text = """
👋 Привет! Я — Onboard AI, твой цифровой наставник.

Моя задача — провести тебя через первые 7 дней в проекте так, чтобы ты чувствовал себя уверенно, а не потерянно.

🔥 Что я умею:
/start — начать заново
/help — список команд
/guide — пошаговый план адаптации
/faq — ответы на частые вопросы
/contacts — кому писать по любым вопросам
/resources — все ссылки и документы в одном месте

Давай сделаем твой старт максимально комфортным! С чего начнём?
"""
    await message.answer(welcome_text)

# ========== КОМАНДА /help ==========
@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = """
📋 Список команд:

/start — приветствие и знакомство
/guide — пошаговый план на неделю
/faq — частые вопросы новичков
/contacts — кто есть кто в команде
/resources — ссылки на всё важное
"""
    await message.answer(help_text)

# ========== КОМАНДА /guide ==========
@dp.message(Command("guide"))
async def guide_command(message: Message):
    guide_text = """
🗺️ Твой план адаптации:

День 1️⃣ — Знакомство с командой и доступы
День 2️⃣ — Обзор проекта: цели, задачи, сроки
День 3️⃣ — Инструменты и технологии
День 4️⃣ — Рабочие процессы
День 5️⃣ — Первая практическая задача
День 6️⃣ — Обратная связь и вопросы
День 7️⃣ — Итоги недели

Напиши номер дня (1–7), и я расскажу подробнее.
"""
    await message.answer(guide_text)

# ========== КОМАНДА /faq ==========
@dp.message(Command("faq"))
async def faq_command(message: Message):
    faq_text = """
❓ Частые вопросы:

1. Где взять доступы?
2. Как настроить рабочее окружение?
3. Кто мой наставник?
4. Где хранятся документы?
5. Когда ежедневные встречи?

Напиши номер вопроса (1–5) — я дам ответ.
"""
    await message.answer(faq_text)

# ========== КОМАНДА /contacts ==========
@dp.message(Command("contacts"))
async def contacts_command(message: Message):
    contacts_text = """
👥 Ключевые люди в проекте:

🟢 Руководитель проекта — @username
🟡 Тимлид — @username
🔵 Ментор (твой наставник) — @username
🟣 DevOps — @username
🔴 Если не знаешь, к кому идти — пиши мне!
"""
    await message.answer(contacts_text)

# ========== КОМАНДА /resources ==========
@dp.message(Command("resources"))
async def resources_command(message: Message):
    resources_text = """
📚 Полезные ресурсы:

📁 Документация — [ссылка]
📊 Доска задач — [ссылка]
💬 Чат команды — [ссылка]
📅 Календарь — [ссылка]
"""
    await message.answer(resources_text)

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🤖 Бот Onboard AI запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())