"""Static checks: `memesis check script.meme`.

Reports, without running anything:
  error  irreversible tool called without yolo
  error  unknown tool / npc / fren / name
  warn   a value that comes from a sus source flows into an irreversible tool without trustmebro
  warn   yolo on a tool that is not irreversible
  info   grind forever/until without max (runtime cap applies), apu questions, trustmebro sites
"""
from __future__ import annotations

from dataclasses import dataclass

from . import nodes as N
from .lexer import LexError
from .parser import parse, ParseError
from .runtime import Runtime


@dataclass
class Finding:
    level: str   # error | warn | info
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.level:<5} line {self.line:>3}  {self.message}"


class Checker:
    def __init__(self, rt: Runtime, program: N.Program):
        self.rt = rt
        self.prog = program
        self.findings: list[Finding] = []
        self.sus_vars: set[str] = set()   # names that (may) hold sus data in the current scope
        self.trusted: list[int] = []
        self.apus: list[tuple[int, str]] = []
        self.yolos: list[tuple[int, str]] = []

    def add(self, level: str, line: int, msg: str):
        self.findings.append(Finding(level, line, msg))

    # ------------------------------------------------------------ walk
    def run(self) -> list[Finding]:
        for p in self.prog.pepes.values():
            self.sus_vars = set()
            self.block(p.body, set(p.params))
        for f in self.prog.npcs.values():
            self.sus_vars = set()
            self.block(f.body, set(f.params))
        self.sus_vars = set()
        self.block(self.prog.body, set())
        self.findings.sort(key=lambda f: (f.line, f.level))
        return self.findings

    def block(self, stmts: list, names: set):
        for s in stmts:
            self.stmt(s, names)

    def stmt(self, s: N.Node, names: set):
        t = type(s).__name__
        if t == "Such":
            self.expr(s.value, names)
            names.add(s.name)
            if self.is_sus(s.value, names):
                self.sus_vars.add(s.name)
            else:
                self.sus_vars.discard(s.name)
        elif t == "Assign":
            self.expr(s.value, names)
            if isinstance(s.target, N.Name):
                names.add(s.target.name)
                if self.is_sus(s.value, names):
                    self.sus_vars.add(s.target.name)
                else:
                    self.sus_vars.discard(s.target.name)
            else:
                self.expr(s.target, names)
        elif t in ("Wow", "FeelsBad", "TouchGrass"):
            self.expr(getattr(s, "value", None) or getattr(s, "seconds"), names)
        elif t == "FeelsGood":
            if s.value is not None:
                self.expr(s.value, names)
        elif t == "Doge":
            for v in s.values:
                self.expr(v, names)
        elif t == "Tfw":
            self.expr(s.cond, names)
            self.block(s.body, names)
            if s.otherwise:
                self.block(s.otherwise, names)
        elif t == "Grind":
            if s.expr is not None:
                self.expr(s.expr, names)
            if s.max is not None:
                self.expr(s.max, names)
            if s.kind in ("forever", "until") and s.max is None:
                self.add("info", s.line, f"grind {s.kind} without max: the runtime stops it after {self.rt.grind_max} rounds")
            names.add("it")
            if s.var:
                names.add(s.var)
                if self.is_sus(s.expr, names):
                    self.sus_vars.add(s.var)
            self.block(s.body, names)
        elif t == "Chad":
            self.block(s.body, names)
            if s.virgin is not None:
                self.block(s.virgin, names | {"L"})
            if s.finally_ is not None:
                self.block(s.finally_, names)
        elif t in ("ThisIsFine", "Brain"):
            self.block(s.body, names)
        elif t == "Based":
            self.expr(s.cond, names)
            if s.message is not None:
                self.expr(s.message, names)
        elif t == "Stonks":
            self.expr(s.name, names)
            if s.delta is not None:
                self.expr(s.delta, names)
        elif t == "ExprStmt":
            self.expr(s.expr, names)

    def expr(self, e: N.Node, names: set):
        t = type(e).__name__
        if t == "Name":
            if e.name not in names and e.name != "brain":
                self.add("error", e.line, f"unknown name '{e.name}'")
        elif t == "Str":
            for p in e.parts:
                if not isinstance(p, str):
                    self.expr(p, names)
        elif t == "ListLit":
            for x in e.items:
                self.expr(x, names)
        elif t == "RecordLit":
            for _, v in e.pairs:
                self.expr(v, names)
        elif t == "Unary":
            self.expr(e.operand, names)
        elif t == "Binary":
            self.expr(e.left, names); self.expr(e.right, names)
        elif t == "Member":
            self.expr(e.obj, names)
        elif t == "Index":
            self.expr(e.obj, names); self.expr(e.index, names)
        elif t == "Copium":
            self.expr(e.attempt, names); self.expr(e.fallback, names)
        elif t in ("Sus", "Sauce"):
            self.expr(e.value, names)
        elif t == "TrustMeBro":
            self.expr(e.value, names)
            self.trusted.append(e.line)
        elif t == "Apu":
            self.expr(e.question, names)
            q = e.question.value if isinstance(e.question, N.Literal) else "(dynamic question)"
            self.apus.append((e.line, str(q)))
        elif t == "Thonk":
            self.expr(e.prompt, names)
        elif t == "BrainExpr":
            self.expr(e.expr, names)
        elif t == "Fren":
            self.expr(e.message, names)
            if e.target not in self.prog.pepes and e.target not in self.rt.frens:
                self.add("error", e.line, f"unknown fren '{e.target}' (not a pepe in this file and not registered in the runtime)")
        elif t == "Wagmi":
            for _, v in e.entries:
                self.expr(v, names)
        elif t == "Call":
            for a in e.args:
                self.expr(a, names)
            for _, v in e.kwargs:
                self.expr(v, names)
            self.call(e, names)

    def call(self, e: N.Call, names: set):
        if e.callee in self.prog.npcs:
            if e.yolo:
                self.add("warn", e.line, f"yolo on npc {e.callee} does nothing")
            return
        tool = self.rt.tools.get(e.callee)
        if tool is None:
            self.add("error", e.line, f"unknown tool '{e.callee}'")
            return
        if tool.irreversible and not e.yolo:
            self.add("error", e.line, f"{tool.name} is irreversible and needs yolo: yolo {tool.name}(...)")
        if e.yolo and not tool.irreversible:
            self.add("warn", e.line, f"yolo on {tool.name} is not needed (not irreversible)")
        if tool.irreversible:
            self.yolos.append((e.line, tool.name))
            for a in list(e.args) + [v for _, v in e.kwargs]:
                if self.is_sus(a, names):
                    self.add("warn", e.line, f"a sus value flows into {tool.name}; the runtime will refuse it unless you trustmebro it")
                    break

    # ------------------------------------------------------------ taint guess
    def is_sus(self, e: N.Node | None, names: set) -> bool:
        if e is None:
            return False
        t = type(e).__name__
        if t == "Name":
            return e.name in self.sus_vars
        if t == "Sus":
            return True
        if t == "TrustMeBro":
            return False
        if t == "Call":
            tool = self.rt.tools.get(e.callee)
            if tool is not None and tool.sus:
                return True
            return any(self.is_sus(a, names) for a in e.args) or any(self.is_sus(v, names) for _, v in e.kwargs)
        if t == "Str":
            return any(self.is_sus(p, names) for p in e.parts if not isinstance(p, str))
        if t == "Binary":
            return self.is_sus(e.left, names) or self.is_sus(e.right, names)
        if t in ("Member", "Index"):
            return self.is_sus(e.obj, names)
        if t == "Copium":
            return self.is_sus(e.attempt, names) or self.is_sus(e.fallback, names)
        if t == "Thonk":
            return self.is_sus(e.prompt, names)
        if t == "BrainExpr":
            return self.is_sus(e.expr, names)
        if t == "Fren":
            return self.is_sus(e.message, names)
        if t == "ListLit":
            return any(self.is_sus(x, names) for x in e.items)
        if t == "RecordLit":
            return any(self.is_sus(v, names) for _, v in e.pairs)
        if t == "Wagmi":
            return any(self.is_sus(v, names) for _, v in e.entries)
        return False


def check_source(src: str, rt: Runtime | None = None) -> tuple[list[Finding], dict]:
    rt = rt or Runtime()
    try:
        prog = parse(src)
    except (LexError, ParseError) as e:
        return [Finding("error", getattr(e, "line", 0), f"syntax: {e}")], {}
    c = Checker(rt, prog)
    findings = c.run()
    summary = {
        "pepes": list(prog.pepes), "npcs": list(prog.npcs),
        "irreversible": c.yolos, "apu": c.apus, "trustmebro": c.trusted,
        "errors": sum(f.level == "error" for f in findings),
        "warnings": sum(f.level == "warn" for f in findings),
    }
    return findings, summary
