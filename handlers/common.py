from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from keyboards.reply import get_main_reply_keyboard
from keyboards.inline import get_settings_keyboard, get_parsing_menu_keyboard
from config import CHANNEL_ID, DEFAULT_WATERMARK
from database.db import get_setting, set_setting

class SettingsState(StatesGroup):
    waiting_for_watermark_text = State()
    waiting_for_signature_text = State()
    waiting_for_ai_prompt = State()
    waiting_for_target_channels = State()
    waiting_for_max_posts_per_hour = State()

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    
    welcome_text = (
        "🤖 <b>AutoPoster Bot</b>\n\n"
        "Добро пожаловать в панель управления автопостингом Telegram-каналов.\n\n"
        "Бот работает полностью автономно:\n"
        "• 🔍 <b>Мониторинг</b> - собирает свежие посты из других каналов.\n"
        "• 🧠 <b>ИИ-Фильтрация</b> - удаляет рекламу, дубликаты и делает рерайт.\n"
        "• 🎨 <b>Watermark</b> - накладывает водяной знак и подпись.\n\n"
        f"📍 <b>Целевой канал:</b> <code>{CHANNEL_ID}</code>"
    )
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_reply_keyboard())

@router.message(F.text == "🚀 Парсинг")
async def show_parsing_menu(message: Message):
    """Показывает меню управления автопостингом."""
    ap_enabled = await get_setting("autopost_enabled", "0") == "1"
    
    text = (
        "🚀 <b>Управление Парсингом</b>\n\n"
        "Бот постоянно мониторит добавленные вами каналы.\n"
        "Вы можете включить или отключить публикацию найденных постов."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_parsing_menu_keyboard(ap_enabled))

