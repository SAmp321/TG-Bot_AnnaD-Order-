from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
#-----------------------------------------------------------------------------------------------------------------------------#
                                    #ГЛАВНОЕ МЕНЮ

#Главные кнопки
main_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='ТОРТ БЛАЖЕНСТВО')],
        [KeyboardButton(text='Купить вебинар (запись)'), KeyboardButton(text='ввести промокод')],
        [KeyboardButton(text='Прямая трансляция'), KeyboardButton(text='Купленные вебинары', callback_data ='my_video')],
        [KeyboardButton(text='Администраторская', callback_data='/admin'), KeyboardButton(text='Помощь')],
],      resize_keyboard=True,       input_field_placeholder="Выберите действие")

#-----------------------------------------------------------------------------------------------------------------------------#

                                    #ОТДЕЛ КУПЛЕННЫХ ВЕБИНАРОВ
#Купленные вебинары
Purchased_webinars = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Хочу говорить', callback_data='purchased_want_talk')],
    [InlineKeyboardButton(text='Сексуальность', callback_data='purchased_Sexuality')],
    [InlineKeyboardButton(text='Отношения', callback_data='purchased_relationships')],
    [InlineKeyboardButton(text='Тело', callback_data='purchased_body')]
])

#Список видео хочу говорить
parts_want_talk = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='1-я часть ХОЧУ ГОВОРИТЬ', callback_data='purchades_want_talk_video_one')],
    [InlineKeyboardButton(text='2-я часть ХОЧУ ГОВОРИТЬ', callback_data='purchades_want_talk_video_two')],
    [InlineKeyboardButton(text='3-я часть ХОЧУ ГОВОРИТЬ', callback_data='purchades_want_talk_video_three')]
])
#Список видео Сексуальность
parts_sex = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='1-я часть Сексуальность', callback_data='purchades_sex_one')],
    [InlineKeyboardButton(text='2-я часть Сексуальность', callback_data='purchades_sex_two')],
    [InlineKeyboardButton(text='3-я часть Сексуальность', callback_data='purchades_sex_three')]
])
#Список видео Отношения
parts_rela = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='1-я часть Отношения', callback_data='purchades_rela_one')],
    [InlineKeyboardButton(text='2-я часть Отношения', callback_data='purchades_rela_two')],
    [InlineKeyboardButton(text='3-я часть Отношения', callback_data='purchades_rela_three')]
])
#Список видео Тело
parts_body = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='1-я часть Тело', callback_data='purchades_body_one')],
    [InlineKeyboardButton(text='2-я часть Тело', callback_data='purchades_body_two')],
    [InlineKeyboardButton(text='3-я часть Тело', callback_data='purchades_body_three')]
])

#-----------------------------------------------------------------------------------------------------------------------------#
                        #КУПИТЬ ВЕБИНАР (запись)#

#Список вебинаров
webinar_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Хочу говорить', callback_data='Want_talk')],
        [InlineKeyboardButton(text='Сексуальность', callback_data='Sexuality')],
        [InlineKeyboardButton(text='Отношения', callback_data='Relationships')],
        [InlineKeyboardButton(text='Тело', callback_data='Body')]
    ]
)
#Купить курс ХОЧУ ГОВОРИТЬ
want_talk_show_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='КУПИТЬ КУРС 5000₽', callback_data='pay_for_content')]]
)
#Купить курс СЕКСУАЛЬНОСТЬ
sex_show_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='КУПИТЬ КУРС 5000₽', callback_data='pay_for_content_sexu')]]
)
#Купить курс ОТНОШЕНИЯ
rela_show_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='КУПИТЬ КУРС 5000₽', callback_data='pay_for_content_rela')]]
)
#Купить курс ТЕЛО
body_show_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='КУПИТЬ КУРС 5000₽', callback_data='pay_for_content_body')]]
)
#КУПИТЬ ТОРТ БЛАЖЕНСТВО
pie_bliss_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='КУПИТЬ ТОРТ 888₽', callback_data='pay_for_pie_bliss')]]
)

#Быстрый переход на "купленные вебинары" после покупки
my_web_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='перейти к вебинарам', callback_data='go_to_the_webinar')]
    ]
)

#Переход к вебинар ХОЧУ говорить
my_web_want_talk = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='перейти к вебинару', callback_data='webinare_want_talk')]
    ]
)
#переход к вебинару СЕКСУАЛЬСНОТЬ
my_web_sex = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='перейти к вебинару', callback_data='webinare_sex')]
    ]
)
#переход к вебинару тело
my_web_body = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='перейти к вебинару', callback_data='webinare_body')]
    ]
)
#переход к вебинару отношения
my_web_rela = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='перейти к вебинару', callback_data='webinare_rela')]
    ]
)

#-----------------------------------------------------------------------------------------------------------------------------#
