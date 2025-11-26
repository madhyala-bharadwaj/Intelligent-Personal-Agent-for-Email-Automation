"""
Centralized logging configuration for the application.
Ensures consistent log formatting and output.
"""

import logging
import sys
import config


def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance.
    Avoids adding duplicate handlers if the logger is already configured.
    """
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
