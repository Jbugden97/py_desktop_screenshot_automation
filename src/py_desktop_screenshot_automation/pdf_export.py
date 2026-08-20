"""Compress captured screenshots into image or searchable-image PDFs."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from .models import CompressionPreset
from .ocr import TesseractOCR


class PDFExportError(ValueError):
    """Raised when a PDF cannot be created from the supplied screenshots."""


class OCREngine(Protocol):
    """OCR functionality required by the PDF exporter."""

    def create_searchable_page(
        self,
        image_path: Path,
        output_path: Path,
        dpi: int,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class CompressionOptions:
    """JPEG and dimension limits used by a named quality preset."""

    jpeg_quality: int
    max_dimension: int
    dpi: int = 150


COMPRESSION_OPTIONS = {
    CompressionPreset.HIGH_QUALITY: CompressionOptions(92, 4000),
    CompressionPreset.BALANCED: CompressionOptions(82, 2600),
    CompressionPreset.SMALLEST_FILE: CompressionOptions(65, 1800),
}

ProgressCallback = Callable[[str], None]


def export_screenshots_to_pdf(
    screenshot_paths: Sequence[Path],
    output_path: Path,
    *,
    compression: CompressionPreset = CompressionPreset.BALANCED,
    searchable: bool = False,
    report_progress: ProgressCallback | None = None,
    ocr_engine: OCREngine | None = None,
) -> Path:
    """Compress screenshots, optionally OCR them, and atomically write a PDF.

    Input order becomes PDF page order. Source screenshots are deleted only
    after the complete final PDF has been written successfully. Any failure
    leaves every source screenshot available for recovery.
    """
    if not screenshot_paths:
        raise PDFExportError("At least one screenshot is required.")

    try:
        options = COMPRESSION_OPTIONS[compression]
    except KeyError as exc:
        raise PDFExportError("Unknown PDF compression preset.") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_pdf = output_path.with_name(f".{output_path.name}.tmp")
    progress = report_progress or (lambda _message: None)

    try:
        with tempfile.TemporaryDirectory(
            prefix="pdf-capture-",
            dir=output_path.parent,
        ) as work_dir_name:
            work_dir = Path(work_dir_name)
            compressed_paths = _compress_screenshots(
                screenshot_paths,
                work_dir,
                options,
                progress,
            )
            if searchable:
                _create_searchable_pdf(
                    compressed_paths,
                    temporary_pdf,
                    options.dpi,
                    progress,
                    ocr_engine or TesseractOCR(),
                )
            else:
                _create_image_pdf(
                    compressed_paths,
                    temporary_pdf,
                    options.dpi,
                )
            _validate_pdf(temporary_pdf, len(screenshot_paths), searchable)
            temporary_pdf.replace(output_path)
    except Exception:
        temporary_pdf.unlink(missing_ok=True)
        raise

    for screenshot_path in screenshot_paths:
        screenshot_path.unlink()
    return output_path


def _compress_screenshots(
    screenshot_paths: Sequence[Path],
    work_dir: Path,
    options: CompressionOptions,
    progress: ProgressCallback,
) -> list[Path]:
    compressed_paths: list[Path] = []
    total = len(screenshot_paths)
    for index, screenshot_path in enumerate(screenshot_paths, start=1):
        progress(f"Compressing page {index} of {total}...")
        compressed_path = work_dir / f"page_{index:06d}.jpg"
        with Image.open(screenshot_path) as source:
            image = _flatten_to_rgb(source)
            try:
                image.thumbnail(
                    (options.max_dimension, options.max_dimension),
                    Image.Resampling.LANCZOS,
                )
                image.save(
                    compressed_path,
                    format="JPEG",
                    quality=options.jpeg_quality,
                    optimize=True,
                    subsampling=2,
                    dpi=(options.dpi, options.dpi),
                )
            finally:
                image.close()
        compressed_paths.append(compressed_path)
    return compressed_paths


def _create_image_pdf(
    compressed_paths: Sequence[Path],
    output_path: Path,
    dpi: int,
) -> None:
    pdf = canvas.Canvas(str(output_path))
    for compressed_path in compressed_paths:
        with Image.open(compressed_path) as image:
            page_width = image.width * 72 / dpi
            page_height = image.height * 72 / dpi
        pdf.setPageSize((page_width, page_height))
        pdf.drawImage(
            str(compressed_path),
            0,
            0,
            width=page_width,
            height=page_height,
        )
        pdf.showPage()
    pdf.save()


def _create_searchable_pdf(
    compressed_paths: Sequence[Path],
    output_path: Path,
    dpi: int,
    progress: ProgressCallback,
    ocr_engine: OCREngine,
) -> None:
    writer = PdfWriter()
    total = len(compressed_paths)
    for index, compressed_path in enumerate(compressed_paths, start=1):
        progress(f"Recognising text on page {index} of {total}...")
        page_pdf = compressed_path.with_suffix(".ocr.pdf")
        ocr_engine.create_searchable_page(compressed_path, page_pdf, dpi)
        writer.append(PdfReader(page_pdf))
    with output_path.open("wb") as stream:
        writer.write(stream)


def _validate_pdf(path: Path, expected_pages: int, searchable: bool) -> None:
    reader = PdfReader(path)
    if len(reader.pages) != expected_pages:
        raise PDFExportError("The PDF page count did not match the capture.")
    if searchable and not any(page.extract_text().strip() for page in reader.pages):
        raise PDFExportError(
            "OCR found no searchable English text. The screenshots were kept."
        )


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Copy an image as RGB, flattening transparent areas onto white."""
    has_transparency = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    if not has_transparency:
        return image.convert("RGB")

    rgba_image = image.convert("RGBA")
    rgb_image = Image.new("RGB", rgba_image.size, "white")
    rgb_image.paste(rgba_image, mask=rgba_image.getchannel("A"))
    rgba_image.close()
    return rgb_image
