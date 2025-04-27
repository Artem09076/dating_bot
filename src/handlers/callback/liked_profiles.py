import asyncio
import logging.config
from io import BytesIO

import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config.settings import settings
from consumer.logger import LOGGING_CONFIG, logger
from src.handlers.callback.router import router
from src.handlers.command.menu import menu
from src.handlers.state.like_profile import LikedProfilesFlow
from src.storage.minio import minio_client
from src.storage.rabbit import channel_pool
from src.templates.env import render


@router.callback_query(lambda c: c.data == "liked_me")
async def liked_me_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        queue_name = settings.USER_QUEUE.format(user_id=callback.from_user.id)
        user_queue = await channel.declare_queue(queue_name, durable=True)

        await user_queue.bind(exchange, routing_key=queue_name)

        request_body = {"action": "check_likes", "user_id": user_id}

        await exchange.publish(
            aio_pika.Message(msgpack.packb(request_body)), routing_key="user_messages"
        )

        await callback.message.answer("⏳ Проверяю, кто поставил вам лайк...")

        retries = 3
        for _ in range(retries):
            try:
                res = await user_queue.get(timeout=3)
                await res.ack()
                data = msgpack.unpackb(res.body)
                who_liked = data.get("likes", [])
                logger.info("ПРИНЯЛИ ЛАЙКНУВШИХ")
                if not who_liked:
                    await callback.message.answer(
                        "Пока ваша анкета никому не понравилась"
                    )
                    return

                await state.set_state(LikedProfilesFlow.viewing)
                await state.set_data({"likes": who_liked, "current_index": 0})
                await show_next_liked_user(callback, state)
                return

            except asyncio.QueueEmpty:
                logger.info("ОЧЕРЕДЬ ПУСТАЯ!!!!!!")
                await asyncio.sleep(1)

        await callback.message.answer("⚠️ Не удалось получить анкеты. Попробуйте позже.")


async def show_next_liked_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    likes = data.get("likes", [])
    index = data.get("current_index", 0)

    if index >= len(likes):
        await callback.message.answer(
            "🏁 Все анкеты, кому вы понравились, просмотрены!"
        )
        await menu(callback.message)
        await state.clear()
        return

    liked_user = likes[index]
    response = minio_client.get_object(
        settings.MINIO_BUCKET.format(user_id=liked_user["id"]), liked_user["photo"]
    )
    photo_data = BytesIO(response.read())
    response.close()
    response.release_conn()
    bufferd = BufferedInputFile(photo_data.read(), filename=liked_user["photo"])

    liked_user.pop("photo", None)

    caption = render("candidate_card.jinja2", **liked_user)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❤️ Лайк", callback_data="like_on_like")],
            [InlineKeyboardButton(text="👎 Дизлайк", callback_data="dislike_on_like")],
            [
                InlineKeyboardButton(
                    text="❌ Закончить просмотр", callback_data="stop_search"
                )
            ],
        ]
    )

    logger.info("АНКЕТА СФОРМИРОВАНА И ОТПРАВЛЯЕТСЯ")

    await callback.message.answer_photo(
        photo=bufferd, caption=caption, reply_markup=keyboard
    )


@router.callback_query(
    F.data.in_(["like_on_like", "dislike_on_like"]), LikedProfilesFlow.viewing
)
async def handle_reaction(callback: CallbackQuery, state: FSMContext):
    logger.info("СТРЕМ ИЛИ НОРМ")

    data = await state.get_data()
    index = data.get("current_index", 0)
    likes = data.get("likes", [])

    liked_user_id = likes[index]["id"]

    user_id = callback.from_user.id

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        if callback.data == "like_on_like":
            logger.info("ПОСТАВИЛИ ЛАЙК НА ЛАЙК")
            request_body = {
                "action": "like_user",
                "from_user_id": user_id,
                "to_user_id": liked_user_id,
                "is_mutual": True,
            }
            await callback.message.answer(
                "Вы взаимно поставили ❤️ этой анкете. Понравившийся пользователь появится в мэтчах"
            )

        elif callback.data == "dislike_on_like":
            logger.info("ПОСТАВИЛИ ДИЗЛАЙК НА ЛАЙК")
            request_body = {
                "action": "like_user",
                "from_user_id": user_id,
                "to_user_id": liked_user_id,
                "is_mutual": False,
            }

        logger.info("ОТПРАВКА МЭТЧЕЙ И НЕ МЕТЧЕЙ В ОЧЕРЕДЬ")
        await exchange.publish(
            aio_pika.Message(msgpack.packb(request_body)), routing_key="user_messages"
        )

    await state.update_data(current_index=index + 1)
    logger.info("СЛЕДУЮЩИЙ!!!!!!!")
    await show_next_liked_user(callback, state)


@router.callback_query(F.data == "stop_search", LikedProfilesFlow.viewing)
async def stop_search(callback: CallbackQuery, state: FSMContext):
    logger.info("ВСЁ, ХОРОШ. НА ГЛАВНУЮ (из liked_profiles)")
    await callback.message.answer("📋 Возвращаю на главное меню...")
    await menu(callback.message)
    await state.clear()
