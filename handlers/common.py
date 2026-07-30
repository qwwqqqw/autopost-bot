from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from keyboards.reply import get_main_reply_keyboard
from keyboards.inline import get_settings_keyboard
from config import CHANNEL_ID, DEFAULT_WATERMARK
from database.db import get_setting, set_setting

class SettingsState(StatesGroup):
    waiting_for_watermark_text = State()

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    
    welcome_text = (
        "🚀 <b>AutoPoster Bot</b>\n\n"
        "Добро пожаловать в панель управления\n\n"
        "<b>Доступные возможности:</b>\n"
        "• 📰 <b>RSS Парсер</b> - автоматически рерайтит найденные новости через ИИ и публекует их в канал\n"
        "• 📅 <b>Отложенный постинг</b> - управление очередью публикаций\n"
        f"📍 <b>Целевой канал:</b> <code>{CHANNEL_ID}</code>"
    )
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_reply_keyboard())

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Информация о текущих настройках бота."""
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
    
    settings_text = (
        "⚙️ <b>Текущие настройки автопостера:</b>\n\n"
        f"• <b>Канал публикации:</b> <code>{CHANNEL_ID}</code>\n"
        f"• <b>Водяной знак:</b> <code>{wm_text}</code>\n"
    )
    await message.answer(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled))

@router.callback_query(F.data == "toggle_setting_watermark")
async def toggle_watermark_setting(callback: CallbackQuery):
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    new_state = "False" if wm_enabled else "True"
    await set_setting("watermark_enabled", new_state)
    
    wm_enabled = new_state == "True"
    wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
    settings_text = (
        "⚙️ <b>Текущие настройки автопостера:</b>\n\n"
        f"• <b>Канал публикации:</b> <code>{CHANNEL_ID}</code>\n"
        f"• <b>Водяной знак:</b> <code>{wm_text}</code>\n"
    )
    await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled))
    await callback.answer("Настройка водяного знака обновлена")

@router.callback_query(F.data == "edit_setting_watermark_text")
async def start_edit_watermark_text(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новый текст водяного знака:")
    await state.set_state(SettingsState.waiting_for_watermark_text)
    await callback.answer()

@router.message(SettingsState.waiting_for_watermark_text)
async def process_new_watermark_text(message: Message, state: FSMContext):
    new_text = message.text
    await set_setting("watermark_text", new_text)
    await state.clear()
    await message.answer(f"Текст водяного знака успешно обновлен на:\n<code>{new_text}</code>", parse_mode="HTML")
    await show_settings(message)
@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена любого текущего сценария."""
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_reply_keyboard())
