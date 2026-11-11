"""Command-line interface: ``vastu analyze|solar|rules|digitize``."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, solar
from .engine import analyze
from .loader import PlanValidationError, load_plan
from .report import to_json, to_markdown, to_text
from .rules import load_rules


def _cmd_analyze(args: argparse.Namespace) -> int:
    try:
        plan = load_plan(args.plan)
    except PlanValidationError as exc:
        print("Invalid plan:", file=sys.stderr)
        for e in exc.errors:
            print(f"  - {e}", file=sys.stderr)
        return 2
    rules = load_rules(args.rules) if args.rules else None
    result = analyze(plan, rules, optimise=not args.no_optimise)
    render = {"text": to_text, "md": to_markdown, "json": to_json}[args.format]
    out = render(result)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Report written to {args.output} (VCI {result.vci:.1f})")
    else:
        print(out)
    if args.plot:
        from .plotting import plot_plan

        plot_plan(plan, result, args.plot, title=f"{plan.name} - VCI {result.vci:.1f}")
        print(f"Plan figure written to {args.plot}")
    return 0


def _cmd_solar(args: argparse.Namespace) -> int:
    site = solar.Site(args.lat, args.lon, args.tz)
    date = dt.date.fromisoformat(args.date)
    doy = date.timetuple().tm_yday
    clim = solar.Climate(t_max=args.tmax, t_min=args.tmin)
    print(f"Site {args.lat:.4f}, {args.lon:.4f} (UTC{args.tz:+g}), {date.isoformat()} (day {doy})")
    noon = solar.solar_noon_hour(site, doy)
    print(f"Solar noon {noon:.2f} h local, altitude {solar.noon_altitude(site, doy):.2f} deg")
    print(" Wall   Total kWh/m2   AM    PM   Peak T_sa  at")
    for f in solar.facade_table(site, doy, clim):
        h = int(f.peak_hour)
        print(
            f" {f.azimuth:4.0f}   {f.irradiation_kwh:10.2f}  {f.morning_kwh:4.2f}  "
            f"{f.afternoon_kwh:4.2f}   {f.peak_sol_air:7.1f}  {h:02d}:{round((f.peak_hour - h) * 60):02d}"
        )
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    rb = load_rules(args.rules) if args.rules else load_rules()
    print(f"Rule base v{rb.version}")
    zones = rb.ZONES
    print(f"{'type':<16}{'w':>4}  " + " ".join(f"{z:>4}" for z in zones))
    for key, r in rb.rooms.items():
        if key == "other":
            continue
        print(f"{key:<16}{r.weight:>4.0f}  " + " ".join(f"{r.zones[z]:>4.2f}" for z in zones))
    return 0


def _cmd_digitize(args: argparse.Namespace) -> int:  # pragma: no cover - interactive
    from .digitize import digitize

    digitize(args.image, args.output)
    print(f"Plan written to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vastu",
        description="Deterministic Vastu Shastra + building-physics assessment of floor plans.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="assess a floor-plan JSON file")
    a.add_argument("plan", help="path to the plan JSON")
    a.add_argument("-f", "--format", choices=("text", "md", "json"), default="text")
    a.add_argument("-o", "--output", help="write the report to this file")
    a.add_argument("--plot", help="write an annotated plan image (PNG/PDF/SVG)")
    a.add_argument("--rules", help="custom rules JSON (defaults to the bundled rule base)")
    a.add_argument("--no-optimise", action="store_true", help="skip the room-exchange optimiser")
    a.set_defaults(func=_cmd_analyze)

    s = sub.add_parser("solar", help="facade irradiance / sol-air table for a site and date")
    s.add_argument("--lat", type=float, required=True)
    s.add_argument("--lon", type=float, required=True)
    s.add_argument("--tz", type=float, default=5.5)
    s.add_argument("--date", default=f"{dt.date.today().year}-06-21")
    s.add_argument("--tmax", type=float, default=39.0)
    s.add_argument("--tmin", type=float, default=28.0)
    s.set_defaults(func=_cmd_solar)

    r = sub.add_parser("rules", help="print the zone-value matrix of the rule base")
    r.add_argument("--rules", help="custom rules JSON")
    r.set_defaults(func=_cmd_rules)

    d = sub.add_parser("digitize", help="click-trace a scanned plan image into plan JSON")
    d.add_argument("image")
    d.add_argument("-o", "--output", required=True)
    d.set_defaults(func=_cmd_digitize)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
