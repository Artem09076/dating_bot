from io import BytesIO


class MockMinioObject:
    def __init__(self, data: bytes):
        self.data = data
        self._stream = BytesIO(data)

    def read(self):
        return self._stream.read()

    def close(self):
        pass

    def release_conn(self):
        pass


class MockMinioClient:
    def __init__(self, storage: dict[str, dict[str, bytes]]):
        self.storage = storage

    def get_object(self, bucket_name: str, object_name: str) -> MockMinioObject:
        file_data = self.storage.get(bucket_name, {}).get(object_name)
        if file_data is None:
            raise FileNotFoundError()
        return MockMinioObject(file_data)
