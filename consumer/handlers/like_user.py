import logging.config

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from consumer.logger import LOGGING_CONFIG, logger
from consumer.storage.db import async_session
from src.model.model import Like


async def process_like_user(body: dict):
    from_user_id = body["from_user_id"]
    to_user_id = int(body["to_user_id"])
    is_mutual = body["is_mutual"]

    async with async_session() as db:
        logging.config.dictConfig(LOGGING_CONFIG)
        try:
            query = select(Like).where(
                Like.from_user_id == to_user_id, Like.to_user_id == from_user_id
            )
            result = await db.execute(query)
            existing_like = result.scalar_one_or_none()

            if existing_like:
                if existing_like.is_mutual == None and is_mutual == None:
                    existing_like.is_mutual = True
                else:
                    existing_like.is_mutual = is_mutual
            else:
                like = Like(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    is_mutual=is_mutual,
                )
                db.add(like)

            await db.commit()
        except SQLAlchemyError as err:
            logger.error(err)
