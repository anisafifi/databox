import secrets
import string

from ..core.config import settings


class PasswordService:
    def __init__(self, max_length: int) -> None:
        self._max_length = max_length
        self._presets = {
            "strong": {
                "length": 24,
                "lowercase": True,
                "uppercase": True,
                "digits": True,
                "symbols": True,
                "exclude_ambiguous": True,
                "exclude_similar": True,
                "no_repeats": False,
                "min_lowercase": 2,
                "min_uppercase": 2,
                "min_digits": 2,
                "min_symbols": 2,
            },
            "pin": {
                "length": 6,
                "lowercase": False,
                "uppercase": False,
                "digits": True,
                "symbols": False,
                "exclude_ambiguous": False,
                "exclude_similar": False,
                "no_repeats": False,
                "min_lowercase": 0,
                "min_uppercase": 0,
                "min_digits": 6,
                "min_symbols": 0,
            },
            "passphrase": {
                "length": 32,
                "lowercase": True,
                "uppercase": False,
                "digits": False,
                "symbols": False,
                "exclude_ambiguous": False,
                "exclude_similar": False,
                "no_repeats": False,
                "min_lowercase": 1,
                "min_uppercase": 0,
                "min_digits": 0,
                "min_symbols": 0,
            },
        }
        self._wordlist = [
            "alpha",
            "amber",
            "atlas",
            "bamboo",
            "basil",
            "breeze",
            "canyon",
            "cedar",
            "cinder",
            "cloud",
            "comet",
            "coral",
            "crystal",
            "delta",
            "ember",
            "forest",
            "frost",
            "glacier",
            "harbor",
            "horizon",
            "jade",
            "juniper",
            "lilac",
            "lumen",
            "meadow",
            "meteor",
            "mist",
            "nebula",
            "oasis",
            "onyx",
            "orbit",
            "pebble",
            "pioneer",
            "quartz",
            "raven",
            "river",
            "sage",
            "sequoia",
            "shadow",
            "solace",
            "sparrow",
            "summit",
            "terra",
            "thunder",
            "tide",
            "torch",
            "valley",
            "vertex",
            "whisper",
            "wild",
            "zenith",
        ]

    def _resolve_options(
        self,
        preset: str | None,
        length: int | None,
        lowercase: bool | None,
        uppercase: bool | None,
        digits: bool | None,
        symbols: bool | None,
        exclude_ambiguous: bool | None,
        exclude_similar: bool | None,
        no_repeats: bool | None,
        min_lowercase: int | None,
        min_uppercase: int | None,
        min_digits: int | None,
        min_symbols: int | None,
    ) -> dict:
        if preset:
            preset_key = preset.lower()
            if preset_key not in self._presets:
                raise ValueError("unknown preset")
            base = dict(self._presets[preset_key])
        else:
            base = {
                "length": 16,
                "lowercase": True,
                "uppercase": True,
                "digits": True,
                "symbols": False,
                "exclude_ambiguous": True,
                "exclude_similar": False,
                "no_repeats": False,
                "min_lowercase": 0,
                "min_uppercase": 0,
                "min_digits": 0,
                "min_symbols": 0,
            }

        overrides = {
            "length": length,
            "lowercase": lowercase,
            "uppercase": uppercase,
            "digits": digits,
            "symbols": symbols,
            "exclude_ambiguous": exclude_ambiguous,
            "exclude_similar": exclude_similar,
            "no_repeats": no_repeats,
            "min_lowercase": min_lowercase,
            "min_uppercase": min_uppercase,
            "min_digits": min_digits,
            "min_symbols": min_symbols,
        }
        for key, value in overrides.items():
            if value is not None:
                base[key] = value
        return base

    def generate(
        self,
        *,
        preset: str | None = None,
        length: int | None = None,
        lowercase: bool | None = None,
        uppercase: bool | None = None,
        digits: bool | None = None,
        symbols: bool | None = None,
        exclude_ambiguous: bool | None = None,
        exclude_similar: bool | None = None,
        no_repeats: bool | None = None,
        min_lowercase: int | None = None,
        min_uppercase: int | None = None,
        min_digits: int | None = None,
        min_symbols: int | None = None,
    ) -> dict:
        options = self._resolve_options(
            preset,
            length,
            lowercase,
            uppercase,
            digits,
            symbols,
            exclude_ambiguous,
            exclude_similar,
            no_repeats,
            min_lowercase,
            min_uppercase,
            min_digits,
            min_symbols,
        )

        length = options["length"]
        lowercase = options["lowercase"]
        uppercase = options["uppercase"]
        digits = options["digits"]
        symbols = options["symbols"]
        exclude_ambiguous = options["exclude_ambiguous"]
        exclude_similar = options["exclude_similar"]
        no_repeats = options["no_repeats"]
        min_lowercase = options["min_lowercase"]
        min_uppercase = options["min_uppercase"]
        min_digits = options["min_digits"]
        min_symbols = options["min_symbols"]

        if length <= 0:
            raise ValueError("length must be greater than 0")
        if length > self._max_length:
            raise ValueError(f"length must be <= {self._max_length}")

        pools = []
        required = []

        lower_pool = string.ascii_lowercase
        upper_pool = string.ascii_uppercase
        digit_pool = string.digits
        symbol_pool = "!@#$%^&*()-_=+[]{};:,.?/"  # curated ASCII symbols

        if exclude_ambiguous:
            ambiguous = set("{}[]()/\\'\"`~,;:.")
            symbol_pool = "".join(ch for ch in symbol_pool if ch not in ambiguous)
        if exclude_similar:
            similar = set("il1Lo0O")
            lower_pool = "".join(ch for ch in lower_pool if ch not in similar)
            upper_pool = "".join(ch for ch in upper_pool if ch not in similar)
            digit_pool = "".join(ch for ch in digit_pool if ch not in similar)

        if lowercase:
            pools.append(lower_pool)
            required.append((lower_pool, min_lowercase))
        if uppercase:
            pools.append(upper_pool)
            required.append((upper_pool, min_uppercase))
        if digits:
            pools.append(digit_pool)
            required.append((digit_pool, min_digits))
        if symbols:
            pools.append(symbol_pool)
            required.append((symbol_pool, min_symbols))

        if not pools:
            raise ValueError("at least one character set must be enabled")

        if any(count < 0 for _pool, count in required):
            raise ValueError("minimum counts must be >= 0")

        min_total = sum(count for _pool, count in required)
        if min_total > length:
            raise ValueError("sum of minimum counts exceeds length")

        if no_repeats and length > len(set("".join(pools))):
            raise ValueError("no_repeats exceeds unique pool size")

        password_chars: list[str] = []
        for pool, count in required:
            for _ in range(count):
                if not pool:
                    raise ValueError("character pool is empty for requested constraints")
                password_chars.append(secrets.choice(pool))

        all_chars = "".join(pools)
        while len(password_chars) < length:
            if no_repeats:
                remaining = [ch for ch in all_chars if ch not in password_chars]
                if not remaining:
                    raise ValueError("unable to satisfy no_repeats constraint")
                password_chars.append(secrets.choice(remaining))
            else:
                password_chars.append(secrets.choice(all_chars))

        secrets.SystemRandom().shuffle(password_chars)
        return {
            "password": "".join(password_chars),
            "length": length,
            "lowercase": lowercase,
            "uppercase": uppercase,
            "digits": digits,
            "symbols": symbols,
        }

    def generate_passphrase(
        self,
        *,
        words: int,
        separator: str,
        capitalize: bool,
        include_number: bool,
        include_symbol: bool,
    ) -> dict:
        if words <= 0:
            raise ValueError("words must be greater than 0")
        if not separator:
            raise ValueError("separator is required")

        chosen = [secrets.choice(self._wordlist) for _ in range(words)]
        if capitalize:
            chosen = [word.capitalize() for word in chosen]

        if include_number:
            index = secrets.randbelow(len(chosen))
            chosen[index] = f"{chosen[index]}{secrets.randbelow(10)}"

        if include_symbol:
            symbol_pool = "!@#$%^&*"
            index = secrets.randbelow(len(chosen))
            chosen[index] = f"{chosen[index]}{secrets.choice(symbol_pool)}"

        passphrase = separator.join(chosen)
        if len(passphrase) > self._max_length:
            raise ValueError(f"passphrase length must be <= {self._max_length}")

        return {
            "passphrase": passphrase,
            "words": words,
            "separator": separator,
            "capitalize": capitalize,
            "include_number": include_number,
            "include_symbol": include_symbol,
        }


password_service = PasswordService(settings.password_max_length)
