import aiosqlite
from pathlib import Path
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import sqlite3 as sq
from aiogram import Bot
import secrets
import hashlib

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_Ibaza = Path('data/info_baza.db')
DB_NAME = Path("data/streams.db")
DB_PROMOKODE = Path('data/promokode.db')


async def initialize_db():
    #Инициализация базы данных с обработкой ошибок
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            # Включение поддержки внешних ключей
            await db.execute("PRAGMA foreign_keys = ON")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    payment_id TEXT UNIQUE,
                    payload TEXT,
                    status TEXT DEFAULT 'pending',
                    provider_data TEXT,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
                                    #Админ id - Имя
            await db.execute(""" 
                CREATE TABLE IF NOT EXISTS admin(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            username TEXT NOT NULL
                            )
                        """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS content_access (
                    user_id INTEGER NOT NULL,
                    content_id TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    protect_content BOOLEAN DEFAULT TRUE,
                    PRIMARY KEY (user_id, content_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user(
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    money INTEGER DEFAULT 0,
                    user_file TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS file(
                    id INTEGER PRIMARY KEY,
                    name_file TEXT UNIQUE,
                    description TEXT,
                    Datatype INTEGER,
                    id_file_bot TEXT UNIQUE,
                    Storage BLOB
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS sent_messages (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    content_id TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id, content_id) REFERENCES content_access(user_id, content_id),
                    PRIMARY KEY (chat_id, message_id)
                )
            """)
            #БД для массовой рассылки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    subscribed INTEGER DEFAULT 1
                )
            ''')
                
            # Создание индексов для ускорения поиска
            await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_id ON payments(payment_id)")
            
            await db.commit()
            logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        raise

async def save_payment(
    user_id: int,
    username: str,
    amount: int,
    currency: str,
    payment_id: str,
    payload: str,
    status: str = "pending"
) -> bool:
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            await db.execute(
                """
                INSERT INTO payments 
                (user_id, username, amount, currency, payment_id, payload, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, amount, currency, payment_id, payload, status)
            )
            await db.commit()
            logger.info(f"✅ Платёж сохранён. ID: {payment_id}")
            return True
    except aiosqlite.IntegrityError:
        logger.warning(f"⚠️ Платёж {payment_id} уже существует")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {str(e)}")
        return False

# Функция для получения всех пользователей
def get_all_users():
    conn = sq.connect(db_Ibaza)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE subscribed = 1")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


async def check_payment(
    user_id: int, 
    amount: int = 500000,
    days_valid: int = 30
) -> bool:
    """
    Улучшенная проверка платежа с учетом срока действия
    
    Args:
        user_id: ID пользователя
        amount: Сумма для проверки
        days_valid: Количество дней, в течение которых платеж считается действительным

    Returns:
        True если есть действующий платеж, иначе False
    """
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            async with db.execute(
                """
                SELECT 1 FROM payments 
                WHERE user_id = ? AND amount = ? 
                AND payment_date >= datetime('now', ?)
                LIMIT 1
                """,
                (user_id, amount, f"-{days_valid} days")
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа для пользователя {user_id}: {e}")
        return False

async def get_user_payments(user_id: int, limit: int = 10) -> list:
    """
    Получение платежей пользователя с пагинацией
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество возвращаемых платежей

    Returns:
        Список словарей с информацией о платежах
    """
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            db.row_factory = aiosqlite.Row  # Для доступа к полям по имени
            async with db.execute(
                """
                SELECT * FROM payments 
                WHERE user_id = ?
                ORDER BY payment_date DESC
                LIMIT ?
                """,
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении платежей пользователя {user_id}: {e}")
        return []
    
async def update_payment_status(
    payload: str,
    status: str,
    provider_data: Optional[str] = None
) -> bool:
    """Обновляет статус платежа по payload (из invoice_payload)."""
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            await db.execute(
                """
                UPDATE payments 
                SET status = ?, provider_data = ?
                WHERE payload = ?
                """,
                (status, provider_data, payload)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка обновления платежа {payload}: {e}")
        return False
    
async def has_active_payment(
    user_id: int,
    amount: Optional[int] = None,
    days_valid: int = 30
) -> bool:
    """
    Проверяет, есть ли у пользователя успешный платеж.
    Если amount=None, проверяет любой платеж.
    """
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            query = """
                SELECT 1 FROM payments 
                WHERE user_id = ? 
                AND status = 'completed'
                AND payment_date >= datetime('now', ?)
            """
            params = [user_id, f"-{days_valid} days"]
            
            if amount is not None:
                query += " AND amount = ?"
                params.append(amount)

            async with db.execute(query + " LIMIT 1", params) as cursor:
                return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка проверки платежа: {e}")
        return False
    
async def grant_content_access(
    user_id: int, 
    content_id: str, 
    days: int = 30,
    protect_content: bool = True
) -> bool:
    """Даёт доступ к контенту на указанное количество дней"""
    try:
        expires_at = datetime.now() + timedelta(days=days)
        async with aiosqlite.connect(db_Ibaza) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO content_access 
                (user_id, content_id, expires_at, protect_content)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, content_id, expires_at.isoformat(), protect_content)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка предоставления доступа: {e}")
        return False
    
async def check_content_access(user_id: int, content_id: str) -> dict:
    """Возвращает информацию о доступе, включая protect_content"""
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT expires_at, protect_content 
                FROM content_access 
                WHERE user_id = ? AND content_id = ? AND expires_at > datetime('now')
                """,
                (user_id, content_id)
            )
            result = await cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Ошибка проверки доступа: {e}")
        return None

async def check_db_tables():
    """Проверяет существование таблиц"""
    async with aiosqlite.connect(db_Ibaza) as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        return any('payments' in table for table in tables)
    
async def save_sent_message(
    user_id: int,
    chat_id: int,
    message_id: int,
    content_id: str,
    expires_at: datetime
):
    async with aiosqlite.connect(db_Ibaza) as db:
        await db.execute(
            """
            INSERT INTO sent_messages 
            (user_id, chat_id, message_id, content_id, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, chat_id, message_id, content_id, expires_at.isoformat())
        )
        await db.commit()

async def activate_access_after_payment(payload: str, bot: Bot):
    """Активирует доступ и отправляет контент после оплаты"""
    try:
        async with aiosqlite.connect(db_Ibaza) as db:
            # 1. Находим платеж
            cursor = await db.execute(
                "SELECT user_id, amount FROM payments WHERE payload = ? AND status = 'completed'",
                (payload,)
            )
            payment = await cursor.fetchone()
            
            if not payment:
                raise ValueError("Платеж не найден")

            user_id, amount = payment['user_id'], payment['amount']

            # 2. Определяем контент по сумме
            content_map = {
                500000: "want_talk_full",  # Пример для суммы 5000 руб
                300000: "want_talk_part"   # Пример для суммы 3000 руб
            }
            
            content_id = content_map.get(amount)
            if not content_id:
                raise ValueError(f"Неизвестная сумма: {amount}")

            # 3. Даем доступ
            expires_at = datetime.now() + timedelta(days=30)
            await grant_content_access(user_id, content_id, 30)

            # 4. Отправляем контент (пример для видео)
            video_msg = await bot.send_video(
                chat_id=user_id,
                video="BAACAgIAAxkBAAIDOWhiXoFoFPKZf-f8gfBo-1189e6-AAIQeQACgiwRS0EiLJVD7ITfNgQ",
                caption="🎬 Ваш вебинар"
            )

            # 5. Сохраняем сообщение
            await save_sent_message(
                user_id=user_id,
                chat_id=user_id,
                message_id=video_msg.message_id,
                content_id=content_id,
                expires_at=expires_at
            )

            return True
            
    except Exception as e:
        logger.error(f"Ошибка активации доступа: {e}")
        return False

async def is_admin(user_id: int) -> bool:
    """Проверяет, есть ли user_id в таблице admin"""
    async with aiosqlite.connect(db_Ibaza) as db:
        cursor = await db.execute("SELECT 1 FROM admin WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return bool(row)  # True если админ найден, False если нет
    
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount_kopek INTEGER NOT NULL,
            payload TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            invite_link TEXT
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS access_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stream_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used BOOLEAN DEFAULT 0,
            FOREIGN KEY(stream_id) REFERENCES streams(id)
        )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_token ON access_tokens(token)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_stream ON access_tokens(user_id, stream_id)")
        await db.commit()

async def create_stream(
    name: str,
    amount_kopek: int,
    payload: str,
    start_time: datetime,
    end_time: datetime,
    chat_id: str
) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE streams SET is_active = 0")
        cursor = await db.execute(
            """INSERT INTO streams 
            (name, amount_kopek, payload, start_time, end_time, chat_id) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (name, amount_kopek, payload, start_time.isoformat(), end_time.isoformat(), chat_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_active_stream() -> Optional[dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT id, name, amount_kopek, payload, start_time, end_time, chat_id 
        FROM streams 
        WHERE is_active = 1 
        AND datetime(start_time) <= datetime('now') 
        AND datetime(end_time) >= datetime('now')
        LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'amount_kopek': row[2],
                'payload': row[3],
                'start_time': datetime.fromisoformat(row[4]),
                'end_time': datetime.fromisoformat(row[5]),
                'chat_id': row[6]
            }
        return None

async def create_access_token(user_id: int, stream_id: int) -> str:
    """Создает одноразовый токен доступа и сохраняет в БД"""
    token = secrets.token_urlsafe(32)  # Генерация безопасного токена
    expires_at = datetime.now() + timedelta(days=1)  # Токен действует 24 часа
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """INSERT INTO access_tokens 
            (user_id, stream_id, token, expires_at) 
            VALUES (?, ?, ?, ?)""",
            (user_id, stream_id, token, expires_at.isoformat())
        )
        await db.commit()
    
    return token

async def validate_access_token(token: str, user_id: int) -> Optional[dict]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT a.stream_id, s.chat_id 
        FROM access_tokens a
        JOIN streams s ON a.stream_id = s.id
        WHERE a.token = ? 
        AND a.user_id = ?
        AND a.is_used = 0
        AND datetime(a.expires_at) >= datetime('now')
        """, (token_hash, user_id))
        
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE access_tokens SET is_used = 1 WHERE token = ?",
                (token_hash,))
            await db.commit()
            return {'stream_id': row[0], 'chat_id': row[1]}
            
    return None

async def check_tables():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='streams'
        """)
        exists = await cursor.fetchone()
        if not exists:
            raise Exception("Таблица 'streams' не существует!")
        

async def init_promokode():
    async with aiosqlite.connect(DB_PROMOKODE) as db:
        try:    
            await db.execute("""
            CREATE TABLE IF NOT EXISTS promokode_create (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                percent INTEGER NOT NULL,
                start_promokode TEXT NOT NULL,
                end_promokode TEXT NOT NULL,
                max_enteger INTEGER NOT NULL,
                emoynt_enteger INTEGER NOT NULL,  
                tag TEXT NOT NULL UNIQUE,
                chapter TEXT NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS use_promokode_users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            percent         INTEGER NOT NULL,
            tag             TEXT    NOT NULL,
            chapter         TEXT    NOT NULL,
            use_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS promocode_usages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                promocode_tag TEXT NOT NULL,
                use_date TEXT NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_promo_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                promo_tag TEXT NOT NULL,
                payment_id TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS tag ON promokode_create(tag)")
            await db.commit()
            print("✅ Таблица promokode_create успешно создана!")
        except Exception as e:
            print(f"❌ Ошибка при создании таблицы: {e}")