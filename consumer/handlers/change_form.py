import msgpack
from sqlalchemy import update
from src.storage.db import async_session
from src.model.model import User
from src.storage.rabbit import channel_pool

async def change_form():
    async with channel_pool.acquire() as channel:
        queue = await channel.declare_queue("user_messages", durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = msgpack.unpackb(message.body, raw=False)
                        action = data.get("action")

                        if action == "update_form":
                            await process_update_form(data)

                    except Exception as e:
                        print(f"Ошибка обработки сообщения: {e}")

async def process_update_form(data: dict):
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
