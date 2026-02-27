from core.cli import run_cli
from infrastructure.storage import Base, engine
import logging

# ------------------------------
# Run: python -m app.main
# ------------------------------

def configure_logging():
    logging.basicConfig(
        filename="app.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

def main():
    configure_logging()
    Base.metadata.create_all(engine)
    run_cli()

if __name__ == "__main__":
    main()