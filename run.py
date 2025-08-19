import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.dao.database import initialize_db, init_db, init_promokode
from handlers_show.__init__ import router
from scheduler import scheduler, init_scheduler, send_reminder


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    init_scheduler(bot)
    await init_promokode()
    await init_db()
    await initialize_db()
    me = await bot.get_me()
    logger.info(f"🤖 Бот @{me.username} успешно подключён к Telegram")

async def main():
    bot = Bot(token="7729207630:AAGrPOjWgyF4KpoYX4aFOHgJXzK-ncx2MdM")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        await on_startup(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except (TelegramBadRequest, TelegramAPIError) as e:
        logger.error(f"Ошибка Telegram: {e}")
    finally:
        if hasattr(scheduler, 'scheduler') and scheduler.scheduler.running:
            scheduler.scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("🛑 Бот остановлен")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Принудительное завершение")

