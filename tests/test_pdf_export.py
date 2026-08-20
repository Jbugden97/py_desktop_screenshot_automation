from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from py_desktop_screenshot_automation.models import CompressionPreset
from py_desktop_screenshot_automation.ocr import TesseractOCR
from py_desktop_screenshot_automation.pdf_export import (
    PDFExportError,
    export_screenshots_to_pdf,
)


class FakeOCR:
    def __init__(self, text: str = "SEARCHABLE DOCUMENT") -> None:
        self.text = text
        self.calls: list[Path] = []

    def create_searchable_page(
        self,
        image_path: Path,
        output_path: Path,
        dpi: int,
    ) -> None:
        self.calls.append(image_path)
        with Image.open(image_path) as image:
            page_width = image.width * 72 / dpi
            page_height = image.height * 72 / dpi
        pdf = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))
        pdf.drawImage(str(image_path), 0, 0, page_width, page_height)
        text = pdf.beginText(10, 10)
        text.setTextRenderMode(3)
        text.textLine(self.text)
        pdf.drawText(text)
        pdf.save()


class BrokenOCR:
    def create_searchable_page(
        self,
        image_path: Path,
        output_path: Path,
        dpi: int,
    ) -> None:
        raise RuntimeError("OCR unavailable")


def test_export_creates_ordered_pdf_and_removes_screenshots(
    tmp_path: Path,
) -> None:
    screenshot_paths = _create_color_pages(tmp_path)

    output_path = export_screenshots_to_pdf(
        screenshot_paths,
        tmp_path / "page.pdf",
    )

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


def test_searchable_export_keeps_images_and_adds_text(tmp_path: Path) -> None:
    screenshot_paths = _create_color_pages(tmp_path)
    ocr = FakeOCR()

    output_path = export_screenshots_to_pdf(
        screenshot_paths,
        tmp_path / "searchable.pdf",
        searchable=True,
        ocr_engine=ocr,
    )

    pdf = PdfReader(output_path)
    assert len(pdf.pages) == 3
    assert len(ocr.calls) == 3
    assert all("SEARCHABLE DOCUMENT" in page.extract_text() for page in pdf.pages)
    assert all(len(list(page.images)) == 1 for page in pdf.pages)
    assert not any(path.exists() for path in screenshot_paths)


def test_compression_presets_reduce_file_size(tmp_path: Path) -> None:
    sizes: dict[CompressionPreset, int] = {}
    for preset in CompressionPreset:
        source = tmp_path / f"{preset.name}.png"
        Image.effect_noise((1600, 1200), 100).convert("RGB").save(source)
        output = tmp_path / f"{preset.name}.pdf"
        export_screenshots_to_pdf([source], output, compression=preset)
        sizes[preset] = output.stat().st_size

    assert sizes[CompressionPreset.HIGH_QUALITY] > sizes[CompressionPreset.BALANCED]
    assert sizes[CompressionPreset.BALANCED] > sizes[CompressionPreset.SMALLEST_FILE]


def test_export_leaves_screenshots_when_image_processing_fails(
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


def test_export_leaves_screenshots_when_ocr_fails(tmp_path: Path) -> None:
    screenshot_paths = _create_color_pages(tmp_path)

    with pytest.raises(RuntimeError, match="OCR unavailable"):
        export_screenshots_to_pdf(
            screenshot_paths,
            tmp_path / "page.pdf",
            searchable=True,
            ocr_engine=BrokenOCR(),
        )

    assert all(path.exists() for path in screenshot_paths)
    assert not (tmp_path / "page.pdf").exists()


def test_export_reports_progress(tmp_path: Path) -> None:
    screenshot_paths = _create_color_pages(tmp_path)[:1]
    messages: list[str] = []
    export_screenshots_to_pdf(
        screenshot_paths,
        tmp_path / "page.pdf",
        searchable=True,
        ocr_engine=FakeOCR(),
        report_progress=messages.append,
    )

    assert messages == [
        "Compressing page 1 of 1...",
        "Recognising text on page 1 of 1...",
    ]


def test_export_requires_a_screenshot(tmp_path: Path) -> None:
    with pytest.raises(PDFExportError, match="At least one"):
        export_screenshots_to_pdf([], tmp_path / "page.pdf")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows OCR bundle test")
def test_bundled_tesseract_creates_searchable_pdf(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    tesseract_root = project_root / "vendor" / "tesseract"
    engine = TesseractOCR(
        executable=tesseract_root / "tesseract.exe",
        tessdata_dir=tesseract_root / "tessdata",
    )
    screenshot = tmp_path / "ocr-source.png"
    image = Image.new("RGB", (1400, 350), "white")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
    ImageDraw.Draw(image).text(
        (50, 100),
        "SEARCHABLE DOCUMENT 12345",
        fill="black",
        font=font,
    )
    image.save(screenshot)

    output = export_screenshots_to_pdf(
        [screenshot],
        tmp_path / "ocr.pdf",
        searchable=True,
        ocr_engine=engine,
    )

    text = PdfReader(output).pages[0].extract_text()
    assert "SEARCHABLE DOCUMENT 12345" in text


def _create_color_pages(tmp_path: Path) -> list[Path]:
    paths = [tmp_path / f"page_{index:03d}.png" for index in range(1, 4)]
    colors = [(240, 20, 20), (20, 240, 20), (20, 20, 240)]
    for path, color in zip(paths, colors, strict=True):
        Image.new("RGB", (200, 300), color).save(path)
    return paths
