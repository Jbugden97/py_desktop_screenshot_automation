"""Shared data models and user-input validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SettingsError(ValueError):
    """Raised when capture settings are invalid."""


class CompressionPreset(StrEnum):
    """User-facing PDF image compression presets."""

    HIGH_QUALITY = "High quality"
    BALANCED = "Balanced"
    SMALLEST_FILE = "Smallest file"


@dataclass(frozen=True, slots=True)
class ScreenRegion:
    """A rectangular area in absolute screen coordinates."""

    left: int
    top: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.width, self.height


@dataclass(frozen=True, slots=True)
class ScreenPoint:
    """A point in absolute screen coordinates."""

    x: int
    y: int


@dataclass(frozen=True, slots=True)
class CaptureSettings:
    """Validated settings for one capture run."""

    pages: int
    load_delay: float
    initial_delay: float
    filename_prefix: str
    output_folder: Path
    compression: CompressionPreset = CompressionPreset.BALANCED
    ocr_enabled: bool = False


def parse_capture_settings(
    *,
    page_count: str,
    load_delay: str,
    initial_delay: str,
    filename_prefix: str,
    output_folder: Path | None,
    compression: str = CompressionPreset.BALANCED,
    ocr_enabled: bool = False,
) -> CaptureSettings:
    """Validate UI strings and return strongly typed capture settings."""
    if output_folder is None:
        raise SettingsError("Choose an output folder.")

    try:
        pages = int(page_count)
    except ValueError as exc:
        raise SettingsError("Number of pages must be a whole number.") from exc

    try:
        page_delay = float(load_delay)
        start_delay = float(initial_delay)
    except ValueError as exc:
        raise SettingsError("Delay values must be numbers.") from exc

    if pages < 1:
        raise SettingsError("Number of pages must be at least 1.")
    if page_delay < 0 or start_delay < 0:
        raise SettingsError("Delay values cannot be negative.")

    prefix = filename_prefix.strip() or "page"
    if not re.fullmatch(r"[\w .-]+", prefix, flags=re.UNICODE):
        raise SettingsError(
            "Filename prefix may contain letters, numbers, spaces, dots, "
            "underscores, and hyphens only."
        )

    try:
        compression_preset = CompressionPreset(compression)
    except ValueError as exc:
        raise SettingsError("Choose a valid PDF quality preset.") from exc

    return CaptureSettings(
        pages=pages,
        load_delay=page_delay,
        initial_delay=start_delay,
        filename_prefix=prefix,
        output_folder=output_folder,
        compression=compression_preset,
        ocr_enabled=ocr_enabled,
    )
