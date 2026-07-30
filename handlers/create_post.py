import os
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import CHANNEL_ID, DEFAULT_WATERMARK, UPLOADS_DIR
from database.db import add_scheduled_post
from keyboards.reply import get_cancel_keyboard, get_main_reply_keyboard

router = Router()

class CreatePostState(StatesGroup):
    waiting_for_schedule_time = State()

@router.message(CreatePostState.waiting_for_schedule_time)
async def process_schedule_time(message: Message, state: FSMContext):
    """Обработка ввода времени для отложенного поста."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Планирование отменено.", reply_markup=get_main_reply_keyboard())
        return

    time_input = message.text.strip()
    target_dt = None
    
    try:
        if len(time_input) == 5 and ":" in time_input:
            today_date = datetime.now().strftime("%Y-%m-%d")
            time_input = f"{today_date} {time_input}"
            
        target_dt = datetime.strptime(time_input, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат времени! Введите дату и время в формате <code>YYYY-MM-DD HH:MM</code> или <code>HH:MM</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    content_text = data.get("content_text", "")
    photo_path = data.get("active_photo_path")

    publish_time_str = target_dt.strftime("%Y-%m-%d %H:%M")
    post_id = await add_scheduled_post(content_text, photo_path, [], publish_time_str, CHANNEL_ID)
    await state.clear()

    await message.answer(
        f"✅ <b>Пост #{post_id} сохранен в очередь!</b>\n\n"
        f"⏰ <b>Время публикации:</b> {publish_time_str}\n"
        f"📍 <b>Канал:</b> {CHANNEL_ID}",
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard()
    )
