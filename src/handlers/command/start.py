from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.handlers.command.router import router
from src.templates.env import render


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    main_menu = [
        [InlineKeyboardButton(text="Найти пару", callback_data="find_pair")],
        [InlineKeyboardButton(text="Мои мэтчи", callback_data="my_matches")],
        [InlineKeyboardButton(text="Создать анкету", callback_data="make_form")],
        [
            InlineKeyboardButton(
                text="Редактировать анкету", callback_data="change_form"
            )
        ],
        [InlineKeyboardButton(text="Рейтинг", callback_data="rating")],
        [InlineKeyboardButton(text="💖 Кто лайкнул меня", callback_data="liked_me")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=main_menu)
    await message.answer(
        render("start.jinja2", user=message.from_user), reply_markup=reply_markup
    )
