import os
import sys
import hashlib
import platform
import subprocess
import json
from datetime import datetime, date
import time
from services.logger import logger

SECRET_SALT = "PDF2TALLY_SECURE_OFFLINE_LICENSE_SALT_2026_@#$!"
LICENSE_FILE_PATH = os.path.expanduser("~/.pdf2tally.lic")

def get_machine_raw_identifiers():
    """Gathers raw hardware identifiers to form a unique hardware fingerprint."""
    identifiers = []
    
    if platform.system() == "Windows":
        # 1. Motherboard UUID
        uuid = None
        try:
            uuid_out = subprocess.check_output("wmic csproduct get uuid", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
            if len(uuid_out) > 1:
                uuid = uuid_out[1].strip()
        except Exception:
            pass
        if not uuid:
            try:
                uuid = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
            except Exception:
                pass
        if uuid:
            identifiers.append(uuid)
            
        # 2. CPU ID
        cpuid = None
        try:
            cpuid_out = subprocess.check_output("wmic cpu get processorid", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
            if len(cpuid_out) > 1:
                cpuid = cpuid_out[1].strip()
        except Exception:
            pass
        if not cpuid:
            try:
                cpuid = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).ProcessorId"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
            except Exception:
                pass
        if cpuid:
            identifiers.append(cpuid)
            
        # 3. BIOS Serial
        bios = None
        try:
            bios_out = subprocess.check_output("wmic bios get serialnumber", shell=True, stderr=subprocess.DEVNULL).decode().strip().split("\n")
            if len(bios_out) > 1:
                bios = bios_out[1].strip()
        except Exception:
            pass
        if not bios:
            try:
                bios = subprocess.check_output('powershell -NoProfile -Command "(Get-CimInstance Win32_Bios).SerialNumber"', shell=True, stderr=subprocess.DEVNULL).decode().strip()
            except Exception:
                pass
        if bios:
            identifiers.append(bios)
            
    raw_str = "|".join(filter(None, identifiers))
    if not raw_str:
        raw_str = "DEFAULT_WINDOWS_OFFLINE_SIGNATURE_FALLBACK"
    return raw_str

def get_machine_signature():
    """Returns a privacy-safe, SHA-256 hashed and formatted machine signature."""
    raw_str = get_machine_raw_identifiers()
    h = hashlib.sha256(raw_str.encode()).hexdigest()
    # Format signature as XXXX-XXXX-XXXX-XXXX
    return f"{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}".upper()

import base64
import requests
from threading import Lock

# Memory cache for license verification
_cache_lock = Lock()
_license_cache = {
    "activated": False,
    "role": "USER",
    "message": "Not initialized",
    "expiry_date": "-",
    "seconds_remaining": 0,
    "days_remaining": 0.0,
    "signature": None,
    "last_sync_monotonic": 0.0,
    "last_sync_real": 0.0,
    "admin_token": None,
    "admin_email": None,
    "error_type": None
}

def save_local_license(cache_data):
    """Saves the license cache to a local file, signed with SECRET_SALT to prevent tampering."""
    try:
        data_to_sign = {
            "signature": cache_data.get("signature"),
            "activated": cache_data.get("activated"),
            "role": cache_data.get("role"),
            "expiry_date": cache_data.get("expiry_date"),
            "seconds_remaining": cache_data.get("seconds_remaining"),
            "last_sync_real": cache_data.get("last_sync_real"),
            "last_seen_time": cache_data.get("last_seen_time", time.time())
        }
        # Compute signature
        sign_str = f"{data_to_sign['signature']}|{data_to_sign['activated']}|{data_to_sign['role']}|{data_to_sign['expiry_date']}|{data_to_sign['seconds_remaining']}|{data_to_sign['last_sync_real']}|{data_to_sign['last_seen_time']}|{SECRET_SALT}"
        h = hashlib.sha256(sign_str.encode()).hexdigest()
        data_to_sign["sha256"] = h
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(LICENSE_FILE_PATH), exist_ok=True)
        with open(LICENSE_FILE_PATH, "w") as f:
            json.dump(data_to_sign, f)
    except Exception as e:
        logger.error("Failed to save local license cache: %s", str(e))

