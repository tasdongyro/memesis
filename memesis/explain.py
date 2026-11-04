"""`memesis explain script.meme`: the script as plain English, one line per statement.

Meant for review: a human (or a second agent) reads what the script will do, where it asks,
where it acts irreversibly and where it vouches for untrusted data, without reading Memesis.
"""
from __future__ import annotations

from . import nodes as N
from .parser import parse
from .runtime import Runtime


def explain_source(src: str, rt: Runtime | None = None) -> str:
    rt = rt or Runtime()
    prog = parse(src)
    out: list[str] = []
    for p in prog.pepes.values():
        head = f"agent {p.name}" + (f" ({', '.join(p.params)})" if p.params else "")
        out.append(head + (f": {p.doc}" if p.doc else ""))
        out.extend(_block(p.body, 1, rt, prog))
        out.append("")
    for f in prog.npcs.values():
        out.append(f"routine {f.name}({', '.join(f.params)}) (scripted, no model involved)")
        out.extend(_block(f.body, 1, rt, prog))
        out.append("")
    if prog.body:
        out.append("script")
        out.extend(_block(prog.body, 1, rt, prog))
    return "\n".join(out).rstrip() + "\n"


def _block(stmts: list, depth: int, rt, prog) -> list[str]:
    lines: list[str] = []
    for s in stmts:
        lines.extend(_stmt(s, depth, rt, prog))
    return lines


def _ind(depth: int, text: str, line: int) -> str:
    return f"{line:>4}  " + "  " * depth + text


def _stmt(s: N.Node, d: int, rt, prog) -> list[str]:
    t = type(s).__name__
    L = s.line
    if t == "Such":
        return [_ind(d, f"let {s.name} = {ex(s.value, rt, prog)}", L)]
    if t == "Assign":
        return [_ind(d, f"set {ex(s.target, rt, prog)} = {ex(s.value, rt, prog)}", L)]
    if t == "Wow":
        return [_ind(d, f"output {ex(s.value, rt, prog)}", L)]
    if t == "Doge":
        return [_ind(d, "log " + ", ".join(ex(v, rt, prog) for v in s.values), L)]
    if t == "Tfw":
        out = [_ind(d, f"if {ex(s.cond, rt, prog)}:", L)] + _block(s.body, d + 1, rt, prog)
        if s.otherwise:
            if len(s.otherwise) == 1 and isinstance(s.otherwise[0], N.Tfw):
                sub = _stmt(s.otherwise[0], d, rt, prog)
                sub[0] = sub[0].replace("if ", "else if ", 1)
                out += sub
            else:
                out += [_ind(d, "else:", L)] + _block(s.otherwise, d + 1, rt, prog)
        return out
    if t == "Grind":
        if s.kind == "count":
            head = f"repeat {ex(s.expr, rt, prog)} times"
        elif s.kind == "each":
            head = f"for each {s.var} in {ex(s.expr, rt, prog)}"
        elif s.kind == "until":
            head = f"repeat until {ex(s.expr, rt, prog)}"
        else:
            head = "repeat forever"
        if s.max is not None:
            head += f" (at most {ex(s.max, rt, prog)} rounds)"
        elif s.kind in ("forever", "until"):
            head += f" (runtime cap {rt.grind_max})"
        return [_ind(d, head + ":", L)] + _block(s.body, d + 1, rt, prog)
    if t == "Bonk":
        return [_ind(d, "stop the loop", L)]
    if t == "Nah":
        return [_ind(d, "skip to the next round", L)]
    if t == "Chad":
        out = [_ind(d, "try:", L)] + _block(s.body, d + 1, rt, prog)
        if s.virgin is not None:
            out += [_ind(d, "if that fails (error in L):", L)] + _block(s.virgin, d + 1, rt, prog)
        if s.finally_ is not None:
            out += [_ind(d, "finally, always:", L)] + _block(s.finally_, d + 1, rt, prog)
        return out
    if t == "ThisIsFine":
        return [_ind(d, "errors in the next block are logged and ignored:", L)] + _block(s.body, d + 1, rt, prog)
    if t == "Based":
        msg = f" else fail with {ex(s.message, rt, prog)}" if s.message is not None else ""
        return [_ind(d, f"assert {ex(s.cond, rt, prog)}{msg}", L)]
    if t == "FeelsGood":
        return [_ind(d, "done" + (f", result {ex(s.value, rt, prog)}" if s.value is not None else ""), L)]
    if t == "FeelsBad":
        return [_ind(d, f"FAIL with {ex(s.value, rt, prog)}", L)]
    if t == "Brain":
        return [_ind(d, f"with {s.level} brain (model effort):", L)] + _block(s.body, d + 1, rt, prog)
    if t == "TouchGrass":
        return [_ind(d, f"wait {ex(s.seconds, rt, prog)} seconds", L)]
    if t == "Stonks":
        delta = ex(s.delta, rt, prog) if s.delta is not None else "1"
        return [_ind(d, f"metric {ex(s.name, rt, prog)} += {delta}", L)]
    if t == "ExprStmt":
        return [_ind(d, ex(s.expr, rt, prog), L)]
    return [_ind(d, f"({t})", L)]


