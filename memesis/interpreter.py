"""Tree-walking interpreter. One Interpreter per run; `fren` to a local pepe spawns a child."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from . import nodes as N
from .errors import (Cringe, FeelsBad, NotBased, SusError, YoloError, NoHuman, NoBrain, GrindCap, ToolError,
                     NameCringe, TypeCringe, Ngmi, _Bonk, _Nah, _FeelsGood)
from .values import (mark, clean, inherit, is_sus, deep_sus, deep_sauce, plain, describe)
from .runtime import Runtime, Ctx, Output, Result

BRAIN_RANK = {"smooth": 0, "default": 1, "big": 2, "galaxy": 3}


class Env:
    def __init__(self, parent: Optional["Env"] = None):
        self.vars: dict = {}
        self.parent = parent

    def lookup(self, name: str, line: int) -> Any:
        e = self
        while e is not None:
            if name in e.vars:
                return e.vars[name]
            e = e.parent
        raise NameCringe(f"unknown name '{name}' (declare it with: such {name} = ...)", line)

    def declare(self, name: str, value: Any):
        self.vars[name] = value

    def assign(self, name: str, value: Any):
        e = self
        while e is not None:
            if name in e.vars:
                e.vars[name] = value
                return
            e = e.parent
        self.vars[name] = value


def fmt(v: Any) -> str:
    """How values print inside strings and `wow`."""
    if v is None:
        return "loss"
    if isinstance(v, bool):
        return "based" if v else "cringe"
    if isinstance(v, str):
        return str(v)
    if isinstance(v, float):
        return repr(float(v)) if float(v) != int(v) else str(int(v))
    if isinstance(v, int):
        return str(int(v))
    if isinstance(v, (list, dict)):
        return json.dumps(plain(v), ensure_ascii=False, default=str)
    return str(v)


def truthy(v: Any) -> bool:
    return bool(v)


class Interpreter:
    def __init__(self, rt: Runtime, program: N.Program, filename: str = "<memesis>", parent: Optional["Interpreter"] = None,
                 result: Optional[Result] = None):
        self.rt = rt
        self.program = program
        self.filename = filename
        self.result = result or Result(ok=True)
        self.brains: list[str] = [rt.brain if parent is None else parent.brains[-1]]
        self.pepe_name: Optional[str] = None
        self.depth = 0 if parent is None else parent.depth + 1
        if self.depth > 32:
            raise Cringe("frens calling frens too deep (32 levels)")

    # ------------------------------------------------------------ entry
    def run(self, pepe: str | None, args: dict) -> Result:
        env = Env()
        try:
            try:
                value = None
                if self.program.body:
                    self.exec_block(self.program.body, env)
                if pepe is None and not self.program.body and self.program.pepes:
                    pepe = next(iter(self.program.pepes))
                if pepe is not None:
                    if pepe not in self.program.pepes:
                        raise NameCringe(f"no pepe named '{pepe}' in {self.filename}")
                    p = self.program.pepes[pepe]
                    bound = [args.get(name) for name in p.params]
                    value = self.call_pepe(p, bound)
            except _FeelsGood as fg:
                value = fg.value
            self.result.value = value
            self.result.ok = True
        except Cringe as e:
            self.result.ok = False
            self.result.error = e
        except (_Bonk, _Nah):
            self.result.ok = False
            self.result.error = Cringe("bonk/nah outside of a grind")
        return self.result

    def call_pepe(self, p: N.Pepe, args: list) -> Any:
        env = Env()
        for name, val in zip(p.params, args):
            env.declare(name, val)
        for name in p.params[len(args):]:
            env.declare(name, None)
        prev = self.pepe_name
        self.pepe_name = p.name
        self.trace(p.line, f"pepe {p.name} starts")
        try:
            self.exec_block(p.body, env)
        except _FeelsGood as fg:
            return fg.value
        finally:
            self.pepe_name = prev
        return None

    def call_npc(self, f: N.Npc, args: list, kwargs: dict, line: int) -> Any:
        env = Env()
        if len(args) > len(f.params):
            raise TypeCringe(f"npc {f.name} takes {len(f.params)} argument(s), got {len(args)}", line)
        for name, val in zip(f.params, args):
            env.declare(name, val)
        for name in f.params[len(args):]:
            env.declare(name, kwargs.pop(name, None))
        if kwargs:
            raise TypeCringe(f"npc {f.name} has no parameter {', '.join(kwargs)}", line)
        try:
            self.exec_block(f.body, env)
        except _FeelsGood as fg:
            return fg.value
        return None

    # ------------------------------------------------------------ statements
    def exec_block(self, stmts: list, env: Env):
        for s in stmts:
            self.exec(s, env)

    def exec(self, s: N.Node, env: Env):
        m = getattr(self, "s_" + type(s).__name__)
        m(s, env)

    def s_Such(self, s: N.Such, env: Env):
        v = self.eval(s.value, env)
        env.declare(s.name, v)
        self.trace(s.line, f"such {s.name} = {short(v)}")

    def s_Assign(self, s: N.Assign, env: Env):
        v = self.eval(s.value, env)
        t = s.target
        if isinstance(t, N.Name):
            env.assign(t.name, v)
        elif isinstance(t, N.Member):
            obj = self.eval(t.obj, env)
            if not isinstance(obj, dict):
                raise TypeCringe(f"cannot set .{t.name} on a {describe(obj)}", s.line)
            obj[t.name] = v
        elif isinstance(t, N.Index):
            obj = self.eval(t.obj, env)
            idx = self.eval(t.index, env)
            try:
                obj[idx] = v
            except (TypeError, IndexError, KeyError) as e:
                raise TypeCringe(f"cannot assign index {fmt(idx)}: {e}", s.line)
        self.trace(s.line, f"assign {short(v)}")

    def s_Wow(self, s: N.Wow, env: Env):
        v = self.eval(s.value, env)
        out = Output(value=plain(v), sus=deep_sus(v), sauce=deep_sauce(v), line=s.line)
        self.result.outputs.append(out)
        tag = "[sus] " if out.sus else ""
        self.rt.emit(f"{tag}{fmt(v)}")
        self.trace(s.line, f"wow {short(v)}")

    def s_Doge(self, s: N.Doge, env: Env):
        parts = [fmt(self.eval(e, env)) for e in s.values]
        line = " ".join(parts)
        self.result.log.append(line)
        self.rt.say(f"doge: {line}")

    def s_Tfw(self, s: N.Tfw, env: Env):
        if truthy(self.eval(s.cond, env)):
            self.trace(s.line, "tfw: yes")
            self.exec_block(s.body, env)
        elif s.otherwise is not None:
            self.trace(s.line, "tfw: no, pikachu")
            self.exec_block(s.otherwise, env)

    def s_Grind(self, s: N.Grind, env: Env):
        cap = self.eval(s.max, env) if s.max is not None else None
        if cap is not None and (not isinstance(cap, (int, float)) or isinstance(cap, bool)):
            raise TypeCringe("grind max must be a number", s.line)
        n = 0

        def body():
            nonlocal n
            n += 1
            try:
                self.exec_block(s.body, env)
            except _Nah:
                pass

        try:
            if s.kind == "count":
                count = self.eval(s.expr, env)
                if not isinstance(count, (int, float)) or isinstance(count, bool):
                    raise TypeCringe(f"grind <count> needs a number, got {describe(count)} (did you mean `grind x in list`?)", s.line)
                self.trace(s.line, f"grind {int(count)} times")
                for i in range(int(count)):
                    if cap is not None and n >= cap:
                        raise GrindCap(f"grind hit max {int(cap)}", s.line)
                    env.assign("it", i)
                    body()
            elif s.kind == "each":
                seq = self.eval(s.expr, env)
                if isinstance(seq, dict):
                    items = [inherit({"key": k, "value": v}, seq) for k, v in seq.items()]
                elif isinstance(seq, (list, str)):
                    items = [inherit(x, seq) if isinstance(seq, str) else x for x in seq]
                else:
                    raise TypeCringe(f"grind ... in needs a list, text or record, got {describe(seq)}", s.line)
                self.trace(s.line, f"grind {s.var} in {len(items)} items")
                for i, item in enumerate(items):
                    if cap is not None and n >= cap:
                        raise GrindCap(f"grind hit max {int(cap)}", s.line)
                    env.assign(s.var, item)
                    env.assign("it", i)
                    body()
            else:  # forever / until
                limit = int(cap) if cap is not None else self.rt.grind_max
                self.trace(s.line, f"grind {s.kind} (max {limit})")
                while True:
                    if s.kind == "until" and truthy(self.eval(s.expr, env)):
                        break
                    if n >= limit:
                        raise GrindCap(f"grind hit max {limit} without bonk" + (" (condition never became based)" if s.kind == "until" else ""), s.line)
                    env.assign("it", n)
                    body()
        except _Bonk:
            self.trace(s.line, "bonk")

    def s_Bonk(self, s: N.Bonk, env: Env):
        raise _Bonk()

    def s_Nah(self, s: N.Nah, env: Env):
        raise _Nah()

    def s_Chad(self, s: N.Chad, env: Env):
        try:
            self.trace(s.line, "chad")
            self.exec_block(s.body, env)
        except Cringe as e:
            if s.virgin is None:
                raise
            self.trace(s.line, f"virgin ({e.kind}: {e.message})")
            env.declare("L", inherit(e.as_record(), e.payload))
            self.exec_block(s.virgin, env)
        finally:
            if s.finally_ is not None:
                self.trace(s.line, "F")
                self.exec_block(s.finally_, env)

    def s_ThisIsFine(self, s: N.ThisIsFine, env: Env):
        try:
            self.exec_block(s.body, env)
        except Cringe as e:
            self.result.log.append(f"thisisfine swallowed {e}")
            self.rt.say(f"thisisfine: {e}")
            self.trace(s.line, f"thisisfine swallowed {e.kind}")

    def s_Based(self, s: N.Based, env: Env):
        v = self.eval(s.cond, env)
        if not truthy(v):
            msg = fmt(self.eval(s.message, env)) if s.message is not None else "assertion failed"
            raise NotBased(msg, s.line)
        self.trace(s.line, "based")

    def s_FeelsGood(self, s: N.FeelsGood, env: Env):
        v = self.eval(s.value, env) if s.value is not None else None
        self.trace(s.line, f"feelsgood {short(v)}")
        raise _FeelsGood(v)

    def s_FeelsBad(self, s: N.FeelsBad, env: Env):
        v = self.eval(s.value, env)
        self.trace(s.line, f"feelsbad {short(v)}")
        if isinstance(v, dict) and "message" in v:
            raise FeelsBad(fmt(v["message"]), s.line, payload=v)
        raise FeelsBad(fmt(v), s.line, payload=v if not isinstance(v, str) else None)

    def s_Brain(self, s: N.Brain, env: Env):
        self.brains.append(s.level)
        self.trace(s.line, f"{s.level}brain on")
        try:
            self.exec_block(s.body, env)
        finally:
            self.brains.pop()

    def s_TouchGrass(self, s: N.TouchGrass, env: Env):
        secs = self.eval(s.seconds, env)
        if not isinstance(secs, (int, float)) or isinstance(secs, bool) or secs < 0:
            raise TypeCringe("touchgrass needs a duration like 2s, 500ms or a number of seconds", s.line)
        self.trace(s.line, f"touchgrass {secs}s")
        self.rt.sleep(float(secs))

    def s_Stonks(self, s: N.Stonks, env: Env):
        name = fmt(self.eval(s.name, env))
        delta = self.eval(s.delta, env) if s.delta is not None else 1
        if not isinstance(delta, (int, float)) or isinstance(delta, bool):
            raise TypeCringe("stonks delta must be a number", s.line)
        self.result.metrics[name] = self.result.metrics.get(name, 0) + delta
        self.trace(s.line, f"stonks {name} {'+' if delta >= 0 else ''}{fmt(delta)}")

    def s_ExprStmt(self, s: N.ExprStmt, env: Env):
        self.eval(s.expr, env)

    # ------------------------------------------------------------ expressions
    def eval(self, e: N.Node, env: Env) -> Any:
        m = getattr(self, "e_" + type(e).__name__)
        return m(e, env)

    def e_Literal(self, e: N.Literal, env: Env):
        return e.value

    def e_Str(self, e: N.Str, env: Env):
        pieces, vals = [], []
        for p in e.parts:
            if isinstance(p, str):
                pieces.append(p)
            else:
                v = self.eval(p, env)
                vals.append(v)
                pieces.append(fmt(v))
        return inherit("".join(pieces), *vals)

    def e_Name(self, e: N.Name, env: Env):
        if e.name == "brain":
            return self.brains[-1]
        return env.lookup(e.name, e.line)

    def e_ListLit(self, e: N.ListLit, env: Env):
        return [self.eval(x, env) for x in e.items]

    def e_RecordLit(self, e: N.RecordLit, env: Env):
        return {k: self.eval(v, env) for k, v in e.pairs}

    def e_Unary(self, e: N.Unary, env: Env):
        v = self.eval(e.operand, env)
        if e.op == "not":
            return not truthy(v)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise TypeCringe(f"cannot negate a {describe(v)}", e.line)
        return inherit(-v, v)

    def e_Binary(self, e: N.Binary, env: Env):
        op = e.op
        if op == "and":
            l = self.eval(e.left, env)
            return truthy(l) and truthy(self.eval(e.right, env))
        if op == "or":
            l = self.eval(e.left, env)
            return truthy(l) or truthy(self.eval(e.right, env))
        l = self.eval(e.left, env)
        r = self.eval(e.right, env)
        try:
            if op == "+":
                if isinstance(l, str) or isinstance(r, str):
                    res = fmt(l) + fmt(r)
                elif isinstance(l, list) and isinstance(r, list):
                    res = list(l) + list(r)
                elif isinstance(l, dict) and isinstance(r, dict):
                    res = {**l, **r}
                else:
                    res = _num(l, e.line) + _num(r, e.line)
            elif op == "-":
                res = _num(l, e.line) - _num(r, e.line)
            elif op == "*":
                if isinstance(l, str) and isinstance(r, int):
                    res = str(l) * r
                else:
                    res = _num(l, e.line) * _num(r, e.line)
            elif op == "/":
                res = _num(l, e.line) / _num(r, e.line)
            elif op == "%":
                res = _num(l, e.line) % _num(r, e.line)
            elif op == "==":
                return plain(l) == plain(r)
            elif op == "!=":
                return plain(l) != plain(r)
            elif op == "<":
                return l < r
            elif op == "<=":
                return l <= r
            elif op == ">":
                return l > r
            elif op == ">=":
                return l >= r
            elif op == "in":
                if isinstance(r, dict):
                    return l in r
                if isinstance(r, str):
                    return fmt(l) in r
                if isinstance(r, list):
                    return plain(l) in plain(r)
                raise TypeCringe(f"'in' needs a list, text or record on the right, got {describe(r)}", e.line)
            else:  # pragma: no cover
                raise TypeCringe(f"unknown operator {op}", e.line)
        except ZeroDivisionError:
            raise TypeCringe("division by zero", e.line)
        except TypeError:
            raise TypeCringe(f"cannot apply {op} to {describe(l)} and {describe(r)}", e.line)
        return inherit(res, l, r)

    def e_Member(self, e: N.Member, env: Env):
        obj = self.eval(e.obj, env)
        if isinstance(obj, dict):
            if e.name in obj:
                return inherit(obj[e.name], obj)
            return None
        if isinstance(obj, (list, str)) and e.name == "length":
            return inherit(len(obj), obj)
        raise TypeCringe(f"a {describe(obj)} has no field .{e.name}", e.line)

    def e_Index(self, e: N.Index, env: Env):
        obj = self.eval(e.obj, env)
        idx = self.eval(e.index, env)
        try:
            if isinstance(obj, dict):
                return inherit(obj.get(idx), obj)
            if isinstance(obj, (list, str)):
                return inherit(obj[int(idx)], obj)
        except (IndexError, ValueError, TypeError):
            return None
        raise TypeCringe(f"cannot index a {describe(obj)}", e.line)

    def e_Copium(self, e: N.Copium, env: Env):
        try:
            v = self.eval(e.attempt, env)
        except Cringe as err:
            self.trace(e.line, f"copium ({err.kind})")
            return self.eval(e.fallback, env)
        if v is None:
            self.trace(e.line, "copium (loss)")
            return self.eval(e.fallback, env)
        return v

    def e_Sus(self, e: N.Sus, env: Env):
        v = self.eval(e.value, env)
        self.trace(e.line, "sus")
        return mark(v, sus=True, sauce=(f"sus@line{e.line}",) if not deep_sauce(v) else ())

    def e_Sauce(self, e: N.Sauce, env: Env):
        v = self.eval(e.value, env)
        return list(deep_sauce(v))

    def e_TrustMeBro(self, e: N.TrustMeBro, env: Env):
        v = self.eval(e.value, env)
        if deep_sus(v):
            self.result.trusted.append({"line": e.line, "sauce": list(deep_sauce(v)), "pepe": self.pepe_name})
            self.rt.say(f"trustmebro: line {e.line} vouched for {', '.join(deep_sauce(v)) or 'a sus value'}")
            self.trace(e.line, "trustmebro")
        return clean(v)

    def e_Apu(self, e: N.Apu, env: Env):
        q = fmt(self.eval(e.question, env))
        if self.rt.ask_hook is None:
            raise NoHuman(f"apu asked '{q}' but no human is attached (use copium for a default)", e.line)
        self.trace(e.line, f"apu {q!r}")
        ans = self.rt.ask_hook(q, self.ctx(e.line))
        if ans is None:
            raise NoHuman(f"the human did not answer '{q}'", e.line)
        return mark(ans, sus=False, sauce=("apu",))

    def e_Thonk(self, e: N.Thonk, env: Env):
        p = self.eval(e.prompt, env)
        if self.rt.think_hook is None:
            raise NoBrain("thonk needs a model: attach one with Runtime.on_think or run with --brain", e.line)
        ctx = self.ctx(e.line, sus=deep_sus(p), sauce=deep_sauce(p))
        self.trace(e.line, f"thonk ({self.brains[-1]}brain{', sus input' if ctx.sus else ''})")
        try:
            out = self.rt.think_hook(fmt(p), ctx)
        except Cringe:
            raise
        except Exception as ex:
            raise NoBrain(f"the model failed: {ex}", e.line)
        return mark(inherit(out, p), sauce=(f"thonk:{self.brains[-1]}",))

    def e_Fren(self, e: N.Fren, env: Env):
        msg = self.eval(e.message, env)
        ctx = self.ctx(e.line, sus=deep_sus(msg), sauce=deep_sauce(msg))
        self.trace(e.line, f"fren {e.target} {short(msg)}")
        if e.target in self.program.pepes:
            child = Interpreter(self.rt, self.program, self.filename, parent=self, result=self.result)
            p = self.program.pepes[e.target]
            if isinstance(msg, dict) and len(p.params) > 1:
                args = [msg.get(k) for k in p.params]
            else:
                args = [msg]
            out = child.call_pepe(p, args)
        elif e.target in self.rt.frens:
            try:
                out = self.rt.frens[e.target](plain(msg), ctx)
            except Cringe:
                raise
            except Exception as ex:
                raise ToolError(f"fren {e.target} failed: {ex}", e.line)
        else:
            known = ", ".join(sorted(list(self.program.pepes) + list(self.rt.frens))) or "none"
            raise NameCringe(f"no fren named '{e.target}' (known: {known})", e.line)
        return mark(inherit(out, msg), sauce=(f"fren:{e.target}",))

    def e_BrainExpr(self, e: N.BrainExpr, env: Env):
        self.brains.append(e.level)
        try:
            return self.eval(e.expr, env)
        finally:
            self.brains.pop()

    def e_Wagmi(self, e: N.Wagmi, env: Env):
        def one(entry):
            key, node = entry
            try:
                return key, self.eval(node, env), None
            except Cringe as err:
                return key, None, err

        self.trace(e.line, f"wagmi {len(e.entries)} tasks")
        with ThreadPoolExecutor(max_workers=max(1, min(self.rt.wagmi_workers, len(e.entries) or 1))) as pool:
            done = list(pool.map(one, e.entries))
        failed = {(k if k is not None else i): err for i, (k, _, err) in enumerate(done) if err is not None}
        if failed:
            names = ", ".join(f"{k}: {err.kind}: {err.message}" for k, err in failed.items())
            raise Ngmi(f"wagmi failed for {names}", e.line, payload={str(k): err.as_record() for k, err in failed.items()})
        if e.as_record:
            return {k: v for k, v, _ in done}
        return [v for _, v, _ in done]

    def e_Call(self, e: N.Call, env: Env):
        args = [self.eval(a, env) for a in e.args]
        kwargs = {k: self.eval(v, env) for k, v in e.kwargs}
        if e.callee in self.program.npcs:
            if e.yolo:
                raise YoloError(f"yolo applies to tools, not to npc {e.callee}", e.line)
            self.trace(e.line, f"npc {e.callee}({', '.join(short(a) for a in args)})")
            return self.call_npc(self.program.npcs[e.callee], args, kwargs, e.line)
        tool = self.rt.tools.get(e.callee)
        if tool is None:
            raise NameCringe(f"no tool or npc named '{e.callee}'", e.line)
        if tool.irreversible:
            if not e.yolo:
                raise YoloError(f"{tool.name} is irreversible: write `yolo {tool.name}(...)` to run it", e.line)
            if deep_sus(args) or deep_sus(kwargs):
                src = ", ".join(deep_sauce(args) + deep_sauce(kwargs)) or "unknown"
                raise SusError(f"a sus value (from {src}) reached {tool.name}; review it and wrap it in trustmebro", e.line)
            ctx = self.ctx(e.line, tool=tool.name, args=tuple(plain(a) for a in args), kwargs=plain(kwargs))
            if self.rt.yolo_hook is not None and not self.rt.yolo_hook(ctx):
                raise YoloError(f"{tool.name} was vetoed", e.line)
            self.result.yolos.append({"line": e.line, "tool": tool.name, "args": list(ctx.args), "kwargs": ctx.kwargs, "pepe": self.pepe_name})
        self.trace(e.line, f"{'yolo ' if e.yolo else ''}{tool.name}({', '.join(short(a) for a in args)})")
        try:
            out = tool.fn(*[plain(a) for a in args], **{k: plain(v) for k, v in kwargs.items()})
        except Cringe:
            raise
        except Exception as ex:
            raise ToolError(f"{tool.name} failed: {type(ex).__name__}: {ex}", e.line)
        if tool.sus:
            head = fmt(args[0]) if args else ""
            label = f"{tool.name}:{head[:120]}" if head else tool.name
            return mark(inherit(out, *args, *kwargs.values()), sus=True, sauce=(label,))
        return inherit(out, *args, *kwargs.values())

    # ------------------------------------------------------------ misc
    def ctx(self, line: int, **kw) -> Ctx:
        return Ctx(runtime=self.rt, brain=self.brains[-1], line=line, pepe=self.pepe_name, **kw)

    def trace(self, line: int, text: str):
        if self.rt.trace_enabled:
            entry = (line, ("  " * self.depth) + text)
            self.result.trace.append(entry)
            self.rt.say(f"  {line:>4} | {entry[1]}")


def _num(v: Any, line: int):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeCringe(f"expected a number, got {describe(v)}", line)
    return v


def short(v: Any, n: int = 60) -> str:
    s = fmt(v)
    s = s.replace("\n", " ")
    if len(s) > n:
        s = s[: n - 1] + "…"
    if is_sus(v) or deep_sus(v):
        s += " [sus]"
    return s
