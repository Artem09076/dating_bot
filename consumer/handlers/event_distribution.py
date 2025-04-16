from typing import Any, Dict

from consumer.handlers.create_form import create_form
from consumer.handlers.find_candidates import find_candidates
from consumer.handlers.get_profile import get_profile


async def handle_event_distribution(body: Dict[str, Any]) -> None:
    match body["action"]:
        case "make_form":
            await create_form(body)
        case 'find_pair':
            await find_candidates(body)
        # case 'like_user':
        #     await like_user(body)
        case "get_profile":
            await get_profile(body)
