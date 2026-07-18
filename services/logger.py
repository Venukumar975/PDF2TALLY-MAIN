import os
import sys
import logging
import platform
from logging.handlers import RotatingFileHandler

def log_compatibility_info(logger):
    try:
        if platform.system() == "Windows":
            logger.info("==================================================")
            logger.info("   HARDWARE SIGNATURE DIAGNOSTICS")
            logger.info("==================================================")
            
            uuid_retrieved = "FAILED"
            cpuid_retrieved = "FAILED"
            bios_retrieved = "FAILED"
            
            import subprocess
            # Motherboard UUID
            try:
                uuid_out = subprocess.check_output("wmic csproduct get uuid", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
                if len(uuid_out) > 1 and uuid_out[1].strip():
                    uuid_retrieved = uuid_out[1].strip()
            except Exception:
                pass
            if uuid_retrieved == "FAILED":
                try:
                    uuid_val = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
                    if uuid_val:
                        uuid_retrieved = uuid_val
                except Exception:
                    pass
            
            # CPU ID
            try:
                cpuid_out = subprocess.check_output("wmic cpu get processorid", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
                if len(cpuid_out) > 1 and cpuid_out[1].strip():
                    cpuid_retrieved = cpuid_out[1].strip()
            except Exception:
                pass
            if cpuid_retrieved == "FAILED":
                try:
                    cpuid_val = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).ProcessorId"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
                    if cpuid_val:
                        cpuid_retrieved = cpuid_val
                except Exception:
                    pass
            
            # BIOS Serial
            try:
                bios_out = subprocess.check_output("wmic bios get serialnumber", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
                if len(bios_out) > 1 and bios_out[1].strip():
                    bios_retrieved = bios_out[1].strip()
            except Exception:
                pass
            if bios_retrieved == "FAILED":
                try:
                    bios_val = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_Bios).SerialNumber"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
                    if bios_val:
                        bios_retrieved = bios_val
                except Exception:
                    pass
            
            logger.info(f"Motherboard UUID: {uuid_retrieved}")
            logger.info(f"CPU Processor ID: {cpuid_retrieved}")
            logger.info(f"BIOS Serial Number: {bios_retrieved}")
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
        
        # Log system compatibility logs right upon startup logging initialization
        log_compatibility_info(logger)
        
    return logger

# Single logger instance for importing across modules
logger = setup_logger()
