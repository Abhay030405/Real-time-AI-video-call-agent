"""The AI judge used in evaluation: a model from a different family than M1 (V0_07 section 6).

It is never used in a call. It reads replies and scores them against written descriptions.
"""

from .judge import build_judge, describe_judge

__all__ = ["build_judge", "describe_judge"]
