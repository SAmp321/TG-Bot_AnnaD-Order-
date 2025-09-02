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
import asyncio
from handlers_show.__init__ import router, logger
from data.reg import Video_id_rela, Audio_id_rela, TXT_caption_rela, Photo_all
from bot.dao.database import db_Ibaza

DB_PROMOKODE = Path('data/promokode.db')
#Чек Отношения -- [Купить вебинар (Запись)]
@router.callback_query(F.data == 'Relationships')
async def Send_relationships_video_1(callback: CallbackQuery, bot: Bot):
    error_messages = []
    try:
        await callback.answer()
        #Берем id Фото
        id_photo = Photo_all.get('Photo_rela_prevu')
        if not id_photo:
            error_messages.append('Фото не смогло загрузиться. Пожалуйста обратитесь в поддержку')
        #Проверка на существования id фото
        if error_messages:
            error_text = "\n".join(error_messages) + "\n\nПожалуйста, напишите в поддержку"
            await callback.message.answer(error_text)
            await callback.answer()  # Завершаем callback
            return
        
        async with ChatActionSender.upload_photo(
            chat_id=callback.message.chat.id,
            bot=bot
        ):
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=id_photo,
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
        payload = "rela_one_one"
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

#Отправка после платежки файл или текст
@router.message(F.successful_payment.invoice_payload == "rela_one_one")
async def process_successful_payment(message: Message, bot: Bot):
    try:
        user_id = message.from_user.id
        error_messages = []

        id_video = Video_id_rela.get('Prevu_rela')
        if not id_video:
            error_messages.append("❌ Видео не найдено в базе")

            if error_messages:
                error_text = "\n".join(error_messages)
                await message.answer(error_text)
                return
        # 1. Обновляем промокод
        async with aiosqlite.connect(DB_PROMOKODE) as db:
            db.row_factory = aiosqlite.Row
            
            # Находим промокод для обновления
            cursor = await db.execute(
                """SELECT tag FROM use_promokode_users 
                WHERE user_id = ? AND chapter = 'rela_one_one'
                LIMIT 1""",
                (user_id,)
            )
            promo = await cursor.fetchone()
            
            if promo:
                await db.execute(
                    """UPDATE use_promokode_users 
                    SET chapter = 'rela_one_one_use' 
                    WHERE user_id = ? AND tag = ?""",
                    (user_id, promo['tag'])
                )
                await db.commit()

        # 2. Отправляем контент
        await bot.send_video(
            chat_id=user_id,
            video=id_video,
            caption="✅ Доступ к вебинару открыт!",
            protect_content=True
        )

        # 3. Обновляем основную БД
        await grant_content_access(
            user_id=user_id,
            content_id="rela_one_one",
            days=30
        )
        await message.answer('Перейти к вебенару?', reply_markup=kb_main.parts_rela)

    except Exception as e:
        print(f"Ошибка обработки платежа: {e}")
        await message.answer("⚠️ Произошла ошибка. Обратитесь в поддержку.")

#---- Видео вебинары ----

#Купленные вебинары - Отношения
@router.callback_query(F.data == 'purchased_relationships')
async def purchased_Sexuality_show(callback: CallbackQuery):
    await callback.message.answer('Выберите часть:', reply_markup=kb_main.parts_rela)
    await callback.answer()

#1
@router.callback_query(F.data == "purchades_rela_one")
async def purchades_rela_one(callback: CallbackQuery, bot: Bot):

    sent_content = 0
    user_id = callback.from_user.id
    specific_content_id = "rela_one_one"
    error_messages = []
    try:
        #Проверка доступа
        async with aiosqlite.connect(db_Ibaza) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute( 
            '''SELECT content_id, protect_content 
            FROM content_access WHERE user_id = ? 
            AND content_id = ?
            and (datetime('now') < expires_at OR NULL)''', 
            (user_id, specific_content_id)) as cursor:
                content_access = await cursor.fetchone()  
                
            if not content_access:
                await callback.answer("❌ У вас нет доступа к этому материалу", show_alert=True)
                return
    
        #Наход ID и проверка на существование файлов
        id_video = Video_id_rela.get('rela_video_one')
        if not id_video:
            error_messages.append("❌ Видео не найдено в базе")
        
        id_audio = Audio_id_rela.get('rela_audio_one')
        if not id_audio:
            error_messages.append("❌ Аудио не найдено в базе")
        
        text_caption_video = TXT_caption_rela.get('text_caption_video_Rela_one')
        if not text_caption_video:
            error_messages.append("❌ Текст описания для видео не найден")
        
        text_caption_audio = TXT_caption_rela.get('text_caption_audio_Rela_one')
        if not text_caption_audio:
            error_messages.append("❌ Текст описания для аудио не найден")

        if error_messages:
            error_text = "\n".join(error_messages) + "\n\nПожалуйста, напишите в поддержку"
            await callback.message.answer(error_text)
            await callback.answer()  # Завершаем callback
            return
        
        

        
        # Отправляем видео
        video_message = await bot.send_video(
            chat_id=user_id,
            video=id_video,
            caption=text_caption_video,
            protect_content=True 
        )

        sent_content += 1
    

        # Отправляем аудио с кнопкой
        audio_message = await bot.send_audio(
            chat_id=user_id,
            audio=id_audio,
            caption=text_caption_audio,
            protect_content=True,
        )
        sent_content += 1

        #Удаляем сообщения через 12 часов
        if video_message:
            await asyncio.sleep(10)
            await bot.delete_message(
                chat_id=user_id,
                message_id=video_message.message_id
            )
            
        if audio_message:
            await bot.delete_message(
                chat_id=user_id,
                message_id=audio_message.message_id
            )

    except Exception as e:
        logger.error(f"Ошибка удаления: {e}")
        await callback.answer("⚠️ Не удалось удалить сообщение", show_alert=True)
