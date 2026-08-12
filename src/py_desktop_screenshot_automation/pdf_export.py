"""Convert captured screenshots into a single ordered PDF."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PIL import Image


class PDFExportError(ValueError):
    """Raised when a PDF cannot be created from the supplied screenshots."""


def export_screenshots_to_pdf(
    screenshot_paths: Sequence[Path],
    output_path: Path,
) -> Path:
    """Write screenshots to a PDF, then remove them after a successful save.

    The sequence order becomes the PDF page order. The PDF is first written to
    a temporary file in the output folder and atomically moved into place. If
    any step fails, the source screenshots are left untouched.
    """
    if not screenshot_paths:
        raise PDFExportError("At least one screenshot is required.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    pages: list[Image.Image] = []

    try:
        for screenshot_path in screenshot_paths:
            with Image.open(screenshot_path) as image:
                pages.append(_flatten_to_rgb(image))

        first_page, *remaining_pages = pages
        first_page.save(
            temporary_path,
            format="PDF",
            save_all=True,
            append_images=remaining_pages,
            resolution=100.0,
        )
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        for page in pages:
            page.close()

    for screenshot_path in screenshot_paths:
        screenshot_path.unlink()

    return output_path


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
