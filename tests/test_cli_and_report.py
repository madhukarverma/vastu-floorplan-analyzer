import json
from pathlib import Path

import pytest

from vastu_analyzer import analyze, to_json, to_markdown, to_text
from vastu_analyzer.cli import main
from vastu_analyzer.models import FloorPlan
from vastu_analyzer.report import grade, net_reassignment


def test_reports_render(sample_plan: FloorPlan) -> None:
    res = analyze(sample_plan)
    text = to_text(res)
    md = to_markdown(res)
    data = json.loads(to_json(res))
    assert "Vastu Compliance Index" in text
    assert "Net result" in text
    assert md.startswith("# Vastu assessment")
    assert "## Solar physics" in md
    assert data["grade"] == grade(res.vci)
    assert data["reassignment"]
    assert data["swaps"][0]["gain"] > 0
    assert {r["room"] for r in data["reassignment"]} == {n for n, _, _ in net_reassignment(res)}


@pytest.mark.parametrize(
    ("vci", "band"), [(90, "Excellent"), (75, "Good"), (60, "Fair"), (10, "Poor")]
)
def test_grade_bands(vci: float, band: str) -> None:
    assert grade(vci) == band


def test_cli_analyze_formats(
    sample_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["analyze", str(sample_path)]) == 0
    assert "VCI" in capsys.readouterr().out
    out = tmp_path / "r.json"
    assert main(["analyze", str(sample_path), "-f", "json", "-o", str(out), "--no-optimise"]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["swaps"] == []


def test_cli_plot(sample_path: Path, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    png = tmp_path / "plan.png"
    assert main(["analyze", str(sample_path), "--plot", str(png), "-o", str(tmp_path / "r.md"),
                 "-f", "md"]) == 0  # fmt: skip
    assert png.stat().st_size > 10_000


def test_cli_invalid_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"rooms": []}), encoding="utf-8")
    assert main(["analyze", str(bad)]) == 2
    assert "Invalid plan" in capsys.readouterr().err


def test_cli_solar_and_rules(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["solar", "--lat", "28.61", "--lon", "77.21", "--date", "2026-12-21"]) == 0
    out = capsys.readouterr().out
    assert "Solar noon" in out
    assert "180" in out
    assert main(["rules"]) == 0
    assert "kitchen" in capsys.readouterr().out


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "vastu" in capsys.readouterr().out
