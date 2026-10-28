"""Console logging configuration for VideoAnalyzer with readable formatting, colors and immediate flush."""

import copy
import logging
import sys
from typing import Any

from uvicorn.config import LOGGING_CONFIG

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_console_logging(level: int = logging.INFO) -> None:
    """Configure console logging for the root logger and all videoanalizer loggers."""
    # Ensure unbuffered standard output for real-time console streaming
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
        except Exception:
            pass

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    app_logger = logging.getLogger("videoanalizer")
    app_logger.setLevel(level)

    has_console = any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (sys.stdout, sys.stderr)
        for h in app_logger.handlers
    )
    if not has_console:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)
    app_logger.propagate = False

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_handler = logging.StreamHandler(sys.stdout)
        root_handler.setLevel(logging.WARNING)
        root_handler.setFormatter(formatter)
        root_logger.addHandler(root_handler)


def get_uvicorn_log_config() -> dict[str, Any]:
    """Return an updated Uvicorn log config dictionary preserving VideoAnalyzer loggers with colors & timestamps."""
    cfg = copy.deepcopy(LOGGING_CONFIG)
    if "formatters" in cfg and "handlers" in cfg and "loggers" in cfg:
        cfg["formatters"]["videoanalizer"] = {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s [%(asctime)s] %(name)s - %(message)s",
            "datefmt": "%H:%M:%S",
            "use_colors": None,
        }
        cfg["handlers"]["videoanalizer_console"] = {
            "formatter": "videoanalizer",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
        cfg["loggers"]["videoanalizer"] = {
            "handlers": ["videoanalizer_console"],
            "level": "INFO",
            "propagate": False,
        }
    return cfg
