import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from services.scheduler import publish_due_posts_task
from services.autoposter import autoposter_task
from handlers import common, create_post, scheduled, rss_feed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

async def main():
    await init_db()

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ ОШИБКА: BOT_TOKEN не указан в .env файле!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(create_post.router)
    dp.include_router(scheduled.router)
    dp.include_router(rss_feed.router)

    asyncio.create_task(publish_due_posts_task(bot))
    asyncio.create_task(autoposter_task(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот  готов к работе")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
