"""Tokenizer for Memesis.

The language is line oriented: a statement ends at a newline (or a `;`), blocks use `{ }`.
`kek` starts a comment that runs to the end of the line. Strings interpolate `{expr}`.
"""
from __future__ import annotations

from dataclasses import dataclass

KEYWORDS = {
    # structure
    "pepe", "npc", "fren",
    # data
    "such", "wow", "doge", "based", "cringe", "loss",
    # control flow
    "tfw", "pikachu", "grind", "in", "until", "max", "forever", "bonk", "nah",
    # failure
    "chad", "virgin", "F", "copium", "thisisfine", "feelsgood", "feelsbad",
    # people and brains
    "apu", "wagmi", "smoothbrain", "bigbrain", "galaxybrain", "thonk",
    # safety
    "sus", "sauce", "trustmebro", "yolo",
    # misc
    "touchgrass", "stonks",
    # operators
    "and", "or", "not",
}

DURATIONS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}


@dataclass
class Token:
    kind: str          # NUMBER STRING IDENT KEYWORD OP NEWLINE EOF
    value: object
    line: int
    col: int

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.kind}({self.value!r})@{self.line}:{self.col}"


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"line {line}:{col}: {message}")
        self.line, self.col = line, col


THREE = {"..."}
TWO = {"==", "!=", "<=", ">=", "..", "+=", "-="}
ONE = set("+-*/%<>=(){}[],.:;!")


def tokenize(src: str) -> list[Token]:
    toks: list[Token] = []
    i, line, col = 0, 1, 1
    n = len(src)
    depth = 0  # () and [] nesting: newlines inside are not statement ends

    def add(kind, value, l, c):
        toks.append(Token(kind, value, l, c))

    while i < n:
        ch = src[i]
        if ch == "\n":
            if depth == 0:
                add("NEWLINE", None, line, col)
            i += 1; line += 1; col = 1
            continue
        if ch in " \t\r":
            i += 1; col += 1
            continue
        if ch == "\\" and i + 1 < n and src[i + 1] == "\n":   # line continuation
            i += 2; line += 1; col = 1
            continue
        # comments: kek ... (only at a word boundary)
        if src.startswith("kek", i) and (i + 3 >= n or not (src[i + 3].isalnum() or src[i + 3] == "_")):
            while i < n and src[i] != "\n":
                i += 1
            continue
        if ch == "#":  # plain comments are allowed too, for people who cannot kek
            while i < n and src[i] != "\n":
                i += 1
            continue
        start_col = col
        if ch == '"':
            value, consumed, nl = _read_string(src, i, line, col)
            add("STRING", value, line, start_col)
            i += consumed
            if nl:
                line += nl; col = 1
            else:
                col += consumed
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
            j = i
            while j < n and (src[j].isdigit() or src[j] == "_"):
                j += 1
            if j < n and src[j] == "." and j + 1 < n and src[j + 1].isdigit():
                j += 1
                while j < n and src[j].isdigit():
                    j += 1
            text = src[i:j].replace("_", "")
            num = float(text) if "." in text else int(text)
            # duration suffix: 2s 500ms 1m 1h
            for suf in ("ms", "s", "m", "h"):
                if src.startswith(suf, j) and (j + len(suf) >= n or not (src[j + len(suf)].isalnum() or src[j + len(suf)] == "_")):
                    num = num * DURATIONS[suf]
                    j += len(suf)
                    break
            add("NUMBER", num, line, start_col)
            col += j - i; i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            add("KEYWORD" if word in KEYWORDS else "IDENT", word, line, start_col)
            col += j - i; i = j
            continue
        if src[i:i + 3] in THREE:
            add("OP", src[i:i + 3], line, start_col); i += 3; col += 3
            continue
        if src[i:i + 2] in TWO:
            add("OP", src[i:i + 2], line, start_col); i += 2; col += 2
            continue
        if ch in ONE:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth = max(0, depth - 1)
            if ch == ";":
                add("NEWLINE", None, line, start_col)
            else:
                add("OP", ch, line, start_col)
            i += 1; col += 1
            continue
        raise LexError(f"unexpected character {ch!r}", line, col)
    add("NEWLINE", None, line, col)
    add("EOF", None, line, col)
    return toks


def _read_string(src: str, i: int, line: int, col: int):
    """Returns (parts, consumed, newlines). parts is a list of str | ("expr", source, line)."""
    assert src[i] == '"'
    j = i + 1
    parts: list = []
    buf: list[str] = []
    newlines = 0
    n = len(src)
    while True:
        if j >= n:
            raise LexError("unterminated string", line, col)
        c = src[j]
        if c == '"':
            j += 1
            break
        if c == "\\":
            if j + 1 >= n:
                raise LexError("unterminated string", line, col)
            esc = src[j + 1]
            buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\", "{": "{", "}": "}"}.get(esc, "\\" + esc))
            j += 2
            continue
        if c == "{":
            if src.startswith("{{", j):
                buf.append("{"); j += 2
                continue
            k = j + 1
            depth = 1
            while k < n and depth:
                if src[k] == "{":
                    depth += 1
                elif src[k] == "}":
                    depth -= 1
                elif src[k] == '"':
                    raise LexError("no quotes inside {interpolation}; bind the value with `such` first", line, col)
                k += 1
            if depth:
                raise LexError("unterminated {interpolation} in string", line, col)
            if buf:
                parts.append("".join(buf)); buf = []
            parts.append(("expr", src[j + 1:k - 1].strip(), line + newlines))
            j = k
            continue
        if c == "}" and src.startswith("}}", j):
            buf.append("}"); j += 2
            continue
        if c == "\n":
            newlines += 1
        buf.append(c)
        j += 1
    if buf or not parts:
        parts.append("".join(buf))
    return parts, j - i, newlines
