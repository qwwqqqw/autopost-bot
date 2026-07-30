import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile, URLInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from database.db import get_due_posts, mark_post_published

logger = logging.getLogger(__name__)

async def publish_due_posts_task(bot: Bot):
    """
    Фоновая задача, регулярно проверяющая базу данных на наличие отложенных постов,
    время публикации которых наступило.
    """
    while True:
        try:
            now_iso = datetime.now().strftime("%Y-%m-%d %H:%M")
            due_posts = await get_due_posts(now_iso)
            
            for post in due_posts:
                post_id = post["id"]
                target_channel = post["target_channel"]
                content_text = post["content_text"] or ""
                photo_path = post["photo_path"]
                
                try:
                    if photo_path:
                        if len(content_text) <= 1024:
                            if photo_path.startswith("http"):
                                photo_file = URLInputFile(photo_path)
                            else:
                                photo_file = FSInputFile(photo_path)
                            sent_message = await bot.send_photo(
                                chat_id=target_channel,
                                photo=photo_file,
                                caption=content_text,
                                parse_mode="HTML"
                            )
                        else:
                            from aiogram.types import LinkPreviewOptions
                            opts = LinkPreviewOptions(
                                url=photo_path, 
                                prefer_large_media=True,
                                show_above_text=True
                            ) if photo_path.startswith("http") else None
                            
                            sent_message = await bot.send_message(
                                chat_id=target_channel,
                                text=content_text,
                                parse_mode="HTML",
                                link_preview_options=opts
                            )
                    else:
                        sent_message = await bot.send_message(
                            chat_id=target_channel,
                            text=content_text,
                            parse_mode="HTML"
                        )
                    
                    if sent_message:
                        await mark_post_published(post_id, sent_message.message_id)
                        logger.info(f"Пост #{post_id} успешно опубликован в {target_channel}!")

                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    logger.warning(
                        f"⚠️ Не удалось опубликовать пост #{post_id} в {target_channel}.\n"
                        f"Причина: {e.message}.\n"
                        f"👉 Убедитесь, что бот добавлен в администраторы канала '{target_channel}' с правом публикации!"
                    )
                    await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"Ошибка в фоновом планировщике публикаций: {e}")
            
        await asyncio.sleep(20)
