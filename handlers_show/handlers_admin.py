
from handlers_show.__init__ import router, logger
from aiogram import F, types
from aiogram.types import Message
from aiogram.filters import CommandStart, Command, CommandObject
import keyboards.keyboards_main as kb_main
import keyboards.keyboards_admin as kb_admin
from bot.dao.database import db_Ibaza
import aiosqlite as aiosq
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

# Проверка на админа
async def is_admin(user_id: int) -> bool:
    admin = await db_Ibaza.fetch_one("SELECT 1 FROM admin WHERE user_id = ?", (user_id,))
    return bool(admin)

# Получаем имя из бд админов
async def get_admin_info_name(user_id: int):
    async with aiosq.connect(db_Ibaza) as conn:
        cursor = await conn.execute(
            "SELECT username FROM admin WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

# Админ панель
@router.message(F.text == 'Администраторская')
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
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

@router.message(Command('stats_for_sell'))
async def stats_for_sell(message: Message):
    if not is_admin(message.from_user.id):
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

@router.message(Command('Exit'))
async def Exit_for_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Доступ запрещен", show_alert=True)
    await message.answer('Выход из админ панели', reply_markup=kb_main.main_kb)



