import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КЛАВИАТУРЫ (КНОПКИ) ==========

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
        InlineKeyboardButton(text="📋 Помощь", callback_data="help")
    )
    return builder.as_markup()

def days_keyboard():
    builder = InlineKeyboardBuilder()
    buttons = []
    for i in range(1, 8):
        buttons.append(InlineKeyboardButton(text=f"День {i}", callback_data=f"day_{i}"))
    builder.add(*buttons)
    builder.adjust(4)
    return builder.as_markup()

def faq_keyboard():
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=f"Вопрос {i}", callback_data=f"faq_{i}"))
    builder.adjust(3)
    return builder.as_markup()

# ========== КОМАНДА /start ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    welcome_text = """
👋 Привет! Я — Onboard AI, твой цифровой наставник.

Моя задача — провести тебя через первые 7 дней в проекте так, чтобы ты чувствовал себя уверенно, а не потерянно.

🔥 Используй кнопки ниже, чтобы узнать больше!
"""
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())

# ========== КОМАНДА /help ==========
@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = "📋 Список команд:\n/start — главное меню\n/guide — план адаптации\n/faq — частые вопросы\n/contacts — контакты команды\n/resources — полезные ссылки"
    await message.answer(help_text, reply_markup=main_menu_keyboard())

# ========== КОМАНДА /guide ==========
@dp.message(Command("guide"))
async def guide_command(message: Message):
    guide_text = "🗺️ Твой план адаптации на 7 дней:\n\nВыбери день, чтобы узнать подробности:"
    await message.answer(guide_text, reply_markup=days_keyboard())

# ========== КОМАНДА /faq ==========
@dp.message(Command("faq"))
async def faq_command(message: Message):
    faq_text = "❓ Частые вопросы:\n\nВыбери номер вопроса:"
    await message.answer(faq_text, reply_markup=faq_keyboard())

# ========== КОМАНДА /contacts ==========
@dp.message(Command("contacts"))
async def contacts_command(message: Message):
    contacts_text = "👥 Ключевые люди в проекте:\n\n🟢 Руководитель проекта — @username\n🟡 Тимлид — @username\n🔵 Ментор — @username\n🟣 DevOps — @username"
    await message.answer(contacts_text, reply_markup=main_menu_keyboard())

# ========== КОМАНДА /resources ==========
@dp.message(Command("resources"))
async def resources_command(message: Message):
    resources_text = "📚 Полезные ресурсы:\n\n📁 Документация — [ссылка]\n📊 Доска задач — [ссылка]\n💬 Чат команды — [ссылка]\n📅 Календарь — [ссылка]"
    await message.answer(resources_text, reply_markup=main_menu_keyboard())

# ========== ОБРАБОТЧИКИ КНОПОК ==========

@dp.callback_query(lambda c: c.data == "guide")
async def handle_guide_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    guide_text = "🗺️ Твой план адаптации на 7 дней:\n\nВыбери день, чтобы узнать подробности:"
    await callback.message.answer(guide_text, reply_markup=days_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq")
async def handle_faq_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    faq_text = "❓ Частые вопросы:\n\nВыбери номер вопроса:"
    await callback.message.answer(faq_text, reply_markup=faq_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "contacts")
async def handle_contacts_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    contacts_text = "👥 Ключевые люди в проекте:\n\n🟢 Руководитель проекта — @username\n🟡 Тимлид — @username\n🔵 Ментор — @username\n🟣 DevOps — @username"
    await callback.message.answer(contacts_text, reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "resources")
async def handle_resources_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    resources_text = "📚 Полезные ресурсы:\n\n📁 Документация — [ссылка]\n📊 Доска задач — [ссылка]\n💬 Чат команды — [ссылка]\n📅 Календарь — [ссылка]"
    await callback.message.answer(resources_text, reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "help")
async def handle_help_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    help_text = "📋 Список команд:\n/start — главное меню\n/guide — план адаптации\n/faq — частые вопросы\n/contacts — контакты команды\n/resources — полезные ссылки"
    await callback.message.answer(help_text, reply_markup=main_menu_keyboard())
    await callback.answer()

# ========== ДНИ ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("day_"))
async def handle_day_callback(callback: types.CallbackQuery):
    day_num = callback.data.split("_")[1]
    
    days_info = {
        "1": "📅 День 1: Знакомство с командой и доступы\n\n✅ Познакомиться с командой\n✅ Получить доступы к системам\n✅ Установить ПО\n✅ Задать вопросы наставнику",
        "2": "📅 День 2: Обзор проекта\n\n✅ Изучить цели и задачи\n✅ Понять свою роль\n✅ Посмотреть текущий статус\n✅ Изучить метрики",
        "3": "📅 День 3: Инструменты и технологии\n\n✅ Изучить стек технологий\n✅ Настроить локальное окружение\n✅ Запустить проект локально",
        "4": "📅 День 4: Рабочие процессы\n\n✅ Как планируем задачи\n✅ Как делаем код-ревью\n✅ Как тестируем\n✅ Как деплоим",
        "5": "📅 День 5: Первая задача\n\n✅ Взять небольшую задачу\n✅ Выполнить её\n✅ Отправить на проверку",
        "6": "📅 День 6: Обратная связь\n\n✅ Обсудить впечатления\n✅ Задать вопросы\n✅ Получить обратную связь",
        "7": "📅 День 7: Итоги\n\n✅ Подвести итоги недели\n✅ Обсудить план\n✅ Чувствовать себя уверенно 💪"
    }
    
    await callback.message.delete()
    await callback.message.answer(days_info.get(day_num, "День не найден"))
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к плану", callback_data="guide")]
    ])
    await callback.message.answer("Выбери действие:", reply_markup=back_keyboard)
    await callback.answer()

# ========== FAQ ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("faq_"))
async def handle_faq_callback(callback: types.CallbackQuery):
    faq_num = callback.data.split("_")[1]
    
    faq_info = {
        "1": "❓ Где взять доступы?\n\nОбратись к наставнику или тимлиду.\nИли напиши в общий чат.",
        "2": "❓ Как настроить окружение?\n\nВсё описано в документации:\n[ссылка]\n\nЕсли что — попроси помощи у DevOps.",
        "3": "❓ Кто мой наставник?\n\nТвой наставник — @mentor_username\nНе стесняйся спрашивать!",
        "4": "❓ Где хранятся документы?\n\nВсе документы в Notion/Confluence:\n[ссылка]",
        "5": "❓ Когда встречи?\n\nDaily в 10:00 по Москве.\nСсылка: [ссылка]"
    }
    
    await callback.message.delete()
    await callback.message.answer(faq_info.get(faq_num, "Вопрос не найден"))
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к FAQ", callback_data="faq")]
    ])
    await callback.message.answer("Выбери действие:", reply_markup=back_keyboard)
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    print("🤖 Бот Onboard AI с кнопками запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
