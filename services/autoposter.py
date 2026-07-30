import asyncio
import logging
from aiogram import Bot
from aiogram.types import FSInputFile, URLInputFile
from aiogram.exceptions import TelegramBadRequest

from config import CHANNEL_ID
from database.db import get_setting, check_link_published, mark_link_published
from services.rss_parser import fetch_all_news
from services.ai_rewrite import rewrite_text_with_gemini
from services.watermark import add_watermark

logger = logging.getLogger(__name__)

async def autoposter_task(bot: Bot):
    """
    Фоновая задача автопостинга. Проверяет настройки каждые 60 секунд.
    Если включен режим autopost_enabled, то раз в autopost_interval_minutes публикует новость.
    """
    logger.info("Служба автопостинга запущена.")
    
    last_run_time = 0

    while True:
        try:
            autopost_enabled = await get_setting("autopost_enabled", "0")
            if autopost_enabled == "1":
                
                interval_str = await get_setting("autopost_interval_minutes", "180")
                try:
                    interval_minutes = int(interval_str)
                except ValueError:
                    interval_minutes = 180
                
                current_time = asyncio.get_event_loop().time()
                
                if current_time - last_run_time >= (interval_minutes * 60):
                    logger.info("Запуск цикла автопостинга...")
                    
                    articles = await fetch_all_news(limit_per_source=3)
                    
                    posted = False
                    for article in articles:
                        is_pub = await check_link_published(article["link"])
                        if not is_pub:
                            logger.info(f"Найдена свежая новость: {article['title']}")
                            
                            rewritten_text = await rewrite_text_with_gemini(article["summary"])
                            if not rewritten_text:
                                rewritten_text = article["summary"]
                                
                            watermark_text = await get_setting("watermark_text", "@qwwqqqw")
                            is_watermark = await get_setting("watermark_enabled", "1")
                            
                            photo_path = article.get("image")
                            if photo_path and is_watermark == "1" and photo_path.startswith("http"):
                                try:
                                    import httpx
                                    import aiofiles
                                    import os
                                    from pathlib import Path
                                    
                                    tmp_path = Path("uploads") / "temp_autopost.jpg"
                                    tmp_path.parent.mkdir(parents=True, exist_ok=True)
                                    
                                    async with httpx.AsyncClient(follow_redirects=True) as client:
                                        r = await client.get(photo_path)
                                        if r.status_code == 200:
                                            async with aiofiles.open(tmp_path, 'wb') as f:
                                                await f.write(r.content)
                                            photo_path = add_watermark(str(tmp_path), watermark_text)
                                except Exception as e:
                                    logger.error(f"Ошибка наложения водяного знака в фоне: {e}")
                            
                            try:
                                if photo_path:
                                    if len(rewritten_text) <= 1024:
                                        photo_file = URLInputFile(photo_path) if photo_path.startswith("http") else FSInputFile(photo_path)
                                        await bot.send_photo(
                                            chat_id=CHANNEL_ID,
                                            photo=photo_file,
                                            caption=rewritten_text,
                                            parse_mode="HTML"
                                        )
                                    else:
                                        from aiogram.types import LinkPreviewOptions
                                        opts = LinkPreviewOptions(
                                            url=photo_path, 
                                            prefer_large_media=True,
                                            show_above_text=True
                                        ) if photo_path.startswith("http") else None
                                        
                                        await bot.send_message(
                                            chat_id=CHANNEL_ID,
                                            text=rewritten_text,
                                            parse_mode="HTML",
                                            link_preview_options=opts
                                        )
                                else:
                                    await bot.send_message(
                                        chat_id=CHANNEL_ID,
                                        text=rewritten_text,
                                        parse_mode="HTML"
                                    )
                                
                                await mark_link_published(article["link"])
                                posted = True
                                logger.info(f"Автопостинг успешен: {article['link']}")
                                break  # Только один пост за цикл!
                                
                            except TelegramBadRequest as e:
                                logger.error(f"Ошибка публикации автопоста: {e}")
                    
                    if not posted:
                        logger.info("Нет новых уникальных новостей для публикации.")
                        
                    last_run_time = current_time

        except Exception as e:
            logger.error(f"Глобальная ошибка в фоновом автопостинге: {e}")
            
        await asyncio.sleep(60)
