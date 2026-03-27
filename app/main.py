from app.cli import run_cli

from infrastructure.storage import Base, engine, _secure_database_file
from infrastructure.logging import configure_logging

import logging
import os

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

def start_app():

    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set in environment")
    
    Base.metadata.create_all(engine)
    _secure_database_file()

def main():
    
    try:
        configure_logging()
        start_app()
        run_cli()
    except Exception as e:
        logging.exception("Fatal error starting application")
        raise

if __name__ == "__main__":
    main()