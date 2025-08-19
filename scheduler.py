from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Инициализация планировщика
scheduler = AsyncIOScheduler()
bot_instance = None  # Будет установлен позже

def init_scheduler(bot):
    global bot_instance
    bot_instance = bot
    scheduler.start()
    logger.info("🟢 Планировщик напоминаний запущен")

async def send_reminder(user_id: int, days_left: int):
    try:
        await bot_instance.send_message(
            chat_id=user_id,
            text=f"🔔 Напоминание! Доступ к вебинару истекает через {days_left} дней.\n"
                "Успейте завершить обучение! 🚀"
        )
        logger.info(f"✉️ Напоминание отправлено user_id={user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки напоминания user_id={user_id}: {e}")

async def add_reminder(user_id: int, days_left: int, seconds: int = 15, reminder_num: int = 0):
    try:
        scheduler.add_job(
            send_reminder,
            'date',
            run_date=datetime.now() + timedelta(seconds=seconds),
            args=[user_id, days_left],
            id=f"reminder_{user_id}_{reminder_num}"  # Уникальный ID для каждого
        )
        logger.info(f"⏰ Напоминание #{reminder_num} для user_id={user_id} установлено")
    except Exception as e:
        logger.error(f"❌ Ошибка добавления напоминания: {e}")