async def update_parsing_menu(callback: CallbackQuery):
    ap_enabled = await get_setting("autopost_enabled", "0") == "1"
    
    text = (
        "🚀 <b>Управление Парсингом</b>\n\n"
        "Бот постоянно мониторит добавленные вами каналы.\n"
        "Вы можете включить или отключить публикацию найденных постов."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_parsing_menu_keyboard(ap_enabled))

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Информация о текущих настройках бота."""
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    sig_enabled = await get_setting("signature_enabled", "0") == "1"
    max_posts = await get_setting("max_posts_per_hour", "0")
    
    settings_text = (
        "⚙️ <b>Настройки автопостера:</b>\n"
        "Нажмите на кнопки ниже, чтобы изменить параметры."
    )
    await message.answer(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled, sig_enabled, max_posts))

async def update_settings_menu(callback: CallbackQuery):
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    sig_enabled = await get_setting("signature_enabled", "0") == "1"
    max_posts = await get_setting("max_posts_per_hour", "0")
    
    settings_text = (
        "⚙️ <b>Настройки автопостера:</b>\n"
        "Нажмите на кнопки ниже, чтобы изменить параметры."
    )
    await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=get_settings_keyboard(wm_enabled, sig_enabled, max_posts))

@router.callback_query(F.data.startswith("toggle_setting_"))
async def toggle_boolean_settings(callback: CallbackQuery):
    setting_type = callback.data.split("_")[-1]
    
    if setting_type == "watermark":
        key = "watermark_enabled"
    elif setting_type == "autopost":
        key = "autopost_enabled"
        # Для autopost используем 1/0
        current = await get_setting(key, "0") == "1"
        new_state = "0" if current else "1"
        await set_setting(key, new_state)
        await update_parsing_menu(callback)
        await callback.answer("Автопостинг обновлен")
        return
    elif setting_type == "signature":
        key = "signature_enabled"
        current = await get_setting(key, "0") == "1"
        new_state = "0" if current else "1"
        await set_setting(key, new_state)
        await update_settings_menu(callback)
        await callback.answer("Настройка обновлена")
        return
        
    current = await get_setting(key, "True") == "True"
    new_state = "False" if current else "True"
    await set_setting(key, new_state)
    await update_settings_menu(callback)
    await callback.answer("Настройка обновлена")

@router.callback_query(F.data.startswith("edit_setting_"))
async def edit_setting_handler(callback: CallbackQuery, state: FSMContext):
    setting_type = callback.data.replace("edit_setting_", "")
    
    import html
    if setting_type == "max_posts_per_hour":
        current = await get_setting("max_posts_per_hour", "0")
        label = "Без лимита" if current == "0" else f"{current} постов/час"
        await callback.message.answer(
            f"Текущий лимит: <code>{label}</code>\n\n"
            "Введите максимальное число постов в час (или 0 для отключения лимита):",
            parse_mode="HTML"
        )
        await state.set_state(SettingsState.waiting_for_max_posts_per_hour)
    elif setting_type == "watermark_text":
        current = await get_setting("watermark_text", DEFAULT_WATERMARK)
        await callback.message.answer(f"Текущий водяной знак:\n<code>{html.escape(current)}</code>\n\nВведите новый текст:", parse_mode="HTML")
        await state.set_state(SettingsState.waiting_for_watermark_text)
    elif setting_type == "signature_text":
        current = await get_setting("custom_signature", "👉 Наш канал. Подписаться")
        await callback.message.answer(f"Текущая подпись:\n<code>{html.escape(current)}</code>\n\nВведите новый текст:", parse_mode="HTML")
        await state.set_state(SettingsState.waiting_for_signature_text)
    elif setting_type == "ai_prompt":
        from services.ai_rewrite import DEFAULT_PROMPT
        current = await get_setting("ai_prompt", DEFAULT_PROMPT)
        await callback.message.answer(f"Текущий промт:\n<code>{html.escape(current)}</code>\n\nВведите новый промпт (или /cancel для отмены):", parse_mode="HTML")
        await state.set_state(SettingsState.waiting_for_ai_prompt)
    elif setting_type == "target_channels":
        current = await get_setting("target_channels", "@topor, @lentachold")
        await callback.message.answer(f"Текущие каналы-доноры:\n<code>{html.escape(current)}</code>\n\nВведите список каналов через запятую (с @):", parse_mode="HTML")
        await state.set_state(SettingsState.waiting_for_target_channels)
        
    await callback.answer()

@router.message(SettingsState.waiting_for_max_posts_per_hour)
async def process_new_max_posts_per_hour(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 0:
        await message.answer("Пожалуйста, введите положительное число (или 0 для отключения лимита).")
        return
    await set_setting("max_posts_per_hour", message.text)
    await state.clear()
    label = "отключен (без лимита)" if message.text == "0" else f"{message.text} постов в час"
    await message.answer(f"✅ Лимит публикаций успешно обновлен: <b>{label}</b>.", parse_mode="HTML")
    await show_settings(message)



@router.message(SettingsState.waiting_for_watermark_text)
async def process_new_watermark_text(message: Message, state: FSMContext):
    await set_setting("watermark_text", message.text)
    await state.clear()
    await message.answer("✅ Текст водяного знака обновлен.")
    await show_settings(message)
    
@router.message(SettingsState.waiting_for_signature_text)
async def process_new_signature_text(message: Message, state: FSMContext):
    await set_setting("custom_signature", message.html_text)
    await state.clear()
    await message.answer("✅ Текст рекламной подписи обновлен.")
    await show_settings(message)

@router.message(SettingsState.waiting_for_ai_prompt)
async def process_new_ai_prompt(message: Message, state: FSMContext):
    await set_setting("ai_prompt", message.text)
    await state.clear()
    await message.answer("✅ Промпт ИИ обновлен.")
    await show_settings(message)

@router.message(SettingsState.waiting_for_target_channels)
async def process_new_target_channels(message: Message, state: FSMContext):
    await set_setting("target_channels", message.text)
    await state.clear()
    await message.answer("✅ Источники каналов обновлены.")
    await show_settings(message)

@router.message(F.text == "❌ Отмена")
@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    """Отмена любого текущего сценария."""
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_reply_keyboard())
