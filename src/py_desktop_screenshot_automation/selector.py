"""Fullscreen overlays for selecting a screen region or point."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox
from typing import Literal

from PIL import Image, ImageTk

from .models import ScreenPoint, ScreenRegion

SelectionMode = Literal["rectangle", "point"]
Selection = ScreenRegion | ScreenPoint


class ScreenSelector:
    """Let the user select a rectangle or point on a fullscreen overlay."""

    def __init__(
        self,
        parent: tk.Tk,
        mode: SelectionMode,
        desktop_image: Image.Image,
        on_selected: Callable[[Selection], None],
        on_cancelled: Callable[[], None],
    ) -> None:
        self._parent = parent
        self._mode = mode
        self._on_selected = on_selected
        self._on_cancelled = on_cancelled
        self._start_x: int | None = None
        self._start_y: int | None = None
        self._rectangle_id: int | None = None

        self._window = tk.Toplevel(parent)
        self._window.attributes("-fullscreen", True)
        self._window.attributes("-topmost", True)
        self._window.configure(bg="black")
        self._window.focus_force()

        screen_width = self._window.winfo_screenwidth()
        screen_height = self._window.winfo_screenheight()
        visible_desktop = desktop_image.resize(
            (screen_width, screen_height),
            Image.Resampling.LANCZOS,
        )
        self._desktop_photo = ImageTk.PhotoImage(visible_desktop)

        self._canvas = tk.Canvas(
            self._window,
            bg="black",
            highlightthickness=0,
            cursor="crosshair",
        )
        self._canvas.pack(fill="both", expand=True)
        self._canvas.create_image(
            0,
            0,
            image=self._desktop_photo,
            anchor="nw",
        )

        instruction = (
            "Click and drag around the PDF page area"
            if mode == "rectangle"
            else "Click the PDF viewer's Next Page button"
        )
        self._canvas.create_rectangle(
            0,
            0,
            screen_width,
            105,
            fill="#111827",
            outline="",
        )
        self._canvas.create_text(
            screen_width // 2,
            52,
            text=f"{instruction}\nPress Escape to cancel",
            fill="white",
            font=("Arial", 20, "bold"),
        )

        if mode == "rectangle":
            self._canvas.bind("<ButtonPress-1>", self._on_press)
            self._canvas.bind("<B1-Motion>", self._on_drag)
            self._canvas.bind("<ButtonRelease-1>", self._on_release)
        else:
            self._canvas.bind("<Button-1>", self._on_point)
        self._window.bind("<Escape>", lambda _event: self._cancel())

    def _on_press(self, event: tk.Event) -> None:
        self._start_x = event.x_root
        self._start_y = event.y_root
        if self._rectangle_id is not None:
            self._canvas.delete(self._rectangle_id)
        self._rectangle_id = self._canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#ff4d4d",
            width=3,
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self._start_x is None or self._rectangle_id is None:
            return
        canvas_x = self._start_x - self._window.winfo_rootx()
        canvas_y = self._start_y - self._window.winfo_rooty()
        self._canvas.coords(
            self._rectangle_id,
            canvas_x,
            canvas_y,
            event.x,
            event.y,
        )

    def _on_release(self, event: tk.Event) -> None:
        if self._start_x is None or self._start_y is None:
            return
        left = min(self._start_x, event.x_root)
        top = min(self._start_y, event.y_root)
        width = abs(event.x_root - self._start_x)
        height = abs(event.y_root - self._start_y)
        if width < 20 or height < 20:
            messagebox.showwarning(
                "Selection too small",
                "Draw a larger rectangle.",
                parent=self._window,
            )
            return
        self._finish(ScreenRegion(left, top, width, height))

    def _on_point(self, event: tk.Event) -> None:
        self._finish(ScreenPoint(event.x_root, event.y_root))

    def _finish(self, selection: Selection) -> None:
        self._window.destroy()
        self._parent.after(100, lambda: self._on_selected(selection))

    def _cancel(self) -> None:
        self._window.destroy()
        self._parent.after(100, self._on_cancelled)
