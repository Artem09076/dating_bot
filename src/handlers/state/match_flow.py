from aiogram.fsm.state import State, StatesGroup


class MatchFlow(StatesGroup):
    viewing = State()
