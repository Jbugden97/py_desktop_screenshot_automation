from __future__ import annotations

import threading
from pathlib import Path

from py_desktop_screenshot_automation.automation import CaptureRunner
from py_desktop_screenshot_automation.models import (
    CaptureSettings,
    ScreenPoint,
    ScreenRegion,
)


class FakeImage:
    def __init__(self, saved_paths: list[Path]) -> None:
        self.saved_paths = saved_paths

    def save(self, path: object) -> None:
        assert isinstance(path, Path)
        self.saved_paths.append(path)


class FakeBackend:
    def __init__(self) -> None:
        self.saved_paths: list[Path] = []
        self.clicks: list[ScreenPoint] = []
        self.regions: list[ScreenRegion] = []

    def screenshot(self, region: ScreenRegion) -> FakeImage:
        self.regions.append(region)
        return FakeImage(self.saved_paths)

    def click(self, point: ScreenPoint) -> None:
        self.clicks.append(point)


def test_runner_captures_every_page_and_clicks_between_pages(tmp_path: Path) -> None:
    backend = FakeBackend()
    progress: list[str] = []
    runner = CaptureRunner(backend, threading.Event(), progress.append)
    region = ScreenRegion(10, 20, 800, 1000)
    button = ScreenPoint(900, 700)
    settings = CaptureSettings(3, 0, 0, "page", tmp_path)

    saved_paths = runner.run(settings, region, button)

    assert [path.name for path in saved_paths] == [
        "page_001.png",
        "page_002.png",
        "page_003.png",
    ]
    assert backend.regions == [region, region, region]
    assert backend.clicks == [button, button]
    assert [path.name for path in backend.saved_paths] == [
        "page_001.png",
        "page_002.png",
        "page_003.png",
    ]
    assert progress[-1] == "Capturing page 3 of 3..."


def test_runner_stops_before_capture_when_already_cancelled(tmp_path: Path) -> None:
    stop_event = threading.Event()
    stop_event.set()
    backend = FakeBackend()
    runner = CaptureRunner(backend, stop_event, lambda _message: None)
    settings = CaptureSettings(3, 0, 0, "page", tmp_path)

    saved_paths = runner.run(
        settings,
        ScreenRegion(0, 0, 100, 100),
        ScreenPoint(100, 100),
    )

    assert saved_paths == []
    assert backend.saved_paths == []
    assert backend.clicks == []
