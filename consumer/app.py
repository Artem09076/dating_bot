import logging.config

import msgpack

from consumer.handlers.event_distribution import handle_event_distribution
from consumer.storage import rabbit


async def main() -> None:
    queue_name = 'user_messages'
    async with rabbit.channel_pool.acquire() as channel:
        await channel.set_qos(
            prefetch_count=10,
        )

        queue = await channel.declare_queue(queue_name, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    body = msgpack.unpackb(message.body)
                    await handle_event_distribution(body)
