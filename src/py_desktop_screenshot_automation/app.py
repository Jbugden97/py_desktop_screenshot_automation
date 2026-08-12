"""Tkinter application for configuring and starting screenshot captures."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .automation import CaptureRunner
from .backend import PyAutoGUIBackend
from .models import (
    CaptureSettings,
    ScreenPoint,
    ScreenRegion,
    SettingsError,
    parse_capture_settings,
)
from .pdf_export import export_screenshots_to_pdf
from .selector import ScreenSelector, Selection, SelectionMode


class PDFCaptureApp:
    """Desktop UI for selecting coordinates and controlling a capture run."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Page Screenshot Capture")
        self.root.geometry("650x520")
        self.root.resizable(False, False)

        self.capture_region: ScreenRegion | None = None
        self.next_button: ScreenPoint | None = None
        self.output_folder: Path | None = None
        self.stop_event = threading.Event()
        self.backend = PyAutoGUIBackend()

        self.page_count = tk.StringVar(value="10")
        self.load_delay = tk.StringVar(value="1.5")
        self.initial_delay = tk.StringVar(value="3")
        self.filename_prefix = tk.StringVar(value="page")
        self.region_status = tk.StringVar(value="Not selected")
        self.button_status = tk.StringVar(value="Not selected")
        self.folder_status = tk.StringVar(value="Not selected")
        self.progress_status = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text="PDF Page Screenshot Capture",
            font=("Arial", 20, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Select the page area and the Next Page button, "
                "then run the capture."
            ),
        ).pack(anchor="w", pady=(5, 20))

        selections = ttk.LabelFrame(
            container, text="Screen selections", padding=12
        )
        selections.pack(fill="x")
        self._add_selection_row(
            selections,
            0,
            "1. Select page area",
            self.select_capture_region,
            self.region_status,
        )
        self._add_selection_row(
            selections,
            1,
            "2. Select Next button",
            self.select_next_button,
            self.button_status,
        )
        self._add_selection_row(
            selections,
            2,
            "3. Choose output folder",
            self.choose_output_folder,
            self.folder_status,
        )

        settings = ttk.LabelFrame(container, text="Capture settings", padding=12)
        settings.pack(fill="x", pady=15)
        self._add_setting(settings, 0, "Number of pages:", self.page_count)
        self._add_setting(
            settings, 1, "Loading delay after click:", self.load_delay, "seconds"
        )
        self._add_setting(
            settings, 2, "Delay before starting:", self.initial_delay, "seconds"
        )
        self._add_setting(settings, 3, "Filename prefix:", self.filename_prefix)

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=10)
        self.start_button = ttk.Button(
            controls, text="Start capture", command=self.start_capture
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            controls, text="Stop", command=self.stop_capture, state="disabled"
        )
        self.stop_button.pack(side="left", padx=10)

        ttk.Label(
            container,
            textvariable=self.progress_status,
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", pady=10)
        ttk.Label(
            container,
            text=(
                "Emergency stop: move the mouse quickly to the top-left "
                "corner of the screen."
            ),
            foreground="#8a0000",
        ).pack(anchor="w")

    @staticmethod
    def _add_selection_row(
        parent: ttk.LabelFrame,
        row: int,
        button_text: str,
        command,
        status: tk.StringVar,
    ) -> None:
        ttk.Button(parent, text=button_text, command=command).grid(
            row=row, column=0, sticky="w", pady=5
        )
        ttk.Label(parent, textvariable=status, wraplength=360).grid(
            row=row, column=1, sticky="w", padx=15
        )

    @staticmethod
    def _add_setting(
        parent: ttk.LabelFrame,
        row: int,
        label: str,
        variable: tk.StringVar,
        suffix: str = "",
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=variable, width=15).grid(
            row=row, column=1, sticky="w", padx=10
        )
        if suffix:
            ttk.Label(parent, text=suffix).grid(row=row, column=2, sticky="w")

    def _restore_after_selection(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def select_capture_region(self) -> None:
        self.root.withdraw()

        def selected(selection: Selection) -> None:
            if isinstance(selection, ScreenRegion):
                self.capture_region = selection
                self.region_status.set(
                    f"x={selection.left}, y={selection.top}, "
                    f"width={selection.width}, height={selection.height}"
                )
            self._restore_after_selection()

        self.root.after(
            250,
            lambda: self._open_selector("rectangle", selected),
        )

    def select_next_button(self) -> None:
        self.root.withdraw()

        def selected(selection: Selection) -> None:
            if isinstance(selection, ScreenPoint):
                self.next_button = selection
                self.button_status.set(f"x={selection.x}, y={selection.y}")
            self._restore_after_selection()

        self.root.after(
            250,
            lambda: self._open_selector("point", selected),
        )

    def _open_selector(self, mode: SelectionMode, on_selected) -> None:
        """Capture the visible desktop and use it as the selector background."""
        try:
            desktop_image = self.backend.desktop_screenshot()
            ScreenSelector(
                self.root,
                mode,
                desktop_image,
                on_selected,
                self._restore_after_selection,
            )
        except Exception as error:
            self._restore_after_selection()
            messagebox.showerror(
                "Cannot capture screen",
                f"The desktop could not be captured: {error}",
                parent=self.root,
            )

    def choose_output_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose screenshot output folder")
        if selected:
            self.output_folder = Path(selected)
            self.folder_status.set(str(self.output_folder))

    def _settings(self) -> CaptureSettings:
        if self.capture_region is None:
            raise SettingsError("Select the PDF page area.")
        if self.next_button is None:
            raise SettingsError("Select the Next Page button.")
        return parse_capture_settings(
            page_count=self.page_count.get(),
            load_delay=self.load_delay.get(),
            initial_delay=self.initial_delay.get(),
            filename_prefix=self.filename_prefix.get(),
            output_folder=self.output_folder,
        )

    def start_capture(self) -> None:
        try:
            settings = self._settings()
        except SettingsError as error:
            messagebox.showerror("Cannot start", str(error))
            return

        assert self.capture_region is not None
        assert self.next_button is not None
        region = self.capture_region
        next_button = self.next_button
        self.stop_event.clear()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.root.withdraw()

        def launch_worker() -> None:
            threading.Thread(
                target=self._capture,
                args=(settings, region, next_button),
                daemon=True,
            ).start()

        # Allow the application window to disappear before the first capture.
        self.root.after(250, launch_worker)

    def _capture(
        self,
        settings: CaptureSettings,
        region: ScreenRegion,
        next_button: ScreenPoint,
    ) -> None:
        runner = CaptureRunner(self.backend, self.stop_event, self._set_progress)
        try:
            screenshot_paths = runner.run(settings, region, next_button)
            if not screenshot_paths:
                self._set_progress("No screenshots were captured.")
                return

            self._set_progress("Creating PDF...")
            pdf_path = export_screenshots_to_pdf(
                screenshot_paths,
                settings.output_folder / f"{settings.filename_prefix}.pdf",
            )
            saved = len(screenshot_paths)
            message = (
                f"Capture stopped. Saved {saved} page(s) to {pdf_path.name}."
                if self.stop_event.is_set()
                else f"Finished. Saved {saved} page(s) to {pdf_path.name}."
            )
            self._set_progress(message)
        except self.backend.fail_safe_exception:
            self._set_progress("Emergency stop triggered by mouse fail-safe.")
        except Exception as error:
            self._set_progress(f"Error: {error}")
        finally:
            self.root.after(0, self._capture_finished)

    def _set_progress(self, message: str) -> None:
        self.root.after(0, lambda: self.progress_status.set(message))

    def stop_capture(self) -> None:
        self.stop_event.set()
        self.progress_status.set("Stopping...")

    def _capture_finished(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")


def run_app() -> None:
    """Create the Tk root window and enter its event loop."""
    root = tk.Tk()
    PDFCaptureApp(root)
    root.mainloop()
