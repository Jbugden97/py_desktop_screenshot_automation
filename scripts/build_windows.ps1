$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

uv sync --locked
uv run pytest -q
uv run pyinstaller --noconfirm --clean packaging/windows.spec

Write-Host "Built dist/PDFPageScreenshotCapture.exe"
