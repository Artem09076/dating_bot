from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from src.handlers.command.router import router
from aiogram.filters import Command
from src.templates.env import render

@router.message(Command('menu'))
async def menu(message: Message):
    main_menu =[
        [InlineKeyboardButton(text="Найти пару", callback_data='find_pair'), InlineKeyboardButton(text="Мои мэтчи", callback_data='my_matches')],
        [InlineKeyboardButton(text="Создать анкету", callback_data='make_form'), InlineKeyboardButton(text="Редактировать анкету", callback_data='change_form')],
        [InlineKeyboardButton(text="Рейтинг", callback_data='rating'), InlineKeyboardButton(text="Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=main_menu)
    await message.answer(render('menu.jinja2'), reply_markup=reply_markup)