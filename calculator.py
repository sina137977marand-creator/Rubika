# -*- coding: utf-8 -*-
import ast
import math
import operator as op

ALLOWED_OPERATORS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow,
    ast.USub: op.neg, ast.UAdd: op.pos,
}

ALLOWED_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "factorial": math.factorial,
}


class CalcError(Exception):
    pass


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalcError("مقدار نامعتبر")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise CalcError("عملگر مجاز نیست")
        return ALLOWED_OPERATORS[op_type](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise CalcError("عملگر مجاز نیست")
        return ALLOWED_OPERATORS[op_type](_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
            raise CalcError("تابع مجاز نیست")
        return ALLOWED_FUNCS[node.func.id](*[_eval_node(a) for a in node.args])
    raise CalcError("عبارت نامعتبر")


def safe_eval(expression: str):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    for i, d in enumerate(persian_digits):
        expression = expression.replace(d, str(i))
    expression = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


async def calc_command(bot, message, expr: str):
    from utils import areply
    from handlers.ui import title
    expr = (expr or "").strip()
    if not expr:
        await areply(message, "یک عبارت ریاضی بعد از دستور بنویس. مثال:\nحساب (5+3)*2")
        return
    try:
        result = safe_eval(expr)
        await areply(message, f"{title('ماشین‌حساب', '🧮')}\n{expr} = {result}")
    except (CalcError, ZeroDivisionError, SyntaxError, ValueError, TypeError):
        await areply(message, "❌ عبارت نامعتبر است.")
