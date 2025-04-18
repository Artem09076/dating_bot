from sqlalchemy import select
from consumer.storage.db import async_session
from src.model.model import User, Like
from config.settings import settings
import logging.config
from consumer.logger import LOGGING_CONFIG, logger
import msgpack
from aio_pika import ExchangeType, Message
from src.storage.rabbit import channel_pool


async def process_check_likes(body: dict):
    user_id = body["user_id"]

    async with async_session() as db:  
        stmt = select(Like.from_user_id).where(
            Like.to_user_id == user_id,
            Like.is_mutual.is_(None)
        )

        result = await db.execute(stmt)
        from_user_ids = result.scalars().all()

        if not from_user_ids:
            response = {
                "user_id": user_id,
                "likes": []
            }
        else:
            stmt = select(User).where(User.id.in_(from_user_ids))
            result = await db.execute(stmt)
            users = result.scalars().all()

            users_data = []
            for user in users:
                users_data.append({
                    "id": user.id,
                    "name": user.name,
                    "age": user.age,
                    "gender": user.gender.value,
                    "city": user.city,
                    "interests": user.interests,
                    "photo": user.photo
                })

            response = {
                "user_id": user_id,
                "likes": users_data
            }

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

        logger.info("ОТПРАВКА ЛАЙКНУВШИХ В ОЧЕРЕДЬ")

        await exchange.publish(
            Message(msgpack.packb(response)),
            routing_key=settings.USER_QUEUE.format(user_id=user_id)
        )
