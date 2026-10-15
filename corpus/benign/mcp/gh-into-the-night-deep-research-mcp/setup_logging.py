import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name):
    logging.basicConfig(level=logging.DEBUG, force=True)
    logger = logging.getLogger(name)

    file_handler = RotatingFileHandler("app.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    logger.addHandler(file_handler)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    for handler in logger.handlers:
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(log_format))

    logger.setLevel(logging.DEBUG)

    return logger