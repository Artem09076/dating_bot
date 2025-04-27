import asyncio
import logging.config
from io import BytesIO

import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config.settings import settings
from src.logger import LOGGING_CONFIG, logger
from src.handlers.callback.router import router
from src.handlers.command.menu import menu
from src.handlers.state.match_flow import MatchFlow
from src.handlers.state.popular_user import PopularUser
from src.storage.minio import minio_client
from src.storage.rabbit import channel_pool
from src.templates.env import render
from src.metrics import SEND_MESSAGE, track_latency

@router.callback_query(F.data == "rating")
@track_latency('find_top_users')
async def find_top_users(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    logging.config.dictConfig(LOGGING_CONFIG)
    await call.message.answer("🔍 Поск топовых анкет...")

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        queue_name = settings.USER_QUEUE.format(user_id=call.from_user.id)
        user_queue = await channel.declare_queue(queue_name, durable=True)

        await user_queue.bind(exchange, routing_key=queue_name)

        request_body = {"action": "rating", "user_id": user_id}

        await exchange.publish(
            aio_pika.Message(msgpack.packb(request_body)), routing_key="user_messages"
        )
        SEND_MESSAGE.inc()
        retries = 3
        for _ in range(retries):
            try:
                res = await user_queue.get(timeout=3)
                await res.ack()
                data = msgpack.unpackb(res.body)
                top_users = data.get("top_users", [])

                if not top_users:
                    await call.message.answer("😕 Подходящих анкет не найдено.")
                    return

                await state.set_state(PopularUser.viewing)

                await state.set_data({"top_users": top_users, "current_index": 0})
                await show_next_top_user(call, state)
                return

            except asyncio.QueueEmpty:
                await asyncio.sleep(1)

        await call.message.answer("⚠️ Не удалось получить анкеты. Попробуйте позже.")


async def show_next_top_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    top_users = data.get("top_users", [])
    index = data.get("current_index", 0)

    if index >= len(top_users):
        await callback.message.answer(
            "🏁 Все анкеты топовых пользователей просмотрены!"
        )
        await menu(callback.message)
        await state.clear()
        return

    top_user = top_users[index]
    response = minio_client.get_object(
        settings.MINIO_BUCKET.format(
            user_id=top_user["id"]), top_user["photo"]
    )
    photo_data = BytesIO(response.read())
    response.close()
    response.release_conn()
    bufferd = BufferedInputFile(
        photo_data.read(), filename=top_user["photo"])

    top_user.pop("photo", None)

    caption = render("candidate_card.jinja2", **top_user)

    top_user_id = top_user["id"]

    user_id = callback.from_user.id




    if str(top_user_id) == str(user_id):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [   
                    InlineKeyboardButton(
                    text="Дальше", callback_data="next_top_user")
                ],
                [
                    InlineKeyboardButton(
                    text="❌ Закончить просмотр", callback_data="stop_search"
                    )
                ]
            ]
        )

    else: 
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="❤️ Лайк", callback_data="like_top_user")],
                [InlineKeyboardButton(
                    text="👎 Дизлайк", callback_data="dislike_top_user")],
                [
                    InlineKeyboardButton(
                        text="❌ Закончить просмотр", callback_data="stop_search"
                    )
                ],
            ]
        )


    await callback.message.answer_photo(
        photo=bufferd, caption=caption, reply_markup=keyboard
    )


@router.callback_query(F.data.in_(["like_top_user", "dislike_top_user"]), PopularUser.viewing)
@track_latency('handle_reaction_on_tops')
async def handle_reaction_on_tops(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    index = data.get("current_index", 0)
    top_users = data.get("top_users", [])

    top_user_id = top_users[index]["id"]

    user_id = callback.from_user.id



    if callback.data == "like_top_user":
        async with channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange(
                "user_form", ExchangeType.TOPIC, durable=True
            )

            if callback.data == "like_top_user":
                request_body = {
                    "action": "like_user",
                    "from_user_id": user_id,
                    "to_user_id": top_user_id,
                    "is_mutual": None,
                }
                await callback.message.answer(
                    "Вы поставили ❤️ этой анкете."
                )
                await notify_liked_popular_user(callback, top_user_id)

            await exchange.publish(
                aio_pika.Message(msgpack.packb(request_body)), routing_key="user_messages"
            )

    await state.update_data(current_index=index + 1)
    await show_next_top_user(callback, state)


async def notify_liked_popular_user(callback: CallbackQuery, target_user_id):

    caption = f"Ваша анкета кому-то понравилась!"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Посмотреть сейчас", callback_data="liked_me"
                ),
                InlineKeyboardButton(
                    text="Посмотрю позже", callback_data="stop_search"
                ),
            ]
        ]
    )

    await callback.message.bot.send_message(
        target_user_id,
        caption,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "stop_search",  PopularUser.viewing)
@track_latency('stop_search')
async def stop_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📋 Возвращаю на главное меню...")
    await menu(callback.message)
    await state.clear()


@router.callback_query(F.data == "next_top_user",  PopularUser.viewing)
@track_latency('next_top_user')
async def next_top_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("current_index", 0)
    await state.update_data(current_index=index + 1)
    await show_next_top_user(callback, state)
