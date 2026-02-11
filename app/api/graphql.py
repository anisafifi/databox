import base64
import strawberry
import httpx
from fastapi import Request
from typing import List
from strawberry.exceptions import GraphQLError
from strawberry.fastapi import GraphQLRouter
from strawberry.scalars import JSON
from strawberry.types import Info

from ..services.api_key_service import api_key_service
from ..core.config import settings
from ..services.data_service import data_service
from ..services.dictionary_service import dictionary_service
from ..services.ipinfo_service import ipinfo_service
from ..services.math_service import math_service
from ..services.password_service import password_service
from ..services.shamir_service import shamir_service
from ..services.site_check_service import site_check_service
from ..services.time_service import time_service
from ..services.timezone_service import timezone_service


async def _require_api_key(info: Info) -> None:
    if not settings.require_api_key:
        return None
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
    zones: List[WorldTime]


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
class IpInfoResponse:
    ipinfo: JSON
    visitor_ip: str | None = None
    ip: str | None = None


@strawberry.type
class MathResult:
    expression: str
    result: str
    precision: int | None


@strawberry.type
class SiteCheckResult:
    url: str
    final_url: str
    status_code: int
    ok: bool
    response_time_ms: float
    headers: JSON
    redirected: bool


@strawberry.type
class PasswordResult:
    password: str
    length: int
    lowercase: bool
    uppercase: bool
    digits: bool
    symbols: bool


@strawberry.type
class PassphraseResult:
    passphrase: str
    words: int
    separator: str
    capitalize: bool
    include_number: bool
    include_symbol: bool


@strawberry.type
class DictionaryResult:
    word: str
    found: bool
    entries: JSON


@strawberry.type
class ShamirSecretSplitResult:
    shares: List[str]
    threshold: int
    count: int
    encoding: str


@strawberry.type
class ShamirSecretCombineResult:
    secret: str
    encoding: str


@strawberry.type
class Query:
    pass


@strawberry.type
class DataNamespace:
    @strawberry.field
    async def entries(self, info: Info) -> List[DataItem]:
        await _require_api_key(info)
        items = await data_service.get_data()
        return [DataItem(source=item.source, payload=item.payload) for item in items]


@strawberry.type
class MathNamespace:
    @strawberry.field
    async def evaluate(self, info: Info, expr: str, precision: int | None = None) -> MathResult:
        await _require_api_key(info)
        try:
            result = await math_service.evaluate(expr, precision)
        except TimeoutError as exc:
            raise GraphQLError(str(exc)) from exc
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return MathResult(expression=result.expression, result=result.result, precision=result.precision)


@strawberry.type
class TimeNamespace:
    @strawberry.field
    async def now(self, info: Info, tz: str = "UTC") -> TimeNow:
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
    async def utc(self, info: Info) -> TimeNow:
        await _require_api_key(info)
        current, ntp = await time_service.get_utc_datetime()
        return TimeNow(timezone="UTC", datetime=current.isoformat(), unix=int(ntp.unix_time), offset_seconds=0, source=ntp.server)

    @strawberry.field
    async def epoch(self, info: Info) -> EpochTime:
        await _require_api_key(info)
        _current, ntp = await time_service.get_utc_datetime()
        return EpochTime(unix=int(ntp.unix_time), source=ntp.server)

    @strawberry.field
    async def convert(self, info: Info, value: str, from_tz: str, to_tz: str) -> TimeConversion:
        await _require_api_key(info)
        source_dt, target_dt = await time_service.convert_datetime(value, from_tz, to_tz)
        return TimeConversion(input=source_dt.isoformat(), from_timezone=from_tz, to_timezone=to_tz, output=target_dt.isoformat())

    @strawberry.field
    async def diff(self, info: Info, start: str, end: str) -> TimeDiffResponse:
        await _require_api_key(info)
        diff = await time_service.diff(start, end)
        return TimeDiffResponse(start=start, end=end, diff=TimeDiff(**diff))

    @strawberry.field
    async def world(self, info: Info, zones: List[str]) -> WorldTimeResponse:
        await _require_api_key(info)
        results = await time_service.world_times(zones)
        return WorldTimeResponse(zones=[WorldTime(**item) for item in results])

    @strawberry.field
    async def format(self, info: Info, timestamp: float, tz: str, fmt: str) -> TimeFormatResponse:
        await _require_api_key(info)
        formatted = await time_service.format_time(timestamp, tz, fmt)
        return TimeFormatResponse(formatted=formatted, timezone=tz, format=fmt)

    @strawberry.field
    async def ntp_status(self, info: Info) -> NtpStatus:
        await _require_api_key(info)
        ntp = await time_service.get_ntp_time()
        return NtpStatus(server=ntp.server, unix=ntp.unix_time, system_unix=ntp.system_time, offset_seconds=ntp.offset_seconds, leap_indicator=ntp.leap_indicator)

    @strawberry.field
    async def leap(self, info: Info) -> NtpLeap:
        await _require_api_key(info)
        ntp = await time_service.get_ntp_time()
        return NtpLeap(leap_indicator=ntp.leap_indicator, server=ntp.server)


