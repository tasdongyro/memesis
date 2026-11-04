"""memesis command line.

  memesis run script.meme [--pepe NAME] [--arg k=v ...] [--brain anthropic|openai|echo] [--no-human]
                          [--confirm] [--trace] [--json]
  memesis check script.meme
  memesis explain script.meme
  memesis prompt
  memesis tools
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .runtime import Runtime
from .values import plain


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="memesis", description="a meme language for agents")
    ap.add_argument("--version", action="version", version=f"memesis {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run a .meme script")
    r.add_argument("file")
    r.add_argument("--pepe", help="which pepe to run (default: the first one)")
    r.add_argument("--arg", action="append", default=[], metavar="k=v", help="argument for the pepe's parameters")
    r.add_argument("--brain", choices=["anthropic", "openai", "echo"], help="model for thonk")
    r.add_argument("--no-human", action="store_true", help="apu raises instead of asking on stdin")
    r.add_argument("--confirm", action="store_true", help="ask before every irreversible (yolo) call")
    r.add_argument("--trace", action="store_true", help="print every step with its line")
    r.add_argument("--json", action="store_true", help="print the result as JSON")
    r.add_argument("--quiet", action="store_true", help="no wow/doge output on the console")

    c = sub.add_parser("check", help="static checks, no execution")
    c.add_argument("file")
    c.add_argument("--json", action="store_true")

    e = sub.add_parser("explain", help="the script in plain English")
    e.add_argument("file")

    sub.add_parser("prompt", help="print the one-page language guide for a model's system prompt")
    sub.add_parser("tools", help="list built-in tools")

    a = ap.parse_args(argv)

    if a.cmd == "prompt":
        from .prompt import cheatsheet
        sys.stdout.write(cheatsheet())
        return 0

    if a.cmd == "tools":
        rt = Runtime()
        for t in sorted(rt.tools.values(), key=lambda t: (not t.irreversible, not t.sus, t.name)):
            print(t.summary())
        return 0

    src = Path(a.file).read_text(encoding="utf-8")

    if a.cmd == "check":
        from .check import check_source
        findings, summary = check_source(src)
        if a.json:
            print(json.dumps({"findings": [vars(f) for f in findings], "summary": summary}, indent=2))
        else:
            for f in findings:
                print(f)
            if summary:
                print(f"\n{len(summary['pepes'])} pepe(s), {len(summary['npcs'])} npc(s), "
                      f"{len(summary['irreversible'])} irreversible call(s), {len(summary['apu'])} human question(s), "
                      f"{len(summary['trustmebro'])} trustmebro site(s)")
                print(f"{summary['errors']} error(s), {summary['warnings']} warning(s)")
        return 1 if any(f.level == "error" for f in findings) else 0

    if a.cmd == "explain":
        from .explain import explain_source
        from .lexer import LexError
        from .parser import ParseError
        try:
            sys.stdout.write(explain_source(src))
        except (LexError, ParseError) as err:
            print(f"syntax: {err}", file=sys.stderr)
            return 1
        return 0

    # run
    rt = Runtime(trace=a.trace)
    rt.quiet = a.quiet
    if not a.no_human:
        rt.on_ask(lambda q, ctx: _ask(q))
    if a.confirm:
        rt.on_yolo(lambda ctx: _confirm(ctx))
    if a.brain:
        from .brains import BRAINS
        try:
            rt.on_think(BRAINS[a.brain]())
        except ImportError as err:
            print(f"--brain {a.brain}: {err} (pip install anthropic)", file=sys.stderr)
            return 2
    args = {}
    for kv in a.arg:
        if "=" not in kv:
            print(f"--arg needs k=v, got {kv!r}", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        args[k] = _coerce(v)
    res = rt.run(src, pepe=a.pepe, args=args, filename=a.file)
    if a.json:
        print(json.dumps({
            "ok": res.ok,
            "value": plain(res.value),
            "error": res.error.as_record() if res.error else None,
            "outputs": [{"value": o.value, "sus": o.sus, "sauce": list(o.sauce), "line": o.line} for o in res.outputs],
            "metrics": res.metrics,
            "yolos": res.yolos,
            "trustmebro": res.trusted,
            "log": res.log,
            "trace": res.trace,
        }, indent=2, ensure_ascii=False, default=str))
    else:
        if res.ok:
            if res.value is not None:
                from .interpreter import fmt
                print(f"feelsgood: {fmt(res.value)}", file=sys.stderr)
        else:
            print(f"feelsbad: {res.error}", file=sys.stderr)
        if res.metrics:
            print("stonks: " + ", ".join(f"{k}={v}" for k, v in res.metrics.items()), file=sys.stderr)
    return 0 if res.ok else 1


def _ask(q: str) -> str | None:
    try:
        return input(f"apu: {q}\n> ")
    except EOFError:
        return None


def _confirm(ctx) -> bool:
    args = ", ".join([repr(x) for x in ctx.args] + [f"{k}={v!r}" for k, v in ctx.kwargs.items()])
    try:
        ans = input(f"yolo {ctx.tool}({args[:200]}) ? [y/N] ")
    except EOFError:
        return False
    return ans.strip().lower() in ("y", "yes")


def _coerce(v: str):
    low = v.lower()
    if low in ("based", "true"):
        return True
    if low in ("cringe", "false"):
        return False
    if low in ("loss", "null", "none"):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    if v[:1] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            pass
    return v


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
