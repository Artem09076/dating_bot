from typing import Any, Dict

from consumer.handlers.create_form import create_form
from consumer.handlers.find_candidates import find_candidates


async def handle_event_distribution(body: Dict[str, Any]) -> None:
    match body["action"]:
        case "make_form":
            await create_form(body)
        case 'find_candidates':
            await find_candidates(body)
