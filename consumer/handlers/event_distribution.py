from typing import Any, Dict

from consumer.handlers.create_form import create_form


async def handle_event_distribution(body: Dict[str, Any]) -> None:
    match body["action"]:
        case "make_form":
            await create_form(body)
