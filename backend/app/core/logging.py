# this file configures shared logging helpers
import logging
import sys


def configure_logging() -> None:
    # this function sets a plain readable log format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
