from fastapi import APIRouter, Depends, HTTPException, Query, Request
import base64
import httpx

from ..core.auth import require_api_key
from ..core.config import settings
from ..schemas import ApiKeyResponse, DataItem, TimezoneEntry
from ..services.data_service import data_service
from ..services.api_key_service import api_key_service
from ..services.dictionary_service import dictionary_service
from ..services.ipinfo_service import ipinfo_service
from ..services.math_service import math_service
from ..services.password_service import password_service
from ..services.shamir_service import shamir_service
from ..services.site_check_service import site_check_service
from ..services.time_service import time_service
from ..services.timezone_service import timezone_service

public_router = APIRouter()
# If API key enforcement is enabled, attach the dependency to the main router,
# otherwise create an unconstrained router.
router = (
    APIRouter(dependencies=[Depends(require_api_key)])
    if settings.require_api_key
    else APIRouter()
)


@public_router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/auth/keys", response_model=ApiKeyResponse)
async def issue_api_key() -> ApiKeyResponse:
    record = await api_key_service.issue_key()
    return ApiKeyResponse(api_key=record["api_key"], created_at=record["created_at"])


@router.get("/data", response_model=list[DataItem])
async def list_data() -> list[DataItem]:
    return await data_service.get_data()


@router.get("/math")
async def math_get(expr: str, precision: int | None = Query(default=None, ge=1, le=16)) -> dict:
    if " " in expr and "+" not in expr and "[" not in expr and "]" not in expr and "," not in expr:
        expr = expr.replace(" ", "+")
    try:
        result = await math_service.evaluate(expr, precision)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"expression": result.expression, "result": result.result, "precision": result.precision}


@router.post("/math")
async def math_post(payload: dict) -> dict:
    expr = payload.get("expr")
    precision = payload.get("precision")
    try:
        result = await math_service.evaluate(expr, precision)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"expression": result.expression, "result": result.result, "precision": result.precision}


