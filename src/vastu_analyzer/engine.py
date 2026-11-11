"""The analysis pipeline: geometry -> zoning -> rule scoring -> physics -> suggestions.

The pipeline is fully deterministic: identical inputs always give identical outputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import solar
from .geometry import (
    Point,
    Polygon,
    angular_difference,
    area,
    bounds,
    centroid,
    compass_bearing,
    distance_to_boundary,
    edges,
    point_in_polygon,
    rect_overlap_area,
    rotate,
)
from .models import (
    AnalysisResult,
    EntranceResult,
    Finding,
    FloorPlan,
    RoomResult,
    SiteResult,
    Swap,
    Wall,
)
from .rules import RuleBase, load_rules
from .zoning import ZONE_SANSKRIT, ZONES, MandalaGrid, dominant_zone, sector16, zone_fractions

OCCUPIED = {"master_bedroom", "bedroom", "living", "study", "pooja", "dining"}
WALL_TOL = (
    0.05  # m, an edge closer than this to the footprint boundary is a candidate exterior wall
)


@dataclass
class _Geometry:
    """Everything about the plan that does not depend on the room-type assignment."""

    theta: float  # true-north angle of the drawing, degrees
    theta_snap: float
    origin: Point  # footprint centroid (drawing frame)
    grid: MandalaGrid
    footprint_aligned: Polygon
    rooms_aligned: list[Polygon]
    fractions: list[dict[str, float]]
    areas: list[float]
    centroids: list[Point]  # drawing frame
    centre_overlap: list[float]  # m^2 of each room inside the Brahmasthana cell
    half_diag: float
    walls: list[list[Wall]] = field(default_factory=list)

    def true_bearing(self, vec: Point) -> float:
        return (compass_bearing(vec[0], vec[1]) - self.theta) % 360.0


def _build_geometry(plan: FloorPlan) -> _Geometry:
    theta = plan.north.true_angle_deg
    theta_snap = round(theta / 90.0) * 90.0
    origin = centroid(plan.footprint)
    fp_al = rotate(plan.footprint, theta_snap, origin)
    rooms_al = [rotate(r.polygon, theta_snap, origin) for r in plan.rooms]
    grid = MandalaGrid(*bounds([fp_al]))
    half_diag = 0.5 * math.hypot(grid.width, grid.height)
    geo = _Geometry(
        theta=theta,
        theta_snap=theta_snap,
        origin=origin,
        grid=grid,
        footprint_aligned=fp_al,
        rooms_aligned=rooms_al,
        fractions=[zone_fractions(p, grid) for p in rooms_al],
        areas=[area(r.polygon) for r in plan.rooms],
        centroids=[centroid(r.polygon) for r in plan.rooms],
        centre_overlap=[rect_overlap_area(p, *grid.cell("C")) for p in rooms_al],
        half_diag=half_diag,
    )
    geo.walls = [_exterior_walls(r.polygon, plan.footprint, geo) for r in plan.rooms]
    return geo


def _exterior_walls(poly: Polygon, footprint: Polygon, geo: _Geometry) -> list[Wall]:
    walls: list[Wall] = []
    for a, b in edges(poly):  # polygon is CCW, so the outward normal is (dy, -dx)
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 0.3:
            continue
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        if distance_to_boundary(mid, footprint) > WALL_TOL:
            continue
        nx, ny = dy / length, -dx / length
        probe = (mid[0] + 0.1 * nx, mid[1] + 0.1 * ny)
        if point_in_polygon(probe, footprint):
            continue
        az = geo.true_bearing((nx, ny))
        walls.append(Wall(length, az, sector16(az)))
    return walls


# --------------------------------------------------------------------------- scoring


@dataclass
class _Scores:
    vci: float
    components: dict[str, float]
    room_scores: list[float]
    brahma_blocked: float
    brahma_score: float
    dipole_bearing: float
    dipole_mag: float
    dipole_score: float


def _score(
    types: list[str], geo: _Geometry, rb: RuleBase, entrance_terms: list[tuple[float, float]],
    shape_score: float, corner_fill: dict[str, float],
) -> _Scores:  # fmt: skip
    site = rb.site
    num = den = 0.0
    room_scores: list[float] = []
    room_num = room_den = 0.0
    for t, f in zip(types, geo.fractions, strict=True):
        rule = rb.rule(t)
        s = sum(f[z] * rule.value(z) for z in ZONES)
        room_scores.append(s)
        room_num += rule.weight * s
        room_den += rule.weight
    num += room_num
    den += room_den

    ent_num = sum(w * s for w, s in entrance_terms)
    ent_den = sum(w for w, _ in entrance_terms)
    num += ent_num
    den += ent_den

    forbidden = set(site["brahmasthana_forbidden"])
    blocked = (
        sum(
            ov
            for t, ov in zip(types, geo.centre_overlap, strict=True)
            if rb.canonical(t) in forbidden
        )
        / geo.grid.cell_area()
    )
    brahma = max(0.0, 1.0 - blocked)
    wb = float(site["brahmasthana_weight"])
    num += wb * brahma
    den += wb

    corner_num = corner_den = 0.0
    for z, w in site["corner_weights"].items():
        corner_num += float(w) * min(1.0, corner_fill[z])
        corner_den += float(w)
    num += corner_num
    den += corner_den

    ws = float(site["shape_weight"])
    num += ws * shape_score
    den += ws

    # Mass dipole: heaviness-weighted centroid offset from the footprint centroid.
    mx = my = msum = 0.0
    for t, a, c in zip(types, geo.areas, geo.centroids, strict=True):
        h = rb.rule(t).heaviness * a
        mx += h * (c[0] - geo.origin[0])
        my += h * (c[1] - geo.origin[1])
        msum += h
    if msum > 0:
        mx, my = mx / msum, my / msum
    mag = math.hypot(mx, my) / geo.half_diag if geo.half_diag > 0 else 0.0
    bearing = geo.true_bearing((mx, my)) if mag > 0 else 0.0
    sat = float(site["dipole_saturation"])
    delta = angular_difference(bearing, float(site["dipole_ideal_bearing"]))
    dip = 0.5 + 0.5 * math.cos(math.radians(delta)) * min(1.0, mag / sat)
    wd = float(site["dipole_weight"])
    num += wd * dip
    den += wd

    components = {
        "rooms": 100.0 * room_num / room_den if room_den else 100.0,
        "entrance": 100.0 * ent_num / ent_den if ent_den else float("nan"),
        "brahmasthana": 100.0 * brahma,
        "corners": 100.0 * corner_num / corner_den if corner_den else 100.0,
        "shape": 100.0 * shape_score,
        "mass_balance": 100.0 * dip,
    }
    return _Scores(100.0 * num / den, components, room_scores, blocked, brahma, bearing, mag, dip)


# --------------------------------------------------------------------------- optimiser


def optimise_swaps(
    types: list[str], names: list[str], geo: _Geometry, rb: RuleBase,
    entrance_terms: list[tuple[float, float]], shape_score: float, corner_fill: dict[str, float],
    area_ratio: float = 2.0, max_iter: int = 10, min_gain: float = 0.5,
) -> tuple[list[Swap], float]:  # fmt: skip
    """Greedy steepest-ascent search over pairwise exchanges of room functions.

    Only rooms whose type is ``movable`` and whose areas differ by at most
    ``area_ratio`` are exchanged. Each step applies the single best exchange;
    the search stops at a local optimum (no exchange improves the VCI by at least
    ``min_gain`` points).
    """
    current = list(types)

    def vci(ts: list[str]) -> float:
        return _score(ts, geo, rb, entrance_terms, shape_score, corner_fill).vci

    best_vci = vci(current)
    swaps: list[Swap] = []
    n = len(current)
    for _ in range(max_iter):
        best: tuple[float, int, int] | None = None
        for i in range(n):
            ri = rb.rule(current[i])
            if not ri.movable or ri.key == "other":
                continue
            for j in range(i + 1, n):
                rj = rb.rule(current[j])
                if not rj.movable or rj.key in ("other", ri.key):
                    continue
                ai, aj = geo.areas[i], geo.areas[j]
                if max(ai, aj) / min(ai, aj) > area_ratio:
                    continue
                trial = list(current)
                trial[i], trial[j] = trial[j], trial[i]
                v = vci(trial)
                if v >= best_vci + min_gain and (best is None or v > best[0]):
                    best = (v, i, j)
        if best is None:
            break
        v, i, j = best
        swaps.append(Swap(names[i], names[j], current[i], current[j], best_vci, v))
        current[i], current[j] = current[j], current[i]
        best_vci = v
    return swaps, best_vci


# --------------------------------------------------------------------------- main entry


def analyze(
    plan: FloorPlan,
    rules: RuleBase | None = None,
    *,
    climate: solar.Climate | None = None,
    optimise: bool = True,
) -> AnalysisResult:
    """Run the full Vastu + physics assessment of ``plan``."""
    rb = rules or load_rules()
    geo = _build_geometry(plan)
    grid = geo.grid
    types = [rb.canonical(r.type) for r in plan.rooms]
    names = [r.name for r in plan.rooms]

    # --- entrances
    ent_results: list[EntranceResult] = []
    entrance_terms: list[tuple[float, float]] = []
    for e in plan.entrances:
        vec = (e.position[0] - geo.origin[0], e.position[1] - geo.origin[1])
        b = geo.true_bearing(vec)
        sec = sector16(b)
        s = rb.entrance_sectors.get(sec, 0.25)
        w = rb.entrance_weight if e.main else rb.entrance_secondary_weight
        ent_results.append(EntranceResult(e.name, e.main, b, sec, s, w))
        entrance_terms.append((w, s))

    # --- site shape and corners
    fp_area = area(plan.footprint)
    bbox_area = grid.width * grid.height
    rect = fp_area / bbox_area
    aspect = max(grid.width, grid.height) / min(grid.width, grid.height)
    max_aspect = float(rb.site["max_aspect_ratio"])
    shape_score = rect * (
        1.0 if aspect <= max_aspect else max(0.0, 1.0 - (aspect - max_aspect) / 2)
    )
    corner_fill = {
        z: rect_overlap_area(geo.footprint_aligned, *grid.cell(z)) / grid.cell_area()
        for z in ("NE", "SE", "SW", "NW")
    }

    sc = _score(types, geo, rb, entrance_terms, shape_score, corner_fill)
    w_total = _total_weight(types, rb, entrance_terms)

    # --- physics per room
    site_obj = solar.Site(plan.location.latitude, plan.location.longitude,
                          plan.location.timezone) if plan.location else None  # fmt: skip
    clim = climate or solar.Climate()
    cache: dict[tuple[int, int], solar.FacadeDay] = {}

    def fday(doy: int, az: float) -> solar.FacadeDay:
        assert site_obj is not None
        key = (doy, round(az))
        if key not in cache:
            cache[key] = solar.facade_day(site_obj, doy, float(round(az)), clim)
        return cache[key]

    summer, winter = solar.DESIGN_DAYS["summer_solstice"], solar.DESIGN_DAYS["winter_solstice"]
    room_results: list[RoomResult] = []
    for idx, room in enumerate(plan.rooms):
        rule = rb.rule(types[idx])
        c_al = centroid(geo.rooms_aligned[idx])
        vec = (geo.centroids[idx][0] - geo.origin[0], geo.centroids[idx][1] - geo.origin[1])
        walls = geo.walls[idx]
        sol: dict[str, float] = {}
        if site_obj and walls:
            sum_kwh = sum(w.length * fday(summer, w.azimuth).irradiation_kwh for w in walls)
            pm = sum(w.length * fday(summer, w.azimuth).afternoon_kwh for w in walls)
            hot = max(walls, key=lambda w: fday(summer, w.azimuth).peak_sol_air)
            sol = {
                "summer_wall_kwh_per_m": sum_kwh,
                "winter_wall_kwh_per_m": sum(
                    w.length * fday(winter, w.azimuth).irradiation_kwh for w in walls
                ),
                "afternoon_fraction": pm / sum_kwh if sum_kwh > 0 else 0.0,
                "peak_sol_air": fday(summer, hot.azimuth).peak_sol_air,
                "peak_sol_air_hour": fday(summer, hot.azimuth).peak_hour,
                "hottest_wall_azimuth": hot.azimuth,
            }
        room_results.append(
            RoomResult(
                name=room.name,
                type=types[idx],
                label=rule.label,
                area=geo.areas[idx],
                centroid=(c_al[0] - grid.centre[0], c_al[1] - grid.centre[1]),
                sector=sector16(geo.true_bearing(vec)),
                zone=dominant_zone(geo.fractions[idx]),
                fractions=geo.fractions[idx],
                score=sc.room_scores[idx],
                weight=rule.weight,
                walls=walls,
                solar=sol,
            )
        )

    site_res = SiteResult(
        area=fp_area,
        bbox_area=bbox_area,
        rectangularity=rect,
        aspect_ratio=aspect,
        shape_score=shape_score,
        corner_fill=corner_fill,
        brahmasthana_blocked=sc.brahma_blocked,
        brahmasthana_score=sc.brahma_score,
        dipole_bearing=sc.dipole_bearing,
        dipole_magnitude=sc.dipole_mag,
        dipole_score=sc.dipole_score,
        orientation_skew=geo.theta - geo.theta_snap,
    )

    solar_summary: dict[str, object] = {}
    if site_obj:
        solar_summary = _solar_summary(site_obj, clim)

    findings = _findings(plan, rb, room_results, ent_results, site_res, types, geo, w_total,
                         solar_summary)  # fmt: skip

    swaps: list[Swap] = []
    opt_vci: float | None = None
    if optimise:
        swaps, opt_vci = optimise_swaps(types, names, geo, rb, entrance_terms, shape_score,
                                        corner_fill)  # fmt: skip

    return AnalysisResult(
        plan_name=plan.name,
        vci=sc.vci,
        components=sc.components,
        rooms=room_results,
        entrances=ent_results,
        site=site_res,
        findings=findings,
        swaps=swaps,
        solar_summary=solar_summary,
        optimised_vci=opt_vci,
    )


def _total_weight(
    types: list[str], rb: RuleBase, entrance_terms: list[tuple[float, float]]
) -> float:
    site = rb.site
    return (
        sum(rb.rule(t).weight for t in types)
        + sum(w for w, _ in entrance_terms)
        + float(site["brahmasthana_weight"])
        + sum(float(w) for w in site["corner_weights"].values())
        + float(site["shape_weight"])
        + float(site["dipole_weight"])
    )


def _solar_summary(site: solar.Site, clim: solar.Climate) -> dict[str, object]:
    out: dict[str, object] = {
        "latitude": site.latitude,
        "longitude": site.longitude,
        "noon_altitude": {k: solar.noon_altitude(site, d) for k, d in solar.DESIGN_DAYS.items()},
        "overhang_depth_ratio": solar.overhang_depth_ratio(site),
    }
    table = {}
    for name, doy in solar.DESIGN_DAYS.items():
        table[name] = [
            {
                "azimuth": f.azimuth,
                "irradiation_kwh": f.irradiation_kwh,
                "morning_kwh": f.morning_kwh,
                "afternoon_kwh": f.afternoon_kwh,
                "peak_sol_air": f.peak_sol_air,
                "peak_hour": f.peak_hour,
            }
            for f in solar.facade_table(site, doy, clim)
        ]
    out["facades"] = table
    return out


# --------------------------------------------------------------------------- findings


def _severity(weight: float, score: float) -> str:
    if score <= 0.25 and weight >= 8:
        return "critical"
    if score < 0.5:
        return "major"
    return "minor"


def _findings(
    plan: FloorPlan, rb: RuleBase, rooms: list[RoomResult], ents: list[EntranceResult],
    site: SiteResult, types: list[str], geo: _Geometry, w_total: float, solar_summary: dict[str, object],
) -> list[Finding]:  # fmt: skip
    out: list[Finding] = []

    for r in rooms:
        rule = rb.rule(r.type)
        if rule.weight == 0 or r.score >= 0.75:
            continue
        best = ", ".join(rule.best_zones())
        out.append(
            Finding(
                severity=_severity(rule.weight, r.score),  # type: ignore[arg-type]
                category="room",
                subject=r.name,
                message=(
                    f"{_who(r.name, rule.label)} lies mainly in the {r.zone} zone "
                    f"({ZONE_SANSKRIT[r.zone]}); placement compliance {r.score:.0%}."
                ),
                suggestion=f"Preferred zone(s): {best}. {rule.remedy}",
                traditional=rule.traditional,
                physics=rule.physics,
                impact=100.0 * rule.weight * (1.0 - r.score) / w_total,
            )
        )

    for e in ents:
        if e.score >= 0.75:
            continue
        out.append(
            Finding(
                severity="critical"
                if e.main and e.score <= 0.25
                else ("major" if e.main else "minor"),
                category="entrance",
                subject=e.name,
                message=(
                    f"{'Main' if e.main else 'Secondary'} entrance '{e.name}' is in the "
                    f"{e.sector} sector (bearing {e.bearing:.0f} deg); compliance {e.score:.0%}."
                ),
                suggestion=rb.entrance_text["remedy"],
                traditional=rb.entrance_text["traditional"],
                physics=rb.entrance_text["physics"],
                impact=100.0 * e.weight * (1.0 - e.score) / w_total,
            )
        )

    if site.brahmasthana_blocked > 0.10:
        forbidden = set(rb.site["brahmasthana_forbidden"])
        offenders = [
            r.name for r, ov, t in zip(rooms, geo.centre_overlap, types, strict=True)
            if ov > 0.05 * geo.grid.cell_area() and t in forbidden
        ]  # fmt: skip
        out.append(
            Finding(
                severity="major",
                category="site",
                subject="Brahmasthana",
                message=(
                    f"{site.brahmasthana_blocked:.0%} of the central zone is occupied by "
                    f"heavy or wet functions ({', '.join(offenders)})."
                ),
                suggestion=(
                    "Keep the centre open (living, circulation or a courtyard); relocate "
                    "toilets, stairs, kitchens and stores away from the centre."
                ),
                traditional="The Brahmasthana is the seat of Brahma and must be kept free and open.",
                physics="An open centre lets daylight and stack ventilation reach every room.",
                impact=100.0
                * float(rb.site["brahmasthana_weight"])
                * (1 - site.brahmasthana_score)
                / w_total,
            )
        )

    tol = float(rb.site["corner_tolerance"])
    for z, fill in site.corner_fill.items():
        if fill >= tol:
            continue
        w = float(rb.site["corner_weights"][z])
        sev = (
            "critical"
            if (z == "NE" and fill < 0.75)
            else ("major" if z in ("NE", "SW") else "minor")
        )
        tip = {
            "NE": "Regularise the plan by extending into the NE; if impossible, keep the cut area open, low and clean (lawn or water feature).",
            "SW": "Build up the SW: a higher, heavier boundary wall or a store/garage block closes the cut.",
            "SE": "Fill the SE cut with an outdoor kitchen platform or utility block.",
            "NW": "Fill the NW cut with a car porch or utility block.",
        }[z]
        out.append(
            Finding(
                severity=sev,  # type: ignore[arg-type]
                category="site",
                subject=f"{z} corner",
                message=f"The {z} corner zone is only {fill:.0%} built (corner cut).",
                suggestion=tip,
                traditional=f"A cut {z} ({ZONE_SANSKRIT[z]}) is a classical dosha (defect).",
                physics="Re-entrant corners increase envelope area and self-shading irregularity.",
                impact=100.0 * w * (1.0 - fill) / w_total,
            )
        )

    if site.shape_score < 0.85:
        out.append(
            Finding(
                severity="minor",
                category="site",
                subject="Plan shape",
                message=(
                    f"Rectangularity {site.rectangularity:.2f}, aspect ratio "
                    f"{site.aspect_ratio:.2f}; Vastu prefers a square or a rectangle up to 1:2."
                ),
                suggestion="Prefer regular extensions; avoid irregular or highly elongated forms.",
                traditional="Square (Chaturasra) and rectangular (Ayata) plans are auspicious.",
                physics="A compact form minimises envelope area per floor area (lower heat gain).",
                impact=100.0 * float(rb.site["shape_weight"]) * (1 - site.shape_score) / w_total,
            )
        )

    if site.dipole_score < 0.5:
        out.append(
            Finding(
                severity="major",
                category="site",
                subject="Mass balance",
                message=(
                    f"The building is heavier towards the {sector16(site.dipole_bearing)} "
                    f"(dipole bearing {site.dipole_bearing:.0f} deg, |p| = "
                    f"{site.dipole_magnitude:.3f}); Vastu requires the SW to be heaviest."
                ),
                suggestion=(
                    "Move heavy uses (stairs, stores, master bedroom, overhead tank) towards "
                    "the SW and keep the NE light and open."
                ),
                traditional="Nairutya (SW) should be the heaviest and highest; Ishanya (NE) the lightest.",
                physics="High thermal mass on the SW/W absorbs the afternoon load (time lag); light, open NE admits morning daylight.",
                impact=100.0 * float(rb.site["dipole_weight"]) * (1 - site.dipole_score) / w_total,
            )
        )

    if abs(site.orientation_skew) > 15.0:
        out.append(
            Finding(
                severity="info",
                category="site",
                subject="Orientation",
                message=(
                    f"Plan axes deviate {site.orientation_skew:+.1f} deg from the nearest cardinal "
                    "direction; zone boundaries are approximate (vidisha plot)."
                ),
                suggestion="Verify the north arrow (true vs magnetic) before acting on zone findings.",
            )
        )

    out.extend(_physics_findings(rooms, solar_summary))
    rank = {"critical": 0, "major": 1, "minor": 2, "info": 3}
    out.sort(key=lambda f: (rank[f.severity], -f.impact))
    return out


def _physics_findings(rooms: list[RoomResult], solar_summary: dict[str, object]) -> list[Finding]:
    out: list[Finding] = []
    if not solar_summary:
        return out
    facades = solar_summary["facades"]["summer_solstice"]  # type: ignore[index]
    east_peak = next(f["peak_sol_air"] for f in facades if f["azimuth"] == 90.0)
    ratio = float(solar_summary["overhang_depth_ratio"])  # type: ignore[arg-type]
    for r in rooms:
        west_walls = [w for w in r.walls if 202.5 <= w.azimuth <= 337.5]
        south_walls = [w for w in r.walls if 135.0 <= w.azimuth <= 225.0]
        east_walls = [w for w in r.walls if 22.5 <= w.azimuth <= 157.5]
        if r.type in OCCUPIED and west_walls and r.solar:
            out.append(
                Finding(
                    severity="minor",
                    category="physics",
                    subject=r.name,
                    message=(
                        f"{_who(r.name, r.label)} has {sum(w.length for w in west_walls):.1f} m of "
                        f"west-type exterior wall; summer sol-air peak {r.solar['peak_sol_air']:.1f} C "
                        f"at {_clock(r.solar['peak_sol_air_hour'])} vs {east_peak:.1f} C on an east wall."
                    ),
                    suggestion=(
                        "Shade the west wall externally (vertical fins, louvres, a tree line or a "
                        "verandah), use >= 230 mm masonry or cavity walls for time lag, and a "
                        "high-albedo finish."
                    ),
                    physics=(
                        "East and west walls receive equal daily irradiation, but the west load "
                        "coincides with the afternoon air-temperature peak, raising the sol-air peak."
                    ),
                )
            )
        if r.type in OCCUPIED and south_walls and r.solar:
            out.append(
                Finding(
                    severity="info",
                    category="physics",
                    subject=r.name,
                    message=f"{_who(r.name, r.label)} has a south-facing exterior wall.",
                    suggestion=(
                        f"Use a horizontal overhang of depth ~{ratio:.2f} x window height over "
                        "south windows: it shades them from the equinox through summer and admits "
                        "the low winter sun."
                    ),
                    physics="Profile-angle geometry: d/h = 1/tan(alpha_noon) at the equinox.",
                )
            )
        if r.type == "kitchen" and not east_walls:
            out.append(
                Finding(
                    severity="minor",
                    category="physics",
                    subject=r.name,
                    message=f"{_who(r.name, r.label)} has no east-type exterior wall (no morning sun).",
                    suggestion="Add an east-facing window or a skylight; provide an exhaust on an outside wall.",
                    physics="Morning beam radiation provides daylight and drying with low heat gain.",
                )
            )
        if r.type == "toilet" and not r.walls:
            out.append(
                Finding(
                    severity="major",
                    category="physics",
                    subject=r.name,
                    message=f"{_who(r.name, r.label)} has no exterior wall (no natural ventilation).",
                    suggestion="Provide a ventilation shaft or mechanical exhaust to the outside.",
                    physics="Moisture and odour removal require air exchange with the exterior.",
                )
            )
    return out


def _who(name: str, label: str) -> str:
    """'Kitchen' rather than "Kitchen 'Kitchen'"; 'Bed 3' (bedroom) otherwise."""
    if name.lower() in label.lower() or label.lower().startswith(name.lower()):
        return f"'{name}'"
    return f"'{name}' ({label.lower()})"


def _clock(hour: float) -> str:
    h = int(hour)
    m = round((hour - h) * 60)
    if m == 60:
        h, m = h + 1, 0
    return f"{h:02d}:{m:02d}"
