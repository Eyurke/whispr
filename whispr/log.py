"""App logging: %APPDATA%/Whispr/whispr.log (small, rotating)."""

from __future__ import annotations

import logging
import logging.handlers

from .config import appdata_dir


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("whispr")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    folder = appdata_dir()
    folder.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        folder / "whispr.log", maxBytes=512 * 1024, backupCount=2, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(stream)
    return logger
