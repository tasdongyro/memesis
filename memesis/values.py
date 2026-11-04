"""Runtime values with provenance.

Memesis values are ordinary Python values. Values that came from outside (a web page, a shell
command, a file, another agent) carry two extra facts:

  sus    - the value is untrusted: text in it may try to instruct the agent (prompt injection)
  sauce  - where it came from, e.g. ("fetch:https://example.com",)

Both ride on thin subclasses of str / int / float / list / dict so normal operations keep working.
The interpreter merges them whenever two values are combined, so a report built from a sus page is
sus too, until somebody writes `trustmebro` in front of it.
"""
from __future__ import annotations

from typing import Any, Iterable


class Tracked:
    """Mixin: _sus (bool) and _sauce (tuple of str)."""
    _sus: bool = False
    _sauce: tuple = ()


class SusStr(str, Tracked):
    pass


class SusInt(int, Tracked):
    pass


class SusFloat(float, Tracked):
    pass


class SusList(list, Tracked):
    pass


class SusDict(dict, Tracked):
    pass


WRAP = {str: SusStr, int: SusInt, float: SusFloat, list: SusList, dict: SusDict}


def is_sus(v: Any) -> bool:
    return bool(getattr(v, "_sus", False))


def sauce_of(v: Any) -> tuple:
    return tuple(getattr(v, "_sauce", ()))


def deep_sus(v: Any) -> bool:
    """True if v or anything inside it is sus."""
    if is_sus(v):
        return True
    if isinstance(v, dict):
        return any(deep_sus(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(deep_sus(x) for x in v)
    return False


def deep_sauce(v: Any) -> tuple:
    out: list = list(sauce_of(v))
    if isinstance(v, dict):
        for x in v.values():
            out.extend(deep_sauce(x))
    elif isinstance(v, (list, tuple)):
        for x in v:
            out.extend(deep_sauce(x))
    return _uniq(out)


def _uniq(items: Iterable[str]) -> tuple:
    seen: list = []
    for x in items:
        if x not in seen:
            seen.append(x)
    return tuple(seen)


def mark(v: Any, sus: bool | None = None, sauce: Iterable[str] = ()) -> Any:
    """Return v carrying the given facts (merged with what it already carries).

    Booleans and None cannot carry facts: taint through a comparison is control-flow taint, which
    Memesis does not track (documented in README, 'Honest notes').
    """
    if v is None or isinstance(v, bool):
        return v
    old_sus = is_sus(v)
    old_sauce = sauce_of(v)
    new_sus = old_sus if sus is None else sus
    new_sauce = _uniq(list(old_sauce) + list(sauce))
    if new_sus == old_sus and new_sauce == old_sauce and (isinstance(v, Tracked) or (not new_sus and not new_sauce)):
        return v
    base = type(v)
    for t, w in WRAP.items():
        if isinstance(v, t):
            if t is dict:
                out = w(v)
            elif t is list:
                out = w(v)
            else:
                out = w(v)
            out._sus = new_sus
            out._sauce = new_sauce
            return out
    return v  # unknown type (callable etc.): untracked


def clean(v: Any) -> Any:
    """trustmebro: strip the sus flag (keep the sauce) from v and everything inside it."""
    if isinstance(v, dict):
        out = {k: clean(x) for k, x in v.items()}
        return mark(out, sus=False, sauce=sauce_of(v))
    if isinstance(v, (list, tuple)):
        out = [clean(x) for x in v]
        return mark(out, sus=False, sauce=sauce_of(v))
    if is_sus(v):
        return mark(v, sus=False)
    return v


def inherit(result: Any, *inputs: Any) -> Any:
    """Make result carry the merged facts of all inputs (used for every operation and stdlib call)."""
    sus = any(deep_sus(x) for x in inputs)
    sauce: list = []
    for x in inputs:
        sauce.extend(deep_sauce(x))
    if not sus and not sauce:
        return result
    return mark(result, sus=sus, sauce=sauce)


def plain(v: Any) -> Any:
    """Convert tracked values back to plain Python (for JSON output and tool callbacks)."""
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [plain(x) for x in v]
    if isinstance(v, SusStr):
        return str(v)
    if isinstance(v, SusInt):
        return int(v)
    if isinstance(v, SusFloat):
        return float(v)
    return v


def describe(v: Any) -> str:
    """Short type name for error messages and `type()`."""
    if v is None:
        return "loss"
    if isinstance(v, bool):
        return "based" if v else "cringe"
    if isinstance(v, str):
        return "text"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "record"
    return type(v).__name__
