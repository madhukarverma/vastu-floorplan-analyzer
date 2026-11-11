"""Generate every figure and the numerical results quoted in the paper.

Run:  python paper/figures.py        (writes docs/figures/*.png and paper/build/results.json)
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import itertools

from vastu_analyzer import analyze, load_plan, solar
from vastu_analyzer.models import North
from vastu_analyzer.plotting import plot_plan
from vastu_analyzer.report import net_reassignment

FIG = ROOT / "docs" / "figures"
BUILD = ROOT / "paper" / "build"
FIG.mkdir(parents=True, exist_ok=True)
BUILD.mkdir(parents=True, exist_ok=True)

# Palette (validated reference instance): categorical slots 1-4 and chart chrome.
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRIDC, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
COL_W = 3.37  # inches, one column of the paper

plt.rcParams.update(
    {
        "font.family": "STIXGeneral",
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.grid": True,
        "grid.color": GRIDC,
        "grid.linewidth": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.4,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "axes.linewidth": 0.6,
        "savefig.dpi": 400,
        "figure.dpi": 150,
    }
)

DELHI = solar.Site(28.6139, 77.2090, 5.5)


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIG / name, bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)
    print("wrote", FIG / name)


# --------------------------------------------------------------------------- flowchart


def flowchart() -> None:
    fig, ax = plt.subplots(figsize=(COL_W, 6.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 22)
    ax.axis("off")
    fill_proc, fill_io, fill_dec, fill_term = "#eef4fc", "#fdf0ea", "#fdf6e3", "#f0efec"

    def box(x, y, w, h, text, kind="proc"):  # type: ignore[no-untyped-def]
        if kind == "dec":
            pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
            ax.add_patch(Polygon(pts, closed=True, fc=fill_dec, ec=INK2, lw=0.8))
        elif kind == "io":
            sk = 0.35
            pts = [(x - w / 2 + sk, y + h / 2), (x + w / 2 + sk, y + h / 2),
                   (x + w / 2 - sk, y - h / 2), (x - w / 2 - sk, y - h / 2)]  # fmt: skip
            ax.add_patch(Polygon(pts, closed=True, fc=fill_io, ec=INK2, lw=0.8))
        else:
            style = (
                "round,pad=0.02,rounding_size=0.55"
                if kind == "term"
                else "round,pad=0.02,rounding_size=0.12"
            )
            fc = fill_term if kind == "term" else fill_proc
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=style, fc=fc,
                                        ec=INK2, lw=0.8))  # fmt: skip
        ax.text(x, y, text, ha="center", va="center", fontsize=6.3, color=INK, linespacing=1.15)

    def arrow(x0, y0, x1, y1, label=None, lx=0.0, ly=0.0):  # type: ignore[no-untyped-def]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops={"arrowstyle": "-|>", "color": INK2, "lw": 0.8,
                                "shrinkA": 0, "shrinkB": 0, "mutation_scale": 7})  # fmt: skip
        if label:
            ax.text((x0 + x1) / 2 + lx, (y0 + y1) / 2 + ly, label, fontsize=6, color=INK2,
                    ha="center", va="center", style="italic")  # fmt: skip

    cx = 5.0
    W, H = 8.6, 1.15
    ys = [21.2, 19.6, 18.0, 16.4, 14.8, 13.2]
    box(
        cx,
        ys[0],
        7.0,
        0.95,
        "START: architectural plan of the house\n(scan / PDF / CAD / sketch)",
        "term",
    )
    box(
        cx,
        ys[1],
        7.6,
        H,
        "Step 1 - Digitise: footprint, room polygons + labels,\ndoors, north arrow, scale  $\\rightarrow$  plan.json",
        "io",
    )
    box(
        cx,
        ys[2],
        W,
        H,
        "Step 2 - Validate & normalise: units $\\rightarrow$ m, CCW order,\nclosure, non-zero area, rooms inside footprint",
    )
    box(
        cx,
        ys[3],
        W,
        H,
        "Step 3 - Orientation: $\\theta_{true}=\\theta_{arrow}-D$ (WMM2025);\nrotate by $\\mathbf{R}(\\theta_s)$ to the cardinal frame",
    )
    box(
        cx,
        ys[4],
        W,
        H,
        "Step 4 - Geometry: shoelace area, centroid,\nexterior walls + outward normals $\\hat{n}$",
    )
    box(
        cx,
        ys[5],
        W,
        H,
        "Step 5 - Zoning: 3$\\times$3 Vastu-Purusha grid;\nmembership $f_z$ by polygon clipping; 16-sector bearings",
    )
    for a, b in itertools.pairwise(ys):
        arrow(cx, a - 0.5 if a == ys[0] else a - H / 2, cx, b + H / 2)

    # parallel engines
    yl = 11.25
    box(
        2.55,
        yl,
        4.6,
        1.75,
        "Step 6a - Vastu rule engine\nroom-zone values $v_t(z)$,\nentrance sector, Brahmasthana,\ncorner cuts, shape, mass dipole",
    )
    box(
        7.55,
        yl,
        4.4,
        1.75,
        "Step 6b - Physics engine\nNOAA sun position, Meinel\nDNI, facade irradiation $H(\\gamma)$,\nsol-air temperature $T_{sa}$",
    )
    arrow(cx, ys[5] - H / 2, 2.55, yl + 0.875)
    arrow(cx, ys[5] - H / 2, 7.55, yl + 0.875)

    y7 = 9.0
    box(
        cx,
        y7,
        W,
        H,
        "Step 7 - Score: $s_r=\\Sigma_z\\, f_z\\,v_t(z)$;\nVCI $=100\\,\\Sigma_k w_k s_k\\,/\\,\\Sigma_k w_k$",
    )
    arrow(2.55, yl - 0.875, cx - 1.2, y7 + H / 2)
    arrow(7.55, yl - 0.875, cx + 1.2, y7 + H / 2)

    y8 = 6.75
    box(cx, y8, 6.2, 2.0, "VCI $\\geq$ target and\nno critical dosha?", "dec")
    arrow(cx, y7 - H / 2, cx, y8 + 1.0)

    # optimiser loop on the right
    ox_, ow_ = 8.15, 2.9
    box(
        ox_,
        4.6,
        ow_,
        1.9,
        "Step 8 - Optimiser:\npairwise exchange\nof room uses\n($\\Delta$VCI $\\geq$ 0.5)",
    )
    ax.plot([cx + 3.1, ox_], [y8, y8], color=INK2, lw=0.8)
    arrow(ox_, y8, ox_, 4.6 + 0.95, "no", lx=0.3, ly=0.25)
    ax.plot([ox_ + ow_ / 2, 9.95, 9.95], [4.6, 4.6, y7], color=INK2, lw=0.8)
    arrow(9.95, y7, cx + W / 2, y7)
    ax.text(
        10.1, 6.9, "re-score", rotation=90, fontsize=5.8, color=INK2, va="center", style="italic"
    )

    y9 = 3.0
    box(
        cx - 1.4,
        y9,
        6.0,
        1.3,
        "Step 9 - Suggestions: prioritised\nVastu remedies + physics mitigations",
    )
    arrow(cx, y8 - 1.0, cx - 1.4, y9 + 0.65, "yes", lx=0.35, ly=0.0)
    ax.plot([ox_, ox_], [4.6 - 0.95, y9], color=INK2, lw=0.8)
    arrow(ox_, y9, cx - 1.4 + 3.0, y9)
    ax.text(ox_ + 0.15, y9 + 0.35, "exchanges", fontsize=5.8, color=INK2, style="italic")
    y10 = 1.0
    box(
        cx - 1.4,
        y10,
        6.0,
        0.95,
        "END: report (text / Markdown / JSON)\n+ annotated zone map",
        "term",
    )
    arrow(cx - 1.4, y9 - 0.65, cx - 1.4, y10 + 0.475)
    save(fig, "fig1_flowchart.png")


# --------------------------------------------------------------------------- plans


TYPE_ABBR = {"living": "Liv", "bedroom": "Bed", "kitchen": "Kit", "pooja": "Pj", "toilet": "WC",
             "master_bedroom": "MB", "store": "Sto", "utility": "Ut", "dining": "Din"}  # fmt: skip


def plans(sample, res, optimised_plan, opt_res) -> None:  # type: ignore[no-untyped-def]
    sample_types = {r.name: r.type for r in res.rooms}
    abbrev = {"Living Room": "Liv", "Kitchen": "Kit", "Toilet 1": "T1", "Utility": "Ut",
              "Bedroom 2": "B2", "Dining": "Din", "Staircase": "St", "Pooja": "Pj",
              "Store": "Sto", "Master Bedroom": "MB", "Toilet 2": "T2", "Foyer": "Foy",
              "Bedroom 3": "B3"}  # fmt: skip
    fig, axes = plt.subplots(1, 2, figsize=(COL_W, 2.55))
    for ax, plan, r, ttl in ((axes[0], sample, res, f"(a) as built, VCI = {res.vci:.1f}"),
                             (axes[1], optimised_plan, opt_res, f"(b) re-assigned, VCI = {opt_res.vci:.1f}")):  # fmt: skip
        p2 = copy.deepcopy(plan)
        r2 = copy.deepcopy(r)
        for room, rr in zip(p2.rooms, r2.rooms, strict=True):
            short = abbrev.get(room.name, room.name[:3])
            orig = next(o for o in sample.rooms if o.name == room.name)
            changed = sample_types[orig.name] != rr.type
            arrow_to = r"$\rightarrow$" + TYPE_ABBR.get(rr.type, rr.type[:3])
            rr.name = f"{short}\n{arrow_to}" if changed else short
        plot_plan(p2, r2, ax=ax, label_size=4.3, zone_size=4.6, arrow_size=6, marker_size=3.5)
        ax.set_title(ttl, fontsize=7, color=INK)
        ax.tick_params(labelsize=5.5)
        ax.xaxis.label.set_size(6)
        ax.yaxis.label.set_size(6)
        ax.grid(False)
    axes[1].set_ylabel("")
    fig.tight_layout(w_pad=0.6)
    save(fig, "fig2_plans.png")


# --------------------------------------------------------------------------- physics figures


def irradiation_vs_azimuth() -> dict[str, list[float]]:
    az = list(range(0, 361, 5))
    days = [
        ("summer_solstice", "21 Jun", S1),
        ("equinox", "21 Mar", S2),
        ("winter_solstice", "21 Dec", S3),
    ]
    fig, ax = plt.subplots(figsize=(COL_W, 2.3))
    out: dict[str, list[float]] = {}
    for key, label, c in days:
        doy = solar.DESIGN_DAYS[key]
        h = [solar.facade_day(DELHI, doy, float(a), step_minutes=10).irradiation_kwh for a in az]
        out[key] = h
        ax.plot(az, h, color=c, label=label)
        i = az.index(180) if key == "equinox" else h.index(max(h))
        ax.annotate(label, (az[i], h[i]), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=6.5, color=INK2)  # fmt: skip
    ax.set_xlim(0, 360)
    ax.set_xticks(range(0, 361, 45))
    ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"])
    ax.set_xlabel(r"wall outward normal $\gamma$")
    ax.set_ylabel(r"$H(\gamma)$  (kWh m$^{-2}$ day$^{-1}$)")
    ax.set_ylim(0, 6)
    ax.legend(loc="upper right", frameon=False, ncol=3, bbox_to_anchor=(1.0, 1.14))
    save(fig, "fig3_irradiation_azimuth.png")
    return out


def sol_air_curves() -> dict[str, float]:
    clim = solar.Climate()
    doy = solar.DESIGN_DAYS["summer_solstice"]
    noon = solar.solar_noon_hour(DELHI, doy)
    hours = [h / 4 for h in range(0, 24 * 4 + 1)]
    fig, ax = plt.subplots(figsize=(COL_W, 2.35))
    peaks: dict[str, float] = {}
    for name, az, c in (("E", 90.0, S1), ("W", 270.0, S2), ("S", 180.0, S3), ("N", 0.0, S4)):
        ts = []
        for t in hours:
            sun = solar.sun_position(DELHI, doy, t)
            irr, _ = solar.vertical_irradiance(sun, az, clim.albedo)
            ts.append(clim.air_temperature(t - noon + 12) + clim.absorptance * irr / clim.h_out)
        ax.plot(hours, ts, color=c, label=f"{name} wall")
        i = ts.index(max(ts))
        peaks[name] = max(ts)
        ax.annotate(name, (hours[i], ts[i]), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=6.5, color=INK2)  # fmt: skip
    air = [clim.air_temperature(t - noon + 12) for t in hours]
    ax.plot(hours, air, color=MUTED, lw=1.0, ls=(0, (4, 2)), label="air $T_o$")
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xlabel("local time (IST, h)")
    ax.set_ylabel(r"$T_{sa}$ (°C)")
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.set_ylim(24, 70)
    save(fig, "fig4_sol_air.png")
    return peaks


def vci_vs_rotation(sample, compliant) -> dict[str, list[float]]:  # type: ignore[no-untyped-def]
    thetas = list(range(0, 360, 3))
    out: dict[str, list[float]] = {"theta": [float(t) for t in thetas]}
    fig, ax = plt.subplots(figsize=(COL_W, 2.2))
    for plan, label, c in ((compliant, "reference plan", S1), (sample, "as-built plan", S2)):
        v = []
        for t in thetas:
            p = copy.deepcopy(plan)
            p.north = North(angle_deg=float(t))
            v.append(analyze(p, optimise=False).vci)
        out[label] = v
        ax.plot(thetas, v, color=c, label=label, drawstyle="steps-mid")
    ax.set_xlim(0, 357)
    ax.set_xticks(range(0, 361, 45))
    ax.set_xlabel(r"north-arrow angle $\theta$ on the drawing (deg)")
    ax.set_ylabel("VCI")
    ax.set_ylim(20, 100)
    ax.legend(loc="lower right", frameon=False)
    save(fig, "fig5_vci_rotation.png")
    return out


def latitude_dependence() -> dict[str, list[float]]:
    lats = [8 + 0.5 * k for k in range(0, 55)]  # 8 N .. 35 N
    doy = solar.DESIGN_DAYS["summer_solstice"]
    fig, ax = plt.subplots(figsize=(COL_W, 2.2))
    out: dict[str, list[float]] = {"lat": lats}
    for name, az, c in (("E/W", 90.0, S1), ("S", 180.0, S3), ("N", 0.0, S4)):
        h = [solar.facade_day(solar.Site(lat, 78.0, 5.5), doy, az, step_minutes=10).irradiation_kwh
             for lat in lats]  # fmt: skip
        out[name] = h
        ax.plot(lats, h, color=c, label=f"{name} wall")
        dy = {"S": 5, "N": -5}.get(name, 0)
        ax.annotate(name, (lats[-1], h[-1]), xytext=(3, dy), textcoords="offset points",
                    va="center", fontsize=6.5, color=INK2)  # fmt: skip
    ax.axvline(23.44, color=MUTED, lw=0.8, ls=(0, (3, 2)))
    ax.text(23.8, 0.15, "Tropic of Cancer", fontsize=6, color=INK2, va="bottom")
    ax.set_xlim(8, 37)
    ax.set_xlabel(r"latitude $\varphi$ (°N)")
    ax.set_ylabel(r"$H$ on 21 Jun (kWh m$^{-2}$ day$^{-1}$)")
    ax.set_ylim(0, 5)
    ax.legend(loc="upper center", frameon=False, ncol=3, bbox_to_anchor=(0.5, 1.15))
    save(fig, "fig6_latitude.png")
    return out


# --------------------------------------------------------------------------- main


def apply_reassignment(plan, res):  # type: ignore[no-untyped-def]
    p = copy.deepcopy(plan)
    new_use = {n: b for n, _, b in net_reassignment(res)}
    for room in p.rooms:
        if room.name in new_use:
            room.type = new_use[room.name]
    return p


def main() -> None:
    sample = load_plan(ROOT / "examples" / "sample_3bhk_delhi.json")
    compliant = load_plan(ROOT / "examples" / "compliant_3bhk.json")
    res = analyze(sample)
    opt_plan = apply_reassignment(sample, res)
    opt_res = analyze(opt_plan, optimise=False)
    comp_res = analyze(compliant)

    flowchart()
    plans(sample, res, opt_plan, opt_res)
    h = irradiation_vs_azimuth()
    peaks = sol_air_curves()
    rot = vci_vs_rotation(sample, compliant)
    lat = latitude_dependence()

    from vastu_analyzer.report import to_dict

    results = {
        "sample": to_dict(res),
        "optimised": to_dict(opt_res),
        "compliant": to_dict(comp_res),
        "irradiation_azimuth": h,
        "sol_air_peaks": peaks,
        "rotation": {
            k: (v if k == "theta" else {"min": min(v), "max": max(v), "mean": sum(v) / len(v)})
            for k, v in rot.items()
        },
        "latitude": {k: [v[0], v[-1]] for k, v in lat.items()},
        "delhi": {
            "noon_alt": {k: solar.noon_altitude(DELHI, d) for k, d in solar.DESIGN_DAYS.items()},
            "solar_noon": {
                k: solar.solar_noon_hour(DELHI, d) for k, d in solar.DESIGN_DAYS.items()
            },
            "overhang": solar.overhang_depth_ratio(DELHI),
            "dni_noon_summer": solar.direct_normal_irradiance(
                solar.noon_altitude(DELHI, solar.DESIGN_DAYS["summer_solstice"])
            ),
        },
    }
    (BUILD / "results.json").write_text(
        json.dumps(results, indent=1, default=float), encoding="utf-8"
    )
    print(
        f"VCI as-built {res.vci:.1f}, re-assigned {opt_res.vci:.1f}, reference {comp_res.vci:.1f}"
    )
    print("rotation:", {k: v for k, v in results["rotation"].items() if k != "theta"})
    print("sol-air peaks:", {k: round(v, 1) for k, v in peaks.items()})
    _ = math


if __name__ == "__main__":
    main()
