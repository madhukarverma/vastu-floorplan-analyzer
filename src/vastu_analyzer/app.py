"""The window app (Tkinter, comes with Python).

How to use it:
    1. Pick a room type, then click-and-drag on the house to draw that room.
    2. Choose "Place main door" and click on an outside wall.
    3. Say which way north points on your drawing.
    4. Click "Analyse": rooms turn green (good), yellow (okay) or red (bad),
       and the report card appears on the right.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .compass import grid_boxes, side_to_compass
from .house import Door, House, Room, check_house, load_house, save_house
from .report import report
from .rules import RULES
from .suggestions import analyse

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "sample_house.json"
SNAP = 0.5  # rooms snap to half a metre so they line up neatly
CANVAS_W, CANVAS_H, MARGIN = 470, 580, 30
COLOURS = {"good": "#9be3a4", "okay": "#ffe08a", "bad": "#f4a3a3", "none": "#dbe7f5"}


class VastuApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Vastu Checker")
        self.house = House("My house", 12, 15)
        self.scores: dict[str, float] = {}  # room name -> points, after "Analyse"
        self.start: tuple[float, float] | None = None  # where a drag started (metres)
        self.preview: int | None = None  # the rectangle shown while dragging

        # ---- left: the drawing --------------------------------------------------
        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="white")
        self.canvas.grid(row=0, column=0, padx=8, pady=8)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # ---- right: the controls ------------------------------------------------
        panel = ttk.Frame(root)
        panel.grid(row=0, column=1, sticky="ns", padx=8, pady=8)

        ttk.Label(panel, text="House size (m)").grid(row=0, column=0, sticky="w")
        self.width_var = tk.DoubleVar(value=12)
        self.depth_var = tk.DoubleVar(value=15)
        size = ttk.Frame(panel)
        size.grid(row=1, column=0, sticky="w")
        ttk.Spinbox(size, from_=4, to=40, increment=1, width=5, textvariable=self.width_var).pack(side="left")
        ttk.Label(size, text=" x ").pack(side="left")
        ttk.Spinbox(size, from_=4, to=40, increment=1, width=5, textvariable=self.depth_var).pack(side="left")
        ttk.Button(size, text="New house", command=self.new_house).pack(side="left", padx=6)

        ttk.Label(panel, text="Room type").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.type_var = tk.StringVar(value="kitchen")
        ttk.Combobox(panel, textvariable=self.type_var, values=[*RULES, "other"],
                     state="readonly").grid(row=3, column=0, sticky="we")  # fmt: skip
        ttk.Label(panel, text="Room name (optional)").grid(row=4, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.name_var).grid(row=5, column=0, sticky="we")

        self.mode = tk.StringVar(value="room")
        ttk.Radiobutton(panel, text="Draw room (click and drag)", variable=self.mode,
                        value="room").grid(row=6, column=0, sticky="w", pady=(8, 0))  # fmt: skip
        ttk.Radiobutton(panel, text="Place main door (click a wall)", variable=self.mode,
                        value="door").grid(row=7, column=0, sticky="w")  # fmt: skip

        ttk.Label(panel, text="North points").grid(row=8, column=0, sticky="w", pady=(8, 0))
        self.north_var = tk.StringVar(value="up")
        north = ttk.Combobox(panel, textvariable=self.north_var, state="readonly",
                             values=["up", "right", "down", "left"])  # fmt: skip
        north.grid(row=9, column=0, sticky="we")
        north.bind("<<ComboboxSelected>>", lambda _e: self.changed())

        buttons = ttk.Frame(panel)
        buttons.grid(row=10, column=0, pady=10, sticky="we")
        for i, (label, action) in enumerate([("Load sample", self.load_sample), ("Open...", self.open_file),
                                             ("Save...", self.save_file), ("Undo", self.undo),
                                             ("Clear", self.clear)]):  # fmt: skip
            ttk.Button(buttons, text=label, command=action).grid(row=i // 3, column=i % 3, sticky="we")

        ttk.Button(panel, text="ANALYSE", command=self.run_analysis).grid(
            row=11, column=0, sticky="we", ipady=6
        )
        self.score_label = ttk.Label(panel, text="Draw your house, then click ANALYSE",
                                     font=("Segoe UI", 12, "bold"))  # fmt: skip
        self.score_label.grid(row=12, column=0, sticky="w", pady=6)

        self.text = tk.Text(panel, width=70, height=24, wrap="word", font=("Consolas", 9))
        self.text.grid(row=13, column=0, sticky="nswe")
        self.redraw()

    # ---- converting between metres and screen pixels --------------------------------
    def scale(self) -> float:
        return min((CANVAS_W - 2 * MARGIN) / self.house.width, (CANVAS_H - 2 * MARGIN) / self.house.depth)

    def to_px(self, x: float, y: float) -> tuple[float, float]:
        return MARGIN + x * self.scale(), MARGIN + y * self.scale()

    def to_m(self, px: float, py: float) -> tuple[float, float]:
        """Screen pixels -> metres, snapped to the grid and kept inside the house."""
        x = round((px - MARGIN) / self.scale() / SNAP) * SNAP
        y = round((py - MARGIN) / self.scale() / SNAP) * SNAP
        return min(max(x, 0), self.house.width), min(max(y, 0), self.house.depth)

    # ---- drawing ---------------------------------------------------------------------
    def redraw(self) -> None:
        c, h = self.canvas, self.house
        c.delete("all")
        for i in range(int(h.width) + 1):  # 1 m grid
            c.create_line(*self.to_px(i, 0), *self.to_px(i, h.depth), fill="#eeeeee")
        for j in range(int(h.depth) + 1):
            c.create_line(*self.to_px(0, j), *self.to_px(h.width, j), fill="#eeeeee")

        for room in h.rooms:
            pts = self.scores.get(room.name)
            colour = (
                COLOURS["none"]
                if pts is None
                else (COLOURS["good"] if pts >= 7 else COLOURS["okay"] if pts >= 4 else COLOURS["bad"])
            )
            c.create_rectangle(*self.to_px(room.x, room.y), *self.to_px(room.x + room.w, room.y + room.h),
                               fill=colour, outline="#555555")  # fmt: skip
            label = room.name if pts is None else f"{room.name}\n{pts}/10"
            c.create_text(*self.to_px(room.x + room.w / 2, room.y + room.h / 2), text=label,
                          font=("Segoe UI", 8), justify="center")  # fmt: skip

        if self.scores:  # after analysis, show the 3 x 3 grid with its compass names
            for zone, (x, y, w, bh) in grid_boxes(h).items():
                c.create_rectangle(
                    *self.to_px(x, y), *self.to_px(x + w, y + bh), outline="#7a5cc7", dash=(4, 3)
                )
                c.create_text(*self.to_px(x + 0.3, y + 0.3), text=zone, anchor="nw",
                              fill="#7a5cc7", font=("Segoe UI", 9, "bold"))  # fmt: skip

        c.create_rectangle(*self.to_px(0, 0), *self.to_px(h.width, h.depth), outline="black", width=2)
        if h.door:
            x, y = self.to_px(h.door.x, h.door.y)
            c.create_rectangle(x - 6, y - 6, x + 6, y + 6, fill="#7a3e00", outline="")
        # Compass letters on each side of the house.
        cx, cy = self.to_px(h.width / 2, h.depth / 2)
        x0, y0 = self.to_px(0, 0)
        x1, y1 = self.to_px(h.width, h.depth)
        for side, (tx, ty) in {"up": (cx, y0 - 14), "down": (cx, y1 + 14),
                               "left": (x0 - 14, cy), "right": (x1 + 14, cy)}.items():  # fmt: skip
            c.create_text(tx, ty, text=side_to_compass(side, h.north), font=("Segoe UI", 11, "bold"))

    def changed(self) -> None:
        """Something was edited: old results no longer apply."""
        self.house.north = self.north_var.get()
        self.scores = {}
        self.score_label.config(text="Click ANALYSE to score this house")
        self.redraw()

    # ---- mouse -------------------------------------------------------------------------
    def on_press(self, event: tk.Event[tk.Canvas]) -> None:
        x, y = self.to_m(event.x, event.y)
        if self.mode.get() == "door":
            self.house.door = Door(*self.nearest_wall_point(x, y))
            self.changed()
        else:
            self.start = (x, y)

    def on_drag(self, event: tk.Event[tk.Canvas]) -> None:
        if self.start is None:
            return
        if self.preview:
            self.canvas.delete(self.preview)
        self.preview = self.canvas.create_rectangle(*self.to_px(*self.start), event.x, event.y, dash=(3, 2))

    def on_release(self, event: tk.Event[tk.Canvas]) -> None:
        if self.start is None:
            return
        (x0, y0), (x1, y1) = self.start, self.to_m(event.x, event.y)
        self.start, self.preview = None, None
        if abs(x1 - x0) >= SNAP and abs(y1 - y0) >= SNAP:
            kind = self.type_var.get()
            name = (
                self.name_var.get().strip() or f"{kind.replace('_', ' ').title()} {len(self.house.rooms) + 1}"
            )
            self.house.rooms.append(Room(name, kind, min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)))
            self.name_var.set("")
        self.changed()

    def nearest_wall_point(self, x: float, y: float) -> tuple[float, float]:
        """Move a click onto the closest outside wall (a door must be on a wall)."""
        w, d = self.house.width, self.house.depth
        options = [(y, (x, 0.0)), (d - y, (x, d)), (x, (0.0, y)), (w - x, (w, y))]
        return min(options)[1]

    # ---- buttons -----------------------------------------------------------------------
    def new_house(self) -> None:
        self.house = House("My house", self.width_var.get(), self.depth_var.get(), self.north_var.get())
        self.changed()

    def set_house(self, house: House) -> None:
        self.house = house
        self.width_var.set(house.width)
        self.depth_var.set(house.depth)
        self.north_var.set(house.north)
        self.changed()

    def load_sample(self) -> None:
        if EXAMPLE.exists():
            self.set_house(load_house(EXAMPLE))
        else:  # installed without the examples folder: let the user pick a file
            self.open_file()

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("House files", "*.json")])
        if path:
            self.set_house(load_house(path))

    def save_file(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("House files", "*.json")])
        if path:
            save_house(self.house, path)

    def undo(self) -> None:
        if self.house.rooms:
            self.house.rooms.pop()
        self.changed()

    def clear(self) -> None:
        self.house.rooms.clear()
        self.house.door = None
        self.changed()

    def run_analysis(self) -> None:
        problems = check_house(self.house)  # STEP 2
        if problems:
            messagebox.showwarning("Please fix the drawing", "\n".join(problems))
            return
        result = analyse(self.house)  # STEPS 3-9
        self.scores = {r.name: r.points for r in result.rooms if r.type != "other"}
        self.score_label.config(text=f"Vastu score: {result.score} / 100  ({result.grade})")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", report(self.house, result))
        self.redraw()


def run_app() -> None:
    root = tk.Tk()
    VastuApp(root)
    root.mainloop()
