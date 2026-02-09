import base64
import secrets


class ShamirService:
    def __init__(self) -> None:
        self._exp = [0] * 512
        self._log = [0] * 256
        self._init_tables()

    def _init_tables(self) -> None:
        value = 1
        for i in range(255):
            self._exp[i] = value
            self._log[value] = i
            value <<= 1
            if value & 0x100:
                value ^= 0x11B
        for i in range(255, 512):
            self._exp[i] = self._exp[i - 255]

    def _gf_add(self, a: int, b: int) -> int:
        return a ^ b

    def _gf_mul(self, a: int, b: int) -> int:
        if a == 0 or b == 0:
            return 0
        return self._exp[self._log[a] + self._log[b]]

    def _gf_div(self, a: int, b: int) -> int:
        if b == 0:
            raise ValueError("division by zero in field")
        if a == 0:
            return 0
        return self._exp[(self._log[a] - self._log[b]) % 255]

    def _eval_poly(self, coeffs: list[int], x: int) -> int:
        result = 0
        for coeff in reversed(coeffs):
            result = self._gf_mul(result, x)
            result = self._gf_add(result, coeff)
        return result

    def _lagrange_at_zero(self, points: list[tuple[int, int]]) -> int:
        result = 0
        for j, (xj, yj) in enumerate(points):
            num = 1
            den = 1
            for m, (xm, _ym) in enumerate(points):
                if m == j:
                    continue
                num = self._gf_mul(num, xm)
                den = self._gf_mul(den, self._gf_add(xm, xj))
            term = self._gf_mul(yj, self._gf_div(num, den))
            result = self._gf_add(result, term)
        return result

    def split(self, secret: bytes, shares: int, threshold: int) -> list[str]:
        if threshold < 2:
            raise ValueError("threshold must be at least 2")
        if shares < threshold:
            raise ValueError("shares must be >= threshold")
        if shares > 255 or threshold > 255:
            raise ValueError("shares and threshold must be <= 255")
        if not secret:
            raise ValueError("secret must not be empty")

        share_bytes = [bytearray() for _ in range(shares)]
        for secret_byte in secret:
            coeffs = [secret_byte] + [secrets.randbelow(256) for _ in range(threshold - 1)]
            for idx in range(shares):
                x = idx + 1
                share_bytes[idx].append(self._eval_poly(coeffs, x))

        results = []
        for idx, data in enumerate(share_bytes, start=1):
            payload = base64.urlsafe_b64encode(bytes(data)).decode("ascii")
            results.append(f"s:{idx}:{payload}")
        return results

    def combine(self, shares: list[str]) -> bytes:
        if len(shares) < 2:
            raise ValueError("at least 2 shares are required")

        points: list[tuple[int, bytes]] = []
        for share in shares:
            if not share.startswith("s:"):
                raise ValueError("invalid share format")
            parts = share.split(":", 2)
            if len(parts) != 3:
                raise ValueError("invalid share format")
            try:
                x = int(parts[1])
            except ValueError as exc:
                raise ValueError("invalid share index") from exc
            if x <= 0 or x > 255:
                raise ValueError("share index out of range")
            try:
                data = base64.urlsafe_b64decode(parts[2].encode("ascii"))
            except ValueError as exc:
                raise ValueError("invalid share payload") from exc
            points.append((x, data))

        lengths = {len(data) for _x, data in points}
        if len(lengths) != 1:
            raise ValueError("shares have different lengths")

        secret = bytearray()
        share_points = [(x, data) for x, data in points]
        for i in range(lengths.pop()):
            column = [(x, data[i]) for x, data in share_points]
            secret.append(self._lagrange_at_zero(column))
        return bytes(secret)


shamir_service = ShamirService()
