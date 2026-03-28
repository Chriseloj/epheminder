import logging
import os
import sys

def configure_logging():
    """
    Configure the root logger based on environment variables.

    This function sets up logging handlers and formatting dynamically using
    environment configuration. It supports logging to console, file, or both.

    Environment variables:
        LOG_LEVEL (str): Logging level (e.g., DEBUG, INFO). Defaults to INFO.
        LOG_TO_FILE (str): "true" to enable file logging to 'app.log'.
        LOG_TO_CONSOLE (str): "true" to enable logging to stderr.
        LOG_FORCE (str): "true" to override existing logging configuration.

    Behavior:
        - If no handlers are enabled, a NullHandler is used.
        - If the root logger already has handlers, configuration is skipped
          unless LOG_FORCE is set to true.

    Side effects:
        - Modifies the global root logger configuration.
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
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