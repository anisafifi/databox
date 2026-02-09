import httpx

from .base import DataSource


class HttpJsonSource(DataSource):
    name = "http_json"

    def __init__(self, url: str):
        self._url = url

    async def fetch(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self._url)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list):
            return data
        return [data]
