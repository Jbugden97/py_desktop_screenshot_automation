"""Capture workflow, kept independent from the desktop UI."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol

from .models import CaptureSettings, ScreenPoint, ScreenRegion


class Screenshot(Protocol):
    """The part of a Pillow image used by the workflow."""

    def save(self, path: object) -> None: ...


class DesktopBackend(Protocol):
    """Mouse and screenshot operations required by the workflow."""

    def screenshot(self, region: ScreenRegion) -> Screenshot: ...

    def click(self, point: ScreenPoint) -> None: ...


ProgressCallback = Callable[[str], None]


class CaptureRunner:
    """Capture pages sequentially using an interchangeable desktop backend."""

    def __init__(
        self,
        backend: DesktopBackend,
        stop_event: threading.Event,
        report_progress: ProgressCallback,
    ) -> None:
        self._backend = backend
        self._stop_event = stop_event
        self._report_progress = report_progress

    def run(
        self,
        settings: CaptureSettings,
        region: ScreenRegion,
        next_button: ScreenPoint,
    ) -> int:
        """Run a capture and return the number of screenshots saved."""
        self._report_progress(
            f"Starting in {settings.initial_delay:g} seconds..."
        )
        if self._stop_event.wait(settings.initial_delay):
            return 0

        settings.output_folder.mkdir(parents=True, exist_ok=True)
        number_width = max(3, len(str(settings.pages)))
        saved = 0

        for page_number in range(1, settings.pages + 1):
            if self._stop_event.is_set():
                break

            self._report_progress(
                f"Capturing page {page_number} of {settings.pages}..."
            )
            image = self._backend.screenshot(region)
            filename = (
                f"{settings.filename_prefix}_"
                f"{page_number:0{number_width}d}.png"
            )
            image.save(settings.output_folder / filename)
            saved += 1

            if page_number == settings.pages:
                break

            self._backend.click(next_button)
            if self._stop_event.wait(settings.load_delay):
                break

        return saved
