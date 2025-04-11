import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from consumer.api.router import router as tech_router
from consumer.app import main


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:

    task = asyncio.create_task(main())

    yield
    task.cancel()