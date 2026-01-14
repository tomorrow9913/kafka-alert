import os
import logging
from logging.handlers import RotatingFileHandler
from core.config import settings

def setup_logging(logger_name: str, log_dir: str = settings.log_dir) -> logging.Logger:
    logger = logging.getLogger(logger_name)

    # 이미 핸들러가 있다면 리턴
    if logger.handlers:
        return logger

    log_format = '%(asctime)s - [%(levelname)s] %(name)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'monitor.log'),
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
