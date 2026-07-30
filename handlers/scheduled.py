import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_pending_posts, get_post_by_id, cancel_scheduled_post
from keyboards.inline import get_scheduled_posts_keyboard

router = Router()

@router.message(F.text == "📅 Очередь постов")
async def show_scheduled_queue(message: Message):
    """Отображение текущей очереди отложенных публикаций."""
    posts = await get_pending_posts()
    
    if not posts:
        await message.answer(
            "<b>Очередь постов пуста.</b>\n\nВы можете добавить пост в очередь из раздела «📰 RSS Новости».",
            parse_mode="HTML"
        )
        return

    text = f"<b>Запланированные публикации ({len(posts)}):</b>\n\nВыберите пост для просмотра или отмены:"
    await message.answer(text, parse_mode="HTML", reply_markup=get_scheduled_posts_keyboard(posts))

@router.callback_query(F.data.startswith("view_post_"))
async def view_scheduled_post_handler(callback: CallbackQuery):
    """Просмотр конкретного отложенного поста при нажатии на него в списке."""
    post_id = int(callback.data.replace("view_post_", ""))
    post = await get_post_by_id(post_id)
    
    if not post:
        await callback.answer("Пост не найден или уже был опубликован/удален.")
        return

    content_text = post["content_text"] or "<i>(Без текста)</i>"
    photo_path = post["photo_path"]
    publish_time = post["publish_time"]
    target_channel = post["target_channel"]

    preview_header = (
        f"📌 <b>Отложенный пост #{post_id}</b>\n"
        f"⏰ <b>Время публикации:</b> {publish_time}\n"
        f"<b>Канал:</b> {target_channel}\n" + "—"*25 + "\n"
    )
    full_text = preview_header + content_text

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Отменить и удалить пост", callback_data=f"cancel_sched_{post_id}")
        ],
        [
            InlineKeyboardButton(text="Назад к списку очереди", callback_data="back_to_queue_list")
        ]
    ])

    if photo_path and os.path.exists(photo_path):
        photo_file = FSInputFile(photo_path)
        await callback.message.answer_photo(
            photo=photo_file,
            caption=full_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await callback.message.answer(
            full_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback.answer()

@router.callback_query(F.data == "back_to_queue_list")
async def back_to_queue_list_handler(callback: CallbackQuery):
    """Возврат к списку отложенных постов."""
    posts = await get_pending_posts()
    if posts:
        text = f"<b>Запланированные публикации ({len(posts)}):</b>\n\nВыберите пост для просмотра или отмены:"
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_scheduled_posts_keyboard(posts))
    else:
        await callback.message.answer("<b>Очередь постов пуста.</b>", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_sched_"))
async def cancel_scheduled_handler(callback: CallbackQuery):
    """Удаление/отмена отложенного поста."""
    post_id = int(callback.data.replace("cancel_sched_", ""))
    await cancel_scheduled_post(post_id)
    
    await callback.answer("Публикация отменена!")
    
    posts = await get_pending_posts()
    if posts:
        text = f"<b>Запланированные публикации ({len(posts)}):</b>"
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_scheduled_posts_keyboard(posts))
    else:
        await callback.message.answer("<b>Все отложенные публикации отменены. Очередь пуста.</b>", parse_mode="HTML")
