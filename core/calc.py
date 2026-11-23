"""Turns an arithmetic sentence into a number, safely (no eval)."""
import ast
import math
import operator
import re

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def safe_eval(expr: str) -> float:
    return _eval(ast.parse(expr, mode="eval"))


_NUM = r"(\d+(?:\.\d+)?)"


def sentence_to_expression(text: str):
    """Returns (expression_string, pretty_string) or (None, None)."""
    t = text.lower().replace(",", "").replace("?", " ")
    t = re.sub(r"\b(please|for me|now|right now|thanks|kitne hotay hain|kitne hote hain|equals|equal to)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    m = re.search(rf"square root of {_NUM}", t)
    if m:
        return f"{math.sqrt(float(m.group(1)))}", f"√{m.group(1)}"
    m = re.search(rf"{_NUM} (?:percent|%) of {_NUM}", t)
    if m:
        return f"{m.group(1)}/100*{m.group(2)}", f"{m.group(1)}% of {m.group(2)}"
    m = re.search(rf"(?:add|sum of) {_NUM} (?:and|to) {_NUM}", t)
    if m:
        return f"{m.group(1)}+{m.group(2)}", f"{m.group(1)} + {m.group(2)}"
    m = re.search(rf"subtract {_NUM} from {_NUM}", t)
    if m:
        return f"{m.group(2)}-{m.group(1)}", f"{m.group(2)} − {m.group(1)}"
    m = re.search(rf"multiply {_NUM} by {_NUM}", t)
    if m:
        return f"{m.group(1)}*{m.group(2)}", f"{m.group(1)} × {m.group(2)}"
    m = re.search(rf"divide {_NUM} by {_NUM}", t)
    if m:
        return f"{m.group(1)}/{m.group(2)}", f"{m.group(1)} ÷ {m.group(2)}"
    m = re.search(rf"{_NUM} ko {_NUM} se multiply", t)
    if m:
        return f"{m.group(1)}*{m.group(2)}", f"{m.group(1)} × {m.group(2)}"

    words = [
        (r"\bto the power of\b|\bpower\b", "**"), (r"\bmultiplied by\b|\btimes\b|\bmultiply\b|\bx\b", "*"),
        (r"\bdivided by\b|\bover\b", "/"), (r"\bplus\b|\band\b", "+"), (r"\bminus\b|\bless\b", "-"),
    ]
    for pat, sym in words:
        t = re.sub(pat, f" {sym} ", t)
    cleaned = re.sub(r"[^0-9+\-*/().\s]", " ", t)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not re.search(r"\d", cleaned) or not re.search(r"[+\-*/]", cleaned):
        return None, None
    pretty = cleaned.replace("*", " × ").replace("/", " ÷ ")
    return cleaned, re.sub(r"\s+", " ", pretty)


def solve(text: str):
    """Returns dict(expression, result) or None if the sentence has no solvable arithmetic."""
    expr, pretty = sentence_to_expression(text)
    if not expr:
        return None
    try:
        value = safe_eval(expr)
    except Exception:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    elif isinstance(value, float):
        value = round(value, 6)
    return {"expression": pretty, "result": value}
