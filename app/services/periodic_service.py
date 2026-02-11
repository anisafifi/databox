import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings


class PeriodicService:
    def __init__(self, source_url: str | None, cache_path: str | None) -> None:
        self.source_url = source_url
        self.cache_path = cache_path
        self._lock = asyncio.Lock()
        self._data: Optional[Dict[str, Any]] = None

        # common group names mapping (1-18)
        self._group_names: Dict[int, str] = {
            1: "Alkali metals",
            2: "Alkaline earth metals",
            3: "Scandium group",
            4: "Titanium group",
            5: "Vanadium group",
            6: "Chromium group",
            7: "Manganese group",
            8: "Iron group",
            9: "Cobalt group",
            10: "Nickel group",
            11: "Coinage metals",
            12: "Zinc group",
            13: "Boron group",
            14: "Carbon group",
            15: "Pnictogens",
            16: "Chalcogens",
            17: "Halogens",
            18: "Noble gases",
        }

        self._block_descriptions: Dict[str, str] = {
            "s": "s block (alkali and alkaline earth metals)",
            "p": "p block (nonmetals, metalloids, post-transition metals)",
            "d": "d block (transition metals)",
            "f": "f block (lanthanides and actinides)",
        }

    async def _fetch_remote(self) -> Dict[str, Any]:
        if not self.source_url:
            return {}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self.source_url)
            resp.raise_for_status()
            return resp.json()

    def _load_cache(self) -> Dict[str, Any]:
        if not self.cache_path or not os.path.exists(self.cache_path):
            return {}
        with open(self.cache_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save_cache(self, data: Dict[str, Any]) -> None:
        if not self.cache_path:
            return
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    async def load(self) -> Dict[str, Any]:
        async with self._lock:
            if self._data is not None:
                return self._data
            # prefer cache to avoid remote hits
            cached = self._load_cache()
            if cached:
                self._data = cached
                return self._data
            try:
                remote = await self._fetch_remote()
            except Exception:
                remote = {}
            if remote:
                self._save_cache(remote)
            self._data = remote
            return self._data

    async def _normalize_element(self, key: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        # Best-effort normalization for core fields
        names = raw.get("names", {})
        atomic_mass = None
        if isinstance(raw.get("atomic_mass"), dict):
            atomic_mass = raw["atomic_mass"].get("value")
        elif isinstance(raw.get("standard_atomic_weight"), dict):
            atomic_mass = raw["standard_atomic_weight"].get("value")
        else:
            atomic_mass = raw.get("atomic_mass")

        # category: prefer 'set' (nonmetal, metal, etc.)
        category = raw.get("set") or raw.get("classification") or None

        return {
            "atomicNumber": raw.get("number"),
            "symbol": raw.get("symbol") or raw.get("symbol"),
            "name": names.get("en") or raw.get("name") or key.upper(),
            "category": category,
            "atomicWeight": atomic_mass,
            "period": raw.get("period"),
            "group": raw.get("group") or raw.get("column"),
            "block": raw.get("block"),
            "stateAtSTP": raw.get("phase") or raw.get("state") or None,
            "appearance": (raw.get("appearance") or {}).get("en") if isinstance(raw.get("appearance"), dict) else raw.get("appearance"),
            "discovery": raw.get("discovery"),
            # keep raw for advanced consumers
            "_raw": raw,
        }

    async def list_elements(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = await self.load()
        out: List[Dict[str, Any]] = []
        for key, raw in data.items():
            try:
                el = await self._normalize_element(key, raw)
            except Exception:
                continue
            match = True
            for k, v in filters.items():
                if v is None:
                    continue
                if k == "group" or k == "period":
                    if el.get(k) != (int(v) if str(v).isdigit() else v):
                        match = False
                        break
                elif k == "block":
                    if (el.get("block") or "").lower() != str(v).lower():
                        match = False
                        break
                elif k == "category":
                    # category may be complex; do simple substring match
                    cat = el.get("category")
                    if not cat:
                        match = False
                        break
                    if isinstance(cat, dict):
                        cat_str = json.dumps(cat).lower()
                    else:
                        cat_str = str(cat).lower()
                    if str(v).lower() not in cat_str:
                        match = False
                        break
                elif k == "discoverer":
                    disc = el.get("discovery") or {}
                    by = disc.get("by") if isinstance(disc, dict) else None
                    if not by or str(v).lower() not in str(by).lower():
                        match = False
                        break
            if match:
                out.append(el)
        return out

    async def get_element(self, identifier: str) -> Optional[Dict[str, Any]]:
        data = await self.load()
        if not data:
            return None
        ident = identifier.strip()
        # numeric atomic number
        if ident.isdigit():
            number = int(ident)
            for raw in data.values():
                if raw.get("number") == number:
                    return await self._normalize_element(raw.get("symbol", "").lower(), raw)
            return None
        # symbol
        key = ident.lower()
        if key in data:
            return await self._normalize_element(key, data[key])
        # name
        for k, raw in data.items():
            names = raw.get("names", {})
            if isinstance(names, dict) and names.get("en") and names.get("en").lower() == ident.lower():
                return await self._normalize_element(k, raw)
        return None

    async def groups(self) -> List[Dict[str, Any]]:
        data = await self.load()
        counts: Dict[int, int] = {}
        for raw in data.values():
            g = raw.get("group") or raw.get("column")
            if g is None:
                continue
            try:
                gi = int(g)
            except Exception:
                continue
            counts[gi] = counts.get(gi, 0) + 1
        result = [{"number": num, "elements": counts[num], "name": self._group_names.get(num)} for num in sorted(counts.keys())]
        return result

    async def periods(self) -> List[Dict[str, Any]]:
        data = await self.load()
        counts: Dict[int, int] = {}
        for raw in data.values():
            p = raw.get("period")
            if p is None:
                continue
            try:
                pi = int(p)
            except Exception:
                continue
            counts[pi] = counts.get(pi, 0) + 1
        result = [{"number": num, "elements": counts[num]} for num in sorted(counts.keys())]
        return result

    async def blocks(self) -> List[Dict[str, Any]]:
        data = await self.load()
        counts: Dict[str, int] = {}
        for raw in data.values():
            b = raw.get("block")
            if not b:
                continue
            bi = str(b)
            counts[bi] = counts.get(bi, 0) + 1
        result = [
            {"code": code, "elements": counts[code], "description": self._block_descriptions.get(code)}
            for code in sorted(counts.keys())
        ]
        return result

    async def constants(self) -> Dict[str, Any]:
        return {
            "avogadro": 6.02214076e23,
            "gasConstant": 8.314462618,
            "faraday": 96485.33212,
        }


periodic_service = PeriodicService(settings.periodic_data_url, settings.periodic_cache_path)
