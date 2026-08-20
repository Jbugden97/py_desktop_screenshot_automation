$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$source = Join-Path $env:ProgramFiles "Tesseract-OCR"
$destination = Join-Path $projectRoot "vendor\tesseract"

if (-not (Test-Path (Join-Path $source "tesseract.exe"))) {
    throw "Tesseract was not found at $source"
}

if (Test-Path $destination) {
    Remove-Item $destination -Recurse -Force
}

New-Item $destination -ItemType Directory -Force | Out-Null
Copy-Item (Join-Path $source "*") $destination -Recurse -Force

$allowedLanguages = @("eng.traineddata", "osd.traineddata")
Get-ChildItem (Join-Path $destination "tessdata\*.traineddata") |
    Where-Object { $_.Name -notin $allowedLanguages } |
    Remove-Item -Force

if (-not (Test-Path (Join-Path $destination "tessdata\eng.traineddata"))) {
    throw "English Tesseract language data was not found."
}

Write-Host "Prepared bundled English Tesseract runtime at $destination"
