import asyncio
import logging.config
from io import BytesIO

import aio_pika
import msgpack
from aio_pika import ExchangeType
from aio_pika.exceptions import QueueEmpty
from aiogram.filters import Command
from aiogram.types import (BufferedInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from config.settings import settings
from src.handlers.command.router import router
from src.logger import LOGGING_CONFIG, logger
from src.storage.minio import minio_client
from src.storage.rabbit import channel_pool
from src.templates.env import render


@router.message(Command("my_profile"))
async def get_profile(message: Message) -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
    user_id = message.from_user.id
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        user_queue = await channel.declare_queue("user_messages", durable=True)
        queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id), durable=True
        )

        await user_queue.bind(exchange, "user_messages")
        await queue.bind(exchange, settings.USER_QUEUE.format(user_id=user_id))
        body = {"id": user_id, "action": "get_profile"}
        await exchange.publish(aio_pika.Message(msgpack.packb(body)), "user_messages")

        for _ in range(3):
            try:
                res = await queue.get()
                await res.ack()

                profile = msgpack.unpackb(res.body)

                buttons = [
                    [
                        InlineKeyboardButton(
                            text="Изменить профиль", callback_data="change_form"
                        )
                    ]
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

                response = minio_client.get_object(
                    settings.MINIO_BUCKET.format(user_id=user_id), profile["photo"]
                )
                photo_data = BytesIO(response.read())
                response.close()
                response.release_conn()
                bufferd = BufferedInputFile(
                    photo_data.read(), filename=profile["photo"]
                )

                await message.answer_photo(
                    photo=bufferd,
                    caption=render("profile.jinja2", user_data=profile),
                    reply_markup=keyboard,
                )
                return
            except QueueEmpty:
                await asyncio.sleep(1)
