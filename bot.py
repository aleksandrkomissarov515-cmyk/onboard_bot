import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Токен не найден!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer("👋 Привет! Бот работает!")

@dp.message(Command("admin"))
async def admin_command(message: Message):
    await message.answer("🔐 Админ-панель")

async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
