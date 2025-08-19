from aiogram import Bot, types, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, SuccessfulPayment
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import aiosqlite
from handlers_show.handlers_admin import is_admin
from bot.dao.database import save_payment, create_access_token, get_active_stream, create_access_token
import time, asyncio, os
import keyboards.keyboards_admin as kb_admin
from bot.dao.database import init_db
from handlers_show.__init__ import logger, router


DB_PATH = Path('data/streams.db')
DB_PROMOKODE = Path('data/promokode.db')

#группу для сохранения о платёжки в БД
class NewStream(StatesGroup):
    NAME = State()
    PRICE = State()
    DESCRIPTION = State()
    CHAT_ID = State()
    START_TIME = State()
    END_TIME = State()
    INVITE_LINK = State()

def extract_chat_id_from_link(invite_link: str) -> Optional[int]:
    """Извлекает chat_id из invite-ссылки"""
    try:
        # Для ссылок вида https://t.me/c/1234567890
        if "/c/" in invite_link:
            chat_part = invite_link.split("/c/")[1]
            if chat_part.isdigit():
                return int(f"-100{chat_part}")
        
        # Для стандартных invite-ссылок
        # (если нужно получить chat_id для approve_chat_join_request)
        # Здесь может потребоваться дополнительная логика в зависимости от формата ссылки
        return None
    except Exception:
        return None

