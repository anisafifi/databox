import ipaddress
import socket
import time
from urllib.parse import urlparse

import httpx

from ..core.config import settings


class SiteCheckService:
    def __init__(
        self,
        timeout_connect_seconds: int,
        timeout_read_seconds: int,
        max_redirects: int,
        user_agent: str,
        allowlist: list[str],
        header_allowlist: list[str],
    ) -> None:
        self._timeout_connect_seconds = timeout_connect_seconds
        self._timeout_read_seconds = timeout_read_seconds
        self._max_redirects = max_redirects
        self._user_agent = user_agent
        self._allowlist = [item.lower() for item in allowlist if item]
        self._header_allowlist = {item.lower() for item in header_allowlist if item}

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("url must start with http or https")
        if not parsed.netloc:
            raise ValueError("url must include a host")
        host = parsed.hostname or ""
        if self._allowlist:
            if not any(host == domain or host.endswith(f".{domain}") for domain in self._allowlist):
                raise ValueError("host is not in allowlist")

    def _is_blocked_ip(self, ip_value: str) -> bool:
        ip_obj = ipaddress.ip_address(ip_value)
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )

    def _resolve_and_validate(self, url: str) -> None:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError("url must include a host")
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ValueError("unable to resolve host") from exc
        for info in infos:
            ip_value = info[4][0]
            if self._is_blocked_ip(ip_value):
                raise ValueError("host resolves to a blocked address")

    def _filter_headers(self, headers: httpx.Headers) -> dict:
        if not self._header_allowlist:
            return {}
        return {
            key: value
            for key, value in headers.items()
            if key.lower() in self._header_allowlist
        }

    async def check(self, url: str) -> dict:
        self._validate_url(url)
        self._resolve_and_validate(url)
        headers = {"User-Agent": self._user_agent}
        timeout = httpx.Timeout(
            connect=self._timeout_connect_seconds,
            read=self._timeout_read_seconds,
            write=self._timeout_read_seconds,
            pool=self._timeout_read_seconds,
        )
        start = time.perf_counter()
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=self._max_redirects,
        ) as client:
            response = await client.request("HEAD", url, headers=headers)
            if response.status_code in {403, 405}:
                response = await client.get(url, headers=headers)
        duration_ms = (time.perf_counter() - start) * 1000
        filtered_headers = self._filter_headers(response.headers)
        return {
            "url": url,
            "final_url": str(response.url),
            "status_code": response.status_code,
            "ok": response.status_code < 400,
            "response_time_ms": round(duration_ms, 2),
            "headers": filtered_headers,
            "redirected": str(response.url) != url,
        }


site_check_service = SiteCheckService(
    settings.site_check_timeout_connect_seconds,
    settings.site_check_timeout_read_seconds,
    settings.site_check_max_redirects,
    settings.site_check_user_agent,
    settings.site_check_allowlist,
    settings.site_check_header_allowlist,
)
