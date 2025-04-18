from typing import Dict, Any
from sqlalchemy import delete
from consumer.storage.db import async_session
from src.model.model import User
from consumer.logger import logger, LOGGING_CONFIG
import logging.config
async def delete_profile(body: Dict[str, Any]):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("Прием запроса", body)
    async with async_session() as db:
        user_id = body.get('id')
        res = await db.execute(delete(User).where(User.id==user_id))
        logger.info(res)
        await db.commit()