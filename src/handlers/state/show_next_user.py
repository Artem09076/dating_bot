from io import BytesIO

import msgpack
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

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

    caption = render("candidate_card.jinja2", **liked_user)
    buttons = []
    if conversation_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✉️ Перейти к беседе",
                    callback_data=f"open_conversation_{conversation_id}",
                )
            ]
        )
    buttons += [
        [InlineKeyboardButton(text="❤️ Лайк", callback_data="like_on_like")],
        [InlineKeyboardButton(text="👎 Дизлайк", callback_data="dislike_on_like")],
        [
            InlineKeyboardButton(
                text="❌ Закончить просмотр", callback_data="stop_search"
            )
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer_photo(caption=caption, reply_markup=keyboard)
    await state.update_data(current_index=index + 1)
