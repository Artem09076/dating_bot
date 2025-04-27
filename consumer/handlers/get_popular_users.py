import logging
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from consumer.storage.db import async_session
from src.model.model import User, CombinedRating
from consumer.logger import LOGGING_CONFIG, logger
from src.storage.rabbit import channel_pool
import msgpack
from aio_pika import ExchangeType, Message
from sqlalchemy import select
from config.settings import settings



async def get_top_popular_users(body):
    user_id = body["user_id"]
    candidates_data = []
    try:
        async with async_session() as db:
            logging.config.dictConfig(LOGGING_CONFIG)
            logger.info(
                "ПРИЁМ ЗАПРОСА НА ПОЛУЧЕНИЕ ТОПА ПОПУЛЯРНЫХ ПОЛЬЗОВАТЕЛЕЙ", body)

            result = await db.execute(
                select(User)
                .options(selectinload(User.combined_rating))
                .join(CombinedRating, CombinedRating.user_id == User.id)
                .order_by(desc(CombinedRating.score))
                .limit(10)
            )
            users = result.scalars().all()

            if not users:
                logger.info("Не найдено популярных пользователей.")
                return []

            candidates_data = [user.to_dict() for user in users]

            logger.info(f"ТОП-ПОЛЬЗОВАТЕЛИ СФОРМИРОВАНЫ: {candidates_data}")

            response = {"user_id": user_id, "top_users": candidates_data}

    except Exception as err:
        logger.error(
            f"Ошибка при получении топа популярных пользователей: {err}")
        return []
    
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        user_queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id), durable=True
        )

        await user_queue.bind(
            exchange,
            settings.USER_QUEUE.format(user_id=user_id),
        )

        logger.info("ОТПРАВКА ТОПОВ В ОЧЕРЕДЬ")

        await exchange.publish(
            Message(msgpack.packb(response)),
            routing_key=settings.USER_QUEUE.format(user_id=user_id),
        )
