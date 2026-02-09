from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from ..schemas import TimezoneEntry


class TimezoneService:
    def __init__(self) -> None:
        self._zones = sorted(available_timezones())

    def _get_zone(self, zone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(zone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown time zone: {zone_name}") from exc

    def _current_entry(self, zone_name: str) -> TimezoneEntry:
        tz = self._get_zone(zone_name)
        now = datetime.now(tz=tz)
        offset = int(now.utcoffset().total_seconds())
        dst = int(bool(now.dst()))
        abbr = now.tzname() or ""
        return TimezoneEntry(
            zone_name=zone_name,
            abbreviation=abbr,
            offset_seconds=offset,
            dst=dst,
        )

    async def list_entries(
        self,
        *,
        search: str | None = None,
        abbreviation: str | None = None,
        dst: int | None = None,
        min_offset: int | None = None,
        max_offset: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TimezoneEntry]:
        normalized_search = search.lower() if search else None
        results: list[TimezoneEntry] = []
        matched = 0
        for zone in self._zones:
            if normalized_search and normalized_search not in zone.lower():
                continue
            entry = self._current_entry(zone)
            if abbreviation and entry.abbreviation != abbreviation:
                continue
            if dst is not None and entry.dst != dst:
                continue
            if min_offset is not None and entry.offset_seconds < min_offset:
                continue
            if max_offset is not None and entry.offset_seconds > max_offset:
                continue
            if matched < offset:
                matched += 1
                continue
            results.append(entry)
            matched += 1
            if len(results) >= limit:
                break
        return results

    async def get_current_entry(self, zone_name: str) -> TimezoneEntry:
        return self._current_entry(zone_name)

    async def list_abbreviations(self) -> list[str]:
        values = {self._current_entry(zone).abbreviation for zone in self._zones}
        return sorted({value for value in values if value})

    async def list_offsets(self) -> list[int]:
        values = {self._current_entry(zone).offset_seconds for zone in self._zones}
        return sorted(values)

    async def list_zone_names(self) -> list[str]:
        return list(self._zones)


timezone_service = TimezoneService()
