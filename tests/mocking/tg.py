from unittest.mock import AsyncMock


class MockTgMessage(AsyncMock):
    def __init__(self, from_user, **kwargs):
        super().__init__(**kwargs)
        self.from_user = from_user


class MockTgCall(AsyncMock):
    def __init__(self, from_user, message, data, **kwargs):
        super().__init__(**kwargs)
        self.from_user = from_user
        self.message = message
        self.data = data
