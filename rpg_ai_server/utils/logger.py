from __future__ import annotations

import logging
import sys

from ..config.settings import settings


def setup_logger(name: str = "rpg_ai_server") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(settings.app.log_level.upper())

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.app.log_level.upper())
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
