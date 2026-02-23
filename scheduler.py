import logging
import time

from feed_fetcher import refresh_all_feeds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

while True:
    logger.info("Refreshing feeds...")
    try:
        refresh_all_feeds()
        logger.info("Done.")
    except Exception:
        logger.exception("Feed refresh failed")
    time.sleep(1800)
