from aiogram import F, Router, Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, FSInputFile, PreCheckoutQuery, LabeledPrice
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton)

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from yookassa import Configuration, Webhook
from pathlib import Path
import aiosqlite
import keyboards.keyboards_admin as kb_admin
import keyboards.keyboards_main as kb_main
import keyboards.keyboards_shop as kb_shop
import bot.dao.database as db
from bot.dao.database import save_payment, update_payment_status
from bot.dao.database import check_payment, grant_content_access
from bot.dao.database import get_user_payments, check_content_access
import time
import os
from handlers_show.__init__ import router, logger

DB_PROMOKODE = Path('data/promokode.db')
#Чек Отношения -- [Купить вебинар (Запись)]
@router.callback_query(F.data == 'Relationships')
async def Send_relationships_video_1(callback: CallbackQuery, bot: Bot):
    try:
        await callback.answer()
        
        id_file = 'AgACAgIAAxkBAAIP7mid0ogyuW9fA_CBHlcUW6wOG3TnAAIN9jEbVxDoSLaEAAEhsgJ3VgEAAwIAA3gAAzYE'
            
        async with ChatActionSender.upload_photo(
            chat_id=callback.message.chat.id,
            bot=bot
        ):
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=id_file,
                reply_markup=kb_main.rela_show_kb,
                caption='Тут про чувственность и честность с собой. ' 
                'Узнавать себя и свои точки взаимодействия с собой. ' 
                'Познание всего в себе, что выходит на взаимодействия. ' 
                'Что входит в контакт, те части, что узлучают приветствия ' 
                'или отторгают любое взаимодействие. '
                'Это не про делать и получить. '
                'Это про быть, являться и чувствовать. ')
            
    except Exception as e:
        logger.error(f"Ошибка в rela_show_kb: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

#Создание платежа 
@router.callback_query(F.data == 'pay_for_content_rela')
async def handle_pay_for_content_rela(callback: CallbackQuery, bot: Bot):
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or "NoUsername"
        base_amount = 500000  # 5000.00 RUB в копейках
        payload = "rela_one"
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
                WHERE up.user_id = ? AND up.chapter = 'rela'
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
            title=f'Курс "Отношения"{discount_message}',
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
    
@router.callback_query(F.data == 'rela')
async def send_file_from_db_rela(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    
    if not await check_payment(user_id):
        pay_button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Оплатить доступ", 
                callback_data="pay_for_content"
            )]
        ])
        await callback.message.answer(
            "❌ Доступ к видео закрыт. Необходима оплата 5000 руб.",
            reply_markup=pay_button
        )
        await callback.answer()
        return
    
    # Если оплата есть - продолжаем отправку
    file_path = get_user_payments(1)
    max_size_description = "Доступ вебинар Отношения"
    
    if not file_path or not os.path.exists(file_path):
        await callback.message.answer("Видео не найдено | 404 | Обратитесь к администратору")
        return
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size <= 50:
        async with ChatActionSender.upload_video(
            chat_id=callback.message.chat.id,  
            bot=bot
        ):
            file = FSInputFile(file_path)
            await callback.message.answer_video(file)  
    else:
        try:
            file_id = "BAACAgIAAxkBAAIDOWhiXoFoFPKZf-f8gfBo-1189e6-AAIQeQACgiwRS0EiLJVD7ITfNgQ"
            await bot.send_document(
                chat_id=callback.message.chat.id,  
                document=file_id,
                caption=max_size_description
            )
        except Exception as e:
            await callback.message.answer(f"Ошибка отправки: {e} | Обратитесь к администратору")  
    
    await callback.answer()  