from aiogram import F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, PreCheckoutQuery, LabeledPrice
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton)
from bot.dao.database import db_Ibaza
import logging
import aiosqlite
import keyboards.keyboards_admin as kb_admin
import keyboards.keyboards_main as kb_main
import keyboards.keyboards_shop as kb_shop
from bot.dao.database import (get_user_payments, check_payment, 
                            grant_content_access,)
import secrets
from datetime import datetime, timedelta
import time
from pathlib import Path
from handlers_show.__init__ import logger, router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data.reg import information_pie_bliss

DB_PROMOKODE = Path('data/promokode.db')
TARGET_CHAT_ID = -1002722473030

#Информация о торте
@router.message(F.text == 'ТОРТ БЛАЖЕНСТВО')
async def info_pie(message: Message, bot: Bot):
    error_messages = []
    user_id = message.chat.id
    try:
        #Проверям и инифиадизируем информацию
        id_photo = information_pie_bliss.get('photo_prevu_pie')
        if not id_photo:
            error_messages.append("❌ Фото не найдено в базе")
        
        id_caption = information_pie_bliss.get('text_caption_prevu_pie')
        if not id_caption:
            error_messages.append("❌ Описание не найдено в базе")
        #Проверка на ошибку, если нет
            if error_messages:
                error_text = "\n".join(error_messages) + "\n\nПожалуйста, напишите в поддержку"
                await message.answer(error_text)
                return
        
        #Отправляем фото с описанием
        await bot.send_photo(
            chat_id= user_id,
            photo = id_photo,
            reply_markup=kb_main.pie_bliss_kb,
            protect_content=True,
            caption= id_caption
        )
    except Exception as e:
        logger.info(f'Ошибка в торте блаженство! {e}')
        message.answer('Неизвестная ошибка! Обратитеть в поддержку!')

#Создание платежа 
@router.callback_query(F.data == 'pay_for_pie_bliss')
async def handle_pay_for_content_rela(callback: CallbackQuery, bot: Bot):
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or "NoUsername"
        base_amount = 88800  # 888.00 RUB в копейках
        payload = "pie_bliss"
        payment_id = f"pay_{user_id}_{int(time.time())}"
        used_promo_tag = None
        discount_percent = 0
        
        # Проверяем активный промокод
        async with aiosqlite.connect(DB_PROMOKODE) as db:
            db.row_factory = aiosqlite.Row
            # Получаем информацию о примененном промокоде
            cursor = await db.execute(
                """SELECT up.tag, pc.percent 
                FROM use_promokode_users up
                JOIN promokode_create pc ON up.tag = pc.tag
                WHERE up.user_id = ? AND up.chapter = 'pie_bliss_buy'
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
            title=f'торт блаженство"{discount_message}',
            description='Доступ к материалам курса',
            payload=payload,
            provider_token='381764678:TEST:129002',
            currency='RUB',
            prices=[LabeledPrice(label='Доступ к курсу', amount=final_amount)],
            need_email=True
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка в handle_pay_for_content: {e}")
        await callback.answer("⚠️ Произошла ошибка", show_alert=True)

#Проверка прошла ли платёжка
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

#Создание одноразовой ссылки
async def create_chat_invite_link(bot: Bot):
    #Создает одноразовую инвайт-ссылку для беседы
    try:
        # Создаем инвайт-ссылку для КОНКРЕТНОЙ БЕСЕДЫ
        invite_link = await bot.create_chat_invite_link(
            chat_id=TARGET_CHAT_ID,
            name=f"invite_{secrets.token_hex(8)}",
            expire_date=datetime.now() + timedelta(hours=24),
            member_limit=1,  # Одноразовая
            creates_join_request=False  # Прямое вступление, а не запрос
        )
        return invite_link.invite_link
    except Exception as e:
        logger.error(f"Ошибка создания инвайт-ссылки: {e}")
        raise

#Отправка после платежки файл или текст
@router.message(F.successful_payment.invoice_payload == "pie_bliss")
async def process_successful_payment(message: Message, bot: Bot):
    try:
        user_id = message.from_user.id
        invite_link = await create_chat_invite_link(bot)
        
        # Сохраняем в базу
        async with aiosqlite.connect('database.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS chat_invites (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    chat_id INTEGER,
                    invite_link TEXT,
                    used BOOLEAN DEFAULT 0,
                    created_at DATETIME
                )
            ''')
            
            await db.execute(
                '''INSERT INTO chat_invites 
                (user_id, chat_id, invite_link, created_at) 
                VALUES (?, ?, ?, ?)''',
                (user_id, TARGET_CHAT_ID, invite_link, datetime.now())
            )
            await db.commit()
        
        # Отправляем пользователю ссылку НА БЕСЕДУ
        await message.answer(
            "🎉 Оплата прошла успешно!\n\n"
            f"Присоединяйтесь к нашему закрытому чату:\n"
            f"👉 {invite_link}\n\n"
            "⚠️ Ссылка действительна 24 часа и может быть использована только один раз!",
            protect_content=True
        )

        #Обновляем промокод
        async with aiosqlite.connect(DB_PROMOKODE) as db:
            db.row_factory = aiosqlite.Row
            
            # Находим промокод для обновления
            cursor = await db.execute(
                """SELECT tag FROM use_promokode_users 
                WHERE user_id = ? AND chapter = 'pie_bliss'
                LIMIT 1""",
                (user_id,)
            )
            promo = await cursor.fetchone()
            
            if promo:
                await db.execute(
                    """UPDATE use_promokode_users 
                    SET chapter = 'pie_bliss_use' 
                    WHERE user_id = ? AND tag = ?""",
                    (user_id, promo['tag'])
                )
                await db.commit()

        # Обновляем основную БД
        await grant_content_access(
            user_id=user_id,
            content_id="pie_bliss",
            days=30
        )

    except Exception as e:
        print(f"Ошибка обработки платежа: {e}")
        await message.answer("⚠️ Произошла ошибка. Обратитесь в поддержку.")
    