import os
import sys
import hashlib
import platform
import subprocess
import json
from datetime import datetime, date
import time

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

def sync_with_cloud(retry_duration=60) -> dict:
    """
    Tries to connect to the cloud licensing server for up to retry_duration seconds.
    Updates the global _license_cache on success or failure.
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
                with _cache_lock:
                    _license_cache.update({
                        "activated": res_data.get("activated", False),
                        "role": res_data.get("role", "USER"),
                        "message": res_data.get("message", ""),
                        "expiry_date": res_data.get("expiry_date", "Lifetime"),
                        "seconds_remaining": res_data.get("seconds_remaining", -1),
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
                return _license_cache
            
            elif response.status_code >= 500:
                last_error_type = "server"
                last_error_msg = f"Server-side issue (HTTP {response.status_code})"
            else:
                try:
                    res_data = response.json()
                except Exception:
                    res_data = {}
                last_error_type = "server"
                last_error_msg = res_data.get("message", "Licensing server returned an error.")
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            last_error_type = "internet"
            last_error_msg = "Internet connectivity issue."
            
        elapsed = time.time() - start_time
        if elapsed >= retry_duration:
            break
            
        time.sleep(2)
        
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
    If the cache is empty or in error state, triggers a sync.
    Otherwise, computes remaining time using python monotonic clock.
    """
    import time
    with _cache_lock:
        is_synced = (_license_cache["last_sync_monotonic"] > 0)
        has_error = (_license_cache["error_type"] is not None)
        
    if not is_synced or has_error or force_refresh:
        timeout = 60 if not is_synced else 5
        return sync_with_cloud(retry_duration=timeout)
        
    with _cache_lock:
        if _license_cache["admin_token"] is not None:
            return _license_cache.copy()
            
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
        
        if not activated and _license_cache["activated"]:
            _license_cache["activated"] = False
            _license_cache["message"] = "License expired."
            
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

