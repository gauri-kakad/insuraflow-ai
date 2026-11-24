import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_database
from services.seed_service import seed_database
from utils.logger import logger


def main():
    force = "--reset" in sys.argv
    logger.info(f"Initializing InsuraFlow AI MongoDB database (force_reset={force})...")
    get_database()
    counts = seed_database(force_reset=force)
    logger.info(f"Initialization complete: {counts}")


if __name__ == "__main__":
    main()
