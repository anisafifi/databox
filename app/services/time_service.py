import asyncio
import socket
import struct
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..core.config import settings


_NTP_UNIX_EPOCH_DELTA = 2208988800


@dataclass
class NtpResult:
    server: str
    unix_time: float
    system_time: float
    offset_seconds: float
    leap_indicator: int


class TimeService:
    def __init__(self, servers: list[str], timeout_seconds: int) -> None:
        self._servers = servers
        self._timeout_seconds = timeout_seconds

    def _get_timezone(self, tz_name: str) -> ZoneInfo | UTC:
        normalized = tz_name.upper()
        if normalized in {"UTC", "ETC/UTC"}:
            return UTC
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown time zone: {tz_name}") from exc

    async def _query_server(self, server: str) -> NtpResult:
        def _fetch() -> NtpResult:
            packet = b"\x1b" + 47 * b"\0"
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self._timeout_seconds)
                sock.sendto(packet, (server, 123))
                data, _addr = sock.recvfrom(48)

            if len(data) < 48:
                raise RuntimeError("Invalid NTP response")

            leap_indicator = (data[0] >> 6) & 0x3
            unpacked = struct.unpack("!12I", data[0:48])
            transmit_seconds = unpacked[10]
            transmit_fraction = unpacked[11]
            ntp_time = transmit_seconds + transmit_fraction / 2**32
            unix_time = ntp_time - _NTP_UNIX_EPOCH_DELTA
            system_time = time.time()
            offset = unix_time - system_time
            return NtpResult(
                server=server,
                unix_time=unix_time,
                system_time=system_time,
                offset_seconds=offset,
                leap_indicator=leap_indicator,
            )

        return await asyncio.to_thread(_fetch)

    async def get_ntp_time(self) -> NtpResult:
        last_error: Exception | None = None
        for server in self._servers:
            try:
                return await self._query_server(server)
            except Exception as exc:
                last_error = exc
        raise RuntimeError("All NTP servers failed") from last_error

    async def get_current_datetime(self, tz_name: str) -> tuple[datetime, NtpResult]:
        ntp = await self.get_ntp_time()
        tz = self._get_timezone(tz_name)
        current = datetime.fromtimestamp(ntp.unix_time, tz=tz)
        return current, ntp

    async def get_utc_datetime(self) -> tuple[datetime, NtpResult]:
        return await self.get_current_datetime("UTC")

    async def convert_datetime(
        self, value: str, from_tz: str, to_tz: str
    ) -> tuple[datetime, datetime]:
        source_tz = self._get_timezone(from_tz)
        target_tz = self._get_timezone(to_tz)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=source_tz)
        converted = parsed.astimezone(target_tz)
        return parsed, converted

    async def format_time(self, timestamp: float, tz_name: str, fmt: str) -> str:
        tz = self._get_timezone(tz_name)
        value = datetime.fromtimestamp(timestamp, tz=tz)
        return value.strftime(fmt)

    async def diff(self, start: str, end: str) -> dict:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        delta = end_dt - start_dt
        seconds = int(delta.total_seconds())
        abs_seconds = abs(seconds)
        days, remainder = divmod(abs_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        return {
            "seconds": seconds,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "secs": secs,
        }

    async def world_times(self, zones: list[str]) -> list[dict]:
        ntp = await self.get_ntp_time()
        results = []
        for zone in zones:
            tz = self._get_timezone(zone)
            current = datetime.fromtimestamp(ntp.unix_time, tz=tz)
            results.append(
                {
                    "timezone": zone,
                    "datetime": current.isoformat(),
                    "unix": int(ntp.unix_time),
                    "offset_seconds": int(current.utcoffset().total_seconds()),
                }
            )
        return results


_time_service = TimeService(settings.ntp_servers, settings.ntp_timeout_seconds)


time_service = _time_service
