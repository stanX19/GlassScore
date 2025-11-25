import ast
import operator as op
from langchain.tools import tool

_allowed_operators: dict[type[op], callable] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):  # Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed")
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op_type = type(node.op)
        if op_type in _allowed_operators:
            return _allowed_operators[op_type](left, right)
        raise ValueError(f"Operator {op_type} not allowed")
    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in _allowed_operators:
            return _allowed_operators[op_type](operand)
        raise ValueError(f"Unary operator {op_type} not allowed")
    raise ValueError("Unsupported expression")

def _calc_body(expr: str) -> str:
    parsed = ast.parse(expr, mode="eval")
    val = _safe_eval(parsed)
    return str(val)

@tool
def calc(expr: str) -> str:
    """
    Evaluate arithmetic expression safely. Supports + - * / % and **.
    Example: calc("2*(3+4)**2")
    """
    try:
        return _calc_body(expr)
    except Exception as e:
        return f"Error evaluating expression: {e}"