@router.get("/site/check")
async def site_check(url: str) -> dict:
    try:
        return await site_check_service.check(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/password")
async def password_get(
    preset: str | None = None,
    length: int | None = Query(default=None, ge=1, le=128),
    lowercase: bool | None = None,
    uppercase: bool | None = None,
    digits: bool | None = None,
    symbols: bool | None = None,
    exclude_ambiguous: bool | None = None,
    exclude_similar: bool | None = None,
    no_repeats: bool | None = None,
    min_lowercase: int | None = Query(default=None, ge=0),
    min_uppercase: int | None = Query(default=None, ge=0),
    min_digits: int | None = Query(default=None, ge=0),
    min_symbols: int | None = Query(default=None, ge=0),
) -> dict:
    try:
        return password_service.generate(
            preset=preset,
            length=length,
            lowercase=lowercase,
            uppercase=uppercase,
            digits=digits,
            symbols=symbols,
            exclude_ambiguous=exclude_ambiguous,
            exclude_similar=exclude_similar,
            no_repeats=no_repeats,
            min_lowercase=min_lowercase,
            min_uppercase=min_uppercase,
            min_digits=min_digits,
            min_symbols=min_symbols,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/password")
async def password_post(payload: dict) -> dict:
    try:
        return password_service.generate(
            preset=payload.get("preset"),
            length=payload.get("length"),
            lowercase=payload.get("lowercase"),
            uppercase=payload.get("uppercase"),
            digits=payload.get("digits"),
            symbols=payload.get("symbols"),
            exclude_ambiguous=payload.get("exclude_ambiguous"),
            exclude_similar=payload.get("exclude_similar"),
            no_repeats=payload.get("no_repeats"),
            min_lowercase=payload.get("min_lowercase"),
            min_uppercase=payload.get("min_uppercase"),
            min_digits=payload.get("min_digits"),
            min_symbols=payload.get("min_symbols"),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/passphrase")
async def passphrase_get(
    words: int = Query(default=4, ge=1, le=16),
    separator: str = "-",
    capitalize: bool = False,
    include_number: bool = True,
    include_symbol: bool = False,
) -> dict:
    try:
        return password_service.generate_passphrase(
            words=words,
            separator=separator,
            capitalize=capitalize,
            include_number=include_number,
            include_symbol=include_symbol,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/passphrase")
async def passphrase_post(payload: dict) -> dict:
    try:
        return password_service.generate_passphrase(
            words=int(payload.get("words", 4)),
            separator=str(payload.get("separator", "-")),
            capitalize=bool(payload.get("capitalize", False)),
            include_number=bool(payload.get("include_number", True)),
            include_symbol=bool(payload.get("include_symbol", False)),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dictionary/en/{word}")
async def dictionary_lookup(word: str) -> dict:
    try:
        return await dictionary_service.lookup(word)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/shamir/secret/split")
async def shamir_secret_split(payload: dict) -> dict:
    secret = payload.get("secret")
    shares = payload.get("shares")
    threshold = payload.get("threshold")
    encoding = payload.get("encoding", "utf-8")
    if not isinstance(secret, str):
        raise HTTPException(status_code=400, detail="secret must be a string")
    try:
        shares = int(shares)
        threshold = int(threshold)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="shares and threshold must be integers") from exc
    try:
        if encoding == "base64":
            secret_bytes = base64.urlsafe_b64decode(secret.encode("ascii"))
        else:
            secret_bytes = secret.encode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid secret encoding") from exc
    try:
        shares_out = shamir_service.split(secret_bytes, shares, threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "shares": shares_out,
        "threshold": threshold,
        "count": shares,
        "encoding": encoding,
    }


@router.post("/shamir/secret/combine")
async def shamir_secret_combine(payload: dict) -> dict:
    shares = payload.get("shares")
    if not isinstance(shares, list) or not shares:
        raise HTTPException(status_code=400, detail="shares must be a non-empty list")
    try:
        secret_bytes = shamir_service.combine(shares)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        secret = secret_bytes.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        secret = base64.urlsafe_b64encode(secret_bytes).decode("ascii")
        encoding = "base64"
    return {"secret": secret, "encoding": encoding}


@router.get("/ip/lookup")
async def ip_lookup(ip: str) -> dict:
    try:
        data = await ipinfo_service.fetch_lookup(ip)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ip": ip, "ipinfo": data}


@router.get("/ip/visitor")
async def ip_visitor(request: Request) -> dict:
    try:
        data = await ipinfo_service.fetch_visitor()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    visitor_ip = request.client.host if request.client else None
    return {"visitor_ip": visitor_ip, "ipinfo": data}


@router.get("/time/now")
async def get_time_now(tz: str = "UTC") -> dict:
    try:
        current, ntp = await time_service.get_current_datetime(tz)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "timezone": tz,
        "datetime": current.isoformat(),
        "unix": int(ntp.unix_time),
        "offset_seconds": int(current.utcoffset().total_seconds()),
        "source": ntp.server,
    }


@router.get("/time/utc")
async def get_time_utc() -> dict:
    current, ntp = await time_service.get_utc_datetime()
    return {
        "timezone": "UTC",
        "datetime": current.isoformat(),
        "unix": int(ntp.unix_time),
        "offset_seconds": 0,
        "source": ntp.server,
    }


@router.get("/time/epoch")
async def get_time_epoch() -> dict:
    _current, ntp = await time_service.get_utc_datetime()
    return {"unix": int(ntp.unix_time), "source": ntp.server}


@router.get("/time/convert")
async def convert_time(value: str, from_tz: str, to_tz: str) -> dict:
    try:
        source_dt, target_dt = await time_service.convert_datetime(value, from_tz, to_tz)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "input": source_dt.isoformat(),
        "from_timezone": from_tz,
        "to_timezone": to_tz,
        "output": target_dt.isoformat(),
    }


@router.get("/time/diff")
async def diff_time(start: str, end: str) -> dict:
    diff = await time_service.diff(start, end)
    return {"start": start, "end": end, "diff": diff}


@router.get("/time/world")
async def world_time(zones: str) -> dict:
    zone_list = [zone.strip() for zone in zones.split(",") if zone.strip()]
    if not zone_list:
        raise HTTPException(status_code=400, detail="zones is required")
    try:
        results = await time_service.world_times(zone_list)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"zones": results}


@router.get("/time/format")
async def format_time(timestamp: float, tz: str, fmt: str) -> dict:
    try:
        formatted = await time_service.format_time(timestamp, tz, fmt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"formatted": formatted, "timezone": tz, "format": fmt}


@router.get("/time/ntp/status")
async def get_ntp_status() -> dict:
    ntp = await time_service.get_ntp_time()
    return {
        "server": ntp.server,
        "unix": ntp.unix_time,
        "system_unix": ntp.system_time,
        "offset_seconds": ntp.offset_seconds,
        "leap_indicator": ntp.leap_indicator,
    }


@router.get("/time/leap")
async def get_ntp_leap_indicator() -> dict:
    ntp = await time_service.get_ntp_time()
    return {"leap_indicator": ntp.leap_indicator, "server": ntp.server}


@router.get("/timezones", response_model=list[TimezoneEntry])
async def list_timezones(
    search: str | None = None,
    abbreviation: str | None = None,
    dst: int | None = Query(default=None, ge=0, le=1),
    min_offset: int | None = None,
    max_offset: int | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[TimezoneEntry]:
    return await timezone_service.list_entries(
        search=search,
        abbreviation=abbreviation,
        dst=dst,
        min_offset=min_offset,
        max_offset=max_offset,
        limit=limit,
        offset=offset,
    )


@router.get("/timezones/abbreviations", response_model=list[str])
async def list_timezone_abbreviations() -> list[str]:
    return await timezone_service.list_abbreviations()


@router.get("/timezones/offsets", response_model=list[int])
async def list_timezone_offsets() -> list[int]:
    return await timezone_service.list_offsets()


@router.get("/timezones/zones", response_model=list[str])
async def list_timezone_zones() -> list[str]:
    return await timezone_service.list_zone_names()


@router.get("/timezones/{zone_name:path}/current", response_model=TimezoneEntry)
async def get_timezone_current(zone_name: str) -> TimezoneEntry:
    try:
        return await timezone_service.get_current_entry(zone_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/timezones/{zone_name:path}", response_model=TimezoneEntry)
async def get_timezone(zone_name: str) -> TimezoneEntry:
    try:
        return await timezone_service.get_current_entry(zone_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
