from aiogram.fsm.state import StatesGroup, State


class MatchFlow(StatesGroup):
    viewing = State()
