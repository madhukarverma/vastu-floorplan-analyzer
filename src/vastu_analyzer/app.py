"""The window app (Tkinter, comes with Python).

How to use it:
    1. Pick a sample house from the list, or pick a room type and click-and-drag
       on the house to draw that room.
    2. Choose "Place main door" and click on an outside wall.
    3. Say which way north points on your drawing.
    4. Click "ANALYSE": rooms turn green (good), yellow (okay) or red (bad), the big
       score appears, and the colour-coded report card fills the right-hand panel.

Keys: F11 = full screen on/off, Esc = leave full screen.
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .compass import grid_boxes, side_to_compass
from .house import Door, House, Room, check_house, load_house, save_house
from .report import report
from .rules import RULES
from .suggestions import analyse

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
SNAP = 0.5  # rooms snap to half a metre so they line up neatly
MARGIN = 34  # space around the house for the compass letters

# Room colours on the drawing.
ROOM_COLOURS = {"good": "#9be3a4", "okay": "#ffe08a", "bad": "#f4a3a3", "none": "#dbe7f5"}
# Score banner colours per grade: (background, text).
GRADE_COLOURS = {
    "Excellent": ("#1e8e3e", "white"),
    "Good": ("#2a78d6", "white"),
    "Needs work": ("#eda100", "#3b2a00"),
    "Poor": ("#d93025", "white"),
}
ACCENT = "#5b3fd1"


def points_level(points: float) -> str:
    """good (7-10), okay (4-7) or bad (0-4): used for the room and text colours."""
    return "good" if points >= 7 else "okay" if points >= 4 else "bad"


class VastuApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Vastu Checker")
        root.geometry("1180x760")
        root.minsize(900, 600)
        self.house = House("My house", 12, 15)
        self.scores: dict[str, float] = {}  # room name -> points, after "Analyse"
        self.start: tuple[float, float] | None = None  # where a drag started (metres)
        self.preview: int | None = None  # the rectangle shown while dragging
        self.canvas_w, self.canvas_h = 560, 680  # updated whenever the window is resized
        self.full_screen = False

        # The drawing (column 0) grows with the window; the panel (column 1) keeps its width.
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # ---- left: the drawing --------------------------------------------------
        self.canvas = tk.Canvas(root, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", self.on_resize)

        # ---- right: the controls ------------------------------------------------
        panel = ttk.Frame(root)
        panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(14, weight=1)  # the report box takes the spare height

        ttk.Label(panel, text="Sample houses").grid(row=0, column=0, sticky="w")
        self.samples = self.find_samples()
        self.sample_var = tk.StringVar(value="Choose a sample house...")
        sample_box = ttk.Combobox(panel, textvariable=self.sample_var, values=list(self.samples),
                                  state="readonly")  # fmt: skip
        sample_box.grid(row=1, column=0, sticky="we")
        sample_box.bind("<<ComboboxSelected>>", lambda _e: self.load_sample())

        size = ttk.Frame(panel)
        size.grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(size, text="New house size (m) ").pack(side="left")
        self.width_var = tk.DoubleVar(value=12)
        self.depth_var = tk.DoubleVar(value=15)
        ttk.Spinbox(size, from_=4, to=40, increment=1, width=5, textvariable=self.width_var).pack(side="left")
        ttk.Label(size, text=" x ").pack(side="left")
        ttk.Spinbox(size, from_=4, to=40, increment=1, width=5, textvariable=self.depth_var).pack(side="left")
        ttk.Button(size, text="New house", command=self.new_house).pack(side="left", padx=6)

        draw = ttk.Frame(panel)
        draw.grid(row=3, column=0, sticky="we", pady=(8, 0))
        draw.columnconfigure(1, weight=1)
        ttk.Label(draw, text="Room type").grid(row=0, column=0, sticky="w")
        self.type_var = tk.StringVar(value="kitchen")
        ttk.Combobox(draw, textvariable=self.type_var, values=[*RULES, "other"],
                     state="readonly").grid(row=0, column=1, sticky="we", padx=(6, 0))  # fmt: skip
        ttk.Label(draw, text="Room name").grid(row=1, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(draw, textvariable=self.name_var).grid(row=1, column=1, sticky="we", padx=(6, 0))
        ttk.Label(draw, text="North points").grid(row=2, column=0, sticky="w")
        self.north_var = tk.StringVar(value="up")
        north = ttk.Combobox(draw, textvariable=self.north_var, state="readonly",
                             values=["up", "right", "down", "left"])  # fmt: skip
        north.grid(row=2, column=1, sticky="we", padx=(6, 0))
        north.bind("<<ComboboxSelected>>", lambda _e: self.changed())

        self.mode = tk.StringVar(value="room")
        modes = ttk.Frame(panel)
        modes.grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Radiobutton(modes, text="Draw room (drag)", variable=self.mode, value="room").pack(side="left")
        ttk.Radiobutton(modes, text="Place main door (click a wall)", variable=self.mode,
                        value="door").pack(side="left", padx=10)  # fmt: skip

        buttons = ttk.Frame(panel)
        buttons.grid(row=5, column=0, pady=8, sticky="we")
        for i, (label, action) in enumerate([("Open...", self.open_file), ("Save...", self.save_file),
                                             ("Undo", self.undo), ("Clear", self.clear),
                                             ("Full screen (F11)", self.toggle_full_screen)]):  # fmt: skip
            ttk.Button(buttons, text=label, command=action).grid(row=0, column=i, sticky="we", padx=1)

        tk.Button(panel, text="ANALYSE", command=self.run_analysis, bg=ACCENT, fg="white",
                  activebackground="#46309f", activeforeground="white", relief="flat",
                  font=("Segoe UI", 12, "bold"), cursor="hand2").grid(row=6, column=0, sticky="we", ipady=4)  # fmt: skip

        # ---- the big score banner ----------------------------------------------------
        self.banner = tk.Frame(panel, bg="#eeeeee")
        self.banner.grid(row=7, column=0, sticky="we", pady=(10, 4))
        self.score_text = tk.Label(self.banner, text="-- / 100", font=("Segoe UI", 34, "bold"),
                                   bg="#eeeeee", fg="#555555")  # fmt: skip
        self.score_text.pack(pady=(6, 0))
        self.grade_text = tk.Label(self.banner, text="Draw or load a house, then click ANALYSE",
                                   font=("Segoe UI", 12, "bold"), bg="#eeeeee", fg="#555555")  # fmt: skip
        self.grade_text.pack(pady=(0, 8))

        # Colour legend for the rooms.
        legend = ttk.Frame(panel)
        legend.grid(row=8, column=0, sticky="w", pady=(0, 6))
        for level, label in (("good", "Good 7-10"), ("okay", "Okay 4-7"), ("bad", "Bad 0-4")):
            tk.Label(legend, text=f"  {label}  ", bg=ROOM_COLOURS[level], font=("Segoe UI", 9)).pack(
                side="left", padx=(0, 6)
            )

        # ---- the colour-coded report card -------------------------------------------
        box = ttk.Frame(panel)
        box.grid(row=14, column=0, sticky="nsew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.text = tk.Text(box, width=72, wrap="word", font=("Consolas", 10), bg="#fbfbfd",
                            relief="flat", padx=8, pady=6)  # fmt: skip
        scroll = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.setup_text_colours()

        root.bind("<F11>", lambda _e: self.toggle_full_screen())
        root.bind("<Escape>", lambda _e: self.leave_full_screen())
        self.redraw()

    # ---- full screen -----------------------------------------------------------------
    def toggle_full_screen(self) -> None:
        self.full_screen = not self.full_screen
        self.root.attributes("-fullscreen", self.full_screen)

    def leave_full_screen(self) -> None:
        self.full_screen = False
        self.root.attributes("-fullscreen", False)

    def on_resize(self, event: tk.Event[tk.Canvas]) -> None:
        """The window changed size: remember the new canvas size and redraw bigger/smaller."""
        self.canvas_w, self.canvas_h = event.width, event.height
        self.redraw()

    # ---- converting between metres and screen pixels --------------------------------
    def scale(self) -> float:
        """Pixels per metre, so the whole house fits on the canvas."""
        return min(
            (self.canvas_w - 2 * MARGIN) / self.house.width, (self.canvas_h - 2 * MARGIN) / self.house.depth
        )

    def offset(self) -> tuple[float, float]:
        """Where the house's top-left corner goes, so the house is centred."""
        s = self.scale()
        return (self.canvas_w - self.house.width * s) / 2, (self.canvas_h - self.house.depth * s) / 2

    def to_px(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self.offset()
        return ox + x * self.scale(), oy + y * self.scale()

    def to_m(self, px: float, py: float) -> tuple[float, float]:
        """Screen pixels -> metres, snapped to the grid and kept inside the house."""
        ox, oy = self.offset()
        x = round((px - ox) / self.scale() / SNAP) * SNAP
        y = round((py - oy) / self.scale() / SNAP) * SNAP
        return min(max(x, 0), self.house.width), min(max(y, 0), self.house.depth)

    # ---- drawing ---------------------------------------------------------------------
    def redraw(self) -> None:
        c, h = self.canvas, self.house
        c.delete("all")
        font_size = max(8, min(14, int(self.scale() * 0.22)))  # bigger text in full screen
        for i in range(int(h.width) + 1):  # 1 m grid
            c.create_line(*self.to_px(i, 0), *self.to_px(i, h.depth), fill="#eeeeee")
        for j in range(int(h.depth) + 1):
            c.create_line(*self.to_px(0, j), *self.to_px(h.width, j), fill="#eeeeee")

        for room in h.rooms:
            pts = self.scores.get(room.name)
            colour = ROOM_COLOURS["none"] if pts is None else ROOM_COLOURS[points_level(pts)]
            c.create_rectangle(*self.to_px(room.x, room.y), *self.to_px(room.x + room.w, room.y + room.h),
                               fill=colour, outline="#555555")  # fmt: skip
            label = room.name if pts is None else f"{room.name}\n{pts}/10"
            c.create_text(*self.to_px(room.x + room.w / 2, room.y + room.h / 2), text=label,
                          font=("Segoe UI", font_size), justify="center")  # fmt: skip

        if self.scores:  # after analysis, show the 3 x 3 grid with its compass names
            for zone, (x, y, w, bh) in grid_boxes(h).items():
                c.create_rectangle(*self.to_px(x, y), *self.to_px(x + w, y + bh), outline=ACCENT, dash=(4, 3))
                c.create_text(*self.to_px(x + 0.25, y + 0.25), text=zone, anchor="nw",
                              fill=ACCENT, font=("Segoe UI", font_size + 1, "bold"))  # fmt: skip

        c.create_rectangle(*self.to_px(0, 0), *self.to_px(h.width, h.depth), outline="black", width=2)
        if h.door:
            x, y = self.to_px(h.door.x, h.door.y)
            c.create_rectangle(x - 7, y - 7, x + 7, y + 7, fill="#7a3e00", outline="")
        # Compass letters on each side of the house.
        cx, cy = self.to_px(h.width / 2, h.depth / 2)
        x0, y0 = self.to_px(0, 0)
        x1, y1 = self.to_px(h.width, h.depth)
        for side, (tx, ty) in {"up": (cx, y0 - 16), "down": (cx, y1 + 16),
                               "left": (x0 - 16, cy), "right": (x1 + 16, cy)}.items():  # fmt: skip
            c.create_text(tx, ty, text=side_to_compass(side, h.north), font=("Segoe UI", 13, "bold"))

    def changed(self) -> None:
        """Something was edited: old results no longer apply."""
        self.house.north = self.north_var.get()
        self.scores = {}
        self.set_banner(None, "Click ANALYSE to score this house", "#eeeeee", "#555555")
        self.redraw()

    # ---- the score banner and the coloured report -----------------------------------
    def set_banner(self, score: float | None, message: str, bg: str, fg: str) -> None:
        self.banner.configure(bg=bg)
        self.score_text.configure(text="-- / 100" if score is None else f"{score:.1f} / 100", bg=bg, fg=fg)
        self.grade_text.configure(text=message, bg=bg, fg=fg)

    def setup_text_colours(self) -> None:
        t = self.text
        t.tag_configure("title", font=("Segoe UI", 13, "bold"), foreground=ACCENT)
        t.tag_configure("step", font=("Segoe UI", 11, "bold"), foreground="white", background="#4a4a8a",
                        spacing1=8, spacing3=2)  # fmt: skip
        t.tag_configure("good", foreground="#1e7a34")
        t.tag_configure("okay", foreground="#9a6700")
        t.tag_configure("bad", foreground="#c5221f", font=("Consolas", 10, "bold"))
        t.tag_configure("swap", foreground="#1a5fb4", font=("Consolas", 10, "bold"))
        t.tag_configure("sun", foreground="#b5530b")
        t.tag_configure("todo", foreground="#202124")
        for grade, (bg, fg) in GRADE_COLOURS.items():
            t.tag_configure(grade, font=("Segoe UI", 15, "bold"), background=bg, foreground=fg,
                            spacing1=10, spacing3=6)  # fmt: skip

    def show_report(self, text: str, grade: str) -> None:
        """Put the report in the panel, colouring each line by what it says."""
        self.text.delete("1.0", "end")
        for i, line in enumerate(text.splitlines()):
            tag = ""
            points = re.search(r"(\d+(?:\.\d+)?)/10", line)
            if i == 0:
                tag = "title"
            elif line.startswith("STEP 7"):
                tag = grade
            elif line.startswith("STEP"):
                tag = "step"
            elif line.strip().startswith("Swap"):
                tag = "swap"
            elif any(word in line for word in ("west wall", "morning sun", "exhaust fan")):
                tag = "sun"
            elif points:
                tag = points_level(float(points.group(1)))
            elif re.match(r"\s+\d+\.", line):
                tag = "todo"
            self.text.insert("end", line + "\n", tag)

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
    @staticmethod
    def find_samples() -> dict[str, Path]:
        """The sample houses in the examples folder, as {"1. House name": path}."""
        samples = {}
        for path in sorted(EXAMPLES.glob("*.json")) if EXAMPLES.exists() else []:
            samples[f"{path.stem.split('_')[0]}. {load_house(path).name}"] = path
        return samples

    def load_sample(self) -> None:
        path = self.samples.get(self.sample_var.get())
        if path:
            self.set_house(load_house(path))

    def new_house(self) -> None:
        self.house = House("My house", self.width_var.get(), self.depth_var.get(), self.north_var.get())
        self.changed()

    def set_house(self, house: House) -> None:
        self.house = house
        self.width_var.set(house.width)
        self.depth_var.set(house.depth)
        self.north_var.set(house.north)
        self.changed()

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
        bg, fg = GRADE_COLOURS[result.grade]
        better = f"   (up to {result.swaps[-1][2]:.1f} with the swaps below)" if result.swaps else ""
        self.set_banner(result.score, f"{result.grade}{better}", bg, fg)
        self.show_report(report(self.house, result), result.grade)
        self.redraw()


def run_app() -> None:
    root = tk.Tk()
    VastuApp(root)
    root.mainloop()
