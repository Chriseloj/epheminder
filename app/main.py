from app.cli import run_cli
from infrastructure.storage import Base, engine, _secure_database_file
import logging
import os
import sys

# ------------------------------
# Run: python -m app.main
# ------------------------------

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"

    handlers = []

    # Logs to stderr (do not interfere with prints of CLI)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    handlers.append(console_handler)

    # Optional: file 
    if log_to_file:
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

def start_app():

    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set in environment")
    
    configure_logging()
    
    _secure_database_file()
    Base.metadata.create_all(engine)

def main():
    
    try:
        start_app()
        run_cli()
    except Exception as e:
        logging.exception("Fatal error starting application")
        raise

if __name__ == "__main__":
    main()