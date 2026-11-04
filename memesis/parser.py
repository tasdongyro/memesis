"""Recursive-descent parser: tokens -> Program."""
from __future__ import annotations

from . import nodes as N
from .lexer import Token, tokenize, LexError


class ParseError(Exception):
    def __init__(self, message: str, line: int):
        super().__init__(f"line {line}: {message}")
        self.line = line


BRAINS = {"smoothbrain": "smooth", "bigbrain": "big", "galaxybrain": "galaxy"}
COMPARE = {"==", "!=", "<", "<=", ">", ">="}


def parse(src: str) -> N.Program:
    return Parser(tokenize(src)).program()


class Parser:
    def __init__(self, toks: list[Token]):
        self.toks = toks
        self.i = 0

    # ------------------------------------------------------------ helpers
    @property
    def cur(self) -> Token:
        return self.toks[self.i]

    def peek(self, k: int = 1) -> Token:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def at(self, kind: str, value=None) -> bool:
        t = self.cur
        return t.kind == kind and (value is None or t.value == value)

    def at_kw(self, *words: str) -> bool:
        return self.cur.kind == "KEYWORD" and self.cur.value in words

    def at_op(self, *ops: str) -> bool:
        return self.cur.kind == "OP" and self.cur.value in ops

    def advance(self) -> Token:
        t = self.cur
        if t.kind != "EOF":
            self.i += 1
        return t

    def expect_op(self, op: str) -> Token:
        if not self.at_op(op):
            raise ParseError(f"expected {op!r}, got {self._desc()}", self.cur.line)
        return self.advance()

    def expect_kw(self, word: str) -> Token:
        if not self.at_kw(word):
            raise ParseError(f"expected '{word}', got {self._desc()}", self.cur.line)
        return self.advance()

    def expect_ident(self) -> str:
        if self.cur.kind == "IDENT":
            return self.advance().value
        if self.cur.kind == "KEYWORD":
            raise ParseError(f"'{self.cur.value}' is a keyword and cannot be used as a name", self.cur.line)
        raise ParseError(f"expected a name, got {self._desc()}", self.cur.line)

    def _desc(self) -> str:
        t = self.cur
        if t.kind == "NEWLINE":
            return "end of line"
        if t.kind == "EOF":
            return "end of file"
        return repr(t.value)

    def skip_newlines(self):
        while self.at("NEWLINE"):
            self.advance()

    def end_statement(self):
        if self.at("NEWLINE"):
            self.advance()
        elif self.at("EOF") or self.at_op("}"):
            return
        else:
            raise ParseError(f"unexpected {self._desc()} after statement", self.cur.line)

    # ------------------------------------------------------------ program
    def program(self) -> N.Program:
        prog = N.Program(pepes={}, npcs={}, body=[], line=1)
        self.skip_newlines()
        while not self.at("EOF"):
            if self.at_kw("pepe"):
                p = self.pepe()
                if p.name in prog.pepes:
                    raise ParseError(f"pepe '{p.name}' defined twice", p.line)
                prog.pepes[p.name] = p
            elif self.at_kw("npc"):
                f = self.npc()
                if f.name in prog.npcs:
                    raise ParseError(f"npc '{f.name}' defined twice", f.line)
                prog.npcs[f.name] = f
            else:
                prog.body.append(self.statement())
            self.skip_newlines()
        return prog

    def params(self) -> list[str]:
        if not self.at_op("("):
            return []
        self.advance()
        names = []
        while not self.at_op(")"):
            names.append(self.expect_ident())
            if self.at_op(","):
                self.advance()
        self.expect_op(")")
        return names

    def pepe(self) -> N.Pepe:
        line = self.expect_kw("pepe").line
        name = self.expect_ident()
        params = self.params()
        doc = None
        if self.at("STRING"):
            parts = self.advance().value
            if len(parts) == 1 and isinstance(parts[0], str):
                doc = parts[0]
            else:
                raise ParseError("a pepe description must be a plain string", line)
        body = self.block()
        return N.Pepe(name=name, params=params, body=body, doc=doc, line=line)

    def npc(self) -> N.Npc:
        line = self.expect_kw("npc").line
        name = self.expect_ident()
        params = self.params()
        body = self.block()
        return N.Npc(name=name, params=params, body=body, line=line)

    def block(self) -> list:
        self.expect_op("{")
        stmts = []
        self.skip_newlines()
        while not self.at_op("}"):
            if self.at("EOF"):
                raise ParseError("unclosed block, expected '}'", self.cur.line)
            if self.at_kw("pepe", "npc"):
                raise ParseError("pepe and npc can only be defined at the top level", self.cur.line)
            stmts.append(self.statement())
            self.skip_newlines()
        self.expect_op("}")
        return stmts

    # ------------------------------------------------------------ statements
    def statement(self) -> N.Node:
        t = self.cur
        line = t.line
        if t.kind == "KEYWORD":
            w = t.value
            if w == "such":
                self.advance()
                name = self.expect_ident()
                self.expect_op("=")
                value = self.expression()
                self.end_statement()
                return N.Such(name=name, value=value, line=line)
            if w == "wow":
                self.advance()
                value = self.expression()
                self.end_statement()
                return N.Wow(value=value, line=line)
            if w == "doge":
                self.advance()
                values = [self.expression()]
                while self.at_op(","):
                    self.advance()
                    values.append(self.expression())
                self.end_statement()
                return N.Doge(values=values, line=line)
            if w == "tfw":
                return self.tfw()
            if w == "grind":
                return self.grind()
            if w == "bonk":
                self.advance(); self.end_statement()
                return N.Bonk(line=line)
            if w == "nah":
                self.advance(); self.end_statement()
                return N.Nah(line=line)
            if w == "chad":
                self.advance()
                body = self.block()
                virgin = finally_ = None
                self.skip_newlines_if_followed_by("virgin", "F")
                if self.at_kw("virgin"):
                    self.advance()
                    virgin = self.block()
                    self.skip_newlines_if_followed_by("F")
                if self.at_kw("F"):
                    self.advance()
                    finally_ = self.block()
                self.end_statement()
                return N.Chad(body=body, virgin=virgin, finally_=finally_, line=line)
            if w == "thisisfine":
                self.advance()
                body = self.block()
                self.end_statement()
                return N.ThisIsFine(body=body, line=line)
            if w == "based":
                # `based` alone on a line is the boolean literal as a (useless) expression; `based <expr>` asserts
                if self.peek().kind == "NEWLINE":
                    e = self.expression(); self.end_statement()
                    return N.ExprStmt(expr=e, line=line)
                self.advance()
                cond = self.expression()
                msg = None
                if self.at_op(","):
                    self.advance()
                    msg = self.expression()
                self.end_statement()
                return N.Based(cond=cond, message=msg, line=line)
            if w == "feelsgood":
                self.advance()
                value = None if self.at("NEWLINE") or self.at_op("}") or self.at("EOF") else self.expression()
                self.end_statement()
                return N.FeelsGood(value=value, line=line)
            if w == "feelsbad":
                self.advance()
                value = self.expression()
                self.end_statement()
                return N.FeelsBad(value=value, line=line)
            if w in BRAINS:
                self.advance()
                body = self.block()
                self.end_statement()
                return N.Brain(level=BRAINS[w], body=body, line=line)
            if w == "touchgrass":
                self.advance()
                secs = self.expression()
                self.end_statement()
                return N.TouchGrass(seconds=secs, line=line)
            if w == "stonks":
                self.advance()
                name = self.postfix()
                delta = None
                if not (self.at("NEWLINE") or self.at("EOF") or self.at_op("}")):
                    delta = self.expression()
                self.end_statement()
                return N.Stonks(name=name, delta=delta, line=line)
            if w in ("pikachu", "virgin", "F"):
                raise ParseError(f"'{w}' without a matching block before it", line)
            if w in ("in", "until", "max", "forever", "and", "or", "cringe", "loss", "copium"):
                raise ParseError(f"'{w}' cannot start a statement", line)
        # assignment: name = expr / name.field = expr / name[i] = expr
        if t.kind == "IDENT":
            j = self.i
            target = self.postfix(allow_call=False)
            if self.at_op("="):
                self.advance()
                value = self.expression()
                self.end_statement()
                if not isinstance(target, (N.Name, N.Member, N.Index)):
                    raise ParseError("cannot assign to that", line)
                return N.Assign(target=target, value=value, line=line)
            if self.at_op("+=", "-="):
                op = self.advance().value[0]
                value = self.expression()
                self.end_statement()
                if not isinstance(target, (N.Name, N.Member, N.Index)):
                    raise ParseError("cannot assign to that", line)
                return N.Assign(target=target, value=N.Binary(op=op, left=target, right=value, line=line), line=line)
            self.i = j
        expr = self.expression()
        self.end_statement()
        return N.ExprStmt(expr=expr, line=line)

    def skip_newlines_if_followed_by(self, *words: str):
        j = self.i
        while self.toks[j].kind == "NEWLINE":
            j += 1
        if self.toks[j].kind == "KEYWORD" and self.toks[j].value in words:
            self.i = j

    def tfw(self) -> N.Tfw:
        line = self.expect_kw("tfw").line
        cond = self.expression()
        body = self.block()
        otherwise = None
        self.skip_newlines_if_followed_by("pikachu")
        if self.at_kw("pikachu"):
            self.advance()
            if self.at_kw("tfw"):
                otherwise = [self.tfw()]
                return N.Tfw(cond=cond, body=body, otherwise=otherwise, line=line)
            otherwise = self.block()
        self.end_statement()
        return N.Tfw(cond=cond, body=body, otherwise=otherwise, line=line)

    def grind(self) -> N.Grind:
        line = self.expect_kw("grind").line
        kind, expr, var, mx = "forever", None, None, None
        if self.at_kw("forever"):
            self.advance()
        elif self.at_kw("until"):
            self.advance()
            kind, expr = "until", self.expression()
        elif self.at_op("{") or self.at_kw("max"):
            pass
        elif self.cur.kind == "IDENT" and self.peek().kind == "KEYWORD" and self.peek().value == "in":
            var = self.advance().value
            self.advance()
            kind, expr = "each", self.expression()
        else:
            kind, expr = "count", self.expression()
        if self.at_kw("max"):
            self.advance()
            mx = self.expression()
        body = self.block()
        self.end_statement()
        return N.Grind(kind=kind, expr=expr, var=var, max=mx, body=body, line=line)

    # ------------------------------------------------------------ expressions
    def expression(self) -> N.Node:
        return self.copium()

    def copium(self) -> N.Node:
        left = self.disjunction()
        while self.at_kw("copium"):
            line = self.advance().line
            right = self.disjunction()
            left = N.Copium(attempt=left, fallback=right, line=line)
        return left

    def disjunction(self) -> N.Node:
        left = self.conjunction()
        while self.at_kw("or"):
            line = self.advance().line
            left = N.Binary(op="or", left=left, right=self.conjunction(), line=line)
        return left

    def conjunction(self) -> N.Node:
        left = self.negation()
        while self.at_kw("and"):
            line = self.advance().line
            left = N.Binary(op="and", left=left, right=self.negation(), line=line)
        return left

    def negation(self) -> N.Node:
        if self.at_kw("not"):
            line = self.advance().line
            return N.Unary(op="not", operand=self.negation(), line=line)
        return self.comparison()

    def comparison(self) -> N.Node:
        left = self.additive()
        while True:
            if self.cur.kind == "OP" and self.cur.value in COMPARE:
                t = self.advance()
                left = N.Binary(op=t.value, left=left, right=self.additive(), line=t.line)
            elif self.at_kw("in"):
                t = self.advance()
                left = N.Binary(op="in", left=left, right=self.additive(), line=t.line)
            elif self.at_kw("not") and self.peek().kind == "KEYWORD" and self.peek().value == "in":
                t = self.advance(); self.advance()
                left = N.Unary(op="not", operand=N.Binary(op="in", left=left, right=self.additive(), line=t.line), line=t.line)
            else:
                return left

    def additive(self) -> N.Node:
        left = self.multiplicative()
        while self.at_op("+", "-"):
            t = self.advance()
            left = N.Binary(op=t.value, left=left, right=self.multiplicative(), line=t.line)
        return left

    def multiplicative(self) -> N.Node:
        left = self.unary()
        while self.at_op("*", "/", "%"):
            t = self.advance()
            left = N.Binary(op=t.value, left=left, right=self.unary(), line=t.line)
        return left

    def unary(self) -> N.Node:
        if self.at_op("-"):
            line = self.advance().line
            return N.Unary(op="-", operand=self.unary(), line=line)
        if self.cur.kind == "KEYWORD":
            w, line = self.cur.value, self.cur.line
            if w == "sus":
                self.advance(); return N.Sus(value=self.unary(), line=line)
            if w == "sauce":
                self.advance(); return N.Sauce(value=self.unary(), line=line)
            if w == "trustmebro":
                self.advance(); return N.TrustMeBro(value=self.unary(), line=line)
            if w == "apu":
                self.advance(); return N.Apu(question=self.unary(), line=line)
            if w == "thonk":
                self.advance(); return N.Thonk(prompt=self.unary(), line=line)
            if w == "fren":
                self.advance()
                target = self.expect_ident()
                return N.Fren(target=target, message=self.unary(), line=line)
            if w == "yolo":
                self.advance()
                call = self.postfix()
                if not isinstance(call, N.Call):
                    raise ParseError("yolo must be followed by a tool call, e.g. yolo write(path, text)", line)
                call.yolo = True
                return call
            if w == "wagmi":
                self.advance()
                return self.wagmi(line)
            if w in BRAINS and not (self.peek().kind == "OP" and self.peek().value == "{"):
                self.advance()
                return N.BrainExpr(level=BRAINS[w], expr=self.unary(), line=line)
        return self.postfix()

    def wagmi(self, line: int) -> N.Wagmi:
        entries = []
        if self.at_op("{"):
            self.advance(); self.skip_newlines()
            while not self.at_op("}"):
                key = self.expect_ident()
                self.expect_op(":")
                entries.append((key, self.expression()))
                if self.at_op(","):
                    self.advance()
                self.skip_newlines()
            self.expect_op("}")
            return N.Wagmi(entries=entries, as_record=True, line=line)
        if self.at_op("["):
            self.advance(); self.skip_newlines()
            while not self.at_op("]"):
                entries.append((None, self.expression()))
                if self.at_op(","):
                    self.advance()
                self.skip_newlines()
            self.expect_op("]")
            return N.Wagmi(entries=entries, as_record=False, line=line)
        raise ParseError("wagmi needs { name: expr, ... } or [ expr, ... ]", line)

    def postfix(self, allow_call: bool = True) -> N.Node:
        node = self.primary(allow_call)
        while True:
            if self.at_op("."):
                line = self.advance().line
                name = self.expect_ident_or_keyword()
                node = N.Member(obj=node, name=name, line=line)
            elif self.at_op("["):
                line = self.advance().line
                idx = self.expression()
                self.expect_op("]")
                node = N.Index(obj=node, index=idx, line=line)
            else:
                return node

    def expect_ident_or_keyword(self) -> str:
        if self.cur.kind in ("IDENT", "KEYWORD"):
            return self.advance().value
        raise ParseError(f"expected a field name, got {self._desc()}", self.cur.line)

    def primary(self, allow_call: bool = True) -> N.Node:
        t = self.cur
        line = t.line
        if t.kind == "NUMBER":
            self.advance()
            return N.Literal(value=t.value, line=line)
        if t.kind == "STRING":
            self.advance()
            parts = []
            for p in t.value:
                if isinstance(p, tuple):
                    sub = Parser(tokenize(p[1]))
                    sub_expr = sub.expression()
                    sub.skip_newlines()
                    if not sub.at("EOF"):
                        raise ParseError("bad {interpolation} in string", p[2])
                    _relabel(sub_expr, p[2])
                    parts.append(sub_expr)
                else:
                    parts.append(p)
            if len(parts) == 1 and isinstance(parts[0], str):
                return N.Literal(value=parts[0], line=line)
            return N.Str(parts=parts, line=line)
        if t.kind == "KEYWORD":
            if t.value == "based":
                self.advance(); return N.Literal(value=True, line=line)
            if t.value == "cringe":
                self.advance(); return N.Literal(value=False, line=line)
            if t.value == "loss":
                self.advance(); return N.Literal(value=None, line=line)
            raise ParseError(f"'{t.value}' cannot be used here", line)
        if t.kind == "IDENT":
            self.advance()
            if allow_call and self.at_op("("):
                self.advance()
                args, kwargs = [], []
                self.skip_newlines()
                while not self.at_op(")"):
                    if self.cur.kind == "IDENT" and self.peek().kind == "OP" and self.peek().value == ":":
                        k = self.advance().value; self.advance()
                        kwargs.append((k, self.expression()))
                    else:
                        if kwargs:
                            raise ParseError("positional argument after a named one", self.cur.line)
                        args.append(self.expression())
                    if self.at_op(","):
                        self.advance()
                    self.skip_newlines()
                self.expect_op(")")
                return N.Call(callee=t.value, args=args, kwargs=kwargs, line=line)
            return N.Name(name=t.value, line=line)
        if t.kind == "OP":
            if t.value == "(":
                self.advance(); self.skip_newlines()
                e = self.expression()
                self.skip_newlines()
                self.expect_op(")")
                return e
            if t.value == "[":
                self.advance(); self.skip_newlines()
                items = []
                while not self.at_op("]"):
                    items.append(self.expression())
                    if self.at_op(","):
                        self.advance()
                    self.skip_newlines()
                self.expect_op("]")
                return N.ListLit(items=items, line=line)
            if t.value == "{":
                self.advance()
                pairs = []
                self._skip_nl_in_braces()
                while not self.at_op("}"):
                    if self.cur.kind == "STRING" and len(self.cur.value) == 1 and isinstance(self.cur.value[0], str):
                        key = self.advance().value[0]
                    else:
                        key = self.expect_ident_or_keyword()
                    self.expect_op(":")
                    self._skip_nl_in_braces()
                    pairs.append((key, self.expression()))
                    self._skip_nl_in_braces()
                    if self.at_op(","):
                        self.advance()
                    self._skip_nl_in_braces()
                self.expect_op("}")
                return N.RecordLit(pairs=pairs, line=line)
        raise ParseError(f"unexpected {self._desc()}", line)

    def _skip_nl_in_braces(self):
        while self.at("NEWLINE"):
            self.advance()


def _relabel(node, line: int):
    """Interpolated expressions are parsed from a substring; give them the real line."""
    if isinstance(node, N.Node):
        node.line = line
        for v in vars(node).values():
            _relabel(v, line)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _relabel(v, line)
