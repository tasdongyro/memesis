"""AST node types for Memesis. Every node carries the source line for traces and error messages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Node:
    line: int = field(default=0, kw_only=True)


# ---------------------------------------------------------------- expressions

@dataclass
class Literal(Node):
    value: Any


@dataclass
class Str(Node):
    """A string with interpolation parts: str | Node"""
    parts: list


@dataclass
class Name(Node):
    name: str


@dataclass
class ListLit(Node):
    items: list


@dataclass
class RecordLit(Node):
    pairs: list  # [(key, Node)]


@dataclass
class Unary(Node):
    op: str  # "-" | "not"
    operand: Node


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Member(Node):
    obj: Node
    name: str


@dataclass
class Index(Node):
    obj: Node
    index: Node


@dataclass
class Call(Node):
    callee: str
    args: list
    kwargs: list  # [(name, Node)]
    yolo: bool = False


@dataclass
class Copium(Node):
    attempt: Node
    fallback: Node


@dataclass
class Sus(Node):
    value: Node


@dataclass
class Sauce(Node):
    value: Node


@dataclass
class TrustMeBro(Node):
    value: Node


@dataclass
class Apu(Node):
    question: Node


@dataclass
class Thonk(Node):
    prompt: Node


@dataclass
class Fren(Node):
    target: str
    message: Node


@dataclass
class BrainExpr(Node):
    level: str
    expr: Node


@dataclass
class Wagmi(Node):
    entries: list  # [(key or None, Node)]
    as_record: bool


# ---------------------------------------------------------------- statements

@dataclass
class Such(Node):
    name: str
    value: Node


@dataclass
class Assign(Node):
    target: Node  # Name | Member | Index
    value: Node


@dataclass
class Wow(Node):
    value: Node


@dataclass
class Doge(Node):
    values: list


@dataclass
class Tfw(Node):
    cond: Node
    body: list
    otherwise: Optional[list]  # pikachu block (may contain a nested Tfw for else-if)


@dataclass
class Grind(Node):
    kind: str                       # "forever" | "count" | "each" | "until"
    expr: Optional[Node]
    var: Optional[str]
    max: Optional[Node]
    body: list


@dataclass
class Bonk(Node):
    pass


@dataclass
class Nah(Node):
    pass


@dataclass
class Chad(Node):
    body: list
    virgin: Optional[list]
    finally_: Optional[list]


@dataclass
class ThisIsFine(Node):
    body: list


@dataclass
class Based(Node):
    cond: Node
    message: Optional[Node]


@dataclass
class FeelsGood(Node):
    value: Optional[Node]


@dataclass
class FeelsBad(Node):
    value: Node


@dataclass
class Brain(Node):
    level: str  # smooth | big | galaxy
    body: list


@dataclass
class TouchGrass(Node):
    seconds: Node


@dataclass
class Stonks(Node):
    name: Node
    delta: Optional[Node]


@dataclass
class ExprStmt(Node):
    expr: Node


@dataclass
class Pepe(Node):
    name: str
    params: list
    body: list
    doc: Optional[str] = None


@dataclass
class Npc(Node):
    name: str
    params: list
    body: list


@dataclass
class Program(Node):
    pepes: dict      # name -> Pepe
    npcs: dict       # name -> Npc
    body: list       # top-level statements