@strawberry.type
class TimezonesNamespace:
    @strawberry.field
    async def entries(self, info: Info, search: str | None = None, abbreviation: str | None = None, dst: int | None = None, min_offset: int | None = None, max_offset: int | None = None, limit: int = 100, offset: int = 0) -> List[TimezoneEntry]:
        await _require_api_key(info)
        entries = await timezone_service.list_entries(search=search, abbreviation=abbreviation, dst=dst, min_offset=min_offset, max_offset=max_offset, limit=limit, offset=offset)
        return [TimezoneEntry(zone_name=entry.zone_name, abbreviation=entry.abbreviation, offset_seconds=entry.offset_seconds, dst=entry.dst) for entry in entries]

    @strawberry.field
    async def abbreviations(self, info: Info) -> List[str]:
        await _require_api_key(info)
        return await timezone_service.list_abbreviations()

    @strawberry.field
    async def offsets(self, info: Info) -> List[int]:
        await _require_api_key(info)
        return await timezone_service.list_offsets()

    @strawberry.field
    async def zones(self, info: Info) -> List[str]:
        await _require_api_key(info)
        return await timezone_service.list_zone_names()

    @strawberry.field
    async def get(self, info: Info, zone_name: str) -> TimezoneEntry | None:
        await _require_api_key(info)
        try:
            entry = await timezone_service.get_current_entry(zone_name)
        except ValueError:
            return None
        return TimezoneEntry(zone_name=entry.zone_name, abbreviation=entry.abbreviation, offset_seconds=entry.offset_seconds, dst=entry.dst)


@strawberry.type
class IPNamespace:
    @strawberry.field
    async def lookup(self, info: Info, ip: str) -> IpInfoResponse:
        await _require_api_key(info)
        try:
            data = await ipinfo_service.fetch_lookup(ip)
        except Exception as exc:
            raise GraphQLError(str(exc)) from exc
        return IpInfoResponse(ipinfo=data, ip=ip)

    @strawberry.field
    async def visitor(self, info: Info) -> IpInfoResponse:
        await _require_api_key(info)
        request: Request = info.context["request"]
        visitor_ip = request.client.host if request.client else None
        try:
            data = await ipinfo_service.fetch_visitor()
        except Exception as exc:
            raise GraphQLError(str(exc)) from exc
        return IpInfoResponse(ipinfo=data, visitor_ip=visitor_ip)


