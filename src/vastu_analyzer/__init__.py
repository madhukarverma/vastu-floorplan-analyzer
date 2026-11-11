"""vastu-floorplan-analyzer: deterministic Vastu Shastra + building-physics assessment.

Typical use::

    from vastu_analyzer import load_plan, analyze, to_markdown
    result = analyze(load_plan("examples/sample_3bhk_delhi.json"))
    print(result.vci)
"""

from __future__ import annotations

__version__ = "1.0.0"

from .engine import analyze
from .loader import PlanValidationError, load_plan, plan_from_dict
from .report import to_json, to_markdown, to_text
from .rules import load_rules

__all__ = [
    "PlanValidationError",
    "__version__",
    "analyze",
    "load_plan",
    "load_rules",
    "plan_from_dict",
    "to_json",
    "to_markdown",
    "to_text",
]
