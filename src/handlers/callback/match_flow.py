import asyncio
import logging.config
from io import BytesIO

import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (BufferedInputFile, CallbackQuery,
                           InlineKeyboardButton, InlineKeyboardMarkup)

from config.settings import settings
from src.handlers.callback.router import router
from src.handlers.command.menu import menu
from src.handlers.state.match_flow import MatchFlow
from src.logger import LOGGING_CONFIG, logger
from src.metrics import SEND_MESSAGE, track_latency
from src.storage.minio import minio_client
from src.storage.rabbit import channel_pool
from src.templates.env import render


@router.callback_query(F.data == "find_pair")
@track_latency("find_pair_handler")
async def find_pair_handler(call: CallbackQuery, state: FSMContext):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info(f"ПОИСК АНКЕТ НАЧАЛСЯ {call.from_user.id}")
    await call.message.answer("🔍 Ищу подходящие анкеты...")

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        queue_name = settings.USER_QUEUE.format(user_id=call.from_user.id)
        user_queue = await channel.declare_queue(queue_name, durable=True)

        await user_queue.bind(exchange, routing_key=queue_name)

        request_body = {"user_id": call.from_user.id, "action": "find_pair"}

        logger.info("ЗАПРОС ПОШЕЛ В USER_MESSAGES")

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
                candidates = data.get("candidates", [])
                logger.info(f"ПРИНЯЛИ КАНДИДАТОВ : {data}")
                if not candidates:
                    await call.message.answer("😕 Подходящих анкет не найдено.")
                    return

                await state.set_state(MatchFlow.viewing)
                await state.set_data({"candidates": candidates, "current_index": 0})
                await show_next_candidate(call, state)
                return

            except asyncio.QueueEmpty:
                logger.info("ОЧЕРЕДЬ ПУСТАЯ!!!!!!")
                await asyncio.sleep(1)

        await call.message.answer("⚠️ Не удалось получить анкеты. Попробуйте позже.")


async def show_next_candidate(call: CallbackQuery, state: FSMContext):
    logger.info("ПОКАЗ КАНДИДАТОВ")
    data = await state.get_data()
    index = data.get("current_index", 0)
    candidates = data.get("candidates", [])

    if index >= len(candidates):
        await call.message.answer("✅ Больше анкет нет.")
        await menu(call.message)
        await state.clear()
        return

    candidate = candidates[index]

    response = minio_client.get_object(
        settings.MINIO_BUCKET.format(user_id=candidate["id"]), candidate["photo"]
    )
    photo_data = BytesIO(response.read())
    response.close()
    response.release_conn()
    bufferd = BufferedInputFile(photo_data.read(), filename=candidate["photo"])

    candidate.pop("photo", None)

    caption = render("candidate_card.jinja2", **candidate)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❤️ Лайк", callback_data="like")],
            [InlineKeyboardButton(text="👎 Дизлайк", callback_data="dislike")],
            [
                InlineKeyboardButton(
                    text="❌ Закончить просмотр", callback_data="stop_search"
                )
            ],
        ]
    )

    logger.info("АНКЕТА СФОРМИРОВАНА И ОТПРАВЛЯЕТСЯ")

    await call.message.answer_photo(
        photo=bufferd, caption=caption, reply_markup=keyboard
    )


@router.callback_query(F.data.in_(["like", "dislike"]), MatchFlow.viewing)
@track_latency("handle_reaction")
async def handle_reaction(callback: CallbackQuery, state: FSMContext):
    logger.info("СТРЕМ ИЛИ НОРМ")

    data = await state.get_data()
    index = data.get("current_index", 0)
    candidates = data.get("candidates", [])

    if index >= len(candidates):
        await callback.message.answer("✅ Больше анкет нет.")
        await menu(callback.message)
        await state.clear()
        return

    if callback.data == "like":
        liked_user_id = candidates[index]["id"]
        logger.info("ПОСТАВИЛИ ЛАЙК")
        user_id = callback.from_user.id

        async with channel_pool.acquire() as channel:
            exchange = await channel.declare_exchange(
                "user_form", ExchangeType.TOPIC, durable=True
            )

            request_body = {
                "action": "like_user",
                "from_user_id": user_id,
                "to_user_id": liked_user_id,
                "is_mutual": None,
            }

            logger.info("ОТПРАВКА ЛАЙКА В ОЧЕРЕДЬ")
            await callback.message.answer("Вы поставили ❤️ этой анкете")

            await exchange.publish(
                aio_pika.Message(msgpack.packb(request_body)),
                routing_key="user_messages",
            )
            SEND_MESSAGE.inc()

        await notify_liked_user_match_flow(callback, liked_user_id)

    await state.update_data(current_index=index + 1)
    logger.info("СЛЕДУЮЩИЙ!!!!!!!")
    await show_next_candidate(callback, state)


async def notify_liked_user_match_flow(callback: CallbackQuery, target_user_id):
    logger.info("МЫ В УВЕДОМЛЕНИИ О ЛАЙКЕ")

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
        target_user_id, caption, reply_markup=keyboard
    )
    logger.info(f"УВЕДОМЛЕНИЕ ОТПРАВЛЕНО ПОЛЬЗОВАТЕЛЮ {target_user_id}")


@router.callback_query(F.data == "stop_search")
@track_latency("stop_search")
async def stop_search(callback: CallbackQuery, state: FSMContext):
    logger.info("ВСЁ, ХОРОШ. НА ГЛАВНУЮ")
    await callback.message.answer("📋 Возвращаю на главное меню...")
    await menu(callback.message)
    await state.clear()
    return
