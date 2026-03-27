import logging
import os
import sys

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    log_to_console = os.getenv("LOG_TO_CONSOLE", "false").lower() == "true"
    force = os.getenv("LOG_FORCE", "false").lower() == "true"

    handlers = []

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if log_to_file:
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    if not handlers:
        handlers.append(logging.NullHandler())

    root_logger = logging.getLogger()
    if not root_logger.handlers or force:
        logging.basicConfig(level=log_level, handlers=handlers)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
    )