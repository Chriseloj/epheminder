from app.cli import run_cli
from infrastructure.storage import Base, engine, _secure_database_file
import logging
import os
import sys

# ------------------------------
# Run (default):
#   python -m app.main
#
# Run (debug logging):
#   LOG_TO_CONSOLE=true LOG_LEVEL=DEBUG python -m app.main
#
# Run (file logging):
#   LOG_TO_FILE=true python -m app.main
# ------------------------------

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    log_to_console = os.getenv("LOG_TO_CONSOLE", "false").lower() == "true"

    handlers = []

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        handlers.append(console_handler)

    if log_to_file:
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        handlers.append(file_handler)

    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

def start_app():

    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set in environment")
    
    configure_logging()
    
    Base.metadata.create_all(engine)
    _secure_database_file()

def main():
    
    try:
        start_app()
        run_cli()
    except Exception as e:
        logging.exception("Fatal error starting application")
        raise

if __name__ == "__main__":
    main()