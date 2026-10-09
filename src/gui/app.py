"""Main GUI window: a list of named targets (captured screen regions),
buttons to capture/click/delete them, and scroll controls.

Every button performs exactly one action and returns to idle — same
manual-tool philosophy as the CLI (`main.py`). Nothing here loops or runs
unattended.

Built with `ttk` (themed Tk widgets, still standard library — no new
dependency) rather than plain `tk`, specifically for a native, modern
look without adding a GUI framework.
"""

from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from natural_mouse import (
    BezierPathGenerator,
    TemplateMatchLocator,
    UIAutomator,
    Win32InputExecutor,
    capture_region,
)

from .capture_overlay import CaptureOverlay
from .targets import load_targets, save_targets

TEMPLATES_DIR = Path("templates")
_PREVIEW_MAX_PX = 160
_STATUS_COLORS = {"ok": "#1a7f37", "warn": "#9a6700", "error": "#cf222e", "neutral": "#57606a"}


class App:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._root.title("natural_mouse")
        self._root.minsize(440, 360)
        self._root.geometry("480x420")

        self._automator = UIAutomator(
            locator=TemplateMatchLocator(),
            executor=Win32InputExecutor(),
            path_generator=BezierPathGenerator(),
        )
        self._targets = load_targets()
        self._preview_image: tk.PhotoImage | None = None  # keep a ref so Tk doesn't GC it

        self._apply_theme()
        self._build_ui()

    def _apply_theme(self) -> None:
        style = ttk.Style(self._root)
        # "vista" gives native Windows look; fall back quietly if unavailable
        # (e.g. running this on a non-Windows Tk build during development).
        for theme in ("vista", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("Status.TLabel", padding=(8, 4))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        container = ttk.Frame(self._root, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self._build_targets_section(container)
        self._build_scroll_section(container)
        self._build_status_bar()

    def _build_targets_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="Targets", style="Section.TLabelframe", padding=8)
        section.grid(row=0, column=0, sticky="nsew")
        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(section, show="tree", selectmode="browse")
        self._tree.grid(row=0, column=0, sticky="nsew")
        for name in self._targets:
            self._tree.insert("", "end", iid=name, text=name)

        tree_scroll = ttk.Scrollbar(section, orient="vertical", command=self._tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=tree_scroll.set)

        self._tree.bind("<<TreeviewSelect>>", lambda _e: self._update_preview())
        self._tree.bind("<Double-1>", lambda _e: self._on_click_selected())
        self._tree.bind("<Delete>", lambda _e: self._on_delete_selected())

        preview_frame = ttk.Frame(section, width=_PREVIEW_MAX_PX, height=_PREVIEW_MAX_PX, relief="groove")
        preview_frame.grid(row=0, column=2, sticky="n", padx=(8, 0))
        preview_frame.grid_propagate(False)
        self._preview_label = ttk.Label(preview_frame, text="No target\nselected", justify="center", anchor="center")
        self._preview_label.place(relx=0.5, rely=0.5, anchor="center")

        button_row = ttk.Frame(section)
        button_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        button_row.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(button_row, text="New Target…", command=self._on_new_target).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(button_row, text="Click Selected", command=self._on_click_selected).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(button_row, text="Delete Selected", command=self._on_delete_selected).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def _build_scroll_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="Scroll", style="Section.TLabelframe", padding=8)
        section.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ttk.Label(section, text="Amount:").pack(side="left")
        self._scroll_amount = ttk.Spinbox(section, from_=1, to=999, width=5)
        self._scroll_amount.set(5)
        self._scroll_amount.pack(side="left", padx=(5, 10))

        ttk.Button(section, text="▲ Up", width=8, command=lambda: self._on_scroll(1)).pack(side="left", padx=(0, 4))
        ttk.Button(section, text="▼ Down", width=8, command=lambda: self._on_scroll(-1)).pack(side="left")

    def _build_status_bar(self) -> None:
        self._status = ttk.Label(self._root, text="Ready", anchor="w", relief="sunken", style="Status.TLabel")
        self._status.grid(row=1, column=0, sticky="ew")

    def _set_status(self, text: str, level: str = "neutral") -> None:
        self._status.configure(text=text, foreground=_STATUS_COLORS[level])

    def _selected_name(self) -> str | None:
        selection = self._tree.selection()
        return selection[0] if selection else None

    def _update_preview(self) -> None:
        name = self._selected_name()
        if name is None:
            self._preview_label.configure(image="", text="No target\nselected")
            self._preview_image = None
            return

        try:
            image = tk.PhotoImage(file=self._targets[name])
        except tk.TclError:
            self._preview_label.configure(image="", text="Preview\nunavailable")
            self._preview_image = None
            return

        factor = max(1, math.ceil(max(image.width(), image.height()) / _PREVIEW_MAX_PX))
        if factor > 1:
            image = image.subsample(factor, factor)

        self._preview_image = image  # keep the reference alive
        self._preview_label.configure(image=image, text="")

    def _on_new_target(self) -> None:
        self._root.withdraw()

        def after_region(region: tuple[int, int, int, int] | None) -> None:
            self._root.deiconify()
            if region is None:
                self._set_status("Capture cancelled.")
                return

            name = simpledialog.askstring("Target name", "Name this target:", parent=self._root)
            if not name:
                self._set_status("Capture cancelled.")
                return

            if name in self._targets and not messagebox.askyesno(
                "Overwrite target?", f"A target named '{name}' already exists. Overwrite it?", parent=self._root
            ):
                self._set_status("Capture cancelled.")
                return

            TEMPLATES_DIR.mkdir(exist_ok=True)
            output_path = str(TEMPLATES_DIR / f"{name}.png")
            capture_region(region, output_path)

            is_new = name not in self._targets
            self._targets[name] = output_path
            save_targets(self._targets)
            if is_new:
                self._tree.insert("", "end", iid=name, text=name)
            self._tree.selection_set(name)
            self._set_status(f"Captured target '{name}'.", "ok")

        CaptureOverlay(self._root, after_region)

    def _on_click_selected(self) -> None:
        name = self._selected_name()
        if name is None:
            self._set_status("No target selected.", "warn")
            return

        path = self._targets[name]
        self._set_status(f"Clicking '{name}'…")
        self._root.update_idletasks()

        found = self._automator.find_and_click(path)
        if found:
            self._set_status(f"Clicked '{name}'.", "ok")
        else:
            self._set_status(f"'{name}' not found on screen.", "error")

    def _on_delete_selected(self) -> None:
        name = self._selected_name()
        if name is None:
            self._set_status("No target selected.", "warn")
            return

        self._tree.delete(name)
        del self._targets[name]
        save_targets(self._targets)
        self._update_preview()
        self._set_status(f"Deleted target '{name}'.", "ok")

    def _on_scroll(self, direction: int) -> None:
        try:
            amount = int(self._scroll_amount.get())
        except ValueError:
            self._set_status("Scroll amount must be a whole number.", "error")
            return

        # Windows delivers wheel events to whatever's under the cursor, so
        # if a target is selected, move there first rather than scrolling
        # wherever the cursor happens to already be sitting.
        at = None
        name = self._selected_name()
        if name is not None:
            match = self._automator.locate(self._targets[name])
            if match is not None:
                at = match.center

        self._automator.scroll(amount * direction, at=at)
        self._set_status(f"Scrolled {'up' if direction > 0 else 'down'} {amount}.", "ok")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
