import httpx
import os
import random
from typing import Optional

from ..core.config import settings


_DEFAULT_TRUTHS = [
    "What's the funniest thing you've ever done?",
    "What's a secret you've never told anyone?",
    "Who was your first crush?",
]

_DEFAULT_DARES = [
    "Do an impression of your favorite celebrity.",
    "Sing the chorus of your favorite song.",
    "Do 10 jumping jacks right now.",
]


async def _proxy_generate(game: str, mode: str, stage: str, notes: Optional[str], lang: str) -> dict:
    url = settings.truth_dare_proxy_url
    if not url:
        raise RuntimeError("No proxy URL configured")
    params = {
        "game": game,
        "mode": mode,
        "stage": stage,
        "notes": notes or "",
        "lang": lang,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def generate_prompt(game: str = "party", mode: str = "dare", stage: str = "chill", notes: Optional[str] = None, lang: str = "English") -> dict:
    """Generate a truth-or-dare prompt.

    If `settings.truth_dare_proxy_url` is set, proxy to that URL. Otherwise produce
    a simple locally generated prompt in English.
    """
    if settings.truth_dare_proxy_url:
        try:
            return await _proxy_generate(game, mode, stage, notes, lang)
        except Exception:
            # fall back to local generator on error
            pass

    # Local simple generator (English only)
    ok = True
    text = ""
    if mode.lower() == "truth":
        text = random.choice(_DEFAULT_TRUTHS)
    else:
        text = random.choice(_DEFAULT_DARES)
    if notes:
        text = f"{text} ({notes})"
    return {"ok": ok, "text": text}


truth_dare_service = object()
