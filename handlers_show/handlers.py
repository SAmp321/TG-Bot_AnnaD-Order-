from aiogram import F, Router, Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, FSInputFile, PreCheckoutQuery, LabeledPrice
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender
import asyncio
import logging
import aiosqlite
from yookassa import Configuration
from pathlib import Path
import keyboards.keyboards_admin as kb_admin
import keyboards.keyboards_main as kb_main
import keyboards.keyboards_shop as kb_shop
from bot.dao.database import db_Ibaza as db

Configuration.account_id = '7729207630'
Configuration.secret_key = 'ваш_secret_key'

dp = Dispatcher()
from handlers_show.__init__ import router, logger

PROVIDER_TOKEN = '381764678:TEST:129002'
CURRENCY = 'RUB'

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('👽', reply_markup=kb_main.main_kb)


@router.message(F.text == 'Купленные вебинары')
async def NaMe(message: Message):
    await message.answer('Выберите выбинар', reply_markup=kb_main.Purchased_webinars)

@router.message(F.text == 'Купить вебинар (запись)')
async def buy_webinare_show(message: Message):
    await message.answer('Выберите категорию', reply_markup=kb_main.webinar_kb)

@router.message(F.text == 'Помощь')
async def help(message: Message):
    await message.answer('При возникновении сложностей или ошибок пишите https://t.me/herqqa')

@router.message(F.text == 'Прямая трансляция')
async def open_stream(message: Message):
    await message.answer('Выберите действие', reply_markup=kb_admin.get_payment_kb)

@router.message(Command("test_delete"))
async def test_delete(message: Message, bot: Bot):
    test_msg = await message.answer("Тестовое сообщение")
    await asyncio.sleep(10)
    try:
        await bot.delete_message(message.chat.id, test_msg.message_id)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def delete_message_after_delay(bot: Bot, chat_id: int, message_id: int, delay: int):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения {message_id}: {e}")

@router.message(F.content_type.in_({'photo', 'video', 'document', 'audio'}))
async def handle_media(message: Message):
    if message.photo:
        file_id = message.photo[-1].file_id  # Берем самое высокое качество
        media_type = "Фото"
    elif message.video:
        file_id = message.video.file_id
        media_type = "Видео"
    elif message.document:
        file_id = message.document.file_id
        media_type = "Документ"
    elif message.audio:
        file_id = message.audio.file_id
        media_type = 'Аудио'
    
    await message.answer(
        f"{media_type} ID:\n<code>{file_id}</code>\n\n"
        "Используйте этот ID в вашем коде",
        parse_mode="HTML"
    )