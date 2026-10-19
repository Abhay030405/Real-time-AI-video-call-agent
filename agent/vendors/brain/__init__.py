"""The brain: M1 (direct), M2 (through OpenRouter) and S1 (the background helper)."""

from .brain import build_brain, build_m1, build_m2, build_s1, describe_brain
from .fallback import BrainFallback

__all__ = [
    "BrainFallback",
    "build_brain",
    "build_m1",
    "build_m2",
    "build_s1",
    "describe_brain",
]
