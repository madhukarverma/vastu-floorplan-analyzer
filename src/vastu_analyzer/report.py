"""Human- and machine-readable renderings of an :class:`AnalysisResult`."""

from __future__ import annotations

import dataclasses
import json
import math
from typing import Any

from .models import AnalysisResult, Swap

SEVERITY_TAG = {"critical": "[CRITICAL]", "major": "[MAJOR]", "minor": "[MINOR]", "info": "[INFO]"}


def grade(vci: float) -> str:
    """Qualitative band for a Vastu Compliance Index."""
    if vci >= 85:
        return "Excellent"
    if vci >= 70:
        return "Good"
    if vci >= 55:
        return "Fair"
    return "Poor"


def describe_swap(s: Swap) -> str:
    """Plain-language description of a function exchange."""
    return (
        f"use '{s.room_a}' as {s.type_b.replace('_', ' ')} and "
        f"'{s.room_b}' as {s.type_a.replace('_', ' ')}"
    )


def net_reassignment(result: AnalysisResult) -> list[tuple[str, str, str]]:
    """Collapse the sequential exchanges into ``(room, original_use, final_use)`` triples."""
    uses = {r.name: r.type for r in result.rooms}
    original = dict(uses)
    for s in result.swaps:
        uses[s.room_a], uses[s.room_b] = uses[s.room_b], uses[s.room_a]
    return [(n, original[n], uses[n]) for n in uses if uses[n] != original[n]]


def to_dict(result: AnalysisResult) -> dict[str, Any]:
    """JSON-serialisable dictionary (NaN replaced by ``None``)."""

    def clean(obj: Any) -> Any:
        if isinstance(obj, float) and math.isnan(obj):
            return None
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean(v) for v in obj]
        return obj

    d = dataclasses.asdict(result)
    d["grade"] = grade(result.vci)
    for s, raw in zip(d["swaps"], result.swaps, strict=True):
        s["gain"] = raw.gain
    d["reassignment"] = [{"room": n, "from": a, "to": b} for n, a, b in net_reassignment(result)]
    return clean(d)  # type: ignore[no-any-return]


def to_json(result: AnalysisResult, indent: int = 2) -> str:
    return json.dumps(to_dict(result), indent=indent)


def to_text(result: AnalysisResult) -> str:
    """Compact console summary."""
    lines = [
        f"Vastu assessment: {result.plan_name}",
        f"  Vastu Compliance Index (VCI): {result.vci:.1f} / 100  [{grade(result.vci)}]",
    ]
    comp = ", ".join(f"{k}={v:.0f}" for k, v in result.components.items() if not math.isnan(v))
    lines.append(f"  components: {comp}")
    if result.optimised_vci is not None and result.swaps:
        lines.append(f"  after suggested exchanges: {result.optimised_vci:.1f}")
    lines.append("")
    lines.append("  Room                 Type             Zone  Sector  Area m2  Score")
    for r in result.rooms:
        lines.append(
            f"  {r.name[:20]:<20} {r.type[:16]:<16} {r.zone:<5} {r.sector:<7} "
            f"{r.area:7.1f}  {r.score:5.2f}"
        )
    lines.append("")
    lines.append("  Findings (most severe first):")
    for f in result.findings:
        lines.append(f"  {SEVERITY_TAG[f.severity]:<11} {f.subject}: {f.message}")
        lines.append(f"  {'':<11} -> {f.suggestion}")
    if result.swaps:
        lines.append("")
        lines.append("  Suggested function exchanges (greedy optimiser):")
        for i, s in enumerate(result.swaps, 1):
            lines.append(
                f"  {i}. {describe_swap(s)}: VCI {s.vci_before:.1f} -> {s.vci_after:.1f} (+{s.gain:.1f})"
            )
        lines.append(
            "  Net result: "
            + "; ".join(f"'{n}' {a} -> {b}" for n, a, b in net_reassignment(result))
        )
    return "\n".join(lines)


