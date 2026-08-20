"""Bundled Tesseract adapter for searchable-image PDF generation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader


class OCRError(RuntimeError):
    """Raised when the OCR engine cannot produce a searchable PDF page."""


class TesseractOCR:
    """Create searchable PDF pages with the bundled English OCR engine."""

    def __init__(
        self,
        executable: Path | None = None,
        tessdata_dir: Path | None = None,
    ) -> None:
        self.executable = executable or _find_tesseract_executable()
        self.tessdata_dir = tessdata_dir or _find_tessdata_dir(self.executable)

    def create_searchable_page(
        self,
        image_path: Path,
        output_path: Path,
        dpi: int,
    ) -> None:
        """Create one image-backed PDF page with an invisible text layer."""
        command = [
            str(self.executable),
            str(image_path),
            "stdout",
            "--tessdata-dir",
            str(self.tessdata_dir),
            "-l",
            "eng",
            "--oem",
            "1",
            "--psm",
            "3",
            "--dpi",
            str(dpi),
            "pdf",
        ]
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
        except FileNotFoundError as exc:
            raise OCRError("The bundled OCR engine could not be found.") from exc
        except subprocess.CalledProcessError as exc:
            details = exc.stderr.decode("utf-8", errors="replace").strip()
            message = "OCR failed while processing a captured page."
            if details:
                message = f"{message} {details}"
            raise OCRError(message) from exc

        if not result.stdout.startswith(b"%PDF-"):
            raise OCRError("OCR did not return a valid PDF page.")
        output_path.write_bytes(result.stdout)


def run_ocr_self_test() -> None:
    """Exercise the OCR binary embedded in the packaged Windows app."""
    with tempfile.TemporaryDirectory(prefix="ocr-self-test-") as directory:
        work_dir = Path(directory)
        image_path = work_dir / "source.png"
        output_path = work_dir / "result.pdf"
        image = Image.new("RGB", (1400, 350), "white")
        font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arial.ttf"
        font = ImageFont.truetype(str(font_path), 72)
        ImageDraw.Draw(image).text(
            (50, 100),
            "SEARCHABLE DOCUMENT 12345",
            fill="black",
            font=font,
        )
        image.save(image_path)

        TesseractOCR().create_searchable_page(image_path, output_path, 150)
        extracted_text = PdfReader(output_path).pages[0].extract_text()
        if "SEARCHABLE DOCUMENT 12345" not in extracted_text:
            raise OCRError("The bundled OCR self-test did not recognise its text.")


def _runtime_root() -> Path:
    """Return the PyInstaller extraction root or the source checkout root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _find_tesseract_executable() -> Path:
    configured = os.environ.get("TESSERACT_CMD")
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file():
            return configured_path

    bundled_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    bundled_path = _runtime_root() / "tesseract" / bundled_name
    if bundled_path.is_file():
        return bundled_path

    system_path = shutil.which("tesseract")
    if system_path:
        return Path(system_path)

    raise OCRError(
        "The OCR engine is unavailable. Reinstall the application or turn off OCR."
    )


def _find_tessdata_dir(executable: Path) -> Path:
    configured = os.environ.get("TESSDATA_PREFIX")
    candidates = [
        Path(configured) if configured else None,
        executable.parent / "tessdata",
        _runtime_root() / "tesseract" / "tessdata",
        Path("/opt/homebrew/share/tessdata"),
        Path("/usr/local/share/tessdata"),
        Path(sys.prefix) / "share" / "tessdata",
    ]
    for candidate in candidates:
        if candidate and (candidate / "eng.traineddata").is_file():
            return candidate
    raise OCRError("English OCR language data is missing from the application.")
