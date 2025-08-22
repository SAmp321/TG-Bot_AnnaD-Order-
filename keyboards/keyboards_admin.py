from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

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
        [KeyboardButton(text='/stats_for_sell')],
        [KeyboardButton(text='/start_stream')],
        [KeyboardButton(text='Создать промокод')],
        [KeyboardButton(text='/Exit')]
    ],
    resize_keyboard=True
)

# Клавиатура после успешной оплаты
def get_success_kb(invite_link: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔗 Перейти в чат', url=invite_link)],
            [InlineKeyboardButton(text='📌 Сохранить ссылку', callback_data='save_link')]
        ]
    )

get_payment_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='💳 Оплатить доступ', callback_data='pay_stream')],
            [InlineKeyboardButton(text='ℹ️ Подробнее о стриме', callback_data='stream_info')]
        ]
    )

new_promokode = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Хочу говорить', callback_data='Want_talk_promokode')],
        [InlineKeyboardButton(text='Сексуальность', callback_data='Sex_promokode')],
        [InlineKeyboardButton(text='Отношения', callback_data='Relationships_promokode')],
        [InlineKeyboardButton(text='Тело', callback_data='Body_promokode')]
])