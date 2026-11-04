"""The Runtime: tools, frens, hooks and the result of a run.

    from memesis import Runtime

    rt = Runtime()

    @rt.tool(sus=True)                 # output is untrusted (web, shell, mail ...)
    def search(q): ...

    @rt.tool(irreversible=True)        # needs `yolo` in the script, refuses sus input
    def send_mail(to, body): ...

    rt.on_ask(lambda q, ctx: input(q))             # apu
    rt.on_think(lambda prompt, ctx: my_llm(prompt)) # thonk
    rt.fren("scout", lambda msg, ctx: other_agent(msg))

    result = rt.run_file("plan.meme", args={"topic": "frogs"})
    result.value, result.outputs, result.metrics, result.trace
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .errors import Cringe
from . import stdlib


@dataclass
class Tool:
    name: str
    fn: Callable
    sus: bool = False            # the tool's output is untrusted data
    irreversible: bool = False   # the tool changes the world; needs `yolo`, refuses sus input
    doc: str = ""
    builtin: bool = False

    def summary(self) -> str:
        tags = []
        if self.irreversible:
            tags.append("irreversible")
        if self.sus:
            tags.append("sus output")
        t = f" [{', '.join(tags)}]" if tags else ""
        return f"{self.name}{t}: {self.doc}".rstrip(": ")


@dataclass
class Ctx:
    """What hooks (ask / think / fren / yolo) get to see."""
    runtime: "Runtime"
    brain: str
    line: int
    sus: bool = False
    sauce: tuple = ()
    pepe: Optional[str] = None
    tool: Optional[str] = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)


@dataclass
class Output:
    value: Any
    sus: bool
    sauce: tuple
    line: int


@dataclass
class Result:
    ok: bool
    value: Any = None
    error: Optional[Cringe] = None
    outputs: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    trace: list = field(default_factory=list)
    yolos: list = field(default_factory=list)      # irreversible calls that ran
    trusted: list = field(default_factory=list)    # trustmebro sites that ran

    def __bool__(self) -> bool:
        return self.ok


class Runtime:
    def __init__(self, *, brain: str = "default", trace: bool = False, stdout=None, stderr=None,
                 include_stdlib: bool = True, grind_max: int = 1000, wagmi_workers: int = 8):
        self.tools: dict[str, Tool] = {}
        self.frens: dict[str, Callable] = {}
        self.ask_hook: Optional[Callable] = None
        self.think_hook: Optional[Callable] = None
        self.yolo_hook: Optional[Callable] = None       # (ctx) -> bool, may veto an irreversible call
        self.brain = brain
        self.trace_enabled = trace
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.grind_max = grind_max
        self.wagmi_workers = wagmi_workers
        self.sleep: Callable[[float], None] = time.sleep
        self.quiet = False
        if include_stdlib:
            stdlib.install(self)

    # ------------------------------------------------------------ registration
    def tool(self, fn: Callable | None = None, *, name: str | None = None, sus: bool = False,
             irreversible: bool = False, doc: str | None = None, builtin: bool = False):
        def deco(f: Callable):
            n = name or f.__name__
            self.tools[n] = Tool(n, f, sus=sus, irreversible=irreversible,
                                 doc=(doc if doc is not None else (f.__doc__ or "").strip().splitlines()[0] if (f.__doc__ or "").strip() else ""),
                                 builtin=builtin)
            return f
        return deco(fn) if fn is not None else deco

    def fren(self, name: str, fn: Callable | None = None):
        """Register another agent. fn(message, ctx) -> value. Usable as a decorator."""
        def deco(f: Callable):
            self.frens[name] = f
            return f
        return deco(fn) if fn is not None else deco

    def on_ask(self, fn: Callable):
        """fn(question: str, ctx) -> str. Used by `apu`."""
        self.ask_hook = fn
        return fn

    def on_think(self, fn: Callable):
        """fn(prompt: str, ctx) -> str. Used by `thonk`. ctx.brain is smooth|default|big|galaxy."""
        self.think_hook = fn
        return fn

    def on_yolo(self, fn: Callable):
        """fn(ctx) -> bool. Called before every irreversible tool call; return False to veto."""
        self.yolo_hook = fn
        return fn

    # ------------------------------------------------------------ running
    def run(self, src: str, *, pepe: str | None = None, args: dict | None = None, filename: str = "<memesis>") -> Result:
        from .interpreter import Interpreter
        from .parser import parse
        from .lexer import LexError
        from .parser import ParseError
        try:
            program = parse(src)
        except (LexError, ParseError) as e:
            err = Cringe(str(e), getattr(e, "line", 0))
            err.kind = "syntax"
            return Result(ok=False, error=err)
        interp = Interpreter(self, program, filename=filename)
        return interp.run(pepe=pepe, args=args or {})

    def run_file(self, path: str | Path, **kw) -> Result:
        p = Path(path)
        return self.run(p.read_text(encoding="utf-8"), filename=str(p), **kw)

    # ------------------------------------------------------------ output
    def emit(self, text: str):
        if not self.quiet:
            print(text, file=self.stdout)

    def say(self, text: str):
        if not self.quiet:
            print(text, file=self.stderr)
