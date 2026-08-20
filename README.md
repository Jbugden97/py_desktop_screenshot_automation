# PDF Page Screenshot Capture

A small desktop application that automatically captures a selected area of a
PDF viewer, clicks its **Next Page** button, waits for the next page, and
repeats. The captured pages are combined into one ordered PDF automatically.
PDF output is compressed, and an optional English OCR mode makes captured text
searchable with Ctrl+F while preserving the original page image. The
distributable application targets Windows 10 and Windows 11.

## Download for Windows

Download `PDFPageScreenshotCapture.exe` from the repository's latest GitHub
release. It is a portable, single-file application: Python does not need to be
installed.

Windows SmartScreen may warn about the first launch because the executable is
not code-signed. Choose **More info → Run anyway** only if you downloaded it
from this repository's Releases page.

## How to use it

1. Open the PDF and leave its viewer stationary.
2. Click **Select page area**, then drag around the visible PDF page.
3. Click **Select Next button**, then click the viewer's next-page control.
4. Choose an output folder.
5. Enter the number of pages and loading delays.
6. Choose **High quality**, **Balanced**, or **Smallest file** PDF quality.
7. Optionally enable **Make PDF searchable with English OCR**. OCR is off by
   default because it takes longer.
8. Click **Start capture** and leave the PDF viewer unobstructed.

The main window can be resized. When the available height is smaller than the
controls, use the vertical scrollbar or mouse wheel to reach every setting.

The selector displays a frozen image of the current desktop so the page stays
visible while you draw the capture region. The app temporarily saves images as
`page_001.png`, `page_002.png`, and so on, then combines them in that order as
`page.pdf` (or `<your-prefix>.pdf`). After the PDF is safely written, the
temporary PNG files are deleted. If PDF creation fails, the PNG files are kept
so no captured pages are lost.

### PDF quality and OCR

- **High quality** keeps the most image detail and produces the largest PDF.
- **Balanced** is the default and is suitable for most documents.
- **Smallest file** uses stronger compression and limits very large pages.
- **English OCR** preserves the compressed page image and adds an invisible
  text layer. Text can then be found with Ctrl+F, selected, and copied. Photos,
  diagrams, formatting, and the visible page remain image-based.

The standalone Windows executable includes the English Tesseract OCR engine;
users do not need to install Tesseract or Python. If OCR fails or finds no
English text, the PDF is not replaced and the captured PNG files are retained.

If you stop a run early, the pages captured so far are still converted into a
PDF.

Move the mouse pointer to the top-left corner at any time to trigger
PyAutoGUI's emergency stop.

## Run from source

This project uses [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
uv run py-desktop-screenshot-automation
```

Run the tests with:

```bash
uv run pytest
```

## Build the Windows executable

On a Windows machine with `uv` installed:

```powershell
.\scripts\build_windows.ps1
```

The portable executable is written to:

```text
dist/PDFPageScreenshotCapture.exe
```

GitHub Actions runs the same tests and PyInstaller build on a Windows runner.
The workflow artifact can be downloaded from the completed Actions run.

## Project structure

```text
src/py_desktop_screenshot_automation/
├── __init__.py    # command entry point
├── __main__.py    # python -m entry point
├── app.py         # Tkinter window and lifecycle
├── automation.py  # testable capture workflow
├── backend.py     # PyAutoGUI desktop adapter
├── models.py      # data models and validation
├── ocr.py         # bundled English Tesseract adapter
├── pdf_export.py  # compression, searchable PDF assembly, and cleanup
├── scrollable_frame.py # resizable scrolling UI container
└── selector.py    # visible desktop region/point selector
packaging/
└── windows.spec   # single-file Windows executable recipe
scripts/
├── build_windows.ps1
└── prepare_tesseract.ps1
tests/
├── test_automation.py
└── test_models.py
```

## Limitations

- Keep the PDF window stationary and unobstructed during capture.
- Page loading uses a fixed delay rather than visual change detection.
- OCR currently recognises English only.
- The downloadable executable is currently unsigned.

## Third-party software

The Windows executable bundles Tesseract OCR and English language data under
the Apache License 2.0. See the Tesseract project for license and attribution
details: <https://github.com/tesseract-ocr/tesseract>.