def load_local_license() -> dict:
    """Loads the license cache from the local file and verifies its signature."""
    if not os.path.exists(LICENSE_FILE_PATH):
        return None
    try:
        with open(LICENSE_FILE_PATH, "r") as f:
            data = json.load(f)
            
        required_keys = ["signature", "activated", "role", "expiry_date", "seconds_remaining", "last_sync_real", "last_seen_time", "sha256"]
        if not all(k in data for k in required_keys):
            logger.warning("Local license cache is missing required keys.")
            return None
            
        # Verify signature
        sign_str = f"{data['signature']}|{data['activated']}|{data['role']}|{data['expiry_date']}|{data['seconds_remaining']}|{data['last_sync_real']}|{data['last_seen_time']}|{SECRET_SALT}"
        h = hashlib.sha256(sign_str.encode()).hexdigest()
        if h != data["sha256"]:
            logger.warning("Local license cache signature mismatch. Tampering suspected.")
            return None
            
        return data
    except Exception as e:
        logger.error("Failed to load local license cache: %s", str(e))
        return None

OBFUSCATED_BACKEND_URL = "aHR0cHM6Ly9waWthY2h1OTc1LnB5dGhvbmFueXdoZXJlLmNvbQ=="

def get_cloud_backend_url():
    url = os.environ.get("PDF2TALLY_CLOUD_URL")
    if url:
        return url.strip().rstrip("/")
    try:
        decoded = base64.b64decode(OBFUSCATED_BACKEND_URL.encode()).decode("utf-8")
        return decoded.strip().rstrip("/")
    except Exception:
        return "http://127.0.0.1:8000"

