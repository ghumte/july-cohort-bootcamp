"""Shared setup for every demo in this folder.

Keeps each demo file short and focused on the ONE idea it teaches.

    from common import MODEL, get_model, calculator
"""
from __future__ import annotations

import ast
import operator
import os
from getpass import getpass

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# Load .env if python-dotenv is available (optional).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MODEL = os.getenv("MODEL", "gpt-4o-mini")


def ensure_api_key() -> None:
    """Make sure an OpenAI key is present; prompt once if not (input hidden)."""
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass("OPENAI_API_KEY: ")


def get_model(temperature: float = 0.0) -> ChatOpenAI:
    """Return a chat model, ensuring the API key exists first."""
    ensure_api_key()
    return ChatOpenAI(model=MODEL, temperature=temperature)


# --------------------------------------------------------------------------
# A SAFE calculator tool.
#
# Teaching point (principle of least power): the obvious implementation is
# `eval(expression)` — which would let a prompt-injected model run ANY Python.
# Instead we parse the expression and walk the syntax tree, allowing only
# arithmetic. The tool can do exactly one thing, and nothing else.
# --------------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate only arithmetic nodes; reject everything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Only basic arithmetic is supported.")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression, e.g. '393 * 12.25' or '(2+3)**2'."""
    return str(_eval_node(ast.parse(expression, mode="eval").body))


def show(messages) -> None:
    """Pretty-print a list of LangChain messages, including tool calls."""
    for m in messages:
        kind = m.type
        if getattr(m, "tool_calls", None):
            for call in m.tool_calls:
                print(f"  {kind:9} → tool call: {call['name']}({call['args']})")
        elif m.content:
            print(f"  {kind:9} {m.content}")
