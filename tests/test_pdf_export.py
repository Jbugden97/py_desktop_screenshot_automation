from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from py_desktop_screenshot_automation.pdf_export import (
    PDFExportError,
    export_screenshots_to_pdf,
)


def test_export_creates_ordered_pdf_and_removes_screenshots(
    tmp_path: Path,
) -> None:
    screenshot_paths = [
        tmp_path / "page_001.png",
        tmp_path / "page_002.png",
        tmp_path / "page_003.png",
    ]
    colors = [(240, 20, 20), (20, 240, 20), (20, 20, 240)]
    for path, color in zip(screenshot_paths, colors, strict=True):
        Image.new("RGB", (20, 30), color).save(path)

    output_path = export_screenshots_to_pdf(
        screenshot_paths,
        tmp_path / "page.pdf",
    )

    assert output_path == tmp_path / "page.pdf"
    assert output_path.is_file()
    assert not any(path.exists() for path in screenshot_paths)

    pdf = PdfReader(output_path)
    assert len(pdf.pages) == 3
    dominant_channels: list[int] = []
    for page in pdf.pages:
        images = list(page.images)
        assert len(images) == 1
        pixel = images[0].image.convert("RGB").getpixel((10, 15))
        dominant_channels.append(pixel.index(max(pixel)))
    assert dominant_channels == [0, 1, 2]


def test_export_leaves_screenshots_when_pdf_creation_fails(
    tmp_path: Path,
) -> None:
    valid_path = tmp_path / "page_001.png"
    invalid_path = tmp_path / "page_002.png"
    Image.new("RGB", (20, 30), "red").save(valid_path)
    invalid_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(UnidentifiedImageError):
        export_screenshots_to_pdf(
            [valid_path, invalid_path],
            tmp_path / "page.pdf",
        )

    assert valid_path.exists()
    assert invalid_path.exists()
    assert not (tmp_path / "page.pdf").exists()
    assert not (tmp_path / ".page.pdf.tmp").exists()


def test_export_requires_a_screenshot(tmp_path: Path) -> None:
    with pytest.raises(PDFExportError, match="At least one"):
        export_screenshots_to_pdf([], tmp_path / "page.pdf")
