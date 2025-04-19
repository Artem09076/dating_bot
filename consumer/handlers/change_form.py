import msgpack
from sqlalchemy import update
from src.storage.db import async_session
from src.model.model import User
from src.storage.rabbit import channel_pool

async def change_form(data: dict):
    user_id = data.get("id")
    if not user_id:
        print("Нет ID пользователя в сообщении")
        return

    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                name=data.get("name"),
                age=data.get("age"),
                gender=data.get("gender"),
                city=data.get("city"),
                interests=",".join(data.get("interests", [])) if isinstance(data.get("interests"), list) else data.get("interests"),
                preferred_gender=data.get("preferred_gender"),
                preferred_age_min=data.get("preferred_age_min"),
                preferred_age_max=data.get("preferred_age_max"),
                preferred_city=data.get("preferred_city"),
                photo=data.get("photo"),
            )
        )
        await session.commit()

    print(f"✅ Анкета пользователя {user_id} успешно обновлена.")
