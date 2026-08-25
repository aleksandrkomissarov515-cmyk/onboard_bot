import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Включаем логирование, чтобы видеть ошибки
logging.basicConfig(level=logging.INFO)

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КЛАВИАТУРЫ (КНОПКИ) ==========

def main_menu_keyboard():
    """Главное меню с кнопками"""
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
    """Клавиатура с днями 1-7"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 8):
        builder.add(InlineKeyboardButton(text=f"📅 День {i}", callback_data=f"day_{i}"))
    builder.adjust(4)  # 4 кнопки в ряд
    return builder.as_markup()

def faq_keyboard():
    """Клавиатура с вопросами 1-5"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=f"❓ Вопрос {i}", callback_data=f"faq_{i}"))
    builder.adjust(3)
    return builder.as_markup()

def back_to_guide_keyboard():
    """Кнопка 'Назад к плану'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к плану", callback_data="guide")]
    ])

def back_to_faq_keyboard():
    """Кнопка 'Назад к FAQ'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к FAQ", callback_data="faq")]
    ])

def back_to_menu_keyboard():
    """Кнопка 'В главное меню'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu")]
    ])

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
    help_text = """
📋 Список команд:

/start — главное меню
/guide — план адаптации
/faq — частые вопросы
/contacts — контакты команды
/resources — полезные ссылки
"""
    await message.answer(help_text, reply_markup=main_menu_keyboard())

# ========== КОМАНДА /guide ==========
@dp.message(Command("guide"))
async def guide_command(message: Message):
    guide_text = """
🗺️ Твой план адаптации на 7 дней:

Выбери день, чтобы узнать подробности:
"""
    await message.answer(guide_text, reply_markup=days_keyboard())

# ========== КОМАНДА /faq ==========
@dp.message(Command("faq"))
async def faq_command(message: Message):
    faq_text = """
❓ Частые вопросы:

Выбери номер вопроса:
"""
    await message.answer(faq_text, reply_markup=faq_keyboard())

# ========== КОМАНДА /contacts ==========
@dp.message(Command("contacts"))
async def contacts_command(message: Message):
    contacts_text = """
👥 Ключевые люди в проекте:

🟢 Руководитель проекта — @username
🟡 Тимлид — @username
🔵 Ментор (твой наставник) — @username
🟣 DevOps — @username

✉️ Общий чат: @chat_username
"""
    await message.answer(contacts_text, reply_markup=back_to_menu_keyboard())

# ========== КОМАНДА /resources ==========
@dp.message(Command("resources"))
async def resources_command(message: Message):
    resources_text = """
📚 Полезные ресурсы:

📁 Документация — [ссылка]
📊 Доска задач (Jira) — [ссылка]
💬 Чат команды — [ссылка]
📅 Календарь встреч — [ссылка]
🔐 Запрос доступов — [ссылка]
"""
    await message.answer(resources_text, reply_markup=back_to_menu_keyboard())

# ========== ОБРАБОТЧИКИ КНОПОК (callback) ==========

@dp.callback_query(lambda c: c.data == "menu")
async def handle_menu_callback(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.delete()
    welcome_text = """
👋 Привет! Я — Onboard AI, твой цифровой наставник.

🔥 Используй кнопки ниже, чтобы узнать больше!
"""
    await callback.message.answer(welcome_text, reply_markup=main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "guide")
async def handle_guide_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'План адаптации'"""
    await callback.message.delete()
    guide_text = """
🗺️ Твой план адаптации на 7 дней:

Выбери день, чтобы узнать подробности:
"""
    await callback.message.answer(guide_text, reply_markup=days_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "faq")
async def handle_faq_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'FAQ'"""
    await callback.message.delete()
    faq_text = """
❓ Частые вопросы:

Выбери номер вопроса:
"""
    await callback.message.answer(faq_text, reply_markup=faq_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "contacts")
async def handle_contacts_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'Контакты'"""
    await callback.message.delete()
    contacts_text = """
👥 Ключевые люди в проекте:

🟢 Руководитель проекта — @username
🟡 Тимлид — @username
🔵 Ментор (твой наставник) — @username
🟣 DevOps — @username

✉️ Общий чат: @chat_username
"""
    await callback.message.answer(contacts_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "resources")
async def handle_resources_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'Ресурсы'"""
    await callback.message.delete()
    resources_text = """
📚 Полезные ресурсы:

