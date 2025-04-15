from aiogram import F

from src.handlers.callback.router import router


@router.callback_query(F.data == "change_form")
async def start_change_form(): ...
