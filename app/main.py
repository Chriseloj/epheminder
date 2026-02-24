from core.cli import run_cli
from infrastructure.storage import Base, engine
import logging

# ------------------------------
# Run: python -m app.main
# ------------------------------

logging.basicConfig(
    filename="app.log",    # logs to this file
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def main():

    # 1️⃣ Inicialize  database (create tables if not exists)
    Base.metadata.create_all(engine)

    # 2️⃣ RUN CLI
    run_cli()

if __name__ == "__main__":
    main()