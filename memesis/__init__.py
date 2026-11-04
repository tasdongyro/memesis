"""Memesis: a programming language for AI agents, written in memes.

    from memesis import Runtime
    rt = Runtime()
    result = rt.run('wow "hello fren"')
"""
__version__ = "0.1.0"

from .runtime import Runtime, Tool, Ctx, Result, Output   # noqa: E402
from .errors import Cringe, SusError, YoloError, NoHuman, NoBrain  # noqa: E402
from .values import mark, is_sus, sauce_of, plain  # noqa: E402

__all__ = ["Runtime", "Tool", "Ctx", "Result", "Output", "Cringe", "SusError", "YoloError", "NoHuman", "NoBrain",
           "mark", "is_sus", "sauce_of", "plain", "__version__"]