📁 Документация — [ссылка]
📊 Доска задач (Jira) — [ссылка]
💬 Чат команды — [ссылка]
📅 Календарь встреч — [ссылка]
🔐 Запрос доступов — [ссылка]
"""
    await callback.message.answer(resources_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "help")
async def handle_help_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'Помощь'"""
    await callback.message.delete()
    help_text = """
📋 Список команд:

/start — главное меню
/guide — план адаптации
/faq — частые вопросы
/contacts — контакты команды
/resources — полезные ссылки
"""
    await callback.message.answer(help_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()

# ========== ОТВЕТЫ НА ДНИ (1-7) ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("day_"))
async def handle_day_callback(callback: types.CallbackQuery):
    """Обработчик нажатия на день (1-7)"""
    day_num = callback.data.split("_")[1]
    
    days_info = {
        "1": """
📅 **День 1: Знакомство с командой и доступы**

✅ Познакомиться с командой в общем чате
✅ Получить доступы ко всем системам
✅ Установить необходимое ПО
✅ Задать вопросы наставнику
""",
        "2": """
📅 **День 2: Обзор проекта**

✅ Изучить цели и задачи проекта
✅ Понять свою роль в команде
✅ Посмотреть текущий статус проекта
✅ Изучить ключевые метрики
""",
        "3": """
📅 **День 3: Инструменты и технологии**

✅ Изучить стек технологий проекта
✅ Настроить локальное окружение
✅ Запустить проект локально
✅ Посмотреть примеры кода
""",
        "4": """
📅 **День 4: Рабочие процессы**

✅ Как мы планируем задачи
✅ Как проходят код-ревью
✅ Как мы тестируем
✅ Как происходит деплой
✅ График встреч и созвонов
""",
        "5": """
📅 **День 5: Первая практическая задача**

✅ Взять небольшую задачу
✅ Самостоятельно выполнить её
✅ Задать вопросы, если непонятно
✅ Отправить результат на проверку
""",
        "6": """
📅 **День 6: Обратная связь и вопросы**

✅ Обсудить первые впечатления
✅ Задать все накопившиеся вопросы
✅ Получить обратную связь по задачам
✅ Узнать, что можно улучшить
""",
        "7": """
📅 **День 7: Итоги первой недели**

✅ Подвести итоги недели
✅ Обсудить план на следующую неделю
✅ Убедиться, что все доступы работают
✅ Чувствовать себя уверенно в проекте 💪
"""
    }
    
    await callback.message.delete()
    await callback.message.answer(days_info.get(day_num, "❌ День не найден"))
    await callback.message.answer("🔙 Вернуться к плану:", reply_markup=back_to_guide_keyboard())
    await callback.answer()

# ========== ОТВЕТЫ НА FAQ (1-5) ==========

@dp.callback_query(lambda c: c.data and c.data.startswith("faq_"))
async def handle_faq_callback(callback: types.CallbackQuery):
    """Обработчик нажатия на вопрос FAQ (1-5)"""
    faq_num = callback.data.split("_")[1]
    
    faq_info = {
        "1": """
❓ **Вопрос 1: Где взять доступы?**

Обратись к своему наставнику или тимлиду.
Они выдадут все необходимые доступы в первый же день.

Или напиши в общий чат: @chat_username
""",
        "2": """
❓ **Вопрос 2: Как настроить рабочее окружение?**

Всё подробно описано в документации:
[ссылка на гайд по настройке]

Если что-то пошло не так — попроси помощи у DevOps или наставника.
""",
        "3": """
❓ **Вопрос 3: Кто мой наставник?**

Твой наставник — @mentor_username

Он поможет тебе с любыми вопросами в первые недели. Не стесняйся спрашивать!
""",
        "4": """
❓ **Вопрос 4: Где хранятся документы?**

Все документы в Notion / Confluence:
[ссылка на базу знаний]

Там есть:
• Описание проекта
• Техническая документация
• Дизайн-макеты
• Описание процессов
""",
        "5": """
❓ **Вопрос 5: Когда и как проходят встречи?**

Ежедневные встречи (daily) проходят в 10:00 по Москве.

Ссылка на Zoom / Google Meet:
[ссылка]

Приходи подготовленным — расскажи, что сделал вчера и что планируешь сегодня.
"""
    }
    
    await callback.message.delete()
    await callback.message.answer(faq_info.get(faq_num, "❌ Вопрос не найден"))
    await callback.message.answer("🔙 Вернуться к FAQ:", reply_markup=back_to_faq_keyboard())
    await callback.answer()

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🤖 Бот Onboard AI с кнопками запущен!")
    print("✅ Бот готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
