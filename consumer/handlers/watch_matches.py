from sqlalchemy import select, and_
from consumer.storage.db import async_session
from src.model.model import Like, User, Conversation
from aio_pika import ExchangeType
from sqlalchemy.exc import SQLAlchemyError
import aio_pika
import msgpack
from config.settings import settings
from consumer.storage import rabbit
import logging.config
from consumer.logger import logger, LOGGING_CONFIG
async def get_my_matches(body: dict):
    logging.config.dictConfig(LOGGING_CONFIG)
    user_id = body["id"]
    response_matches = []

    logger.info("ЗАПРОС В БАЗУ НА МЕТЧИ")

    async with async_session() as db:
        try:
            subquery = (
                select(Like.from_user_id)
                .where(
                    and_(
                        Like.to_user_id == user_id,
                        Like.is_mutual == True
                    )
                )
            )

            query = (
                select(User.id, User.name, User.age)
                .where(User.id.in_(subquery))
            )

            result = await db.execute(query)
            matches = result.mappings().all()

            for match in matches:
                conv_query = select(Conversation).where(
                    ((Conversation.user1_id == user_id) & (Conversation.user2_id == match.id)) |
                    ((Conversation.user1_id == match.id) & (Conversation.user2_id == user_id))
                )
                conv_result = await db.execute(conv_query)
                conversation = conv_result.scalar_one_or_none()

                if not conversation:
                    conversation = Conversation(user1_id=user_id, user2_id=match.id)
                    db.add(conversation)
                    

                response_matches.append({
                    "id": match.id,
                    "name": match.name,
                    "age": match.age,
                    "conversation_id": conversation.id
                })
            await db.commit()
        except Exception as e:
            logger.info(e)
            response_matches = []

    logger.info("ОТПРАВКА МЕТЧЕЙ В ОЧЕРЕДЬ")
    
    async with rabbit.channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )
        await exchange.publish(
            aio_pika.Message(
                body=msgpack.packb({"matches": response_matches}),
            ),
            routing_key=settings.USER_QUEUE.format(user_id=user_id),
        )
