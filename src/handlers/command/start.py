from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.handlers.command.router import router
from src.templates.env import render


@router.message(Command('start'))
async def start(message: Message, state: FSMContext) -> None:
    await message.answer(render('start.jinja2', user=message.from_user))
