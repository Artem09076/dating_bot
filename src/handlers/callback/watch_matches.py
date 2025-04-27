import asyncio
import logging.config

import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from src.handlers.callback.router import router
from src.handlers.command.menu import menu
from src.handlers.state.like_profile import LikedProfilesFlow
from src.handlers.state.show_next_user import show_next_liked_user
from src.logger import LOGGING_CONFIG, logger
from aiogram.filters import StateFilter

from src.storage.rabbit import channel_pool
from src.metrics import track_latency, SEND_MESSAGE


@router.callback_query(F.data == "my_matches")
@track_latency('my_matches_handler')
async def my_matches_handler(call: CallbackQuery, state: FSMContext):
    logging.config.dictConfig(LOGGING_CONFIG)
    user_id = call.from_user.id

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        user_queue = await channel.declare_queue("user_messages", durable=True)

        await user_queue.bind(exchange, "user_messages")
        queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id), durable=True
        )
        await queue.bind(exchange, settings.USER_QUEUE.format(user_id=user_id))
        body = {
            "id": call.from_user.id,
            "action": "get_my_matches",
        }


        await exchange.publish(
            aio_pika.Message(msgpack.packb(body)), routing_key="user_messages"
        )
        SEND_MESSAGE.inc()

        await call.message.answer("Проверяю ваши мэтчи...")

        retries = 3
        for _ in range(retries):
            try:
                res = await queue.get()
                await res.ack()
                data = msgpack.unpackb(res.body)

                matches = data.get("matches", [])

                if matches:
                    await state.set_state(LikedProfilesFlow.viewing)
                    await state.set_data({"likes": matches, "current_index": 0})
                    await show_next_liked_user(call, state)
                    return
                else:
                    await call.message.answer("У вас нет взаимных лайков.")
                    return
            except asyncio.QueueEmpty:
                await asyncio.sleep(1)

        await call.message.answer("Не удалось получить ваши мэтчи. Попробуйте позже.")


@router.callback_query(F.data.startswith("open_conversation_"))
@track_latency('open_conversation_handler')
async def open_conversation_handler(callback: CallbackQuery, state: FSMContext):
    conversation_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    index = data.get("current_index", 1) - 1
    likes = data.get("likes", [])

    if 0 <= index < len(likes):
        user = likes[index]
        if callback.from_user.username:
            await callback.message.answer(
                f"Открываем беседу №{conversation_id}.\n"
                f"👉 [Перейти в Telegram](tg://user?id={user.get('id')})",
                parse_mode="Markdown",
            )
        else:
            await callback.message.answer(
                f"Открываем беседу №{conversation_id}, но у пользователя нет username 😕"
            )
    else:
        await callback.message.answer("Не удалось определить пользователя.")

    await callback.answer()

@router.callback_query(StateFilter(LikedProfilesFlow.viewing), F.data == "next_liked_user")
@track_latency('next_liked_user_handler')
async def next_liked_user_handler(callback: CallbackQuery, state: FSMContext):
    await show_next_liked_user(callback, state)