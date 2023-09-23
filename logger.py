import logging
from config import LOG_FILENAME, LOG_FORMAT


formatter = logging.Formatter(LOG_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if LOG_FILENAME:
    file_handler = logging.FileHandler(LOG_FILENAME, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
else:
    logger.warning("LOG_FILENAME not set! Logging to the file disabled!")
