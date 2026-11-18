# Contributing

Thanks for your interest in improving **vastu-floorplan-analyzer**.

## Ground rules

- **No AI/ML.** The project's core constraint is that every inference is deterministic and
  auditable. Pull requests that add learned models, neural OCR or image segmentation will not
  be merged.
- **Keep it simple.** This is a teaching project: readable code beats clever code.
- **Rules live in one place.** Vastu placement values are in
  [`src/vastu_analyzer/rules.py`](src/vastu_analyzer/rules.py). When you change a value,
  cite your source in the pull request.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
pre-commit install
```

## Before opening a pull request

```bash
ruff check . && ruff format --check .
mypy
pytest --cov
```

All checks must pass, and coverage must stay at or above 85 %. Also try the window app by hand (`vastu app`).

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), for example
`feat(rules): add garage rules` or `fix(app): keep door on the wall`.

## Reporting issues

Use the issue templates. For a wrong assessment, attach the plan JSON; it contains no personal
data beyond what you put in it.
