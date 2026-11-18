# Step-by-step procedure

![Simple flowchart of the analysis](figures/simple_flowchart.svg)

Each step below says **what happens**, gives a **small example**, and names **the code** that
does it.

---

## Step 1 — Trace every room (`house.py`)

The house is a rectangle, for example 12 m wide and 15 m deep. Every room is a rectangle
inside it, described by four numbers:

| Number | Meaning |
|---|---|
| `x` | metres from the **left** edge of the house |
| `y` | metres from the **top** edge of the house |
| `w` | width of the room |
| `h` | height (depth) of the room |

Example: `Kitchen: x=6, y=0, w=4, h=5` is a 4 m × 5 m kitchen at the top, 6 m from the left.

You can draw the rooms with the mouse in the window app (`vastu app`) or type them into a JSON
file ([format](input-format.md)).

## Step 2 — Check the drawing (`house.py → check_house`)

The program refuses to score a broken drawing. It checks that:

- every room is inside the house,
- no two rooms overlap (overlap = shared width × shared height > 0),
- north is one of up / right / down / left.

## Step 3 — Find north (`compass.py → side_to_compass`)

You tell the program which way north points on your drawing. If north points **right**, the
top of the drawing faces **west**, so we "turn the compass" by the right number of
quarter-turns.

## Step 4 — Put a 3×3 grid on top (`compass.py → grid_boxes`)

The house is cut into 9 equal boxes, like a tic-tac-toe board. This is the simplest form of the
**Vastu-Purusha mandala**.

```
+------+------+------+
|  NW  |  N   |  NE  |
+------+------+------+
|  W   |  C   |  E   |     C = Centre (Brahmasthan)
+------+------+------+
|  SW  |  S   |  SE  |
+------+------+------+
```

## Step 5 — Which box is each room in? (`compass.py → room_shares`)

For each room we measure how much of it falls in each box.

Example: a living room 6 m wide at the top-left gives `NW 67%, N 33%`.

## Step 6a — Vastu rules (`rules.py`)

Every room type has favourite boxes:

| Level | Points | Example: kitchen |
|---|---|---|
| best | 10 | SE (fire corner, Agni) |
| good | 7 | NW |
| okay | 5 | E, S |
| bad | 0 | NE, N, SW, Centre |
| not listed | 3 | W |

The **main door** and the **open centre** are also checked: toilets, kitchens, stairs and
stores should not sit in the centre.

## Step 6b — Sun check (`sun.py`)

Each room's **outside walls** are found (a wall touching the edge of the house), and simple
tips are given:

- A bedroom or living room with a **west** wall: that wall reaches about **65 °C** on a summer
  afternoon in Delhi (an east wall reaches about 58.6 °C), so add shade.
- A kitchen with no **east** wall gets no morning sun.
- A toilet with no outside wall needs an exhaust fan.

## Step 7 — Give a score (`scoring.py`)

```
room points  = sum of (share in box × points of that box)                   → 0 to 10
house score  = 100 × sum(importance × points) / sum(importance × 10)         → 0 to 100
```

Importance: kitchen, master bedroom, pooja, toilet and main door count **3×**; bedrooms,
living room, stairs and the open centre count **2×**; everything else counts **1×**.

| Score | Grade |
|---|---|
| 80–100 | Excellent |
| 60–80 | Good |
| 40–60 | Needs work |
| 0–40 | Poor |

## Step 8 — Swap rooms (`suggestions.py → best_swaps`)

Moving walls is expensive, but changing what a room is **used for** is cheap. So the program:

1. tries swapping every pair of rooms of similar size (the bigger one at most 1.5× the
   smaller; stairs and corridors never move),
2. keeps the swap that raises the score the most,
3. repeats until no swap helps by at least 1 point.

## Step 9 — To-do list and report card (`suggestions.py`, `report.py`)

All problems are listed, the ones that cost the most points first. Each one gives:

- **what to do** ("Move the kitchen towards the south-east"),
- **why** (the Vastu reason and the science reason),
- **a tip** if moving is not possible.

The app also colours each room: green (7–10), yellow (4–7), red (0–4).
