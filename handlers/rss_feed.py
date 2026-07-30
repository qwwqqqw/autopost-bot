from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from services.rss_parser import fetch_rbc_pets_news
from services.ai_rewrite import rewrite_text_with_gemini
from services.watermark import add_watermark
from keyboards.inline import get_rss_navigation_keyboard
from config import CHANNEL_ID, UPLOADS_DIR, DEFAULT_WATERMARK
from database.db import add_scheduled_post, mark_post_published, get_setting
from datetime import datetime
from handlers.create_post import CreatePostState
import httpx
import uuid
import os

router = Router()

PARSED_NEWS_CACHE = {}

async def download_rss_image(url: str) -> str:
    if not url:
        return None
    try:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        local_path = str(UPLOADS_DIR / f"rss_{uuid.uuid4().hex}.jpg")
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                return local_path
    except Exception as e:
        print(f"Error downloading RSS image: {e}")
    return None

@router.message(F.text == "📰 RSS Новости")
async def show_pets_news(message: Message):
    """Сбор и показ актуальных новостей(https://www.rbc.ru/life/tag/pets)."""
    user_id = message.from_user.id
    wait_msg = await message.answer("<i>Парсинг...</i>", parse_mode="HTML")
    
    articles = await fetch_rbc_pets_news(limit=10)
            
    try:
        await wait_msg.delete()
    except Exception:
        pass

    if not articles:
        await message.answer("Не удалось получить новости.")
        return

    PARSED_NEWS_CACHE[user_id] = articles
    await message.answer(f"<b>Найдено новостей: {len(articles)}</b>", parse_mode="HTML")
    await send_rss_article_preview(message, user_id, 0, is_edit=False)

async def send_rss_article_preview(message: Message, user_id: int, index: int, is_edit: bool = False):
    """Отображение новости со стрелочками навигации [1/N] ."""
    articles = PARSED_NEWS_CACHE.get(user_id, [])
    if not articles:
        await message.answer("Список новостей пуст.")
        return

    total_count = len(articles)
    if index < 0 or index >= total_count:
        index = 0

    article = articles[index]
    formatted_text = (
        f"<b>{article['title']}</b>\n\n"
        f"{article['summary']}"
    )
    
    keyboard = get_rss_navigation_keyboard(index, total_count)
    
    if is_edit:
        try:
            await message.edit_text(
                formatted_text,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    url=article.get('image') or article['link'], 
                    prefer_large_media=True, 
                    show_above_text=True
                ),
                reply_markup=keyboard
            )
        except Exception:
            await message.answer(
                formatted_text,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    url=article.get('image') or article['link'], 
                    prefer_large_media=True, 
                    show_above_text=True
                ),
                reply_markup=keyboard
            )
    else:
        await message.answer(
            formatted_text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                url=article.get('image') or article['link'], 
                prefer_large_media=True, 
                show_above_text=True
            ),
            reply_markup=keyboard
        )

@router.callback_query(F.data.startswith("rss_nav_"))
async def rss_navigation_handler(callback: CallbackQuery):
    """Переключение по новостям стрелочками Назад / Вперед ."""
    index = int(callback.data.replace("rss_nav_", ""))
    user_id = callback.from_user.id
    await send_rss_article_preview(callback.message, user_id, index, is_edit=True)
    await callback.answer()

@router.callback_query(F.data == "rss_noop")
async def rss_noop_handler(callback: CallbackQuery):
    """Заглушка клика на [1/N]."""
    await callback.answer()

@router.callback_query(F.data.startswith("rss_pub_"))
async def publish_rss_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Автоматический ИИ-рерайт и мгновенная публикация новости."""
    data_parts = callback.data.split("_")
    index = int(data_parts[-1])
    user_id = callback.from_user.id
    articles = PARSED_NEWS_CACHE.get(user_id, [])
    
    if index >= len(articles):
        await callback.answer("Новость не найдена.")
        return
        
    article = articles[index]
    
    await callback.message.edit_text("⏳ <i>ИИ пишет пост, пожалуйста подождите...</i>", parse_mode="HTML")
    
    original_text = f"{article['title']}\n\n{article['summary']}"
    rewritten_text = await rewrite_text_with_gemini(original_text)
    if not rewritten_text:
        rewritten_text = f"<b>{article['title']}</b>\n\n{article['summary']}"
        
    final_text = rewritten_text
    if len(final_text) > 1024:
        final_text = final_text[:1020] + "..."
        
    local_photo = await download_rss_image(article.get('image'))
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    
    final_photo = local_photo
    if local_photo and wm_enabled:
        wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
        final_photo = add_watermark(local_photo, wm_text)
        
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    post_id = await add_scheduled_post(final_text, final_photo, [], now_str, CHANNEL_ID)
    
    from aiogram.types import FSInputFile
    if final_photo and os.path.exists(final_photo):
        sent_msg = await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=FSInputFile(final_photo),
            caption=final_text,
            parse_mode="HTML"
        )
    else:
        sent_msg = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_text,
            parse_mode="HTML"
        )
    await mark_post_published(post_id, sent_msg.message_id)
    await callback.answer("Новость опубликована!")
    await callback.message.answer(f"🎉 Новость успешно опубликована!")


@router.callback_query(F.data.startswith("rss_sched_"))
async def schedule_rss_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Автоматический ИИ-рерайт и переход к планированию новости."""
    data_parts = callback.data.split("_")
    index = int(data_parts[-1])
    user_id = callback.from_user.id
    articles = PARSED_NEWS_CACHE.get(user_id, [])
    
    if index >= len(articles):
        await callback.answer("Новость не найдена.")
        return
        
    article = articles[index]
    
    await callback.message.edit_text("⏳ <i>ИИ пишет пост...</i>", parse_mode="HTML")
    
    original_text = f"{article['title']}\n\n{article['summary']}"
    rewritten_text = await rewrite_text_with_gemini(original_text)
    if not rewritten_text:
        rewritten_text = f"<b>{article['title']}</b>\n\n{article['summary']}"
        
    final_text = rewritten_text
    
    local_photo = await download_rss_image(article.get('image'))
    wm_enabled = await get_setting("watermark_enabled", "True") == "True"
    
    final_photo = local_photo
    if local_photo and wm_enabled:
        wm_text = await get_setting("watermark_text", DEFAULT_WATERMARK)
        final_photo = add_watermark(local_photo, wm_text)

    from keyboards.reply import get_cancel_keyboard
    
    await state.set_state(CreatePostState.waiting_for_schedule_time)
    await state.update_data(
        content_text=final_text,
        raw_photo_path=final_photo,
        active_photo_path=final_photo,
        watermark_applied=wm_enabled
    )
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    await callback.message.answer(
        f"📅 <b>Укажите дату и время публикации</b>\n\n"
        f"Текущее время сервера: <code>{now_str}</code>\n\n"
        f"Введите время в формате <code>ГГГГ-ММ-ДД ЧЧ:ММ</code>\n"
        f"Или просто время на сегодня: <code>18:30</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
