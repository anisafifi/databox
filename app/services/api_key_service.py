import asyncio
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from ..core.config import settings


class ApiKeyService:
    def __init__(self, path: str, retention_days: int) -> None:
        self._path = path
        self._retention_days = retention_days
        self._lock = asyncio.Lock()

    def _parse_datetime(self, value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _prune(self, entries: list[dict], now: datetime) -> list[dict]:
        cutoff = now - timedelta(days=self._retention_days)
        cleaned: list[dict] = []
        for entry in entries:
            created_at = entry.get("created_at")
            if not isinstance(created_at, str):
                continue
            parsed = self._parse_datetime(created_at)
            if parsed is None:
                continue
            if parsed >= cutoff:
                cleaned.append(entry)
        return cleaned

    async def _load(self) -> list[dict]:
        if not os.path.exists(self._path):
            return []

        def _read() -> list[dict]:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else []

        return await asyncio.to_thread(_read)

    async def _save(self, entries: list[dict]) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)

        def _write() -> None:
            with open(self._path, "w", encoding="utf-8") as handle:
                json.dump(entries, handle, indent=2)

        await asyncio.to_thread(_write)

    async def issue_key(self) -> dict:
        now = datetime.now(timezone.utc)
        api_key = f"db_{secrets.token_hex(16)}"

        async with self._lock:
            entries = await self._load()
            entries = self._prune(entries, now)
            record = {"api_key": api_key, "created_at": now.isoformat()}
            entries.append(record)
            await self._save(entries)

        return record

    async def validate_key(self, api_key: str) -> bool:
        now = datetime.now(timezone.utc)
        async with self._lock:
            entries = await self._load()
            pruned = self._prune(entries, now)
            if len(pruned) != len(entries):
                await self._save(pruned)
            return any(entry.get("api_key") == api_key for entry in pruned)


api_key_service = ApiKeyService(settings.api_keys_path, settings.api_key_retention_days)
