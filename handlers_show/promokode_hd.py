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
from bot.dao.database import init_promokode
from handlers_show.__init__ import logger, router


DB_PATH = Path('data/streams.db')
DB_PROMOKODE = Path('data/promokode.db')


class NewPromokode(StatesGroup):
    percent = State()
    start_promokode = State()
    end_promokode = State()
    max_enteger = State()
    tag_promo = State()
    emoynt_enteger = State()

@router.message(F.text == 'new_promokode')
async def new_promokode_create(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен")
    
    await message.answer(
        'Создание промокода состоит из:\n'
        '1. Процент скидки (1-98%)\n'
        '2. Дата начала действия (ГГГГ-ММ-ДД)\n'
        '3. Дата окончания (ГГГГ-ММ-ДД)\n'
        '4. Максимальное количество использований\n'
        '5. TAG промокода (начинается с *)',
        reply_markup=kb_admin.new_promokode
    )

@router.callback_query(F.data == 'Want_talk_promokode')
async def want_create_promokode(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Доступ запрещен", show_alert=True)
    await state.set_state(NewPromokode.percent)
    await callback.message.answer("Укажите процент скидки (1-98) (без %) [более 99, 100 процентов не вводить]:")
    await callback.answer()

@router.message(NewPromokode.percent)
async def process_percent(message: Message, state: FSMContext):
    try:
        percent = int(message.text)
        if not 1 <= percent <= 100:
            raise ValueError
        await state.update_data(percent=percent)
        await state.set_state(NewPromokode.start_promokode)
        await message.answer("Введите дату начала действия (ГГГГ-ММ-ДД):")
    except ValueError:
        await message.answer("Некорректный процент! Введите число от 1 до 100")

@router.message(NewPromokode.start_promokode)
async def process_start_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(start_promokode=message.text)
        await state.set_state(NewPromokode.end_promokode)
        await message.answer("Введите дату окончания (ГГГГ-ММ-ДД):")
    except ValueError:
        await message.answer("Неверный формат даты! Используйте ГГГГ-ММ-ДД")

@router.message(NewPromokode.end_promokode)
async def process_end_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(end_promokode=message.text)
        await state.set_state(NewPromokode.max_enteger)
        await message.answer("Введите максимальное количество использований:")
    except ValueError:
        await message.answer("Неверный формат даты! Используйте ГГГГ-ММ-ДД")

@router.message(NewPromokode.max_enteger)
async def process_max_uses(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text)
        if max_uses <= 0:
            raise ValueError
        await state.update_data(max_enteger=max_uses)
        await state.set_state(NewPromokode.tag_promo)
        await message.answer("Введите TAG вашего промокода (начинается с *):")
    except ValueError:
        await message.answer("Введите целое положительное число!")

@router.message(NewPromokode.tag_promo)
async def process_tag_promo(message: Message, state: FSMContext):
    if not message.text.startswith('*'):
        await message.answer("TAG должен начинаться с *, например: *ХОЧУДЕШЕВЛЕ")
        return
    
    data = await state.get_data()
    chapter = 'want_talk'
    
    async with aiosqlite.connect(DB_PROMOKODE) as db:
        await db.execute(
            """INSERT INTO promokode_create 
            (percent, start_promokode, end_promokode, max_enteger, emoynt_enteger, tag, chapter) 
            VALUES (?, ?, ?, ?, 0, ?, ?)""",  # Устанавливаем emoynt_enteger = 0
            (
                data['percent'],
                data['start_promokode'],
                data['end_promokode'],
                data['max_enteger'],
                message.text,  # TAG промокода
                chapter
            )
        )
        await db.commit()
    
    await message.answer(
        "✅ Промокод успешно создан!\n\n"
        f"Процент: {data['percent']}%\n"
        f"Действует с: {data['start_promokode']} по {data['end_promokode']}\n"
        f"Макс. использований: {data['max_enteger']}\n"
        f"Ваш промокод: {message.text} для Хочу говорить"
    )
    await state.clear()

@router.message(F.text == 'ввести промокод')
async def use_promokode(message: Message):
    try:
        await message.answer('Введите пожалуйста ваш промокод:')
        
        @router.message()
        async def process_promocode(input_msg: Message):
            try:
                user_promocode = input_msg.text.strip().upper()
                user_id = input_msg.from_user.id
                current_date = datetime.now().date()
                
                async with aiosqlite.connect(DB_PROMOKODE) as db:
                    db.row_factory = aiosqlite.Row
                    
                    cursor = await db.execute(
                        "SELECT * FROM promokode_create WHERE tag = ?", 
                        (user_promocode,)
                    )
                    promocode = await cursor.fetchone()
                    
                    if not promocode:
                        await input_msg.answer('❌ Промокод не найден')
                        return
                    
                    try:
                        start_date = datetime.strptime(promocode['start_promokode'], "%Y-%m-%d").date()
                        end_date = datetime.strptime(promocode['end_promokode'], "%Y-%m-%d").date()
                        
                        if current_date < start_date:
                            await input_msg.answer(f'⏳ Промокод будет активен с {start_date.strftime("%d.%m.%Y")}')
                            return
                        
                        if current_date > end_date:
                            await input_msg.answer('⌛ Срок действия промокода истёк')
                            return
                    except ValueError as e:
                        logger.error(f"Ошибка формата даты: {e}")
                        await input_msg.answer('⚠️ Ошибка в данных промокода')
                        return
                    
                    cursor = await db.execute(
                        "SELECT COUNT(*) as count FROM promocode_usages WHERE promocode_tag = ?",
                        (promocode['tag'],)
                    )
                    uses_count = (await cursor.fetchone())['count']
                    
                    if uses_count >= int(promocode['max_enteger']):
                        await input_msg.answer('🚫 Лимит использований промокода исчерпан')
                        return
                    
                    cursor = await db.execute(
                        "SELECT COUNT(*) as count FROM use_promokode_users WHERE user_id = ? AND tag = ?",
                        (user_id, promocode['tag'])
                    )
                    already_used = (await cursor.fetchone())['count']
                    
                    if already_used:
                        await input_msg.answer('⚠️ Вы уже использовали этот промокод ранее')
                        return
                    
                    await db.execute(
                        "INSERT INTO promocode_usages (user_id, promocode_tag, use_date) VALUES (?, ?, ?)",
                        (user_id, promocode['tag'], current_date.isoformat())
                    )
                    
                    await db.execute(
                        "INSERT INTO use_promokode_users (user_id, percent, tag, chapter) VALUES (?, ?, ?, ?)",
                        (user_id, promocode['percent'], promocode['tag'], promocode['chapter'])
                    )
                    
                    await db.execute(
                        """UPDATE promokode_create 
                        SET emoynt_enteger = emoynt_enteger + 1 
                        WHERE tag = ?""",
                        (promocode['tag'],)
                    )

                    await db.commit()
                    
                    await input_msg.answer(
                        f'✅ Промокод "{promocode["tag"]}" применён!\n\n'
                        f'• Скидка: {promocode["percent"]}%\n'
                        f'• Категория: {promocode["chapter"]}'
                    )
            except Exception as e:
                logger.error(f"Ошибка обработки промокода: {e}", exc_info=True)
                await input_msg.answer('⚠️ Ошибка обработки промокода')
    
    except Exception as e:
        logger.error(f"Ошибка в use_promokode: {e}", exc_info=True)
        await message.answer('⚠️ Произошла ошибка. Попробуйте позже.')