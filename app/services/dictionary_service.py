import httpx

from ..core.config import settings


class DictionaryService:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def lookup(self, word: str) -> dict:
        if not word:
            raise ValueError("word is required")
        url = f"{self._base_url}/en/{word}"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return {"word": word, "found": False, "entries": []}
            response.raise_for_status()
            return {"word": word, "found": True, "entries": response.json()}


dictionary_service = DictionaryService(
    settings.dictionary_base_url,
    settings.dictionary_timeout_seconds,
)
