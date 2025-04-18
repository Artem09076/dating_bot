from typing import Any, Dict

from consumer.handlers.create_form import create_form
from consumer.handlers.get_profile import get_profile
from consumer.handlers.delete_profile import delete_profile


async def handle_event_distribution(body: Dict[str, Any]) -> None:
    match body["action"]:
        case "make_form":
            await create_form(body)
        case "get_profile":
            await get_profile(body)
        case "delete_profile":
            await delete_profile(body)