def ex(e: N.Node, rt, prog) -> str:
    t = type(e).__name__
    if t == "Literal":
        v = e.value
        if v is None:
            return "nothing"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            v = v.replace("\n", "\\n")
            return repr(v) if len(v) <= 60 else repr(v[:57] + "...")
        return str(v)
    if t == "Str":
        return '"' + "".join(p.replace("\n", "\\n") if isinstance(p, str) else "{" + ex(p, rt, prog) + "}" for p in e.parts)[:70] + '"'
    if t == "Name":
        return e.name
    if t == "ListLit":
        return "[" + ", ".join(ex(x, rt, prog) for x in e.items) + "]"
    if t == "RecordLit":
        return "{" + ", ".join(f"{k}: {ex(v, rt, prog)}" for k, v in e.pairs) + "}"
    if t == "Unary":
        return f"{e.op} {ex(e.operand, rt, prog)}" if e.op == "not" else f"-{ex(e.operand, rt, prog)}"
    if t == "Binary":
        return f"{ex(e.left, rt, prog)} {e.op} {ex(e.right, rt, prog)}"
    if t == "Member":
        return f"{ex(e.obj, rt, prog)}.{e.name}"
    if t == "Index":
        return f"{ex(e.obj, rt, prog)}[{ex(e.index, rt, prog)}]"
    if t == "Copium":
        return f"{ex(e.attempt, rt, prog)} (on failure or nothing: {ex(e.fallback, rt, prog)})"
    if t == "Sus":
        return f"UNTRUSTED {ex(e.value, rt, prog)}"
    if t == "Sauce":
        return f"sources of {ex(e.value, rt, prog)}"
    if t == "TrustMeBro":
        return f"VOUCH FOR {ex(e.value, rt, prog)} (strips the untrusted mark)"
    if t == "Apu":
        return f"ASK A HUMAN {ex(e.question, rt, prog)}"
    if t == "Thonk":
        return f"ask the model {ex(e.prompt, rt, prog)}"
    if t == "BrainExpr":
        return f"with {e.level} brain: {ex(e.expr, rt, prog)}"
    if t == "Fren":
        kind = "agent in this file" if e.target in prog.pepes else "registered agent"
        return f"delegate to {e.target} ({kind}): {ex(e.message, rt, prog)}"
    if t == "Wagmi":
        inner = ", ".join((f"{k}: " if k else "") + ex(v, rt, prog) for k, v in e.entries)
        return f"in parallel, all must succeed: {inner}"
    if t == "Call":
        args = ", ".join([ex(a, rt, prog) for a in e.args] + [f"{k}: {ex(v, rt, prog)}" for k, v in e.kwargs])
        tool = rt.tools.get(e.callee)
        tag = ""
        if e.callee in prog.npcs:
            tag = " (routine)"
        elif tool is None:
            tag = " (UNKNOWN TOOL)"
        else:
            bits = []
            if tool.irreversible:
                bits.append("IRREVERSIBLE" + (", yolo" if e.yolo else ", MISSING yolo"))
            if tool.sus:
                bits.append("untrusted output")
            tag = f" ({'; '.join(bits)})" if bits else ""
        return f"{e.callee}({args}){tag}"
    return f"({t})"