def to_markdown(result: AnalysisResult) -> str:
    """Full Markdown report."""
    md: list[str] = [f"# Vastu assessment - {result.plan_name}", ""]
    md.append(f"**Vastu Compliance Index (VCI): {result.vci:.1f} / 100 - {grade(result.vci)}**")
    if result.optimised_vci is not None and result.swaps:
        md.append("")
        md.append(
            f"Achievable with the suggested function exchanges: **{result.optimised_vci:.1f}**"
        )
    md += ["", "## Score components", "", "| Component | Score |", "|---|---:|"]
    for k, v in result.components.items():
        md.append(f"| {k.replace('_', ' ')} | {'n/a' if math.isnan(v) else f'{v:.1f}'} |")

    md += ["", "## Rooms", "", "| Room | Type | Zone | Sector | Area (m2) | Score | Exterior walls |",
           "|---|---|---|---|---:|---:|---|"]  # fmt: skip
    for r in result.rooms:
        walls = ", ".join(f"{w.sector} {w.length:.1f} m" for w in r.walls) or "-"
        md.append(
            f"| {r.name} | {r.type} | {r.zone} | {r.sector} | {r.area:.1f} | {r.score:.2f} | {walls} |"
        )

    md += ["", "## Entrances", "", "| Entrance | Main | Bearing | Sector | Score |",
           "|---|---|---:|---|---:|"]  # fmt: skip
    for e in result.entrances:
        md.append(
            f"| {e.name} | {'yes' if e.main else 'no'} | {e.bearing:.0f} | {e.sector} | {e.score:.2f} |"
        )

    s = result.site
    md += [
        "",
        "## Site metrics",
        "",
        f"- Footprint area: {s.area:.1f} m2 (bounding box {s.bbox_area:.1f} m2)",
        f"- Rectangularity: {s.rectangularity:.3f}; aspect ratio: {s.aspect_ratio:.2f}",
        "- Corner fill: " + ", ".join(f"{k} {v:.0%}" for k, v in s.corner_fill.items()),
        f"- Brahmasthana occupied by heavy/wet uses: {s.brahmasthana_blocked:.0%}",
        f"- Mass dipole: bearing {s.dipole_bearing:.0f} deg, magnitude {s.dipole_magnitude:.3f} "
        f"(score {s.dipole_score:.2f})",
        f"- Orientation skew from cardinal: {s.orientation_skew:+.1f} deg",
    ]

    md += ["", "## Findings and suggestions", ""]
    for i, f in enumerate(result.findings, 1):
        md.append(f"{i}. **{f.severity.upper()} - {f.subject}.** {f.message}")
        md.append(f"   - *Suggestion:* {f.suggestion}")
        if f.traditional:
            md.append(f"   - *Vastu basis:* {f.traditional}")
        if f.physics:
            md.append(f"   - *Physical basis:* {f.physics}")
        if f.impact > 0:
            md.append(f"   - *Recoverable VCI:* up to {f.impact:.1f} points")

    if result.swaps:
        md += ["", "## Suggested function exchanges", "",
               "| # | Exchange | VCI before | VCI after | Gain |", "|---:|---|---:|---:|---:|"]  # fmt: skip
        for i, sw in enumerate(result.swaps, 1):
            md.append(
                f"| {i} | {describe_swap(sw)} | {sw.vci_before:.1f} | {sw.vci_after:.1f} | +{sw.gain:.1f} |"
            )
        md += ["", "Exchanges are applied in sequence. Net change of use:", ""]
        md += [f"- **{n}**: {a.replace('_', ' ')} -> {b.replace('_', ' ')}"
               for n, a, b in net_reassignment(result)]  # fmt: skip

    sol = result.solar_summary
    if sol:
        md += ["", "## Solar physics (clear-sky design days)", ""]
        alt = sol["noon_altitude"]
        md.append(
            "Solar-noon altitude: "
            + ", ".join(f"{k.replace('_', ' ')} {v:.1f} deg" for k, v in alt.items())
        )
        md.append("")
        md.append(f"South-window overhang depth ratio (d/h): {sol['overhang_depth_ratio']:.2f}")
        md += ["", "| Wall facing | Summer kWh/m2/day | PM share | Summer peak T_sa (C) | Winter kWh/m2/day |",
               "|---|---:|---:|---:|---:|"]  # fmt: skip
        su, wi = sol["facades"]["summer_solstice"], sol["facades"]["winter_solstice"]
        names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        for n, a, b in zip(names, su, wi, strict=True):
            share = a["afternoon_kwh"] / a["irradiation_kwh"] if a["irradiation_kwh"] else 0
            md.append(
                f"| {n} | {a['irradiation_kwh']:.2f} | {share:.0%} | {a['peak_sol_air']:.1f} | "
                f"{b['irradiation_kwh']:.2f} |"
            )
    md += ["", "---", "*Generated by vastu-floorplan-analyzer. Deterministic rule-based "
           "assessment; no machine learning is used.*", ""]  # fmt: skip
    return "\n".join(md)
