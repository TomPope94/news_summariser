import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)

logger = logging.getLogger("NEWS_SUMMARISER")
logger.setLevel(logging.DEBUG)