def sync_with_cloud(retry_duration=5) -> dict:
    """
    Tries to connect to the cloud licensing server for up to retry_duration seconds.
    Updates the global _license_cache on success or failure.
    If it fails due to network/internet connection issues, falls back to the local file cache.
    """
    sig = get_machine_signature()
    url = f"{get_cloud_backend_url()}/api/cloud/verify"
    
    start_time = time.time()
    last_error_type = None
    last_error_msg = "Could not reach licensing server."
    
    while True:
        try:
            response = requests.post(url, json={"machine_signature": sig}, timeout=5)
            
            if response.status_code == 200:
                res_data = response.json()
                is_active_cloud = res_data.get("activated", False)
                if not is_active_cloud:
                    msg = res_data.get("message", "")
                    if "not registered" in msg:
                        logger.warning("License Verification Failed: Device signature %s is unregistered. Message: %s", sig, msg)
                    elif "expired and Device deactivated" in msg:
                        logger.warning("License Verification Failed: Device signature %s has expired subscription and deactivated device. Message: %s", sig, msg)
                    elif "Deactivated" in msg:
                        logger.warning("License Verification Failed: Device signature %s is deactivated. Message: %s", sig, msg)
                    elif "expired" in msg:
                        logger.warning("License Verification Failed: Device signature %s has expired subscription. Message: %s", sig, msg)
                    else:
                        logger.warning("License Verification Failed: Device signature %s verification failed. Message: %s", sig, msg)
                
                with _cache_lock:
                    _license_cache.update({
                        "activated": is_active_cloud,
                        "role": res_data.get("role", "USER"),
                        "message": res_data.get("message", ""),
                        "expiry_date": res_data.get("expiry_date", "-" if not is_active_cloud else "Lifetime"),
                        "seconds_remaining": res_data.get("seconds_remaining", 0 if not is_active_cloud else -1),
                        "signature": sig,
                        "last_sync_monotonic": time.monotonic(),
                        "last_sync_real": time.time(),
                        "error_type": None
                    })
                    # If we have an active admin session, retain admin privileges
                    if _license_cache["admin_token"] is not None:
                        _license_cache["activated"] = True
                        _license_cache["role"] = "ADMIN"
                        _license_cache["message"] = "Administrator Session Active"
                        _license_cache["seconds_remaining"] = -1
                    
                    # Save to local persistent cache
                    save_local_license({
                        "signature": sig,
                        "activated": _license_cache["activated"],
                        "role": _license_cache["role"],
                        "expiry_date": _license_cache["expiry_date"],
                        "seconds_remaining": _license_cache["seconds_remaining"],
                        "last_sync_real": _license_cache["last_sync_real"],
                        "last_seen_time": _license_cache["last_sync_real"]
                    })
                return _license_cache
            
            elif response.status_code >= 500:
                last_error_type = "server"
                last_error_msg = f"Server-side issue (HTTP {response.status_code})"
                logger.error("License Verification Failed: Server-side issue (HTTP %d) for signature %s", response.status_code, sig)
            else:
                try:
                    res_data = response.json()
                except Exception:
                    res_data = {}
                last_error_type = "server"
                last_error_msg = res_data.get("message", "Licensing server returned an error.")
                logger.error("License Verification Failed: Server returned HTTP %d with message: %s for signature %s", response.status_code, last_error_msg, sig)
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_error_type = "internet"
            last_error_msg = "Internet connectivity issue."
            logger.error("License Verification Failed: Internet connectivity issue for signature %s: %s", sig, str(e))
            
        elapsed = time.time() - start_time
        if elapsed >= retry_duration:
            break
            
        time.sleep(2)
        
    # Attempt offline file cache load on failure
    cache_data = load_local_license()
    if cache_data and cache_data.get("signature") == sig:
        current_time = time.time()
        last_seen = max(current_time, cache_data.get("last_seen_time", 0.0))
        elapsed_offline = last_seen - cache_data["last_sync_real"]
        seconds_remaining = cache_data["seconds_remaining"]
        
        if seconds_remaining == -1:
            is_active = cache_data.get("activated", False)
            remaining_offline = -1
        else:
            remaining_offline = seconds_remaining - elapsed_offline
            if remaining_offline > 0:
                is_active = cache_data.get("activated", False)
            else:
                is_active = False
                
        if is_active:
            with _cache_lock:
                _license_cache.update({
                    "activated": True,
                    "role": cache_data.get("role", "USER"),
                    "message": "License active (Offline Mode)",
                    "expiry_date": cache_data.get("expiry_date", "-"),
                    "seconds_remaining": remaining_offline,
                    "signature": sig,
                    "last_sync_monotonic": time.monotonic(),
                    "last_sync_real": cache_data["last_sync_real"],
                    "error_type": None
                })
                if _license_cache["admin_token"] is not None:
                    _license_cache["activated"] = True
                    _license_cache["role"] = "ADMIN"
                    _license_cache["message"] = "Administrator Session Active"
                    _license_cache["seconds_remaining"] = -1
            
            cache_data["last_seen_time"] = last_seen
            save_local_license(cache_data)
            return _license_cache
            
    with _cache_lock:
        _license_cache.update({
            "activated": False,
            "message": last_error_msg,
            "error_type": last_error_type,
            "signature": sig
        })
        if _license_cache["admin_token"] is not None:
            _license_cache["activated"] = True
            _license_cache["role"] = "ADMIN"
            _license_cache["error_type"] = None
            
    return _license_cache

