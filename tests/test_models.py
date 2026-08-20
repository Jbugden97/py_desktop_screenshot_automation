from pathlib import Path

import pytest

from py_desktop_screenshot_automation.models import (
    CompressionPreset,
    SettingsError,
    parse_capture_settings,
)


def test_parse_capture_settings() -> None:
    output_folder = Path("screenshots")

    settings = parse_capture_settings(
        page_count="12",
        load_delay="1.5",
        initial_delay="3",
        filename_prefix="chapter-1",
        output_folder=output_folder,
    )

    assert settings.pages == 12
    assert settings.load_delay == 1.5
    assert settings.initial_delay == 3
    assert settings.filename_prefix == "chapter-1"
    assert settings.output_folder == output_folder
    assert settings.compression is CompressionPreset.BALANCED
    assert settings.ocr_enabled is False


def test_parse_pdf_options() -> None:
    settings = parse_capture_settings(
        page_count="1",
        load_delay="0",
        initial_delay="0",
        filename_prefix="searchable",
        output_folder=Path("screenshots"),
        compression="Smallest file",
        ocr_enabled=True,
    )

    assert settings.compression is CompressionPreset.SMALLEST_FILE
    assert settings.ocr_enabled is True


def test_invalid_compression_preset_is_rejected() -> None:
    with pytest.raises(SettingsError, match="quality preset"):
        parse_capture_settings(
            page_count="1",
            load_delay="0",
            initial_delay="0",
            filename_prefix="page",
            output_folder=Path("screenshots"),
            compression="Maximum magic",
        )


@pytest.mark.parametrize("page_count", ["0", "-1", "one"])
def test_invalid_page_count_is_rejected(page_count: str) -> None:
    with pytest.raises(SettingsError):
        parse_capture_settings(
            page_count=page_count,
            load_delay="1",
            initial_delay="1",
            filename_prefix="page",
            output_folder=Path("screenshots"),
        )


def test_path_separator_in_prefix_is_rejected() -> None:
    with pytest.raises(SettingsError, match="Filename prefix"):
        parse_capture_settings(
            page_count="1",
            load_delay="1",
            initial_delay="1",
            filename_prefix="chapter/one",
            output_folder=Path("screenshots"),
        )