@strawberry.type
class PasswordNamespace:
    @strawberry.field
    async def generate(self, info: Info, preset: str | None = None, length: int | None = None, lowercase: bool | None = None, uppercase: bool | None = None, digits: bool | None = None, symbols: bool | None = None, exclude_ambiguous: bool | None = None, exclude_similar: bool | None = None, no_repeats: bool | None = None, min_lowercase: int | None = None, min_uppercase: int | None = None, min_digits: int | None = None, min_symbols: int | None = None) -> PasswordResult:
        await _require_api_key(info)
        try:
            result = password_service.generate(preset=preset, length=length, lowercase=lowercase, uppercase=uppercase, digits=digits, symbols=symbols, exclude_ambiguous=exclude_ambiguous, exclude_similar=exclude_similar, no_repeats=no_repeats, min_lowercase=min_lowercase, min_uppercase=min_uppercase, min_digits=min_digits, min_symbols=min_symbols)
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return PasswordResult(password=result["password"], length=result["length"], lowercase=result["lowercase"], uppercase=result["uppercase"], digits=result["digits"], symbols=result["symbols"])

    @strawberry.field
    async def passphrase(self, info: Info, words: int = 4, separator: str = "-", capitalize: bool = False, include_number: bool = True, include_symbol: bool = False) -> PassphraseResult:
        await _require_api_key(info)
        try:
            result = password_service.generate_passphrase(words=words, separator=separator, capitalize=capitalize, include_number=include_number, include_symbol=include_symbol)
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return PassphraseResult(passphrase=result["passphrase"], words=result["words"], separator=result["separator"], capitalize=result["capitalize"], include_number=result["include_number"], include_symbol=result["include_symbol"])


@strawberry.type
class DictionaryNamespace:
    @strawberry.field
    async def en(self, info: Info, word: str) -> DictionaryResult:
        await _require_api_key(info)
        try:
            result = await dictionary_service.lookup(word)
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise GraphQLError(str(exc)) from exc
        return DictionaryResult(word=result["word"], found=result["found"], entries=result["entries"])


@strawberry.type
class ShamirNamespace:
    @strawberry.field
    async def split(self, info: Info, secret: str, shares: int, threshold: int, encoding: str = "utf-8") -> ShamirSecretSplitResult:
        await _require_api_key(info)
        try:
            if encoding == "base64":
                secret_bytes = base64.urlsafe_b64decode(secret.encode("ascii"))
            else:
                secret_bytes = secret.encode("utf-8")
        except Exception as exc:
            raise GraphQLError("invalid secret encoding") from exc
        try:
            shares_out = shamir_service.split(secret_bytes, shares, threshold)
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return ShamirSecretSplitResult(shares=shares_out, threshold=threshold, count=shares, encoding=encoding)

    @strawberry.field
    async def combine(self, info: Info, shares: List[str]) -> ShamirSecretCombineResult:
        await _require_api_key(info)
        try:
            secret_bytes = shamir_service.combine(shares)
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        try:
            secret = secret_bytes.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            secret = base64.urlsafe_b64encode(secret_bytes).decode("ascii")
            encoding = "base64"
        return ShamirSecretCombineResult(secret=secret, encoding=encoding)


@strawberry.type
class SiteNamespace:
    @strawberry.field
    async def check(self, info: Info, url: str) -> SiteCheckResult:
        await _require_api_key(info)
        try:
            result = await site_check_service.check(url)
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise GraphQLError(str(exc)) from exc
        return SiteCheckResult(**result)


@strawberry.type
class Query:
    @strawberry.field
    async def health(self) -> HealthStatus:
        return HealthStatus(status="ok")

    @strawberry.field
    def data(self) -> DataNamespace:
        return DataNamespace()

    @strawberry.field
    def math(self) -> MathNamespace:
        return MathNamespace()

    @strawberry.field
    def time(self) -> TimeNamespace:
        return TimeNamespace()

    @strawberry.field
    def timezones(self) -> TimezonesNamespace:
        return TimezonesNamespace()

    @strawberry.field
    def ip(self) -> IPNamespace:
        return IPNamespace()

    @strawberry.field
    def password(self) -> PasswordNamespace:
        return PasswordNamespace()

    @strawberry.field
    def dictionary(self) -> DictionaryNamespace:
        return DictionaryNamespace()

    @strawberry.field
    def shamir(self) -> ShamirNamespace:
        return ShamirNamespace()

    @strawberry.field
    def site(self) -> SiteNamespace:
        return SiteNamespace()


@strawberry.type
class Mutation:
    @strawberry.field
    async def issue_api_key(self) -> ApiKeyResponse:
        record = await api_key_service.issue_key()
        return ApiKeyResponse(api_key=record["api_key"], created_at=record["created_at"])


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=_get_context)
