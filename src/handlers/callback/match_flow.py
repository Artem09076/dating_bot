import asyncio
import aio_pika
import msgpack
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aio_pika import ExchangeType
from src.storage.rabbit import channel_pool
from config.settings import settings
from src.handlers.callback.router import router
from aiogram.fsm.context import FSMContext
from src.handlers.command.menu import menu
from consumer.logger import LOGGING_CONFIG, logger
import logging.config
from src.templates.env import render
from src.storage.minio import minio_client


@router.callback_query(F.data == "find_pair")
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

        request_body = {
            "user_id": call.from_user.id,
            "action": "find_pair"
        }

        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("ЗАПРОС ПОШЕЛ В USER_MEASSAGES")

        await exchange.publish(
            aio_pika.Message(msgpack.packb(request_body)),
            routing_key="user_messages"
        )


        retries = 3
        for _ in range(retries):
            try:
                res = await user_queue.get(timeout=3)
                await res.ack()
                data = msgpack.unpackb(res.body)
                candidates = data.get("candidates", [])
                logging.config.dictConfig(LOGGING_CONFIG)
                logger.info("ПРИНЯЛИ КАНДИДАТОВ")
                if not candidates:
                    await call.message.answer("😕 Подходящих анкет не найдено.")
                    return

                await state.set_data({"candidates": candidates, "current_index": 0})
                await show_next_candidate(call, state)
                return

            except asyncio.QueueEmpty:
                logging.config.dictConfig(LOGGING_CONFIG)
                logger.info("ОЧЕРЕДЬ ПУСТАЯ!!!!!!")
                await asyncio.sleep(1)

        await call.message.answer("⚠️ Не удалось получить анкеты. Попробуйте позже.")


async def show_next_candidate(call: CallbackQuery, state: FSMContext):
    logging.config.dictConfig(LOGGING_CONFIG)
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

    # TODO: ФОТКУ ИЗ МИНЬОНА ВЫСОСАТЬ

    # bucket_name = settings.MINIO_BUCKET.format(user_id=candidate['id'])
    # file_name = candidate["photo"].split("/", 1)[1]
    # url = minio_client.presigned_get_object(bucket_name, file_name)
    candidate.pop("photo", None)

    caption = render("candidate_card.jinja2", **candidate)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Лайк", callback_data="like")],
        [InlineKeyboardButton(text="👎 Дизлайк", callback_data="dislike")],
        [InlineKeyboardButton(text="❌ Закончить", callback_data="stop_search")]
    ])

    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("АНКЕТА СФОРМИРОВАНА И ОТПРАВЛЯЕТСЯ")

    await call.message.answer(render("candidate_card.jinja2", **candidate), reply_markup=keyboard)


    # await call.message.answer_photo(url, caption=caption, reply_markup=keyboard)


@router.callback_query(F.data.in_(["like", "dislike"]))
async def handle_reaction(callback: CallbackQuery, state: FSMContext):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("СТРЕМ ИЛИ НОРМ")

    data = await state.get_data()
    index = data.get("current_index", 0)
    candidates = data.get("candidates", [])

    if index >= len(candidates):
        await callback.message.answer("📭 Анкеты закончились.")
        return

    if callback.data == "like":
        liked_user_id = candidates[index]["id"]
        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("ПОСТАВИЛИ ЛАЙК")
        # user_id = callback.from_user.id

        # async with channel_pool.acquire() as channel:
        #     exchange = await channel.declare_exchange(
        #         "user_form", ExchangeType.TOPIC, durable=True
        #     )

        #     queue_name = settings.USER_QUEUE.format(user_id=user_id)
        #     user_queue = await channel.declare_queue(queue_name, durable=True)

        #     await user_queue.bind(exchange, routing_key=queue_name)

        #     request_body = {
        #         "user_id": user_id,
        #         "action": "like_user",
        #         "from_user_id": user_id,
        #         "to_user_id": liked_user_id
        #     }

        #     logging.config.dictConfig(LOGGING_CONFIG)
        #     logger.info("ПЕРЕД ПАБЛИШ123 В USER_MEASSAGES")

        #     await exchange.publish(
        #         aio_pika.Message(msgpack.packb(request_body)),
        #         routing_key="user_messages"
        #     )

        await notify_liked_user(liked_user_id, callback.from_user.id)

    await state.update_data(current_index=index + 1)
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("СЛЕДУЮЩИЙ!!!!!!!")
    await show_next_candidate(callback, state)


@router.callback_query(F.data == "stop_search")
async def stop_search(callback: CallbackQuery, state: FSMContext):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("ВСЁ, ХОРОШ. НА ГЛАВНУЮ")
    await callback.message.answer("📋 Возвращаю на главное меню...")
    await menu(callback.message)
    await state.clear()
    return
    

async def notify_liked_user(target_user_id, who_liked_id):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("МЫ В УВЕДОМЛЕНИИ О ЛАЙКЕ")
