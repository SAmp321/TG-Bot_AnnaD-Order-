from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from aiogram import types
from handlers_show.__init__ import router, logger

# Основная клавиатура для пользователей
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🎥 Стрим')],
        [KeyboardButton(text='📚 Материалы'), KeyboardButton(text='💬 Поддержка')]
    ],
    resize_keyboard=True
)


# Админская клавиатура
main_admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Статистика продаж [beta]')],
        [KeyboardButton(text='Создать прямую трансляцию'), KeyboardButton(text='Массовая рассылка')],
        [KeyboardButton(text='Создать промокод')],
        [KeyboardButton(text='Выйти')]
    ],
    resize_keyboard=True
)


get_payment_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='💳 Оплатить доступ', callback_data='pay_stream')],
            [InlineKeyboardButton(text='ℹ️ Подробнее о стриме', callback_data='stream_info')]
        ]
    )

clear_completion = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Прервать заполнение', callback_data='Exit_create_stream')]
])

new_promokode = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Хочу говорить', callback_data='Want_talk_promokode')],
        [InlineKeyboardButton(text='Сексуальность', callback_data='Sex_promokode')],
        [InlineKeyboardButton(text='Отношения', callback_data='Relationships_promokode')],
        [InlineKeyboardButton(text='Тело', callback_data='Body_promokode')],
        [InlineKeyboardButton(text='Торт блаженство', callback_data='pie_bliss')]
])