#2
@router.callback_query(F.data == "purchades_rela_two")
async def purchades_rela_two(callback: CallbackQuery, bot: Bot):

    sent_content = 0
    user_id = callback.from_user.id
    specific_content_id = "rela_one_one"
    error_messages = []
    try:
        #Проверка доступа
        async with aiosqlite.connect(db_Ibaza) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute( 
            '''SELECT content_id, protect_content 
            FROM content_access WHERE user_id = ? 
            AND content_id = ?
            and (datetime('now') < expires_at OR NULL)''', 
            (user_id, specific_content_id)) as cursor:
                content_access = await cursor.fetchone()  
                
            if not content_access:
                await callback.answer("❌ У вас нет доступа к этому материалу", show_alert=True)
                return
        #Наход ID и проверка на существование файлов
        id_video = Video_id_rela.get('rela_video_two')
        if not id_video:
            error_messages.append("❌ Видео не найдено в базе")
        
        id_audio = Audio_id_rela.get('rela_audio_two')
        if not id_audio:
            error_messages.append("❌ Аудио не найдено в базе")
        
        text_caption_video = TXT_caption_rela.get('text_caption_video_Rela_two')
        if not text_caption_video:
            error_messages.append("❌ Текст описания для видео не найден")
        
        text_caption_audio = TXT_caption_rela.get('text_caption_audio_Rela_two')
        if not text_caption_audio:
            error_messages.append("❌ Текст описания для аудио не найден")

        if error_messages:
            error_text = "\n".join(error_messages) + "\n\nПожалуйста, напишите в поддержку"
            await callback.message.answer(error_text)
            await callback.answer()  # Завершаем callback
            return
            
        # Отправляем видео
        video_message = await bot.send_video(
            chat_id=user_id,
            video=id_video,
            caption=text_caption_video,
            protect_content=True 
        )

        sent_content += 1
        

        # Отправляем аудио с кнопкой
        audio_message = await bot.send_audio(
            chat_id=user_id,
            audio=id_audio,
            caption=text_caption_audio,
            protect_content=True,
        )
        sent_content += 1

        #Удаляем сообщения через 12 часов
        if video_message:
            await asyncio.sleep(10)
            await bot.delete_message(
                chat_id=user_id,
                message_id=video_message.message_id
            )
            
        if audio_message:
            await bot.delete_message(
                chat_id=user_id,
                message_id=audio_message.message_id
            )

    except Exception as e:
        logger.error(f"Ошибка удаления: {e}")
        await callback.answer("⚠️ Не удалось удалить сообщение", show_alert=True)
#3
@router.callback_query(F.data == "purchades_rela_three")
async def purchades_rela_three(callback: CallbackQuery, bot: Bot):

    sent_content = 0
    user_id = callback.from_user.id
    specific_content_id = "rela_one_one"
    error_messages = []
    try:
        #Проверка доступа
        async with aiosqlite.connect(db_Ibaza) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute( 
            '''SELECT content_id, protect_content 
            FROM content_access WHERE user_id = ? 
            AND content_id = ?
            and (datetime('now') < expires_at OR NULL)''', 
            (user_id, specific_content_id)) as cursor:
                content_access = await cursor.fetchone()  
                
            if not content_access:
                await callback.answer("❌ У вас нет доступа к этому материалу", show_alert=True)
                return
        #Наход ID и проверка на существование файлов
        id_video = Video_id_rela.get('rela_video_three')
        if not id_video:
            error_messages.append("❌ Видео не найдено в базе")
        
        id_audio = Audio_id_rela.get('rela_audio_three')
        if not id_audio:
            error_messages.append("❌ Аудио не найдено в базе")
        
        text_caption_video = TXT_caption_rela.get('text_caption_video_Rela_three')
        if not text_caption_video:
            error_messages.append("❌ Текст описания для видео не найден")
        
        text_caption_audio = TXT_caption_rela.get('text_caption_audio_Rela_three')
        if not text_caption_audio:
            error_messages.append("❌ Текст описания для аудио не найден")

        if error_messages:
            error_text = "\n".join(error_messages) + "\n\nПожалуйста, напишите в поддержку"
            await callback.message.answer(error_text)
            await callback.answer()  # Завершаем callback
            return
            
        # Отправляем видео
        video_message = await bot.send_video(
            chat_id=user_id,
            video=id_video,
            caption=text_caption_video,
            protect_content=True 
        )

        sent_content += 1
        

        # Отправляем аудио с кнопкой
        audio_message = await bot.send_audio(
            chat_id=user_id,
            audio=id_audio,
            caption=text_caption_audio,
            protect_content=True,
        )
        sent_content += 1

        #Удаляем сообщения через 12 часов
        if video_message:
            await asyncio.sleep(10)
            await bot.delete_message(
                chat_id=user_id,
                message_id=video_message.message_id
            )
            
        if audio_message:
            await bot.delete_message(
                chat_id=user_id,
                message_id=audio_message.message_id
            )

    except Exception as e:
        logger.error(f"Ошибка удаления: {e}")
        await callback.answer("⚠️ Не удалось удалить сообщение", show_alert=True)


#Быстрый переход к вебинару отношения
@router.callback_query(F.data == "webinare_rela")
async def webinare_rela_transition(callback: CallbackQuery):
    await callback.message.answer('Выберите часть:', reply_markup=kb_main.my_web_rela)
