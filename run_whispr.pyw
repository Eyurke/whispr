"""Launcher for Whispr (no console window when opened with pythonw)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from whispr.app import main

main()
