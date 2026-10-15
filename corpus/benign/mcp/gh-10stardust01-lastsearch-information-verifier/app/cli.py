import argparse
import logging
import sys

from app.agent import FactCheckAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a Bengaluru civic claim.")
    parser.add_argument("claim", help="The viral claim to verify")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting fact-check CLI")
    try:
        verdict = FactCheckAgent().check(args.claim)
        print(verdict.model_dump_json(indent=2))
        logger.info("Fact-check completed successfully")
    except Exception as e:
        logger.error(f"Fact-check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