@router.message(Command("start_stream"))
async def start_stream_creation(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен")
        
    await state.set_state(NewStream.NAME)
    await message.answer("Введите название стрима:")

@router.message(NewStream.NAME)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(NewStream.PRICE)
    await message.answer("Введите цену в рублях (например: 299.99):")

@router.message(NewStream.PRICE)
async def process_price(message: Message, state: FSMContext):
    try:
        rub = float(message.text)
        kopek = int(rub * 100)
        await state.update_data(amount_kopek=kopek)
        await state.set_state(NewStream.DESCRIPTION)
        await message.answer("Введите описание стрима:")
    except ValueError:
        await message.answer("Пожалуйста, введите число!")

@router.message(NewStream.DESCRIPTION)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(payload=message.text)
    await state.set_state(NewStream.CHAT_ID)
    await message.answer("Введите ID чата для стрима (начинается с -100):")

@router.message(NewStream.CHAT_ID)
async def process_chat_id(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.text)
    await state.set_state(NewStream.START_TIME)
    await message.answer("Введите дату начала (формат: ДД.ММ.ГГГГ ЧЧ:ММ):")

@router.message(NewStream.START_TIME)
async def process_start_time(message: Message, state: FSMContext):
    try:
        start = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        await state.update_data(start_time=start)
        await state.set_state(NewStream.END_TIME)
        await message.answer("Введите дату окончания (формат: ДД.ММ.ГГГГ ЧЧ:ММ):")
    except ValueError:
        await message.answer("Неправильный формат даты!")

@router.message(NewStream.END_TIME)
async def process_end_time(message: Message, state: FSMContext):
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        end_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        
        # Проверяем корректность даты
        if end_time <= data['start_time']:
            await message.answer("❌ Дата окончания должна быть позже даты начала!")
            return

        # Запрашиваем invite-ссылку
        await state.update_data(end_time=end_time)
        await state.set_state(NewStream.INVITE_LINK)
        
        # Формируем инструкцию для получения ссылки
        instructions = [
            "📌 Теперь нужно создать invite-ссылку для чата:",
            "1. Откройте настройки чата",
            "2. Перейдите в 'Пригласительные ссылки'",
            "3. Создайте новую ссылку (без срока действия)",
            "4. Отправьте её мне в этом чате",
            "",
            "⚠️ Ссылка должна начинаться с https://t.me/ или t.me/"
        ]
        
        await message.answer("\n".join(instructions))
        
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте ДД.ММ.ГГГГ ЧЧ:ММ")
    except Exception as e:
        logger.error(f"Ошибка в process_end_time: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте снова.")
        await state.clear()

@router.message(NewStream.INVITE_LINK)
async def process_invite_link(message: Message, state: FSMContext):
    try:
        # Проверяем ссылку
        if not (message.text.startswith("https://t.me/") or message.text.startswith("t.me/")):
            await message.answer("❌ Некорректная ссылка! Должна начинаться с https://t.me/")
            return
            
        # Нормализуем ссылку
        invite_link = message.text.replace("t.me/", "https://t.me/")
        
        # Получаем все данные
        data = await state.get_data()
        
        # Сохраняем в БД
        async with aiosqlite.connect(DB_PATH) as db:
            # Деактивируем предыдущие стримы
            await db.execute("UPDATE streams SET is_active = 0")
            
            # Добавляем новый стрим
            await db.execute(
                """INSERT INTO streams 
                (name, amount_kopek, payload, chat_id, start_time, end_time, invite_link, is_active) 
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    data['name'],
                    data['amount_kopek'],
                    data['payload'],
                    data['chat_id'],
                    data['start_time'].isoformat(),
                    data['end_time'].isoformat(),
                    invite_link
                )
            )
            await db.commit()
        
        # Формируем отчет о создании
        report = [
            "✅ Стрим успешно создан!",
            f"📌 Название: {data['name']}",
            f"💵 Цена: {data['amount_kopek'] / 100:.2f} руб.",
            f"🆔 ID чата: {data['chat_id']}",
            f"🕒 Период: {data['start_time'].strftime('%d.%m.%Y %H:%M')} - {data['end_time'].strftime('%d.%m.%Y %H:%M')}",
            f"🔗 Ссылка: {invite_link}",
            "",
            "Теперь пользователи смогут присоединяться по этой ссылке после оплаты."
        ]
        
        await message.answer("\n".join(report))
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в process_invite_link: {e}")
        await message.answer("❌ Ошибка при сохранении стрима. Попробуйте снова.")
        await state.clear()

@router.callback_query(F.data == "pay_stream")
async def process_payment(callback: CallbackQuery, bot: Bot):
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or "NoUsername"
        used_promo_tag = None
        discount_percent = 0
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем активный стрим
            cursor = await db.execute("""
                SELECT id, name, amount_kopek, payload, chat_id 
                FROM streams 
                WHERE is_active = 1 
                AND datetime(start_time) <= datetime('now', 'localtime') 
                AND datetime(end_time) >= datetime('now', 'localtime')
                LIMIT 1
            """)
            stream = await cursor.fetchone()
            
        if not stream:
            return await callback.answer("Нет активных стримов", show_alert=True)
        
        stream_id, name, base_amount, payload, chat_id = stream
        payment_id = f"stream_{stream_id}_{user_id}_{int(time.time())}"
        
        # Проверяем активный промокод
        async with aiosqlite.connect(DB_PROMOKODE) as db:
            db.row_factory = aiosqlite.Row
            # Получаем информацию о примененном промокоде
            cursor = await db.execute(
                """SELECT up.tag, pc.percent 
                FROM use_promokode_users up
                JOIN promokode_create pc ON up.tag = pc.tag
                WHERE up.user_id = ? AND up.chapter = 'stream'
                LIMIT 1""",
                (user_id,)
            )
            promo = await cursor.fetchone()
            
            if promo:
                used_promo_tag = promo['tag']
                discount_percent = promo['percent']
                
                # Проверяем, не превышено ли максимальное количество использований промокода
                cursor = await db.execute(
                    """SELECT COUNT(*) as usage_count 
                    FROM promocode_usages 
                    WHERE promocode_tag = ?""",
                    (used_promo_tag,)
                )
                usage_data = await cursor.fetchone()
                usage_count = usage_data['usage_count'] if usage_data else 0
                
                cursor = await db.execute(
                    """SELECT max_enteger 
                    FROM promokode_create 
                    WHERE tag = ?""",
                    (used_promo_tag,)
                )
                promo_data = await cursor.fetchone()
                max_usage = promo_data['max_enteger'] if promo_data else 0
                
                if max_usage > 0 and usage_count >= max_usage:
                    # Промокод исчерпал лимит использований
                    used_promo_tag = None
                    discount_percent = 0
                    await callback.answer("⚠️ Промокод больше не действителен", show_alert=True)
        
        # Рассчитываем сумму с учетом скидки
        if used_promo_tag and discount_percent > 0:
            discount_amount = int(base_amount * discount_percent / 100)
            final_amount = base_amount - discount_amount
            discount_message = f" (скидка {discount_percent}%)"
        else:
            final_amount = base_amount
            discount_message = ""

        # Сохраняем информацию для обновления после оплаты
        if used_promo_tag:
            async with aiosqlite.connect(DB_PROMOKODE) as db:
                await db.execute(
                    """INSERT INTO pending_promo_updates 
                    (user_id, promo_tag, payment_id) 
                    VALUES (?, ?, ?)""",
                    (user_id, used_promo_tag, payment_id)
                )
                await db.commit()

        # Отправляем инвойс
        await bot.send_invoice(
            chat_id=user_id,
            title=f"Доступ к стриму: {name}{discount_message}",
            description=payload,
            payload=payment_id,
            provider_token='381764678:TEST:129002',
            currency="RUB",
            prices=[LabeledPrice(label=name, amount=final_amount)],
            need_email=True,
            protect_content=True
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в process_payment: {e}")
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)

@router.message(F.successful_payment.invoice_payload.startswith("stream_"))
async def handle_successful_payment(message: Message, bot: Bot):
    try:
        payment = message.successful_payment
        user_id = message.from_user.id

        #чек промо
        async with aiosqlite.connect(DB_PROMOKODE) as db:
            db.row_factory = aiosqlite.Row
            
            # Находим промокод для обновления
            cursor = await db.execute(
                """SELECT tag FROM use_promokode_users 
                WHERE user_id = ? AND chapter = 'stream'
                LIMIT 1""",
                (user_id,)
            )
            promo = await cursor.fetchone()
            
            if promo:
                await db.execute(
                    """UPDATE use_promokode_users 
                    SET chapter = 'stream_use' 
                    WHERE user_id = ? AND tag = ?""",
                    (user_id, promo['tag'])
                )
                await db.commit()

        # 1. Парсим payload
        parts = payment.invoice_payload.split('_')
        if len(parts) != 4:
            raise ValueError("Неверный формат payload")
        stream_id = int(parts[1])

        # 2. Получаем данные о стриме из БД
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT invite_link FROM streams WHERE id = ?", 
                (stream_id,)
            )
            stream = await cursor.fetchone()
            
        if not stream or not stream[0]:
            raise ValueError("Стрим не найден или отсутствует invite-ссылка")
            
        invite_link = stream[0]

        # 3. Пытаемся добавить пользователя в чат
        try:
            # Получаем chat_id из invite-ссылки
            chat_id = extract_chat_id_from_link(invite_link)
            if chat_id:
                await bot.approve_chat_join_request(
                    chat_id=chat_id,
                    user_id=user_id
                )
        except Exception as e:
            logger.error(f"Ошибка добавления в чат: {e}")

        # 4. Всегда отправляем постоянную invite-ссылку
        response = [
            "🎉 Оплата прошла успешно!",
            f"💵 Сумма: {payment.total_amount / 100:.2f} RUB",
            "",
            "🔗 Постоянная ссылка для входа в чат:",
            f"{invite_link}",
            "",
            "Можете переходить сразу по ссылке выше"
        ]
        
        await message.answer("\n".join(response))
        
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        await message.answer("❌ Произошла ошибка. Обратитесь в поддержку.")

@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: Message, bot: Bot):
    try:
        # Извлекаем токен из deep link (формат: /start join_<token>)
        token = message.text.split()[1].split('_')[1]
        
        # Проверяем токен в БД
        async with aiosqlite.connect(DB_PATH) as db:
            # Находим токен и связанный стрим
            cursor = await db.execute("""
                SELECT a.user_id, a.stream_id, s.chat_id 
                FROM access_tokens a
                JOIN streams s ON a.stream_id = s.id
                WHERE a.token = ? 
                AND a.used = 0
                AND datetime(a.expires_at) > datetime('now')
            """, (token,))
            data = await cursor.fetchone()
            
            if not data:
                return await message.answer("❌ Недействительная или просроченная ссылка")
            
            user_id, stream_id, chat_id = data
            
            # Проверяем, что пользователь совпадает
            if user_id != message.from_user.id:
                return await message.answer("❌ Эта ссылка предназначена другому пользователю")
            
            # Помечаем токен как использованный
            await db.execute(
                "UPDATE access_tokens SET used = 1 WHERE token = ?",
                (token,)
            )
            await db.commit()
        
        # Добавляем пользователя в чат
        try:
            await bot.add_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                until_date=int((datetime.now() + timedelta(days=1)).timestamp()))
            
            await message.answer(
                f"✅ Вы успешно добавлены в чат стрима!\n"
                f"Ссылка на чат: https://t.me/c/{chat_id[4:]}"
            )
        except Exception as e:
            logger.error(f"Ошибка добавления в чат: {e}")
            await message.answer(
                "❌ Не удалось добавить вас в чат. Обратитесь в поддержку.",
                reply_markup=kb_admin.support_kb()
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки deep link: {e}")
        await message.answer("❌ Ошибка обработки ссылки")

@router.message(Command("i"))
async def get_chat_id(message: Message):
    chat_id = message.chat.id
    
    # Правильное преобразование в формат для супергрупп (-100...)
    if str(chat_id).startswith('-'):
        supergroup_id = f"-100{str(chat_id)[4:]}" if str(chat_id).startswith('-100') else f"-100{str(chat_id)[1:]}"
    else:
        supergroup_id = f"-100{chat_id}"
    
    await message.answer(
        f"ID этого чата: <code>{chat_id}</code>\n\n"
        f"Для стримов используйте ID: <code>{supergroup_id}</code>",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "stream_info")
async def stream_info(callback: CallbackQuery, state: FSMContext):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT name, amount_kopek, payload, start_time, end_time
                FROM streams 
                WHERE is_active = 1 
                ORDER BY start_time DESC 
                LIMIT 1"""  # берём последнюю активную трансляцию
            )
            stream = await cursor.fetchone()  # получаем одну запись
            name, amount_kopek, payload, start_time, end_time = stream  # распаковываем кортеж
            end_time_str = str(end_time)

        if datetime.now() > datetime.fromisoformat(end_time_str):
            await callback.message.answer('В данный момент нет активных стримов, следите за новостями')
            await callback.answer()
            return
        
        
        await callback.message.answer(
            f"🎥 Трансляция: {name}  | {payload}\n\n"
            f"💰 Цена: {amount_kopek / 100} руб.\n"
            f"⏰ Начало: {start_time}\n"
            f"🔚 Конец: {end_time}\n"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при получении данных: {e}")
        await callback.answer()