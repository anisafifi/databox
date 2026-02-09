import httpx

from ..core.config import settings


class IpInfoService:
    def __init__(
        self,
        token: str | None,
        lookup_base_url: str,
        visitor_url: str,
        timeout_seconds: int,
    ) -> None:
        self._token = token
        self._lookup_base_url = lookup_base_url.rstrip("/")
        self._visitor_url = visitor_url
        self._timeout_seconds = timeout_seconds

    async def _fetch(self, url: str) -> dict:
        if not self._token:
            raise RuntimeError("IPINFO token is not configured")

        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def fetch_lookup(self, ip: str) -> dict:
        url = f"{self._lookup_base_url}/{ip}"
        return await self._fetch(url)

    async def fetch_visitor(self) -> dict:
        return await self._fetch(self._visitor_url)


ipinfo_service = IpInfoService(
    settings.ipinfo_token,
    settings.ipinfo_lookup_base_url,
    settings.ipinfo_visitor_url,
    settings.ipinfo_timeout_seconds,
)
