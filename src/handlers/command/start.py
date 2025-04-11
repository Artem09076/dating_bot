from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.handlers.command.router import router
from src.templates.env import render
from src.handlers.command.main_menu import main_menu


@router.message(Command('start'))
async def start(message: Message, state: FSMContext) -> None:
    await message.answer(render('start.jinja2', user=message.from_user), reply_markup=main_menu)
