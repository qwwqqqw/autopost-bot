from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная reply-клавиатура администратора."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📰 RSS Новости"),
                KeyboardButton(text="📅 Очередь постов")
            ],
            [
                KeyboardButton(text="⚙️ Настройки")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура отмены мастера."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard
