from io import BytesIO

import msgpack
from aiogram.fsm.context import FSMContext
from aiogram.types import (BufferedInputFile, CallbackQuery,
                           InlineKeyboardButton, InlineKeyboardMarkup)

from config.settings import settings
from src.handlers.command.menu import menu
from src.handlers.state.like_profile import LikedProfilesFlow
from src.storage.minio import minio_client
from src.templates.env import render


async def show_next_liked_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    likes = data.get("likes", [])
    index = data.get("current_index", 0)

    if index >= len(likes):
        await callback.message.answer("Все анкеты просмотрены!")
        await menu(callback.message)
        await state.clear()
        return

    liked_user = likes[index]
    conversation_id = liked_user.pop("conversation_id", None)
    username = liked_user.get("username")

    response = minio_client.get_object(
        settings.MINIO_BUCKET.format(user_id=liked_user["id"]),
        liked_user["photo"]
    )
    photo_data = BytesIO(response.read())
    response.close()
    response.release_conn()
    bufferd = BufferedInputFile(photo_data.read(), filename=liked_user["photo"])
    liked_user.pop("photo", None)

    caption = render("candidate_card.jinja2", **liked_user)

    buttons = [
            [InlineKeyboardButton(text="✉️ Перейти к беседе", url=f'tg://user?id={liked_user.get('id')}')]
    ]

    if index + 1 < len(likes):
        buttons.append([
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data="next_liked_user"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer_photo(photo=bufferd, caption=caption, reply_markup=keyboard)
    await state.update_data(current_index=index + 1)
