import logging
from core.config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)

logger = logging.getLogger(settings.LOGGER.LOGGER_NAME)
logger.setLevel(logging.DEBUG if settings.LOGGER.DEBUG else logging.INFO)
