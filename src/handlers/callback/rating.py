import msgpack
from aiogram import Router
from aio_pika import ExchangeType
from src.storage.rabbit import channel_pool
from src.handlers.callback.router import router
from config.settings import settings
import aio_pika
import asyncio
from aiogram import F
from aiogram.types import CallbackQuery
from src.logger import logger, LOGGING_CONFIG
import logging.config


@router.callback_query(F.data == "rating")
async def watch_rating(call: CallbackQuery):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info(
        f"Начало обработки запроса для пользователя {call.from_user.id}")

    user_id = call.from_user.id

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )
        user_queue = await channel.declare_queue("user_messages", durable=True)
        await user_queue.bind(exchange, 'user_messages')
        queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id), durable=True
        )
        await queue.bind(exchange, settings.USER_QUEUE.format(user_id=user_id))

        logger.info(f'Запрос на расчет рейтинга для пользователя {user_id}')


        body = {
            "id": user_id,
            "action": "watch_rating",
        }
        await exchange.publish(
            aio_pika.Message(msgpack.packb(body)),
            routing_key="user_messages",
        )

        await call.message.answer("Высчитываю ваш рейтинг...")

        retries = 3
        for _ in range(retries):
            try:
                incoming_message = await asyncio.wait_for(queue.get(), timeout=10.0)

                response_body = msgpack.unpackb(
                    incoming_message.body, raw=False)

                logger.info(
                    f"Получен ответ для пользователя {user_id}: {response_body}")

                text = f"Ваш рейтинг:\n\n"

                primary = response_body.get("primary_rating", {})
                behavior = response_body.get("behavior_rating", {})
                combined = response_body.get("combined_rating")

                if primary:
                    text += (
                        f"Основной рейтинг:\n"
                        f"Заполненность профиля: {primary.get('completeness_score', 0):.2f}\n"
                        f"Фото: {primary.get('photo_score', 0):.2f}\n"
                        f"Совпадение по предпочтениям: {primary.get('preference_match_score', 0):.2f}\n\n"
                    )

                if behavior:
                    text += (
                        f"Поведенческий рейтинг:\n"
                        f"- Получено лайков: {behavior.get('likes_received', 0)}\n"
                        f"- Доля взаимных лайков: {behavior.get('likes_skipped_ratio', 0):.2f}\n"
                        f"- Взаимных лайков: {behavior.get('mutual_likes', 0)}\n"
                        f"- Бесед после лайка: {behavior.get('post_match_conversations', 0)}\n\n"
                    )

                if combined is not None:
                    text += f"Итоговый рейтинг: {combined:.2f}\n"

                await call.message.answer(text)
                await incoming_message.ack()
                return

            except asyncio.TimeoutError:
                logger.warning(
                    f"Не удалось получить рейтинг вовремя для пользователя {user_id}")
                await call.message.answer("Не удалось получить ваш рейтинг вовремя. Попробуйте позже.")
                return


            except asyncio.QueueEmpty:
                logger.warning(f"Очередь пуста для пользователя {user_id}")
                await call.message.answer("Не удалось получить ваш рейтинг. Попробуйте позже.")
                return

            except Exception as e:
                logger.error(
                    f"Ошибка при обработке рейтинга для пользователя {user_id}: {str(e)}")
                await call.message.answer("Произошла ошибка при получении вашего рейтинга. Попробуйте позже.")
                return

        await call.message.answer("Не удалось получить ваш рейтинг. Попробуйте позже.")
