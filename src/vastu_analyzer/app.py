"""The window app (Tkinter, comes with Python).

Two main modes (press Tab to switch):

    EDIT mode    click-and-drag on the house to draw a new room.
    SELECT mode  click a room to select it, drag it to move it.
                 Drop it on another room and the two swap places.
                 Selected room: Delete = remove, R = rotate, arrow keys = nudge.

You can also add a room by typing its size ("Add a room by size"), place the main
door, set north, and click ANALYSE to colour the rooms and see the report card.

Shortcuts: Tab = edit/select, Ctrl+Z = undo, Ctrl+S = save, Ctrl+O = open,
F5 or Ctrl+Enter = analyse, F11 = full screen, Esc = deselect / leave full screen.
"""

from __future__ import annotations

import copy
import re
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .compass import grid_boxes, side_to_compass
from .house import (
    Door,
    House,
    Room,
    check_house,
    collision,
    find_free_spot,
    load_house,
    move_room,
    save_house,
)
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
# How each mode is shown in the coloured mode bar: (text, background colour).
MODE_INFO = {
    "edit": ("EDIT mode: drag on the house to draw a room   (Tab = select mode)", "#2a78d6"),
    "select": ("SELECT mode: click a room, drag to move it, Del / R / arrows   (Tab = edit mode)", ACCENT),
    "door": ("DOOR mode: click an outside wall to place the main door   (Tab = select mode)", "#7a3e00"),
}
SHORTCUTS = """Tab            switch between EDIT and SELECT mode
Ctrl+Z         undo the last change
Ctrl+S / Ctrl+O  save / open a house file
F5 or Ctrl+Enter analyse the house
F11            full screen on/off
Esc            deselect the room / leave full screen

In SELECT mode, with a room selected:
Drag           move it (drop on another room to swap places)
Delete         remove it
R              rotate it (swap width and depth)
Arrow keys     nudge it by half a metre"""


def points_level(points: float) -> str:
    """good (7-10), okay (4-7) or bad (0-4): used for the room and text colours."""
    return "good" if points >= 7 else "okay" if points >= 4 else "bad"


class VastuApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Vastu Checker")
        root.geometry("1240x860")
        root.minsize(1000, 700)
        self.house = House("My house", 12, 15)
        self.history: list[House] = []  # earlier versions of the house, for Ctrl+Z
        self.scores: dict[str, float] = {}  # room name -> points, after "Analyse"
        self.selected: Room | None = None  # the room picked in SELECT mode
        self.start: tuple[float, float] | None = None  # where a drag started (metres)
        self.grab_offset = (0.0, 0.0)  # where inside the room the mouse grabbed it
        self.preview: int | None = None  # the outline shown while dragging
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
        panel.rowconfigure(20, weight=1)  # the report box takes the spare height

        ttk.Label(panel, text="Sample houses").grid(row=0, column=0, sticky="w")
        self.samples = self.find_samples()
        self.sample_var = tk.StringVar(value="Choose a sample house...")
        sample_box = ttk.Combobox(panel, textvariable=self.sample_var, values=list(self.samples),
                                  state="readonly")  # fmt: skip
        sample_box.grid(row=1, column=0, sticky="we")
        sample_box.bind("<<ComboboxSelected>>", lambda _e: self.load_sample())

        size = ttk.Frame(panel)
        size.grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(size, text="New house size (m) ").pack(side="left")
        self.width_var = tk.DoubleVar(value=12)
        self.depth_var = tk.DoubleVar(value=15)
        ttk.Spinbox(size, from_=4, to=40, increment=1, width=5, textvariable=self.width_var).pack(side="left")
        ttk.Label(size, text=" x ").pack(side="left")
        ttk.Spinbox(size, from_=4, to=40, increment=1, width=5, textvariable=self.depth_var).pack(side="left")
        ttk.Button(size, text="New house", command=self.new_house).pack(side="left", padx=6)

        draw = ttk.Frame(panel)
        draw.grid(row=3, column=0, sticky="we", pady=(6, 0))
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
        north.bind("<<ComboboxSelected>>", lambda _e: self.set_north())

        # ---- modes ---------------------------------------------------------------
        self.mode = tk.StringVar(value="edit")
        modes = ttk.Frame(panel)
        modes.grid(row=4, column=0, sticky="w", pady=(6, 0))
        for text, value in (
            ("Edit: draw rooms", "edit"),
            ("Select & move", "select"),
            ("Place main door", "door"),
        ):
            ttk.Radiobutton(modes, text=text, variable=self.mode, value=value).pack(side="left", padx=(0, 10))
        self.mode_bar = tk.Label(panel, font=("Segoe UI", 10, "bold"), fg="white", anchor="w", padx=8, pady=4)
        self.mode_bar.grid(row=5, column=0, sticky="we", pady=(4, 0))
        self.mode.trace_add("write", lambda *_: self.mode_changed())

        # ---- add a room by typing its size ---------------------------------------
        add = ttk.LabelFrame(panel, text=" Add a room by size (uses the room type and name above) ")
        add.grid(row=6, column=0, sticky="we", pady=(8, 0))
        self.add_w, self.add_h = tk.StringVar(value="3"), tk.StringVar(value="3")
        self.add_x, self.add_y = tk.StringVar(), tk.StringVar()
        for col, (label, var) in enumerate((("Width", self.add_w), ("Depth", self.add_h),
                                            ("X (blank = auto)", self.add_x), ("Y", self.add_y))):  # fmt: skip
            ttk.Label(add, text=label).grid(row=0, column=col, sticky="w", padx=4)
            ttk.Entry(add, textvariable=var, width=8).grid(row=1, column=col, sticky="w", padx=4)
            var.trace_add("write", lambda *_: self.add_error.config(text=""))  # editing clears the error
        ttk.Button(add, text="Add room", command=self.add_room_by_size).grid(row=1, column=4, padx=6)
        self.add_error = tk.Label(add, text="", fg="#c5221f", font=("Segoe UI", 9, "bold"),
                                  anchor="w", justify="left", wraplength=560)  # fmt: skip
        self.add_error.grid(row=2, column=0, columnspan=5, sticky="we", padx=4, pady=(2, 4))

        # ---- buttons ---------------------------------------------------------------
        buttons = ttk.Frame(panel)
        buttons.grid(row=7, column=0, pady=8, sticky="we")
        actions = [("Open...", self.open_file), ("Save...", self.save_file), ("Undo (Ctrl+Z)", self.undo),
                   ("Clear", self.clear), ("Update selected", self.update_selected),
                   ("Delete selected", self.delete_selected), ("Shortcuts", self.show_shortcuts),
                   ("Full screen (F11)", self.toggle_full_screen)]  # fmt: skip
        for i, (label, action) in enumerate(actions):
            ttk.Button(buttons, text=label, command=action).grid(
                row=i // 4, column=i % 4, sticky="we", padx=1, pady=1
            )
            buttons.columnconfigure(i % 4, weight=1)

        tk.Button(panel, text="ANALYSE  (F5)", command=self.run_analysis, bg=ACCENT, fg="white",
                  activebackground="#46309f", activeforeground="white", relief="flat",
                  font=("Segoe UI", 12, "bold"), cursor="hand2").grid(row=8, column=0, sticky="we", ipady=4)  # fmt: skip
        self.message = tk.Label(panel, text="", anchor="w", font=("Segoe UI", 10, "bold"))
        self.message.grid(row=9, column=0, sticky="we", pady=(4, 0))

        # ---- the big score banner ----------------------------------------------------
        self.banner = tk.Frame(panel, bg="#eeeeee")
        self.banner.grid(row=10, column=0, sticky="we", pady=(6, 4))
        self.score_text = tk.Label(self.banner, text="-- / 100", font=("Segoe UI", 30, "bold"),
                                   bg="#eeeeee", fg="#555555")  # fmt: skip
        self.score_text.pack(pady=(4, 0))
        self.grade_text = tk.Label(self.banner, text="Draw or load a house, then click ANALYSE",
                                   font=("Segoe UI", 12, "bold"), bg="#eeeeee", fg="#555555")  # fmt: skip
        self.grade_text.pack(pady=(0, 6))

        legend = ttk.Frame(panel)
        legend.grid(row=11, column=0, sticky="w", pady=(0, 6))
        for level, label in (("good", "Good 7-10"), ("okay", "Okay 4-7"), ("bad", "Bad 0-4")):
            tk.Label(legend, text=f"  {label}  ", bg=ROOM_COLOURS[level], font=("Segoe UI", 9)).pack(
                side="left", padx=(0, 6)
            )

        # ---- the colour-coded report card -------------------------------------------
        box = ttk.Frame(panel)
        box.grid(row=20, column=0, sticky="nsew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.text = tk.Text(box, width=74, height=10, wrap="word", font=("Consolas", 10), bg="#fbfbfd",
                            relief="flat", padx=8, pady=6, state="disabled")  # fmt: skip
        scroll = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.setup_text_colours()

        self.bind_shortcuts()
        self.mode_changed()
        self.redraw()

    # ---- keyboard shortcuts --------------------------------------------------------
    def bind_shortcuts(self) -> None:
        r = self.root
        # Tk normally uses Tab to jump between boxes (the <<NextWindow>> event); we take it over.
        r.bind_all("<Tab>", self.on_tab)
        r.bind_all("<<NextWindow>>", self.on_tab)
        for key in ("<Control-z>", "<Control-Z>"):
            r.bind_all(key, lambda _e: self.undo())
        for key in ("<Control-s>", "<Control-S>"):
            r.bind_all(key, lambda _e: self.save_file())
        for key in ("<Control-o>", "<Control-O>"):
            r.bind_all(key, lambda _e: self.open_file())
        for key in ("<F5>", "<Control-Return>"):
            r.bind_all(key, lambda _e: self.run_analysis())
        r.bind_all("<F11>", lambda _e: self.toggle_full_screen())
        r.bind_all("<Escape>", lambda _e: self.on_escape())
        # Keys that act on the selected room (ignored while typing in a box).
        room_keys: dict[str, Callable[[], None]] = {"<Delete>": self.delete_selected, "<BackSpace>": self.delete_selected,
                     "<r>": self.rotate_selected, "<R>": self.rotate_selected,
                     "<Left>": lambda: self.nudge(-SNAP, 0), "<Right>": lambda: self.nudge(SNAP, 0),
                     "<Up>": lambda: self.nudge(0, -SNAP), "<Down>": lambda: self.nudge(0, SNAP)}  # fmt: skip
        for key, action in room_keys.items():
            r.bind_all(key, self.make_room_key_handler(action))

    def make_room_key_handler(self, action: Callable[[], None]) -> Callable[[tk.Event[tk.Misc]], str | None]:
        """A key handler that runs ``action`` on the selected room."""
        return lambda _event: self.room_key(action)

    def typing(self) -> bool:
        """True while the cursor is in a text box (so keys like R and Delete type normally)."""
        return isinstance(self.root.focus_get(), (tk.Entry, ttk.Entry))

    def room_key(self, action: Callable[[], None]) -> str | None:
        if self.typing() or self.mode.get() != "select" or self.selected is None:
            return None
        action()
        return "break"

    def on_tab(self, _event: object) -> str:
        """Tab switches between EDIT and SELECT mode (instead of moving between boxes)."""
        self.mode.set("edit" if self.mode.get() == "select" else "select")
        self.canvas.focus_set()
        return "break"

    def on_escape(self) -> None:
        self.selected = None
        self.leave_full_screen()
        self.redraw()

    def show_shortcuts(self) -> None:
        messagebox.showinfo("Keyboard shortcuts", SHORTCUTS)

    # ---- modes and messages ------------------------------------------------------
    def mode_changed(self) -> None:
        text, colour = MODE_INFO[self.mode.get()]
        self.mode_bar.config(text=text, bg=colour)
        if self.mode.get() != "select":
            self.selected = None
        self.redraw()

    def say(self, text: str, ok: bool = True) -> None:
        """Show a short green (worked) or red (problem) message under the ANALYSE button."""
        self.message.config(text=text, fg="#1e7a34" if ok else "#c5221f")
        if not ok:
            self.root.bell()

    # ---- undo history ------------------------------------------------------------
    def remember(self) -> None:
        """Save a copy of the house before changing it, so Ctrl+Z can bring it back."""
        self.history.append(copy.deepcopy(self.house))
        del self.history[:-50]  # keep the last 50 steps

    def undo(self) -> None:
        if not self.history:
            self.say("Nothing to undo.", ok=False)
            return
        self.house = self.history.pop()
        self.selected = None
        self.sync_fields()
        self.changed()
        self.say("Undone.")

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

    def to_m_exact(self, px: float, py: float) -> tuple[float, float]:
        """Screen pixels -> metres (not snapped)."""
        ox, oy = self.offset()
        return (px - ox) / self.scale(), (py - oy) / self.scale()

    def to_m(self, px: float, py: float) -> tuple[float, float]:
        """Screen pixels -> metres, snapped to the grid and kept inside the house."""
        x, y = self.to_m_exact(px, py)
        x, y = round(x / SNAP) * SNAP, round(y / SNAP) * SNAP
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
            chosen = room is self.selected
            c.create_rectangle(*self.to_px(room.x, room.y), *self.to_px(room.x + room.w, room.y + room.h),
                               fill=colour, outline=ACCENT if chosen else "#555555",
                               width=4 if chosen else 1)  # fmt: skip
            label = room.name if pts is None else f"{room.name}\n{pts}/10"
            c.create_text(*self.to_px(room.x + room.w / 2, room.y + room.h / 2), text=label,
                          font=("Segoe UI", font_size, "bold" if chosen else "normal"), justify="center")  # fmt: skip

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
        self.text.configure(state="normal")
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
        self.text.configure(state="disabled")  # read-only

    # ---- mouse -------------------------------------------------------------------------
    def room_at(self, x: float, y: float) -> Room | None:
        """The room under the point (x, y) in metres, if any."""
        for room in reversed(self.house.rooms):
            if room.x <= x <= room.x + room.w and room.y <= y <= room.y + room.h:
                return room
        return None

    def on_press(self, event: tk.Event[tk.Canvas]) -> None:
        self.canvas.focus_set()  # so arrow keys and Delete reach the drawing
        mode = self.mode.get()
        if mode == "door":
            self.remember()
            self.house.door = Door(*self.nearest_wall_point(*self.to_m(event.x, event.y)))
            self.say("Main door placed.")
            self.changed()
        elif mode == "select":
            mx, my = self.to_m_exact(event.x, event.y)
            self.selected = self.room_at(mx, my)
            if self.selected:
                self.grab_offset = (mx - self.selected.x, my - self.selected.y)
                self.start = (self.selected.x, self.selected.y)
                self.name_var.set(self.selected.name)
                self.type_var.set(self.selected.type if self.selected.type in RULES else "other")
                self.say(f"Selected '{self.selected.name}': drag to move, Delete, R or arrows.")
            self.redraw()
        else:
            self.start = self.to_m(event.x, event.y)

    def drop_position(self, event: tk.Event[tk.Canvas]) -> tuple[float, float]:
        """Where the selected room's top-left corner would go, snapped to the grid."""
        mx, my = self.to_m_exact(event.x, event.y)
        return round((mx - self.grab_offset[0]) / SNAP) * SNAP, round(
            (my - self.grab_offset[1]) / SNAP
        ) * SNAP

    def on_drag(self, event: tk.Event[tk.Canvas]) -> None:
        if self.start is None:
            return
        if self.preview:
            self.canvas.delete(self.preview)
        if self.mode.get() == "select" and self.selected:
            x, y = self.drop_position(event)
            room = self.selected
            self.preview = self.canvas.create_rectangle(*self.to_px(x, y), *self.to_px(x + room.w, y + room.h),
                                                        outline=ACCENT, width=3, dash=(6, 3))  # fmt: skip
        else:
            self.preview = self.canvas.create_rectangle(
                *self.to_px(*self.start), event.x, event.y, dash=(3, 2)
            )

    def on_release(self, event: tk.Event[tk.Canvas]) -> None:
        if self.start is None:
            return
        start, self.start, self.preview = self.start, None, None
        if self.mode.get() == "select":
            if self.selected and self.drop_position(event) != start:
                self.remember()
                ok, text = move_room(self.house, self.selected, *self.drop_position(event))
                if not ok:
                    self.history.pop()  # nothing changed, so nothing to undo
                self.say(text, ok)
                self.changed()
            else:
                self.redraw()
            return
        (x0, y0), (x1, y1) = start, self.to_m(event.x, event.y)
        if abs(x1 - x0) >= SNAP and abs(y1 - y0) >= SNAP:
            self.add_room(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        else:
            self.redraw()

    def nearest_wall_point(self, x: float, y: float) -> tuple[float, float]:
        """Move a click onto the closest outside wall (a door must be on a wall)."""
        w, d = self.house.width, self.house.depth
        options = [(y, (x, 0.0)), (d - y, (x, d)), (x, (0.0, y)), (w - x, (w, y))]
        return min(options)[1]

    # ---- adding rooms ----------------------------------------------------------------
    def new_room(self, x: float, y: float, w: float, h: float) -> Room:
        kind = self.type_var.get()
        name = self.name_var.get().strip() or f"{kind.replace('_', ' ').title()} {len(self.house.rooms) + 1}"
        return Room(name, kind, x, y, w, h)

    def add_room(self, x: float, y: float, w: float, h: float) -> bool:
        """Add a room if it fits; otherwise explain why. Returns True if it was added."""
        room = self.new_room(x, y, w, h)
        problem = collision(self.house, room)
        if problem:
            self.say(f"Cannot add the room: {problem}", ok=False)
            self.redraw()
            return False
        self.remember()
        self.house.rooms.append(room)
        self.name_var.set("")
        self.say(f"Added '{room.name}' ({w} x {h} m).")
        self.changed()
        return True

    def add_room_by_size(self) -> None:
        """'Add room' button: read the typed size (and optional position) and add the room."""
        try:
            w, h = float(self.add_w.get()), float(self.add_h.get())
            x = float(self.add_x.get()) if self.add_x.get().strip() else None
            y = float(self.add_y.get()) if self.add_y.get().strip() else None
        except ValueError:
            self.add_error.config(text="Please type numbers in metres, e.g. 3 or 2.5.")
            return
        if w <= 0 or h <= 0:
            self.add_error.config(text="Width and depth must be bigger than 0.")
            return
        if x is None or y is None:  # no position given: find the first empty space
            spot = find_free_spot(self.house, w, h)
            if spot is None:
                self.add_error.config(text=f"No free space for a {w} x {h} m room. Make it smaller, "
                                           "or move / delete a room first.")  # fmt: skip
                self.say("No space for that room.", ok=False)
                return
            x, y = spot
        problem = collision(self.house, self.new_room(x, y, w, h))
        if problem:
            self.add_error.config(text=f"{problem} Try another position, or leave X and Y blank.")
            self.say("That room does not fit there.", ok=False)
            return
        self.add_error.config(text="")
        self.add_room(x, y, w, h)

    # ---- editing the selected room ---------------------------------------------------
    def delete_selected(self) -> None:
        if self.selected is None:
            self.say("Select a room first (Tab, then click a room).", ok=False)
            return
        self.remember()
        self.house.rooms.remove(self.selected)
        self.say(f"Deleted '{self.selected.name}'.")
        self.selected = None
        self.changed()

    def try_change(self, change: Callable[[], None], undo: Callable[[], None], done: str) -> None:
        """Apply a change to the selected room; if it now collides, undo it and explain."""
        assert self.selected is not None
        self.remember()
        change()
        problem = collision(self.house, self.selected)
        if problem:
            undo()
            self.history.pop()
            self.say(f"Cannot do that: {problem}", ok=False)
            self.redraw()
        else:
            self.say(done)
            self.changed()

    def nudge(self, dx: float, dy: float) -> None:
        room = self.selected
        assert room is not None

        def move() -> None:
            room.x, room.y = room.x + dx, room.y + dy

        def back() -> None:
            room.x, room.y = room.x - dx, room.y - dy

        self.try_change(move, back, f"Moved '{room.name}'.")

    def rotate_selected(self) -> None:
        room = self.selected
        assert room is not None

        def turn() -> None:
            room.w, room.h = room.h, room.w

        self.try_change(turn, turn, f"Rotated '{room.name}'.")

    def update_selected(self) -> None:
        """Give the selected room the name and type typed in the boxes above."""
        if self.selected is None:
            self.say("Select a room first (Tab, then click a room).", ok=False)
            return
        self.remember()
        self.selected.type = self.type_var.get()
        self.selected.name = self.name_var.get().strip() or self.selected.name
        self.say(f"Updated '{self.selected.name}'.")
        self.changed()

    # ---- whole-house buttons -----------------------------------------------------------
    @staticmethod
    def find_samples() -> dict[str, Path]:
        """The sample houses in the examples folder, as {"1. House name": path}."""
        samples = {}
        for path in sorted(EXAMPLES.glob("*.json")) if EXAMPLES.exists() else []:
            samples[f"{path.stem.split('_')[0]}. {load_house(path).name}"] = path
        return samples

    def sync_fields(self) -> None:
        """Show the current house's size and north in the boxes."""
        self.width_var.set(self.house.width)
        self.depth_var.set(self.house.depth)
        self.north_var.set(self.house.north)

    def set_north(self) -> None:
        self.remember()
        self.house.north = self.north_var.get()
        self.changed()

    def load_sample(self) -> None:
        path = self.samples.get(self.sample_var.get())
        if path:
            self.set_house(load_house(path))

    def new_house(self) -> None:
        self.set_house(House("My house", self.width_var.get(), self.depth_var.get(), self.north_var.get()))

    def set_house(self, house: House) -> None:
        self.remember()
        self.house = house
        self.selected = None
        self.sync_fields()
        self.say(f"Loaded '{house.name}'.")
        self.changed()

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("House files", "*.json")])
        if path:
            self.set_house(load_house(path))

    def save_file(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("House files", "*.json")])
        if path:
            save_house(self.house, path)
            self.say(f"Saved to {Path(path).name}.")

    def clear(self) -> None:
        self.remember()
        self.house.rooms.clear()
        self.house.door = None
        self.selected = None
        self.say("Cleared. Ctrl+Z brings it back.")
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
