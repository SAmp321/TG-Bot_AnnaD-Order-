
from handlers_show.__init__ import router, logger
from aiogram import F, types, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import keyboards.keyboards_main as kb_main
import keyboards.keyboards_admin as kb_admin
import aiosqlite as aiosq
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
import aiosqlite
import asyncio
import logging
from pathlib import Path
from bot.dao.database import get_all_users
from aiogram.types import ReplyKeyboardRemove

db_Ibaza = Path('data/info_baza.db')

#Проверка на админа
async def is_admin(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(db_Ibaza) as conn:
            cursor = await conn.execute("SELECT 1 FROM admin WHERE user_id = ?", (user_id,))
            admin = await cursor.fetchone()
            return bool(admin)
    except Exception as e:
        logger.error(f"Ошибка проверки админа: {e}")
        return False

# Получаем имя из бд админов
async def get_admin_info_name(user_id: int):
    try:
        async with aiosqlite.connect(db_Ibaza) as conn:
            cursor = await conn.execute(
                "SELECT username FROM admin WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Ошибка получения имени админа: {e}")
        return None

# Админ панель вход
@router.message(F.text == 'Администраторская')
async def admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен", show_alert=True)
    admin_username = await get_admin_info_name(message.from_user.id)
    
    if admin_username:
        await message.answer(f"👑 Здравствуйте, {admin_username}!", reply_markup=kb_admin.main_admin_kb)
    else:
        await message.answer("🔐 У вас нет прав доступа к админ-панели")

async def info_stats_sell(user_id: int):
    """Безопасное получение статистики продаж"""
    async with aiosq.connect(db_Ibaza) as conn:
        try:
            # Общее количество продаж
            cursor = await conn.execute(
                'SELECT COUNT(*) FROM payments WHERE user_id = ?', 
                (user_id,)
            )
            total_sales = (await cursor.fetchone())[0] or 0  # Если NULL → 0

            cursor = await conn.execute(
                'SELECT SUM(amount) FROM payments WHERE user_id = ?',
                (user_id,)
            )
            sum_result = await cursor.fetchone()
            total_amount = (sum_result[0] / 100) if sum_result and sum_result[0] is not None else 0

            # Последняя продажа
            cursor = await conn.execute(
                'SELECT payload FROM payments WHERE user_id = ? ORDER BY rowid DESC LIMIT 1',
                (user_id,)
            )
            last_payload_result = await cursor.fetchone()
            last_payload = last_payload_result[0] if last_payload_result else "нет данных"

            return {
                'total_sales': total_sales,
                'total_amount': total_amount,
                'last_payload': last_payload
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return None

#Статистика продаж
@router.message(F.text == 'Статистика продаж [beta]')
async def stats_for_sell(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен", show_alert=True)
    stats = await info_stats_sell(message.from_user.id)
    
    if not stats:
        await message.answer("❌ Данные о продажах не найдены")
        return
    
    response = (
        "📊 Статистика продаж:\n"
        f"• Всего продаж: {stats['total_sales']}\n"
        f"• Общая сумма: {stats['total_amount']} руб.\n"
        f"• Последний товар: {stats['last_payload']}"
    )
    
    await message.answer(response)

# Выйти из админ панели
@router.message(F.text == 'Выйти')
async def Exit_for_admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен", show_alert=True)
    await message.answer('Выход из админ панели', reply_markup=kb_main.main_kb)

#Группа для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_content = State()

# Универсальная рассылка
@router.message(F.text == 'Массовая рассылка')
async def broadcast_start(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен", show_alert=True)
    
    await message.answer(
        "📤 Отправьте контент для рассылки:\n"
        "• Текст\n• Фото/видео/GIF с подписью\n• Документ с подписью\n\n"
        "Подпись будет использована как текст сообщения",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(BroadcastStates.waiting_for_content)

# Обработка контента для рассылки
@router.message(BroadcastStates.waiting_for_content)
async def broadcast_content_received(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return await message.answer("Доступ запрещен", show_alert=True)
    
    users = get_all_users()
    success_count = 0
    fail_count = 0
    
    status_msg = await message.answer("🔄 Начинаю рассылку...")
    
    for user_id in users:
        try:
            # Отправляем в зависимости от типа контента
            if message.photo:
                # Фото
                photo_file_id = message.photo[-1].file_id
                caption = message.caption or ""
                await bot.send_photo(user_id, photo_file_id, caption=caption)
                
            elif message.video:
                # Видео
                video_file_id = message.video.file_id
                caption = message.caption or ""
                await bot.send_video(user_id, video_file_id, caption=caption)
                
            elif message.animation:
                # GIF (анимация)
                animation_file_id = message.animation.file_id
                caption = message.caption or ""
                await bot.send_animation(user_id, animation_file_id, caption=caption)
                
            elif message.document:
                # Документ
                document_file_id = message.document.file_id
                caption = message.caption or ""
                await bot.send_document(user_id, document_file_id, caption=caption)
                
            elif message.text:
                # Простой текст
                await bot.send_message(user_id, message.text)
                
            else:
                # Неподдерживаемый тип
                continue
                
            success_count += 1
            await asyncio.sleep(0.15)  # Anti-flood
            
        except Exception as e:
            fail_count += 1
            logging.error(f"Error sending to {user_id}: {e}")
    
    # Формируем отчет
    content_type = "текст"
    if message.photo:
        content_type = "фото"
    elif message.video:
        content_type = "видео"
    elif message.animation:
        content_type = "GIF"
    elif message.document:
        content_type = "документ"
    
    await status_msg.edit_text(
        f"📊 Рассылка {content_type} завершена!\n"
        f"✅ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}\n"
        f"👥 Всего пользователей: {len(users)}"
    )
    await state.clear()

# Обработка отмены рассылки
@router.message(F.text == "❌ Отменить рассылку")
async def cancel_broadcast(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == BroadcastStates.waiting_for_content:
        await state.clear()
        await message.answer(
            "❌ Рассылка отменена",
            reply_markup=ReplyKeyboardRemove()
        )