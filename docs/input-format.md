# House file format

A house is saved as a small JSON file. The window app writes this file for you with **Save...**,
but you can also type it by hand.

```json
{
  "name": "My house",
  "width": 12,
  "depth": 15,
  "north": "up",
  "rooms": [
    {"name": "Kitchen", "type": "kitchen", "x": 8, "y": 10, "w": 4, "h": 5},
    {"name": "Hall",    "type": "living",  "x": 0, "y": 0,  "w": 8, "h": 5}
  ],
  "door": {"x": 9, "y": 0}
}
```

| Field | Meaning |
|---|---|
| `width`, `depth` | Size of the house in metres |
| `north` | Where north points on your drawing: `up`, `right`, `down` or `left` |
| `rooms` | List of rectangles: `x` from the left, `y` from the top, `w` wide, `h` deep (metres) |
| `door` | The main door, a point on an outside wall (optional) |

## Room types

`kitchen`, `master_bedroom`, `bedroom`, `living`, `dining`, `pooja`, `toilet`, `staircase`,
`study`, `store`, `open_space`, `utility`, `circulation`.

Everyday names work too: `bathroom`, `wc`, `puja`, `hall`, `stairs`, `balcony`,
`verandah`, `corridor`, `foyer`, ... (see `ALIASES` in
[`rules.py`](../src/vastu_analyzer/rules.py)). Unknown types are drawn but not scored.
