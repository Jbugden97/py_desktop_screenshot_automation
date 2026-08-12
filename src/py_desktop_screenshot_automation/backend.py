"""PyAutoGUI adapter for real desktop interaction."""

from __future__ import annotations

import pyautogui

from .models import ScreenPoint, ScreenRegion


class PyAutoGUIBackend:
    """Capture screenshots and click points through PyAutoGUI."""

    fail_safe_exception = pyautogui.FailSafeException

    def __init__(self) -> None:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.15

    def screenshot(self, region: ScreenRegion):
        return pyautogui.screenshot(region=region.as_tuple())

    def desktop_screenshot(self):
        """Capture the desktop before the selection overlay is shown."""
        return pyautogui.screenshot()

    def click(self, point: ScreenPoint) -> None:
        pyautogui.click(point.x, point.y)
