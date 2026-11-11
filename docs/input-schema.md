# Plan file schema (v1)

A plan is a UTF-8 JSON object. Coordinates are in the **drawing frame**: x points right on the
sheet and y points up. Do not repeat the first vertex at the end of a polygon.

| Key | Type | Required | Notes |
|---|---|:-:|---|
| `schema_version` | string | no | `"1.0"` (major version must be 1) |
| `name` | string | no | Shown in reports |
| `units` | string | no | `m` (default), `cm`, `mm`, `ft`, `in`; all values are converted to metres |
| `north` | object or number | no | `{"angle_deg": 0, "reference": "true" \| "magnetic", "declination_deg": 0}`. A bare number is shorthand for `angle_deg`. |
| `location` | object | no | `{"latitude": 28.61, "longitude": 77.21, "timezone": 5.5}`. Enables the physics engine. |
| `footprint` | `[[x, y], ...]` | **yes** | Outer wall outline |
| `rooms` | array | **yes** | `{"name": str, "type": str, "polygon": [[x, y], ...]}` |
| `entrances` | array | no | `{"name": str, "position": [x, y], "main": bool}` |
| `metadata` | object | no | Free-form, passed through to reports |

**`north.angle_deg`** is the direction the plan's north arrow points, measured **clockwise from
the sheet's up direction**. An arrow pointing straight up is `0`; an arrow pointing right is
`90`. For a magnetic arrow, give `declination_deg` (east positive). Values for Indian cities
are in Appendix B of the paper. The program uses `θ_true = angle_deg − declination_deg`.

## Room types

`pooja`, `kitchen`, `master_bedroom`, `bedroom`, `living`, `dining`, `toilet`, `staircase`,
`study`, `store`, `garage`, `open_space`, `utility`, `water_tank`, `septic_tank`,
`circulation`, `other`.

Common aliases are accepted (`bathroom`, `wc`, `puja`, `hall`, `stairs`, `foyer`, `balcony`,
`verandah`, ...). See `aliases` in
[`rules.json`](../src/vastu_analyzer/data/rules.json). Unknown types count as `other` and
carry weight 0.

## Minimal example

```json
{
  "footprint": [[0, 0], [10, 0], [10, 12], [0, 12]],
  "north": 0,
  "rooms": [
    {"name": "Kitchen", "type": "kitchen", "polygon": [[6, 0], [10, 0], [10, 4], [6, 4]]},
    {"name": "Hall", "type": "living", "polygon": [[0, 4], [10, 4], [10, 12], [0, 12]]},
    {"name": "Bed", "type": "master_bedroom", "polygon": [[0, 0], [6, 0], [6, 4], [0, 4]]}
  ],
  "entrances": [{"name": "Door", "position": [8, 12], "main": true}]
}
```

See [`examples/`](../examples) for complete plans.
