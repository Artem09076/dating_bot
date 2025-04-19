import msgpack
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from io import BytesIO
from src.handlers.state.like_profile import LikedProfilesFlow
from src.handlers.command.menu import menu
from src.templates.env import render
from src.storage.minio import minio_client
from config.settings import settings
from aiogram.fsm.context import FSMContext

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
        buttons.append([InlineKeyboardButton(text="✉️ Перейти к беседе", callback_data=f"open_conversation_{conversation_id}")])
    buttons += [
        [InlineKeyboardButton(text="❤️ Лайк", callback_data="like_on_like")],
        [InlineKeyboardButton(text="👎 Дизлайк", callback_data="dislike_on_like")],
        [InlineKeyboardButton(text="❌ Закончить просмотр", callback_data="stop_search")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer_photo(caption=caption, reply_markup=keyboard)
    await state.update_data(current_index=index + 1)