def check_activation(force_refresh=False) -> dict:
    """
    Checks the cached activation status.
    If the memory cache is empty, loads from the persistent file cache.
    If we need a force refresh, triggers a cloud sync.
    Otherwise, computes remaining time using python monotonic clock.
    """
    import time
    sig = get_machine_signature()
    
    with _cache_lock:
        is_mem_synced = (_license_cache["last_sync_monotonic"] > 0)
        
    if not is_mem_synced:
        cache_data = load_local_license()
        if cache_data and cache_data.get("signature") == sig:
            current_time = time.time()
            last_seen = max(current_time, cache_data.get("last_seen_time", 0.0))
            elapsed = last_seen - cache_data["last_sync_real"]
            seconds_remaining = cache_data["seconds_remaining"]
            
            if seconds_remaining == -1 or seconds_remaining - elapsed > 0:
                is_active = cache_data.get("activated", False)
            else:
                is_active = False
                
            with _cache_lock:
                _license_cache.update({
                    "activated": is_active,
                    "role": cache_data.get("role", "USER"),
                    "message": "License active (Offline Mode)" if is_active else "License expired.",
                    "expiry_date": cache_data.get("expiry_date", "-"),
                    "seconds_remaining": seconds_remaining - elapsed if seconds_remaining != -1 else -1,
                    "signature": sig,
                    "last_sync_monotonic": time.monotonic(),
                    "last_sync_real": cache_data["last_sync_real"],
                    "error_type": None
                })
            cache_data["last_seen_time"] = last_seen
            save_local_license(cache_data)
            
    with _cache_lock:
        is_synced = (_license_cache["last_sync_monotonic"] > 0)
        
    if not is_synced or force_refresh:
        return sync_with_cloud(retry_duration=5)
        
    with _cache_lock:
        if _license_cache["admin_token"] is not None:
            return _license_cache.copy()
            
        if not _license_cache["activated"]:
            res = _license_cache.copy()
            res["days_remaining"] = 0.0
            return res
            
        seconds_remaining = _license_cache["seconds_remaining"]
        if seconds_remaining == -1:
            days_remaining = 99999
            status_msg = "License active (Lifetime)"
            activated = True
        else:
            elapsed = time.monotonic() - _license_cache["last_sync_monotonic"]
            remaining = seconds_remaining - elapsed
            
            if remaining <= 0:
                activated = False
                days_remaining = 0.0
                status_msg = "License expired."
            else:
                activated = True
                days_remaining = remaining / 86400.0
                
                if remaining < 60:
                    status_msg = f"License active (Expires in {int(remaining)} seconds)"
                elif remaining < 3600:
                    status_msg = f"License active (Expires in {int(remaining / 60)} minutes)"
                else:
                    days_int = int(remaining / 86400)
                    status_msg = f"License active (Expires in {days_int} days)"
                    
        res = _license_cache.copy()
        res["activated"] = activated
        res["message"] = status_msg
        res["days_remaining"] = round(days_remaining, 4)
        if seconds_remaining != -1:
            res["seconds_remaining"] = max(0, int(remaining))
        
        if not activated and _license_cache["activated"]:
            _license_cache["activated"] = False
            _license_cache["message"] = "License expired."
            cache_data = load_local_license()
            if cache_data:
                cache_data["activated"] = False
                save_local_license(cache_data)
                
        current_time = time.time()
        cache_data = load_local_license()
        if cache_data:
            cache_data["last_seen_time"] = max(current_time, cache_data.get("last_seen_time", 0.0))
            save_local_license(cache_data)
            
        return res

def activate(key: str) -> tuple:
    """Trigger a verification sync with the cloud backend."""
    res = sync_with_cloud(retry_duration=5)
    if res["activated"]:
        return True, "License activated successfully!"
    return False, res.get("message", "Activation failed.")

def deactivate():
    """Clear cached token and lock the workspace."""
    with _cache_lock:
        _license_cache.update({
            "activated": False,
            "role": "USER",
            "message": "Deactivated",
            "expiry_date": "-",
            "seconds_remaining": 0,
            "days_remaining": 0.0,
            "last_sync_monotonic": 0.0,
            "last_sync_real": 0.0,
            "admin_token": None,
            "admin_email": None,
            "error_type": None
        })
    if os.path.exists(LICENSE_FILE_PATH):
        try:
            os.remove(LICENSE_FILE_PATH)
        except Exception as e:
            logger.error("Failed to delete local license file on deactivation: %s", str(e))

