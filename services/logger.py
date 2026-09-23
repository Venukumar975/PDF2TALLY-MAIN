import os
import sys
import logging
import platform
from logging.handlers import RotatingFileHandler

def log_compatibility_info(logger):
    try:
        if platform.system() == "Windows":
            logger.info("==================================================")
            logger.info("   SYSTEM & ENVIRONMENT DIAGNOSTICS")
            logger.info("==================================================")
            logger.info(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
            logger.info(f"Machine: {platform.machine()} | Architecture: {platform.architecture()[0]}")
            logger.info(f"Python: {sys.version.split()[0]}")
            logger.info("==================================================")
    except Exception as e:
        logger.error(f"Error logging compatibility details: {e}")

def setup_logger():
    """
    Sets up an application-wide logger.
    Logs are printed to the console and also written to a rotating file.
    The log file is cleared/flushed at startup but persists after execution.
    """
    app_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
    logs_dir = os.path.join(app_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    file_path = os.path.join(logs_dir, "app.log")
    
    # Flush/truncate log file on startup to clean old session logs
    try:
        if os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.truncate(0)
    except Exception:
        pass

    # Configure main logger
    logger = logging.getLogger("pdf2tally")
    logger.setLevel(logging.INFO)
    
    # Check if handlers already exist to prevent duplicate logging inside Flask context
    if not logger.handlers:
        # Formatter: timestamp (12-hour format with AM/PM) - level - message
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%d-%b-%Y %I:%M:%S %p"
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File Handler (rotating, max 5MB, up to 3 backup files)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Log system compatibility logs in background thread to avoid blocking application startup
        import threading
        threading.Thread(target=log_compatibility_info, args=(logger,), daemon=True).start()
        
    return logger

# Single logger instance for importing across modules
logger = setup_logger()
