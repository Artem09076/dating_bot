from consumer.storage.db import async_session
from src.model.model import Like
import logging.config
from consumer.logger import LOGGING_CONFIG, logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, update


async def process_like_user(body: dict):
    from_user_id = body["from_user_id"]
    to_user_id = int(body["to_user_id"])
    is_mutual = body['is_mutual']

    async with async_session() as db:
        logging.config.dictConfig(LOGGING_CONFIG)
        logger.info("ОБРАБОТКА ЛАЙКА", body)
        try:
            query = select(Like).where(
                Like.from_user_id == to_user_id,
                Like.to_user_id == from_user_id
            )
            result = await db.execute(query)
            existing_like = result.scalar_one_or_none()

            if existing_like:
                logger.info("НАЙДЕН СУЩЕСТВУЮЩИЙ ЛАЙК, ОБНОВЛЯЕМ", body)
                existing_like.is_mutual = is_mutual
            else:
                logger.info("СОЗДАЕМ НОВЫЙ ЛАЙК", body)
                like = Like(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    is_mutual=is_mutual
                )
                db.add(like)

            await db.commit()
            logger.info("ИЗМЕНЕНИЯ СОХРАНЕНЫ", body)
        except SQLAlchemyError as err:
            logger.error(err)
