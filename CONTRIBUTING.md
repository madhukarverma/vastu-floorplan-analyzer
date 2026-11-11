# Contributing

Thanks for your interest in improving **vastu-floorplan-analyzer**.

## Ground rules

- **No AI/ML.** The project's core constraint is that every inference is deterministic and
  auditable. Pull requests that add learned models, neural OCR or image segmentation will not
  be merged.
- **Rules are data.** Vastu placement values live in
  [`src/vastu_analyzer/data/rules.json`](src/vastu_analyzer/data/rules.json). When you change
  a value, cite your source in the pull request.
- **Physics must be validated.** Any new physical model needs a test against an analytic or
  published reference value (see `tests/test_solar.py`).

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

All checks must pass. Coverage must stay at or above 85 %.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), for example
`feat(engine): add 32-pada entrance model` or `fix(solar): handle polar night`.

## Reporting issues

Use the issue templates. For a wrong assessment, attach the plan JSON; it contains no personal
data beyond what you put in it.
