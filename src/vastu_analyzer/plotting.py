"""Annotated plan rendering (optional dependency: ``pip install vastu-floorplan-analyzer[plot]``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .engine import _build_geometry
from .geometry import centroid, rotate
from .models import AnalysisResult, FloorPlan
from .zoning import ZONES

# Diverging blue <-> red with a neutral grey midpoint (score 0 = avoid, 1 = ideal).
_RED, _MID, _BLUE = "#e34948", "#f0efec", "#2a78d6"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#c3c2b7"


def _blend(c1: str, c2: str, t: float) -> tuple[float, float, float]:
    a = [int(c1[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    b = [int(c2[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def score_colour(score: float) -> tuple[float, float, float]:
    s = max(0.0, min(1.0, score))
    return _blend(_RED, _MID, s / 0.5) if s < 0.5 else _blend(_MID, _BLUE, (s - 0.5) / 0.5)


def plot_plan(
    plan: FloorPlan, result: AnalysisResult, path: str | Path | None = None, ax: Any = None,
    title: str | None = None, label_size: float = 6.2, zone_size: float = 7.0,
    arrow_size: float = 8.0, marker_size: float = 6.0,
) -> Any:  # fmt: skip
    """Draw the plan in the cardinal frame with the 3 x 3 mandala and score-coloured rooms.

    Rooms are filled on a diverging red (score 0, *avoid*) - grey - blue (score 1, *ideal*)
    scale; the main entrance is a filled diamond, secondary entrances are hollow.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon

    geo = _build_geometry(plan)
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(5.2, 5.6), dpi=200)
    ox, oy = geo.grid.centre

    def shift(poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(x - ox, y - oy) for x, y in poly]

    for z in ZONES:
        x0, _, _, y1 = geo.grid.cell(z)
        inset = 0.025 * max(geo.grid.width, geo.grid.height)
        ax.text(x0 - ox + inset, y1 - oy - inset, z, ha="left", va="top", fontsize=zone_size,
                color=INK2, zorder=6, fontweight="bold", alpha=0.75)  # fmt: skip
    for k in (1, 2):
        xs = geo.grid.xmin + k * geo.grid.width / 3 - ox
        ys = geo.grid.ymin + k * geo.grid.height / 3 - oy
        ax.axvline(xs, color=MUTED, lw=0.6, ls=(0, (4, 3)), zorder=1)
        ax.axhline(ys, color=MUTED, lw=0.6, ls=(0, (4, 3)), zorder=1)

    ax.add_patch(MplPolygon(shift(geo.footprint_aligned), closed=True, fill=False, ec=INK, lw=1.6,
                            zorder=4))  # fmt: skip
    for poly, rr in zip(geo.rooms_aligned, result.rooms, strict=True):
        ax.add_patch(MplPolygon(shift(poly), closed=True, fc=score_colour(rr.score), ec=INK2,
                                lw=0.8, alpha=0.92, zorder=2))  # fmt: skip
        cx, cy = centroid(shift(poly))
        ax.text(cx, cy, f"{rr.name}\n{rr.score:.2f}", ha="center", va="center", fontsize=label_size,
                color=INK, zorder=5)  # fmt: skip

    for e, er in zip(plan.entrances, result.entrances, strict=True):
        ((ex, ey),) = rotate([e.position], geo.theta_snap, geo.origin)
        ax.plot(ex - ox, ey - oy, marker="D", ms=marker_size, mfc=INK if er.main else "white", mec=INK,
                zorder=6)  # fmt: skip

    # North arrow for the exact (unsnapped) true north.
    import math

    skew = math.radians(geo.theta - geo.theta_snap)
    L = 0.12 * max(geo.grid.width, geo.grid.height)
    ax0 = geo.grid.xmax - ox + 0.10 * geo.grid.width
    ay0 = geo.grid.ymax - oy - L
    ax.annotate("", xy=(ax0 + L * math.sin(skew), ay0 + L * math.cos(skew)), xytext=(ax0, ay0),
                arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.2})  # fmt: skip
    ax.text(ax0 + 1.15 * L * math.sin(skew), ay0 + 1.15 * L * math.cos(skew), "N", ha="center",
            va="bottom", fontsize=arrow_size, color=INK)  # fmt: skip

    ax.set_aspect("equal")
    pad = 0.06 * max(geo.grid.width, geo.grid.height)
    ax.set_xlim(geo.grid.xmin - ox - pad, geo.grid.xmax - ox + 0.22 * geo.grid.width)
    ax.set_ylim(geo.grid.ymin - oy - pad, geo.grid.ymax - oy + pad)
    ax.set_xlabel("East (m)", fontsize=8, color=INK2)
    ax.set_ylabel("North (m)", fontsize=8, color=INK2)
    ax.tick_params(labelsize=7, colors=INK2)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    if title:
        ax.set_title(title, fontsize=9, color=INK)
    if own and path:
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
    return ax
