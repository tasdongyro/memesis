"""Errors. Every runtime failure is a Cringe; `virgin` blocks catch them as the record `L`."""
from __future__ import annotations

from typing import Any


class Cringe(Exception):
    """Base runtime error. kind is a short tag an agent can branch on (L.kind)."""
    kind = "cringe"

    def __init__(self, message: str, line: int = 0, payload: Any = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.payload = payload

    def as_record(self) -> dict:
        rec = {"kind": self.kind, "message": self.message, "line": self.line}
        if self.payload is not None:
            rec["payload"] = self.payload
        return rec

    def __str__(self) -> str:
        where = f" (line {self.line})" if self.line else ""
        return f"{self.kind}: {self.message}{where}"


class FeelsBad(Cringe):
    """Raised by `feelsbad <value>` in a script."""
    kind = "feelsbad"


class NotBased(Cringe):
    """A `based` assertion failed."""
    kind = "notbased"


class SusError(Cringe):
    """An untrusted value reached an irreversible tool without trustmebro."""
    kind = "sus"


class YoloError(Cringe):
    """An irreversible tool was called without yolo (or yolo was refused)."""
    kind = "yolo"


class NoHuman(Cringe):
    """apu asked, but no human is attached to the runtime."""
    kind = "nohuman"


class NoBrain(Cringe):
    """thonk was used, but no model is attached to the runtime."""
    kind = "nobrain"


class GrindCap(Cringe):
    """A grind loop hit its max."""
    kind = "grindcap"


class ToolError(Cringe):
    """A tool raised."""
    kind = "tool"


class NameCringe(Cringe):
    kind = "name"


class TypeCringe(Cringe):
    kind = "type"


class Ngmi(Cringe):
    """One or more wagmi entries failed."""
    kind = "ngmi"


# control flow (not errors, never shown to the user)
class _Bonk(Exception):
    pass


class _Nah(Exception):
    pass


class _FeelsGood(Exception):
    def __init__(self, value: Any):
        self.value = value
