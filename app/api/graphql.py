import strawberry
from fastapi import Request
from strawberry.exceptions import GraphQLError
from strawberry.fastapi import GraphQLRouter
from strawberry.scalars import JSON
from strawberry.types import Info

from ..services.api_key_service import api_key_service
from ..services.data_service import data_service
from ..services.time_service import time_service
from ..services.timezone_service import timezone_service


async def _require_api_key(info: Info) -> None:
    request: Request = info.context["request"]
    auth_header = request.headers.get("authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        raise GraphQLError("Missing or invalid Authorization header")
    api_key = auth_header[7:].strip()
    if not await api_key_service.validate_key(api_key):
        raise GraphQLError("Invalid API key")


async def _get_context(request: Request) -> dict:
    return {"request": request}


@strawberry.type
class DataItem:
    source: str
    payload: JSON


@strawberry.type
class TimezoneEntry:
    zone_name: str
    abbreviation: str
    offset_seconds: int
    dst: int


@strawberry.type
class ApiKeyResponse:
    api_key: str
    created_at: str


@strawberry.type
class TimeNow:
    timezone: str
    datetime: str
    unix: int
    offset_seconds: int
    source: str


@strawberry.type
class EpochTime:
    unix: int
    source: str


@strawberry.type
class TimeConversion:
    input: str
    from_timezone: str
    to_timezone: str
    output: str


@strawberry.type
class TimeDiff:
    seconds: int
    days: int
    hours: int
    minutes: int
    secs: int


@strawberry.type
class TimeDiffResponse:
    start: str
    end: str
    diff: TimeDiff


@strawberry.type
class WorldTime:
    timezone: str
    datetime: str
    unix: int
    offset_seconds: int


@strawberry.type
class WorldTimeResponse:
    zones: list[WorldTime]


@strawberry.type
class TimeFormatResponse:
    formatted: str
    timezone: str
    format: str


@strawberry.type
class NtpStatus:
    server: str
    unix: float
    system_unix: float
    offset_seconds: float
    leap_indicator: int


@strawberry.type
class NtpLeap:
    leap_indicator: int
    server: str


@strawberry.type
class HealthStatus:
    status: str


@strawberry.type
class Query:
    @strawberry.field
    async def health(self) -> HealthStatus:
        return HealthStatus(status="ok")

    @strawberry.field
    async def data(self, info: Info) -> list[DataItem]:
        await _require_api_key(info)
        items = await data_service.get_data()
        return [DataItem(source=item.source, payload=item.payload) for item in items]

    @strawberry.field
    async def timezones(
        self,
        info: Info,
        search: str | None = None,
        abbreviation: str | None = None,
        dst: int | None = None,
        min_offset: int | None = None,
        max_offset: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TimezoneEntry]:
        await _require_api_key(info)
        entries = await timezone_service.list_entries(
            search=search,
            abbreviation=abbreviation,
            dst=dst,
            min_offset=min_offset,
            max_offset=max_offset,
            limit=limit,
            offset=offset,
        )
        return [
            TimezoneEntry(
                zone_name=entry.zone_name,
                abbreviation=entry.abbreviation,
                offset_seconds=entry.offset_seconds,
                dst=entry.dst,
            )
            for entry in entries
        ]

    @strawberry.field
    async def timezone_current(self, info: Info, zone_name: str) -> TimezoneEntry | None:
        await _require_api_key(info)
        try:
            entry = await timezone_service.get_current_entry(zone_name)
        except ValueError:
            return None
        return TimezoneEntry(
            zone_name=entry.zone_name,
            abbreviation=entry.abbreviation,
            offset_seconds=entry.offset_seconds,
            dst=entry.dst,
        )

    @strawberry.field
    async def timezone_abbreviations(self, info: Info) -> list[str]:
        await _require_api_key(info)
        return await timezone_service.list_abbreviations()

    @strawberry.field
    async def timezone_offsets(self, info: Info) -> list[int]:
        await _require_api_key(info)
        return await timezone_service.list_offsets()

    @strawberry.field
    async def timezone_zones(self, info: Info) -> list[str]:
        await _require_api_key(info)
        return await timezone_service.list_zone_names()

    @strawberry.field
    async def timezone(self, info: Info, zone_name: str) -> TimezoneEntry | None:
        await _require_api_key(info)
        try:
            entry = await timezone_service.get_current_entry(zone_name)
        except ValueError:
            return None
        return TimezoneEntry(
            zone_name=entry.zone_name,
            abbreviation=entry.abbreviation,
            offset_seconds=entry.offset_seconds,
            dst=entry.dst,
        )

    @strawberry.field
    async def time_now(self, info: Info, tz: str = "UTC") -> TimeNow:
        await _require_api_key(info)
        current, ntp = await time_service.get_current_datetime(tz)
        return TimeNow(
            timezone=tz,
            datetime=current.isoformat(),
            unix=int(ntp.unix_time),
            offset_seconds=int(current.utcoffset().total_seconds()),
            source=ntp.server,
        )

    @strawberry.field
    async def time_utc(self, info: Info) -> TimeNow:
        await _require_api_key(info)
        current, ntp = await time_service.get_utc_datetime()
        return TimeNow(
            timezone="UTC",
            datetime=current.isoformat(),
            unix=int(ntp.unix_time),
            offset_seconds=0,
            source=ntp.server,
        )

    @strawberry.field
    async def time_epoch(self, info: Info) -> EpochTime:
        await _require_api_key(info)
        _current, ntp = await time_service.get_utc_datetime()
        return EpochTime(unix=int(ntp.unix_time), source=ntp.server)

    @strawberry.field
    async def time_convert(self, info: Info, value: str, from_tz: str, to_tz: str) -> TimeConversion:
        await _require_api_key(info)
        source_dt, target_dt = await time_service.convert_datetime(value, from_tz, to_tz)
        return TimeConversion(
            input=source_dt.isoformat(),
            from_timezone=from_tz,
            to_timezone=to_tz,
            output=target_dt.isoformat(),
        )

    @strawberry.field
    async def time_diff(self, info: Info, start: str, end: str) -> TimeDiffResponse:
        await _require_api_key(info)
        diff = await time_service.diff(start, end)
        return TimeDiffResponse(start=start, end=end, diff=TimeDiff(**diff))

    @strawberry.field
    async def time_world(self, info: Info, zones: list[str]) -> WorldTimeResponse:
        await _require_api_key(info)
        results = await time_service.world_times(zones)
        return WorldTimeResponse(
            zones=[WorldTime(**item) for item in results],
        )

    @strawberry.field
    async def time_format(self, info: Info, timestamp: float, tz: str, fmt: str) -> TimeFormatResponse:
        await _require_api_key(info)
        formatted = await time_service.format_time(timestamp, tz, fmt)
        return TimeFormatResponse(formatted=formatted, timezone=tz, format=fmt)

    @strawberry.field
    async def time_ntp_status(self, info: Info) -> NtpStatus:
        await _require_api_key(info)
        ntp = await time_service.get_ntp_time()
        return NtpStatus(
            server=ntp.server,
            unix=ntp.unix_time,
            system_unix=ntp.system_time,
            offset_seconds=ntp.offset_seconds,
            leap_indicator=ntp.leap_indicator,
        )

    @strawberry.field
    async def time_leap(self, info: Info) -> NtpLeap:
        await _require_api_key(info)
        ntp = await time_service.get_ntp_time()
        return NtpLeap(leap_indicator=ntp.leap_indicator, server=ntp.server)


@strawberry.type
class Mutation:
    @strawberry.field
    async def issue_api_key(self) -> ApiKeyResponse:
        record = await api_key_service.issue_key()
        return ApiKeyResponse(api_key=record["api_key"], created_at=record["created_at"])


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=_get_context)
