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
    waiting_for_autopost_interval = State()

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    
    welcome_text = (
        "🤖 <b>AutoPoster Bot</b>\n\n"
        "Добро пожаловать в панель управления автопостингом новостей о животных.\n\n"
        "Бот работает полностью автономно:\n"
        "• 🔍 <b>Мониторинг</b> - собирает свежие новости в фоновом режиме.\n"
        "• 🧠 <b>ИИ-Рерайт</b> - делает уникальные тексты через ИИ.\n"
        "• 🎨 <b>Брендирование</b> - автоматически накладывает ваш водяной знак.\n"
        "• ⏱ <b>Гибкость</b> -  вы можете настроить интервал проверок и тумблер активности.\n\n"
        f"📍 <b>Целевой канал:</b> <code>{CHANNEL_ID}</code>"
    )
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_reply_keyboard())

@router.message(F.text == "📊 Статус работы")
async def show_status(message: Message):
    """Показывает текущий статус автопостера."""
    import aiosqlite
    from config import DB_PATH
    
    ap_enabled = await get_setting("autopost_enabled", "0") == "1"
    ap_interval = await get_setting("autopost_interval_minutes", "180")
    
    count = 0
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM published_links")
            row = await cursor.fetchone()
            if row:
                count = row[0]
    except Exception:
        pass
        
    status = "🟢 Включен" if ap_enabled else "🔴 Выключен"
    
    text = (
        "📊 <b>Статус Автопостера:</b>\n\n"
        f"<b>Режим:</b> {status}\n"
        f"<b>Интервал:</b> каждые {ap_interval} мин.\n"
        f"<b>Опубликовано постов (всего):</b> {count}\n\n"
        "<i>Для изменения настроек используйте кнопку ⚙️ Настройки</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Информация о текущих настройках бота."""
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
    ap_enabled = await get_setting("autopost_enabled", "0") == "1"
    ap_interval = await get_setting("autopost_interval_minutes", "180")
    
    settings_text = (
        "⚙️ <b>Текущие настройки автопостера:</b>\n\n"
        f"• <b>Канал публикации:</b> <code>{CHANNEL_ID}</code>\n"
        f"• <b>Водяной знак:</b> <code>{wm_text}</code>\n"
    )
    await message.answer(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled, ap_enabled, ap_interval))

@router.callback_query(F.data == "toggle_setting_watermark")
async def toggle_watermark_setting(callback: CallbackQuery):
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    new_state = "False" if wm_enabled else "True"
    await set_setting("watermark_enabled", new_state)
    
    wm_enabled = new_state == "True"
    wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
    ap_enabled = await get_setting("autopost_enabled", "0") == "1"
    ap_interval = await get_setting("autopost_interval_minutes", "180")
    
    settings_text = (
        "⚙️ <b>Текущие настройки автопостера:</b>\n\n"
        f"• <b>Канал публикации:</b> <code>{CHANNEL_ID}</code>\n"
        f"• <b>Водяной знак:</b> <code>{wm_text}</code>\n"
    )
    await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled, ap_enabled, ap_interval))
    await callback.answer("Настройка водяного знака обновлена")

@router.callback_query(F.data == "toggle_setting_autopost")
async def toggle_autopost_setting(callback: CallbackQuery):
    ap_enabled = await get_setting("autopost_enabled", "0") == "1"
    new_state = "0" if ap_enabled else "1"
    await set_setting("autopost_enabled", new_state)
    
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
    ap_enabled = new_state == "1"
    ap_interval = await get_setting("autopost_interval_minutes", "180")
    
    settings_text = (
        "⚙️ <b>Текущие настройки автопостера:</b>\n\n"
        f"• <b>Канал публикации:</b> <code>{CHANNEL_ID}</code>\n"
        f"• <b>Водяной знак:</b> <code>{wm_text}</code>\n"
    )
    await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled, ap_enabled, ap_interval))
    await callback.answer("Настройка автопостинга обновлена")

@router.callback_query(F.data == "edit_setting_autopost_interval")
async def start_edit_autopost_interval(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите интервал проверок новостей для авто-постинга (в минутах):")
    await state.set_state(SettingsState.waiting_for_autopost_interval)
    await callback.answer()

@router.message(SettingsState.waiting_for_autopost_interval)
async def process_new_autopost_interval(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1:
        await message.answer("Пожалуйста, введите положительное число (в минутах).")
        return
        
    new_interval = message.text
    await set_setting("autopost_interval_minutes", new_interval)
    await state.clear()
    await message.answer(f"Интервал автопостинга установлен на: <code>{new_interval} минут</code>", parse_mode="HTML")
    await show_settings(message)

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
