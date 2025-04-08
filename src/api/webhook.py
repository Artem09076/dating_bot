from src.api.router import router
from src.bot import dp, bot
from starlette.requests import Request
from fastapi.responses import ORJSONResponse

@router.post('/webhook')
async def webhook(request: Request) -> ORJSONResponse:
    update = await request.json()

    await dp.feed_webhook_update(bot, update)

    return ORJSONResponse({'status': 'ok'})