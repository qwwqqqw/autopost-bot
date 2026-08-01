import asyncio
import logging
import random
from aiogram import Bot
from aiogram.types import FSInputFile, URLInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

from config import CHANNEL_ID
from database.db import get_setting, check_link_published, mark_link_published, get_published_count_last_hour
from services.tg_parser import fetch_tg_channel_posts
from services.ai_rewrite import rewrite_text_with_gemini
from services.watermark import add_watermark

logger = logging.getLogger(__name__)

async def run_manual_parsing(bot: Bot) -> str:
    """Один цикл парсинга (для ручного запуска). Возвращает сообщение о результате."""
    max_posts_str = await get_setting("max_posts_per_hour", "0")
    if max_posts_str.isdigit() and int(max_posts_str) > 0:
        limit = int(max_posts_str)
        published_last_hour = await get_published_count_last_hour()
        if published_last_hour >= limit:
            logger.info(f"Достигнут лимит постов за час ({published_last_hour}/{limit}). Публикация пропущена.")
            return f"ℹ️ Достигнут лимит публикаций за час ({published_last_hour}/{limit})."

    target_channels_str = await get_setting("target_channels", "@topor, @lentachold")
    channels = [c.strip() for c in target_channels_str.split(",") if c.strip()]
    random.shuffle(channels)
    
    for channel in channels:
        articles = await fetch_tg_channel_posts(channel, limit=5)
        for article in articles:
            is_pub = await check_link_published(article["link"])
            if not is_pub:
                logger.info(f"Найден свежий пост: {article['link']}")
                
                rewritten_text = await rewrite_text_with_gemini(article["text"])
                if rewritten_text in ["REJECT_AD", "REJECT_BORING", "DUPLICATE"]:
                    logger.info(f"Пост пропущен ИИ ({rewritten_text}): {article['link']}")
                    await mark_link_published(article["link"], "")
                    continue
                    
                if not rewritten_text:
                    rewritten_text = article["text"]
                    
                sig_enabled = await get_setting("signature_enabled", "0")
                if sig_enabled == "1":
                    custom_sig = await get_setting("custom_signature", "👉 Наш канал. Подписаться")
                    rewritten_text += f"\n\n{custom_sig}"
                    
                watermark_text = await get_setting("watermark_text", "@qwwqqqw")
                is_watermark = await get_setting("watermark_enabled", "1")
                
                video_url = article.get("video")
                photo_urls = article.get("photos", [])
                
                try:
                    if video_url:
                        if len(rewritten_text) > 1024:
                            rewritten_text = rewritten_text[:1020] + "..."
                        media_file = URLInputFile(video_url)
                        await bot.send_video(chat_id=CHANNEL_ID, video=media_file, caption=rewritten_text, parse_mode="HTML")
                        
                    elif photo_urls:
                        processed_photos = []
                        import httpx, aiofiles, os
                        from pathlib import Path
                        
                        for i, p_url in enumerate(photo_urls):
                            if is_watermark == "1" and p_url.startswith("http"):
                                try:
                                    tmp_path = Path("uploads") / f"temp_autopost_{i}.jpg"
                                    tmp_path.parent.mkdir(parents=True, exist_ok=True)
                                    async with httpx.AsyncClient(follow_redirects=True) as client:
                                        r = await client.get(p_url)
                                        if r.status_code == 200:
                                            async with aiofiles.open(tmp_path, 'wb') as f:
                                                await f.write(r.content)
                                            wm_path = add_watermark(str(tmp_path), watermark_text)
                                            processed_photos.append(FSInputFile(wm_path))
                                            continue
                                except Exception as e:
                                    logger.error(f"Ошибка водяного знака на фото {i}: {e}")
                            
                            processed_photos.append(URLInputFile(p_url) if p_url.startswith("http") else FSInputFile(p_url))
                        
                        if len(processed_photos) == 1:
                            if len(rewritten_text) > 1024:
                                rewritten_text = rewritten_text[:1020] + "..."
                            await bot.send_photo(chat_id=CHANNEL_ID, photo=processed_photos[0], caption=rewritten_text, parse_mode="HTML")
                        else:
                            media_group = []
                            for idx, photo_file in enumerate(processed_photos):
                                if idx == 0:
                                    media_group.append(InputMediaPhoto(media=photo_file, caption=rewritten_text, parse_mode="HTML"))
                                else:
                                    media_group.append(InputMediaPhoto(media=photo_file))
                            await bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
                    else:
                        await bot.send_message(chat_id=CHANNEL_ID, text=rewritten_text, parse_mode="HTML", disable_web_page_preview=True)
                        
                    await mark_link_published(article["link"], rewritten_text)
                    return f"✅ Успешно опубликован пост из {channel}!"
                except TelegramBadRequest as e:
                    logger.error(f"Ошибка публикации: {e}")
                    await mark_link_published(article["link"], "")
                except Exception as e:
                    logger.error(f"Неизвестная ошибка: {e}")
                    
    return "ℹ️ Нет новых уникальных новостей для публикации во всех источниках."

async def autoposter_task(bot: Bot):
    """
    Фоновая задача автопостинга.
    Моментальный парсинг каждые 60 секунд.
    """
    logger.info("Служба автопостинга запущена.")

    while True:
        try:
            autopost_enabled = await get_setting("autopost_enabled", "0")
            if autopost_enabled == "1":
                await run_manual_parsing(bot)
        except Exception as e:
            logger.error(f"Критическая ошибка автопостера: {e}")
            
        await asyncio.sleep(20)
