import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from config.settings import settings
from src.api.router import router
from src.bot import bot, dp


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    polling_task: asyncio.Task[None] | None = None
    wh_info = await bot.get_webhook_info()
    if settings.BOT_WEBHOOK_URL and wh_info != settings.BOT_WEBHOOK_URL:
        await bot.set_webhook(settings.BOT_WEBHOOK_URL)
    else:
        polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))

    yield

    if polling_task is not None:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            print("Stop polling")

    await bot.delete_webhook()


def create_app() -> FastAPI:
    app = FastAPI(docs_url="/swagger", lifespan=lifespan)
    app.include_router(router)
    return app


if __name__ == "__main__":
    uvicorn.run(
        "src.app:create_app", factory=True, host="0.0.0.0", port=8001, workers=1
    )
