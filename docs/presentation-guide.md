# Presentation guide (about 10 minutes)

## Slide plan

| # | Slide | What to say (in one or two lines) |
|---|---|---|
| 1 | **Title**: *Vastu Checker for House Maps* | "A Python program that reads a house map and gives a Vastu score out of 100, with suggestions." |
| 2 | **The problem** | Vastu advice is usually manual and differs between people. We wanted a clear, repeatable checker. Rule: **no AI or ML**. |
| 3 | **8 approaches, ranked** (table from [approaches.md](approaches.md)) | We compared image processing, CAD files, a questionnaire, ... and picked *rooms as rectangles + rules*: simple, exact and easy to test. |
| 4 | **The flowchart** ([simple_flowchart.svg](figures/simple_flowchart.svg)) | Walk through the 9 steps: map → grid → rules + sun → score → swaps → to-do list. |
| 5 | **The 3×3 grid** | Tic-tac-toe board = the Vastu-Purusha mandala. Each box is a direction; the centre is the Brahmasthan. |
| 6 | **The rule book** (show `rules.py`, the kitchen entry) | best = 10, good = 7, okay = 5, bad = 0. Kitchen best in the south-east (Agni, fire). |
| 7 | **The two formulas** | Room points = weighted average by area share. House score = importance-weighted average × 10. |
| 8 | **The science part** | East and west walls get the same sunshine, but the west wall gets it in the hot afternoon → about 65 °C vs 58.6 °C. That is a real reason behind "keep the west heavy". |
| 9 | **LIVE DEMO** | See the demo script below. |
| 10 | **Results** | Sample house 48.2 → 67.2 after 3 swaps; well-planned house 91.4. |
| 11 | **Limits and future work** | Rectangles only, one door, Delhi sun numbers. Next: L-shaped rooms, more cities, reading CAD files. |

## Live demo script (3 minutes)

1. Run `vastu app`, then click **Load sample**.
   *"This is a normal builder flat: 12 by 15 metres, 14 rooms."*
2. Click **ANALYSE**.
   *"Score 48 out of 100. Red rooms are in a bad spot: the kitchen is in the north-east,
   which Vastu says belongs to water and prayer, not fire."*
3. Scroll the report to **STEP 8**.
   *"The program suggests swapping the kitchen and bedroom 3. That alone gives about +10 points."*
4. Click **Open...**, choose `examples/good_house.json`, then **ANALYSE**: 91.4, Excellent.
   Now change **North points** to `down` and click **ANALYSE** again: 35.0, Poor.
   *"Exactly the same rooms, just built facing the other way. The score falls from 91 to 35.
   Direction is everything in Vastu."*
5. Click **Clear**, draw a kitchen in the bottom-right corner, then **ANALYSE**.
   *"Kitchen in the south-east: green, 10 out of 10."*

> Tip: practise once on the computer you will present from. If `vastu` is not found, use
> `python -m vastu_analyzer app` instead.

## Questions you may be asked

| Question | Short answer |
|---|---|
| Did you use AI? | No. Every result comes from rules in `rules.py` and simple arithmetic. You can trace any score by hand. |
| Why rectangles? | Most rooms are rectangles, and the maths (overlap = width × height) stays easy to explain. |
| Where do the rules come from? | Classical texts (Mayamata, Manasara) as summarised by modern Vastu guides; where sources disagree we took the common view. |
| Is Vastu scientific? | Some rules match physics (sun and heat), as our sun check shows. Others are cultural; the tool reports both honestly. |
| What if my house faces another way? | Set "North points". The grid labels turn, and the score changes. |
| How do you know the code is correct? | 12 automated tests, one per step (e.g. "a kitchen in the SE gets 10 points"), run on every change by GitHub Actions. |
| Can I change the rules? | Yes. Edit `rules.py`; no other code changes are needed. |
