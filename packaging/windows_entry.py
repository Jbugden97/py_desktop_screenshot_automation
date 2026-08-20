"""PyInstaller entry point for the Windows executable."""

import sys

from py_desktop_screenshot_automation import main
from py_desktop_screenshot_automation.ocr import run_ocr_self_test


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test-ocr"]:
        run_ocr_self_test()
    else:
        main()
