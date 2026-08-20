$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

choco install tesseract --version 5.5.3.20260724 -y --no-progress
& (Join-Path $PSScriptRoot "prepare_tesseract.ps1")
uv sync --locked
uv run pytest -q
uv run pyinstaller --noconfirm --clean packaging/windows.spec

Write-Host "Built dist/PDFPageScreenshotCapture.exe"
