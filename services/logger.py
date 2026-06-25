import os
import sys
import logging
import platform
from logging.handlers import RotatingFileHandler

def log_compatibility_info(logger):
    try:
        logger.info("==================================================")
        logger.info("   APPLICATION STARTUP & SYSTEM COMPATIBILITY")
        logger.info("==================================================")
        logger.info(f"OS Platform: {platform.system()} {platform.release()} ({platform.version()})")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Execution Directory: {os.getcwd()}")
        if hasattr(sys, '_MEIPASS'):
            logger.info(f"PyInstaller Temp Path (_MEIPASS): {sys._MEIPASS}")
        else:
            logger.info("PyInstaller: Running as raw script (Not Bundled)")
            
        # Get hardware info details safely
        try:
            import subprocess
            logger.info("--------------------------------------------------")
            logger.info("   HARDWARE SIGNATURE DIAGNOSTICS")
            logger.info("--------------------------------------------------")
            
            uuid_retrieved = "FAILED"
            cpuid_retrieved = "FAILED"
            bios_retrieved = "FAILED"
            
            if platform.system() == "Windows":
                # Motherboard UUID
                try:
                    uuid_out = subprocess.check_output("wmic csproduct get uuid", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
                    if len(uuid_out) > 1 and uuid_out[1].strip():
                        uuid_retrieved = f"SUCCESS (WMIC: {uuid_out[1].strip()})"
                except Exception:
                    pass
                if "SUCCESS" not in uuid_retrieved:
                    try:
                        uuid_val = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
                        if uuid_val:
                            uuid_retrieved = f"SUCCESS (PowerShell: {uuid_val})"
                    except Exception:
                        pass
                
                # CPU ID
                try:
                    cpuid_out = subprocess.check_output("wmic cpu get processorid", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
                    if len(cpuid_out) > 1 and cpuid_out[1].strip():
                        cpuid_retrieved = f"SUCCESS (WMIC: {cpuid_out[1].strip()})"
                except Exception:
                    pass
                if "SUCCESS" not in cpuid_retrieved:
                    try:
                        cpuid_val = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).ProcessorId"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
                        if cpuid_val:
                            cpuid_retrieved = f"SUCCESS (PowerShell: {cpuid_val})"
                    except Exception:
                        pass
                
                # BIOS Serial
                try:
                    bios_out = subprocess.check_output("wmic bios get serialnumber", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
                    if len(bios_out) > 1 and bios_out[1].strip():
                        bios_retrieved = f"SUCCESS (WMIC: {bios_out[1].strip()})"
                except Exception:
                    pass
                if "SUCCESS" not in bios_retrieved:
                    try:
                        bios_val = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_Bios).SerialNumber"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
                        if bios_val:
                            bios_retrieved = f"SUCCESS (PowerShell: {bios_val})"
                    except Exception:
                        pass
            
            logger.info(f"Motherboard UUID Status: {uuid_retrieved}")
            logger.info(f"CPU Processor ID Status: {cpuid_retrieved}")
            logger.info(f"BIOS Serial Number Status: {bios_retrieved}")
            
            from licensing import get_machine_signature
            logger.info(f"Final Compiled Machine Signature: {get_machine_signature()}")
        except Exception as e:
            logger.error(f"Failed to compile hardware signature diagnostics: {e}")
            
        logger.info("--------------------------------------------------")
        logger.info("   SOFTWARE DEPENDENCY VERSIONS")
        logger.info("--------------------------------------------------")
        dependencies = ['flask', 'webview', 'pdfplumber', 'openpyxl', 'pandas', 'aksharamukha']
        for dep in dependencies:
            try:
                mod = __import__(dep)
                version = getattr(mod, '__version__', 'unknown')
                logger.info(f"Package '{dep}': Version {version}")
            except ImportError:
                logger.warning(f"Package '{dep}': NOT INSTALLED")
            except Exception as e:
                logger.warning(f"Package '{dep}': Version check failed ({e})")
        logger.info("==================================================")
    except Exception as e:
        logger.error(f"Error logging compatibility details: {e}")

def setup_logger():
    """
    Sets up an application-wide logger.
    Logs are printed to the console and also written to a rotating file in ~/.pdf2tally/logs/app.log.
    The log file is cleared/flushed at startup but persists after execution.
    """
    # Make sure logs directory exists in user home folder
    user_dir = os.path.expanduser("~/.pdf2tally")
    logs_dir = os.path.join(user_dir, "logs")
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
        # Formatter: timestamp (12-hour format with AM/PM) - level - [filename:line] - message
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
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
