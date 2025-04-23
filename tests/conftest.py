import aiohttp
import pytest
import pytest_asyncio
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
    return
