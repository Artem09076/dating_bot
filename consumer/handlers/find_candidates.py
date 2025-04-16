from sqlalchemy import select, and_
from consumer.storage.db import async_session
from src.model.model import GenderEnum, User
from config.settings import settings
import msgpack
from aio_pika import ExchangeType, Message
from src.storage.rabbit import channel_pool
import logging.config
from consumer.logger import LOGGING_CONFIG, logger
from sqlalchemy import or_


async def find_candidates(body):
    user_id = body.get("user_id")

    async with async_session() as db:
        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("ПРИЁМ ЗАПРОСА В БАЗУ ДАННЫХ FIND PAIR", body)

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        
        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("ПРИНЯЛИ ЮЗЕРА ИЗ БД, ЩАС ФИЛЬТРЫ")

        filters = and_(
            or_(
                User.gender == user.preferred_gender,
                User.gender == GenderEnum.other  
            ),
            User.age >= user.preferred_age_min,
            User.age <= user.preferred_age_max,
            User.preferred_city == user.preferred_city,
            User.id != user.id
        )

        candidates_result = await db.execute(select(User).where(filters).limit(10))
        candidates = candidates_result.scalars().all()

        candidates_data = [c.to_dict() for c in candidates]

        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("КАНДИДАТЫ СФОРМИРОВАНЫ")


    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )        
        
        user_queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id),
            durable=True
        )

        await user_queue.bind(
            exchange,
            settings.USER_QUEUE.format(user_id=user_id),
        )

        response_body = {
            "action": "show_candidates",
            "user_id": user_id,
            "candidates": candidates_data
        }

        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("ОТПРАВКА КАНДИДАТОВ В ОЧЕРЕДЬ")

        await exchange.publish(
            Message(msgpack.packb(response_body)),
            routing_key=settings.USER_QUEUE.format(user_id=user_id)
        )


# async def like_user(body):
#     user_id = body.get("user_id")
#     logging.config.dictConfig(LOGGING_CONFIG)
#     logger.info("ПРИЁМ ЗАПРОСА В БАЗУ ДАННЫХ LIKE USER", body)
#     async with async_session() as db:
#         like = Like(
#             from_user_id=user_id,
#             to_user_id=liked_user_id,
#             created_at=datetime.utcnow()
#         )
#         session.add(like)
#         await session.commit()
