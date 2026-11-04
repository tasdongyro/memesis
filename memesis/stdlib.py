"""Built-in tools. Pure helpers inherit the sus/sauce facts of their inputs automatically;
`fetch` and `shell` return sus output; `write`, `append`, `delete`, `shell`, `http_post` are irreversible.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode as _urlencode
from urllib.request import Request, urlopen

USER_AGENT = "memesis/0.1 (+https://github.com/eneserdo/memesis)"


def install(rt) -> None:
    T = rt.tool

    # ---------------------------------------------------------------- text
    @T(name="len", builtin=True, doc="length of text, list or record")
    def len_(x):
        return len(x) if x is not None else 0

    @T(builtin=True, doc="lowercase text")
    def lower(s):
        return str(s).lower()

    @T(builtin=True, doc="uppercase text")
    def upper(s):
        return str(s).upper()

    @T(builtin=True, doc="strip whitespace")
    def trim(s):
        return str(s).strip()

    @T(builtin=True, doc="split text by a separator (default: whitespace)")
    def split(s, sep=None, limit=-1):
        return str(s).split(sep, limit) if sep is not None else str(s).split()

    @T(builtin=True, doc="join a list with a separator")
    def join(items, sep=", "):
        return str(sep).join(_fmt(x) for x in items)

    @T(builtin=True, doc="does text/list/record contain x")
    def contains(hay, needle):
        if isinstance(hay, str):
            return _fmt(needle) in hay
        return needle in hay

    @T(builtin=True, doc="does text start with prefix")
    def starts(s, prefix):
        return str(s).startswith(str(prefix))

    @T(builtin=True, doc="does text end with suffix")
    def ends(s, suffix):
        return str(s).endswith(str(suffix))

    @T(builtin=True, doc="replace all occurrences")
    def replace(s, old, new):
        return str(s).replace(str(old), str(new))

    @T(name="slice", builtin=True, doc="text[start:end]")
    def slice_(x, start=0, end=None):
        return x[start:end]

    @T(builtin=True, doc="lines of a text")
    def lines(s):
        return str(s).splitlines()

    @T(builtin=True, doc="all regex matches (first group if the pattern has one)")
    def find(s, pattern):
        out = []
        for m in re.finditer(str(pattern), str(s), re.S):
            out.append(m.group(1) if m.groups() else m.group(0))
        return out

    @T(builtin=True, doc="does the regex match anywhere")
    def matches(s, pattern):
        return re.search(str(pattern), str(s), re.S) is not None

    @T(builtin=True, doc="strip HTML tags and collapse whitespace")
    def text(html):
        s = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", str(html))
        s = re.sub(r"(?s)<[^>]+>", " ", s)
        s = re.sub(r"&nbsp;|&#160;", " ", s)
        s = re.sub(r"&amp;", "&", s); s = re.sub(r"&lt;", "<", s); s = re.sub(r"&gt;", ">", s); s = re.sub(r"&quot;", '"', s)
        return re.sub(r"\s+", " ", s).strip()

    @T(builtin=True, doc="shorten text to n characters")
    def head(s, n=500):
        s = str(s)
        return s if len(s) <= n else s[:n] + "…"

    @T(name="str", builtin=True, doc="convert to text")
    def str_(x):
        return _fmt(x)

    @T(builtin=True, doc="convert to number")
    def num(x):
        if isinstance(x, (int, float)):
            return x
        s = str(x).strip().replace(",", "")
        try:
            return int(s)
        except ValueError:
            return float(s)

    @T(name="type", builtin=True, doc="type of a value: text number list record based cringe loss")
    def type_(x):
        from .values import describe
        return describe(x)

    # ---------------------------------------------------------------- numbers
    @T(name="round", builtin=True, doc="round a number")
    def round_(x, digits=0):
        return round(x, digits) if digits else int(round(x))

    @T(name="min", builtin=True, doc="smallest of a list or of the arguments")
    def min_(*xs):
        xs = xs[0] if len(xs) == 1 and isinstance(xs[0], list) else xs
        return min(xs)

    @T(name="max", builtin=True, doc="largest of a list or of the arguments")
    def max_(*xs):
        xs = xs[0] if len(xs) == 1 and isinstance(xs[0], list) else xs
        return max(xs)

    @T(name="sum", builtin=True, doc="sum of a list")
    def sum_(xs):
        return sum(xs)

    @T(name="range", builtin=True, doc="list of numbers 0..n-1 (or a..b-1)")
    def range_(a, b=None):
        return list(range(a)) if b is None else list(range(a, b))

    # ---------------------------------------------------------------- lists and records
    @T(builtin=True, doc="first item (or loss)")
    def first(xs):
        return xs[0] if xs else None

    @T(builtin=True, doc="last item (or loss)")
    def last(xs):
        return xs[-1] if xs else None

    @T(builtin=True, doc="new list with x appended")
    def push(xs, x):
        return list(xs) + [x]

    @T(builtin=True, doc="sorted copy (optionally by a record field)")
    def sort(xs, by=None, reverse=False):
        if by is None:
            return sorted(xs, reverse=reverse)
        return sorted(xs, key=lambda r: (r.get(by) is None, r.get(by)), reverse=reverse)

    @T(builtin=True, doc="reversed copy")
    def reverse(xs):
        return list(reversed(xs))

    @T(builtin=True, doc="unique items, order kept")
    def uniq(xs):
        out = []
        for x in xs:
            if x not in out:
                out.append(x)
        return out

    @T(builtin=True, doc="keys of a record")
    def keys(r):
        return list(r.keys())

    @T(builtin=True, doc="values of a record")
    def values(r):
        return list(r.values())

    @T(builtin=True, doc="does the record have the key")
    def has(r, key):
        return key in r

    @T(builtin=True, doc="field of every record in a list")
    def pluck(xs, key):
        return [x.get(key) if isinstance(x, dict) else None for x in xs]

    @T(builtin=True, doc="records where field == value")
    def where(xs, key, value):
        return [x for x in xs if isinstance(x, dict) and x.get(key) == value]

    # ---------------------------------------------------------------- json, hashes, ids, time
    @T(builtin=True, doc="parse JSON text")
    def json_parse(s):
        return json.loads(str(s))

    @T(builtin=True, doc="encode as JSON text")
    def json_dump(x, pretty=False):
        return json.dumps(x, ensure_ascii=False, indent=2 if pretty else None, default=str)

    @T(builtin=True, doc="sha256 hex of text")
    def sha256(s):
        return hashlib.sha256(str(s).encode("utf-8")).hexdigest()

    @T(builtin=True, doc="random uuid4")
    def uuid():
        return str(_uuid.uuid4())

    @T(builtin=True, doc="current time as ISO text (UTC)")
    def now():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @T(builtin=True, doc="unix time in seconds")
    def epoch():
        return int(time.time())

    @T(builtin=True, doc="url-encode text or a record of query parameters")
    def urlencode(x):
        return _urlencode(x) if isinstance(x, dict) else quote(str(x), safe="")

    @T(builtin=True, doc="read an environment variable (loss if unset)")
    def env(name, default=None):
        return os.environ.get(str(name), default)

    # ---------------------------------------------------------------- the world (sus in, yolo out)
    @T(builtin=True, sus=True, doc="GET a URL and return the body text")
    def fetch(url, timeout=20, headers=None):
        req = Request(str(url), headers={"User-Agent": USER_AGENT, **(headers or {})})
        with urlopen(req, timeout=timeout) as r:
            raw = r.read()
            ct = r.headers.get("content-type", "")
        charset = "utf-8"
        m = re.search(r"charset=([\w-]+)", ct)
        if m:
            charset = m.group(1)
        return raw.decode(charset, errors="replace")

    @T(builtin=True, sus=True, doc="GET a URL and parse the JSON body")
    def fetch_json(url, timeout=20, headers=None):
        return json.loads(fetch(url, timeout=timeout, headers=headers))

    @T(builtin=True, irreversible=True, doc="POST a JSON body to a URL, returns the response text")
    def http_post(url, body=None, headers=None, timeout=20):
        data = json.dumps(body or {}).encode("utf-8")
        req = Request(str(url), data=data, method="POST",
                      headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", **(headers or {})})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")

    @T(builtin=True, doc="read a local text file")
    def read(path):
        return Path(str(path)).read_text(encoding="utf-8")

    @T(builtin=True, doc="does the path exist")
    def exists(path):
        return Path(str(path)).exists()

    @T(builtin=True, irreversible=True, doc="write text to a local file (creates folders)")
    def write(path, content):
        p = Path(str(path))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_fmt(content), encoding="utf-8")
        return str(p)

    @T(builtin=True, irreversible=True, doc="append text to a local file")
    def append(path, content):
        p = Path(str(path))
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(_fmt(content))
        return str(p)

    @T(builtin=True, irreversible=True, doc="delete a local file")
    def delete(path):
        p = Path(str(path))
        if p.exists():
            p.unlink()
            return True
        return False

    @T(builtin=True, irreversible=True, sus=True, doc="run a shell command, returns {out, err, code}")
    def shell(cmd, timeout=120):
        r = subprocess.run(str(cmd), shell=True, capture_output=True, text=True, timeout=timeout)
        return {"out": r.stdout, "err": r.stderr, "code": r.returncode}


def _fmt(x) -> str:
    from .interpreter import fmt
    return fmt(x)
