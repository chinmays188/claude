import ast
import operator

from pydantic import BaseModel

from app.tools.base import Tool, ToolError

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


class CalculatorArgs(BaseModel):
    expression: str


class CalculatorTool(Tool):
    name = "calculator"
    description = (
        "Evaluate a basic arithmetic expression (+, -, *, /, **). "
        "Use this for numeric calculations, not for general reasoning."
    )
    args_schema = CalculatorArgs
    permissions = ["compute:local"]
    retry_safe = True

    def run(self, args: CalculatorArgs) -> str:
        try:
            tree = ast.parse(args.expression, mode="eval")
            result = _eval_node(tree.body)
        except Exception as exc:
            raise ToolError(f"Could not evaluate expression '{args.expression}': {exc}") from exc
        return str(result)


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"Unsupported expression component: {ast.dump(node)}")
