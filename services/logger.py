import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    Sets up a application-wide logger.
    Logs are printed to the console and also written to a rotating file in logs/app.log.
    """
    # Make sure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Configure main logger
    logger = logging.getLogger("pdf2tally")
    logger.setLevel(logging.INFO)
    
    # Check if handlers already exist to prevent duplicate logging inside Flask context
    if not logger.handlers:
        # Formatter: timestamp - level - [filename:line] - message
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s")
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File Handler (rotating, max 5MB, up to 3 backup files)
        file_path = os.path.join("logs", "app.log")
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# Single logger instance for importing across modules
logger = setup_logger()
