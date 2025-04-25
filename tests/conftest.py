import aiohttp
import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from script.init_db import migrate
from src.app import create_app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _init_db() -> aiohttp.ClientSession:
    await migrate()
    yield
    await migrate("downgrade", "base")


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest_asyncio.fixture(scope="session")
async def http_client(app: FastAPI) -> httpx.AsyncClient:
    async with LifespanManager(app):
        async with httpx.AsyncClient(app=app, base_url="http://localhost") as client:
            yield client
