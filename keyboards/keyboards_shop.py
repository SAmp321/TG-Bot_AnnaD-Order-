from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='')],
    [KeyboardButton(text='')]
])

inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='')],
    [InlineKeyboardButton(text='')]
])