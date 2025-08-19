import aiosqlite
from pathlib import Path
import logging

# Настройки
DB_PATH = Path("bot.dao.database") 
logger = logging.getLogger(__name__)

async def migrate_protect_content():
    """Добавляет столбец protect_content и устанавливает значения по умолчанию"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Добавляем новый столбец, если его нет
            await db.execute(
                "ALTER TABLE content_access ADD COLUMN protect_content BOOLEAN DEFAULT TRUE"
            )
            # Обновляем существующие записи
            await db.execute(
                "UPDATE content_access SET protect_content = TRUE WHERE protect_content IS NULL"
            )
            await db.commit()
        logger.info("Миграция protect_content успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка миграции: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate_protect_content())