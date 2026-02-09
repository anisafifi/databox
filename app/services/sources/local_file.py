import asyncio
import json
import os

from .base import DataSource


class LocalFileSource(DataSource):
    name = "local_file"

    def __init__(self, path: str):
        self._path = path

    async def fetch(self) -> list[dict]:
        if not os.path.exists(self._path):
            return []

        def _read() -> object:
            with open(self._path, "r", encoding="utf-8") as handle:
                return json.load(handle)

        data = await asyncio.to_thread(_read)
        if isinstance(data, list):
            return data
        return [data]
