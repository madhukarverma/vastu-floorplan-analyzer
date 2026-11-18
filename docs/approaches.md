# Solution approaches — ranked

**Problem.** Take the architectural map (floor plan) of a house as input, analyse it with
Vastu Shastra logic *and* physical science, and produce suggestions to improve the house.
**Constraint.** No AI / ML anywhere (no neural image segmentation, no OCR — Tesseract ≥ 4 is an
LSTM network).

Every non-ML solution has the same *back end*: a deterministic rule engine that reasons about
directions. The approaches differ mainly in the *front end*: how the geometry of the house
gets into the program. So the ranking is mostly about how reliably and cheaply each front end
delivers correct geometry and orientation.

## Scoring method

Each approach is scored 1–5 on six criteria (5 = best). The weighted score is
`S = Σ ω_c · x_c`.

| Code | Criterion | Weight | What it measures |
|---|---|---:|---|
| C1 | Objective fit | 0.25 | Does it actually analyse the map *and* produce Vastu suggestions? |
| C2 | Reliability / accuracy | 0.25 | Are room-to-zone assignments correct and repeatable? |
| C3 | No-AI/ML compliance | 0.15 | Fully deterministic? (Any ML disqualifies the approach.) |
| C4 | Feasibility | 0.15 | Can a student build and test it within a semester? (5 = easiest) |
| C5 | Input accessibility | 0.10 | Can a normal homeowner supply the required input? |
| C6 | Extensibility / testability | 0.10 | Easy to unit-test, extend, maintain? |

## Ranking

| Rank | Approach | C1 | C2 | C3 | C4 | C5 | C6 | **Score** |
|---:|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | **A1 Structured polygon model (JSON) + computational-geometry zoning + rule engine + solar physics**, with a click-digitiser for scanned plans | 5 | 5 | 5 | 4 | 4 | 5 | **4.75** |
| 2 | A2 Vector CAD (DXF) parsing — closed polylines on room layers + same back end | 5 | 5 | 5 | 3 | 2 | 4 | 4.30 |
| 3 | A3 Interactive GUI editor (Tkinter canvas) for drawing rooms + same back end | 5 | 4 | 5 | 2 | 4 | 3 | 4.00 |
| 4 | A4 Character-grid (ASCII/CSV matrix) map; areas by cell counting | 4 | 3 | 5 | 5 | 3 | 4 | 3.95 |
| 5 | A5 BIM/IFC parsing (IfcSpace geometry + TrueNorth) | 4 | 5 | 5 | 2 | 1 | 4 | 3.80 |
| 6 | A6 Questionnaire expert system (user states each room's direction) | 2 | 3 | 5 | 5 | 5 | 3 | 3.55 |
| 7 | A7 Classical raster image processing (threshold, morphology, contours, Hough) + manual labels | 4 | 2 | 4 | 2 | 5 | 2 | 3.10 |
| 8 | A8 Room-adjacency graph only (topology, no orientation) | 2 | 2 | 5 | 4 | 3 | 3 | 2.95 |
| ✗ | A9 CNN segmentation + OCR | – | – | 0 | – | – | – | disqualified |

## Why this order

1. **A1 — structured polygons + geometry + rules + physics (chosen).** A polygon description
   is the *canonical* representation that every other front end has to be converted into
   anyway. It is exact and unit-aware, easy to validate, and fully unit-testable. Paired with
   a click-digitiser (the user clicks room corners on a scanned plan; the program never
   interprets pixels), it accepts any plan image while keeping a human, not a model, in the
   loop. It also has the most room to grow: the other front ends become simple adapters.
2. **A2 — DXF parsing.** As exact as A1 and closest to how architects actually work. But it
   needs a CAD file with disciplined layers and labels, which most homeowners do not have, and
   DXF files vary a lot. The best plan is to add it later as an adapter onto A1.
3. **A3 — GUI editor.** The best user experience, but building and testing the GUI would take
   up most of a semester, and snap-to-grid drawing loses accuracy. The core value still comes
   from A1's engine.
4. **A4 — character grid.** The simplest to build and very good for teaching, but resolution is
   capped by the cell size. Zone fractions are quantised, and diagonal or narrow rooms are
   badly approximated.
5. **A5 — IFC/BIM.** The richest data (named spaces and a stored true-north vector), but almost
   no Indian residential project produces an IFC model, and the dependency is heavy.
6. **A6 — questionnaire.** Trivial to build, but it does not analyse a map at all. It leaves the
   geometry to the user's own judgement, which is exactly the error source we want to remove.
7. **A7 — classical image processing.** Fully automatic and not ML, but fragile. Door gaps break
   room enclosures, and hatching, text and dimension lines create false contours. Rooms still
   need manual labels because OCR is excluded. Confidently wrong zone assignments are worse
   than none. It also sits at the edge of the "no image processing" instruction.
8. **A8 — adjacency graph.** It throws away orientation, the one quantity Vastu depends on.

## Decision

Implement **A1**.

- **The classroom code** keeps A1 simple. Rooms are rectangles drawn in a small window app,
  scored against a 3×3 grid with a readable rule book. The sun check uses fixed numbers from
  the paper.
- **The full research version** (polygons, solar-position physics, optimiser) is kept at tag
  `v1.0.0` and described in the paper ([docs/paper](paper/)).

A2 (DXF), A3 (GUI) and A4 (grid) can still be added later as other ways to enter a house.
The step-by-step procedure is in [procedure.md](procedure.md).
