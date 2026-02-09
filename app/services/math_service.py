import asyncio
import ast
import cmath
import math
import statistics
from dataclasses import dataclass

from ..core.config import settings


@dataclass
class MathResult:
    expression: str
    result: str
    precision: int | None


class MathService:
    def __init__(self, timeout_seconds: int, max_expr_length: int) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_expr_length = max_expr_length
        self._constants = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "inf": math.inf,
            "nan": math.nan,
            "i": 1j,
            "j": 1j,
        }
        self._functions = {
            "abs": abs,
            "round": round,
            "sum": sum,
            "prod": math.prod,
            "min": min,
            "max": max,
            "sqrt": self._wrap_math(math.sqrt, cmath.sqrt),
            "log": self._wrap_math(math.log, cmath.log),
            "log10": self._wrap_math(math.log10, cmath.log10),
            "log2": self._wrap_math(math.log2, cmath.log),
            "exp": self._wrap_math(math.exp, cmath.exp),
            "pow": pow,
            "cbrt": self._cbrt,
            "factorial": math.factorial,
            "gcd": math.gcd,
            "lcm": math.lcm,
            "comb": math.comb,
            "perm": math.perm,
            "sin": self._wrap_math(math.sin, cmath.sin),
            "cos": self._wrap_math(math.cos, cmath.cos),
            "tan": self._wrap_math(math.tan, cmath.tan),
            "asin": self._wrap_math(math.asin, cmath.asin),
            "acos": self._wrap_math(math.acos, cmath.acos),
            "atan": self._wrap_math(math.atan, cmath.atan),
            "atan2": math.atan2,
            "sinh": self._wrap_math(math.sinh, cmath.sinh),
            "cosh": self._wrap_math(math.cosh, cmath.cosh),
            "tanh": self._wrap_math(math.tanh, cmath.tanh),
            "asinh": self._wrap_math(math.asinh, cmath.asinh),
            "acosh": self._wrap_math(math.acosh, cmath.acosh),
            "atanh": self._wrap_math(math.atanh, cmath.atanh),
            "floor": math.floor,
            "ceil": math.ceil,
            "trunc": math.trunc,
            "degrees": math.degrees,
            "radians": math.radians,
            "hypot": math.hypot,
            "modf": math.modf,
            "frexp": math.frexp,
            "ldexp": math.ldexp,
            "fmod": math.fmod,
            "remainder": math.remainder,
            "erf": math.erf,
            "erfc": math.erfc,
            "gamma": math.gamma,
            "lgamma": math.lgamma,
            "isfinite": math.isfinite,
            "isnan": math.isnan,
            "isinf": math.isinf,
            "mean": statistics.mean,
            "median": statistics.median,
            "pstdev": statistics.pstdev,
            "pvariance": statistics.pvariance,
            "stdev": statistics.stdev,
            "variance": statistics.variance,
            "complex": complex,
            "conj": lambda x: x.conjugate() if isinstance(x, complex) else complex(x).conjugate(),
            "phase": cmath.phase,
            "polar": cmath.polar,
            "rect": cmath.rect,
            "real": lambda x: x.real if isinstance(x, complex) else float(x),
            "imag": lambda x: x.imag if isinstance(x, complex) else 0.0,
            "sign": lambda x: 0 if x == 0 else (1 if x > 0 else -1),
            "clamp": lambda x, lo, hi: max(lo, min(hi, x)),
            "matrix": self._matrix,
            "matmul": self._matmul,
            "transpose": self._transpose,
            "det": self._det,
            "identity": self._identity,
            "zeros": self._zeros,
            "ones": self._ones,
        }

    def _wrap_math(self, real_func, complex_func):
        def _inner(*args):
            if any(isinstance(arg, complex) for arg in args) and complex_func is not None:
                return complex_func(*args)
            return real_func(*args)

        return _inner

    def _cbrt(self, x):
        if isinstance(x, complex):
            return x ** (1 / 3)
        return math.copysign(abs(x) ** (1 / 3), x)

    def _matrix(self, value):
        if not isinstance(value, list) or not value:
            raise ValueError("matrix expects a non-empty list of rows")
        row_lengths = []
        for row in value:
            if not isinstance(row, list) or not row:
                raise ValueError("matrix rows must be non-empty lists")
            row_lengths.append(len(row))
            for item in row:
                if not isinstance(item, (int, float)):
                    raise ValueError("matrix elements must be numbers")
        if len(set(row_lengths)) != 1:
            raise ValueError("matrix rows must have equal length")
        return value

    def _transpose(self, matrix):
        matrix = self._matrix(matrix)
        return [list(row) for row in zip(*matrix)]

    def _matmul(self, left, right):
        left = self._matrix(left)
        right = self._matrix(right)
        left_cols = len(left[0])
        right_rows = len(right)
        if left_cols != right_rows:
            raise ValueError("matrix shapes are not aligned for multiplication")
        right_cols = len(right[0])
        result = []
        for i in range(len(left)):
            row = []
            for j in range(right_cols):
                total = 0.0
                for k in range(left_cols):
                    total += left[i][k] * right[k][j]
                row.append(total)
            result.append(row)
        return result

    def _det(self, matrix):
        matrix = self._matrix(matrix)
        n = len(matrix)
        if n != len(matrix[0]):
            raise ValueError("det expects a square matrix")
        if n == 1:
            return matrix[0][0]
        if n == 2:
            return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        if n == 3:
            a, b, c = matrix[0]
            d, e, f = matrix[1]
            g, h, i = matrix[2]
            return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
        raise ValueError("det supports up to 3x3 matrices")

    def _identity(self, n):
        if not isinstance(n, int) or n <= 0:
            raise ValueError("identity expects a positive integer")
        return [[1 if i == j else 0 for j in range(n)] for i in range(n)]

    def _zeros(self, rows, cols=None):
        if cols is None:
            cols = rows
        if not isinstance(rows, int) or not isinstance(cols, int) or rows <= 0 or cols <= 0:
            raise ValueError("zeros expects positive integer dimensions")
        return [[0 for _ in range(cols)] for _ in range(rows)]

    def _ones(self, rows, cols=None):
        if cols is None:
            cols = rows
        if not isinstance(rows, int) or not isinstance(cols, int) or rows <= 0 or cols <= 0:
            raise ValueError("ones expects positive integer dimensions")
        return [[1 for _ in range(cols)] for _ in range(rows)]

    def _format_value(self, value, precision: int | None) -> str:
        if isinstance(value, (int, float)):
            if precision is None:
                return str(value)
            if not isinstance(precision, int) or precision <= 0:
                raise ValueError("precision must be a positive integer")
            return format(value, f".{precision}g")
        if isinstance(value, complex):
            real = self._format_value(value.real, precision)
            imag = self._format_value(abs(value.imag), precision)
            sign = "+" if value.imag >= 0 else "-"
            return f"{real}{sign}{imag}j"
        if isinstance(value, list):
            return "[" + ", ".join(self._format_value(item, precision) for item in value) + "]"
        if isinstance(value, tuple):
            return "(" + ", ".join(self._format_value(item, precision) for item in value) + ")"
        return str(value)

    def _format_result(self, value, precision: int | None) -> str:
        if precision is None:
            return self._format_value(value, precision)
        if not isinstance(precision, int) or precision <= 0:
            raise ValueError("precision must be a positive integer")
        return self._format_value(value, precision)

    def _eval_node(self, node: ast.AST):
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, complex)):
            return node.value
        if isinstance(node, ast.List):
            return [self._eval_node(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item) for item in node.elts)
        if isinstance(node, ast.Name):
            if node.id in self._constants:
                return self._constants[node.id]
            raise ValueError(f"Unknown identifier: {node.id}")
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                return left**right
            raise ValueError("Unsupported operator")
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise ValueError("Unsupported unary operator")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            func = self._functions.get(func_name)
            if func is None:
                raise ValueError(f"Unknown function: {func_name}")
            args = [self._eval_node(arg) for arg in node.args]
            return func(*args)
        raise ValueError("Unsupported expression")

    def _evaluate_sync(self, expression: str, precision: int | None) -> MathResult:
        if not expression:
            raise ValueError("expr is required")
        if len(expression) > self._max_expr_length:
            raise ValueError("expr is too long")
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ValueError("Invalid expression") from exc
        result_value = self._eval_node(tree)
        formatted = self._format_result(result_value, precision)
        return MathResult(expression=expression, result=formatted, precision=precision)

    async def evaluate(self, expression: str, precision: int | None) -> MathResult:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._evaluate_sync, expression, precision),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Evaluation timed out") from exc


math_service = MathService(settings.math_eval_timeout_seconds, settings.math_max_expr_length)
