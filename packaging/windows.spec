# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the portable Windows executable."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).parent
entry_point = project_root / "packaging" / "windows_entry.py"

hidden_imports = (
    collect_submodules("pyautogui")
    + collect_submodules("pyscreeze")
    + collect_submodules("mouseinfo")
)

tesseract_root = project_root / "vendor" / "tesseract"
if not (tesseract_root / "tesseract.exe").is_file():
    raise FileNotFoundError(
        "Run scripts/prepare_tesseract.ps1 before building the Windows executable."
    )

analysis = Analysis(
    [str(entry_point)],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[(str(tesseract_root), "tesseract")],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="PDFPageScreenshotCapture",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
