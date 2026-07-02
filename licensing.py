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
LICENSE_DIR = os.path.expanduser("~/.pdf2tally")
LICENSE_FILE_PATH = os.path.join(LICENSE_DIR, ".lic")
LOGS_DIR = os.path.join(LICENSE_DIR, "logs")
INTERNAL_DIR = os.path.join(LICENSE_DIR, "internal")

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
from threading import RLock

# Memory cache for license verification
_cache_lock = RLock()
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
    "error_type": None,
    "license_key": None
}
_last_disk_read_time = 0.0
_boot_sync_done = False

def _xor_crypt(data_str: str, key: str) -> bytes:
    """XOR encrypts/decrypts a string with a key derived from hardware signature."""
    key_hash = hashlib.sha256(key.encode()).digest()
    data_bytes = data_str.encode('utf-8')
    encrypted = bytearray()
    for i, b in enumerate(data_bytes):
        k_byte = key_hash[i % len(key_hash)]
        encrypted.append(b ^ k_byte)
    return bytes(encrypted)

def _xor_decrypt(data_bytes: bytes, key: str) -> str:
    """XOR decrypts bytes with a key derived from hardware signature."""
    key_hash = hashlib.sha256(key.encode()).digest()
    decrypted = bytearray()
    for i, b in enumerate(data_bytes):
        k_byte = key_hash[i % len(key_hash)]
        decrypted.append(b ^ k_byte)
    return decrypted.decode('utf-8')

def save_local_license(cache_data, update_memory=True):
    """Saves the license cache to a local file, signed with SECRET_SALT and encrypted to prevent tampering."""
    try:
        data_to_sign = {
            "signature": cache_data.get("signature"),
            "activated": cache_data.get("activated"),
            "role": cache_data.get("role", "USER"),
            "expiry_date": cache_data.get("expiry_date"),
            "seconds_remaining": cache_data.get("seconds_remaining"),
            "last_sync_real": cache_data.get("last_sync_real"),
            "last_seen_time": cache_data.get("last_seen_time", time.time()),
            "license_id": cache_data.get("license_id"),
            "license_key": cache_data.get("license_key")
        }
        # Compute signature including license_id and license_key
        sign_str = f"{data_to_sign['signature']}|{data_to_sign['activated']}|{data_to_sign['role']}|{data_to_sign['expiry_date']}|{data_to_sign['seconds_remaining']}|{data_to_sign['last_sync_real']}|{data_to_sign['last_seen_time']}|{data_to_sign['license_id'] or ''}|{data_to_sign['license_key'] or ''}|{SECRET_SALT}"
        h = hashlib.sha256(sign_str.encode()).hexdigest()
        data_to_sign["sha256"] = h
        
        # Ensure directories exist
        os.makedirs(LICENSE_DIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(INTERNAL_DIR, exist_ok=True)
        
        # Ensure parent directory and license file are normal/visible on Windows before writing
        if platform.system() == "Windows":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(LICENSE_DIR, 128)  # 128 = FILE_ATTRIBUTE_NORMAL (Unhide)
                if os.path.exists(LICENSE_FILE_PATH):
                    ctypes.windll.kernel32.SetFileAttributesW(LICENSE_FILE_PATH, 128)  # 128 = FILE_ATTRIBUTE_NORMAL (Unhide)
            except Exception:
                pass

        # Encrypt plain text using hardware key signature
        plain_text = json.dumps(data_to_sign)
        encrypted_bytes = _xor_crypt(plain_text, data_to_sign["signature"])
        
        with open(LICENSE_FILE_PATH, "wb") as f:
            f.write(encrypted_bytes)
            
        # Hide license file on Windows
        if platform.system() == "Windows":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(LICENSE_FILE_PATH, 2)
            except Exception:
                pass

        # Update memory cache immediately
        if update_memory:
            with _cache_lock:
                _license_cache.update({
                    "activated": data_to_sign["activated"],
                    "role": data_to_sign["role"],
                    "message": "License active" if data_to_sign["activated"] else "License inactive",
                    "expiry_date": data_to_sign["expiry_date"],
                    "seconds_remaining": data_to_sign["seconds_remaining"],
                    "signature": data_to_sign["signature"],
                    "last_sync_monotonic": time.monotonic(),
                    "last_sync_real": data_to_sign["last_sync_real"],
                    "license_key": data_to_sign["license_key"],
                    "error_type": None
                })
    except Exception:
        logger.error("System settings file write error.")

def load_local_license() -> dict:
    """Loads and decrypts the license cache from the local file and verifies its signature."""
    if not os.path.exists(LICENSE_FILE_PATH):
        return None
    try:
        sig = get_machine_signature()
        with open(LICENSE_FILE_PATH, "rb") as f:
            encrypted_bytes = f.read()
            
        try:
            # Decrypt using machine fingerprint signature
            plain_text = _xor_decrypt(encrypted_bytes, sig)
            data = json.loads(plain_text)
        except Exception:
            logger.error("License integrity verification failed. Initializing login prompt.")
            return None
            
        required_keys = ["signature", "activated", "role", "expiry_date", "seconds_remaining", "last_sync_real", "last_seen_time", "sha256"]
        if not all(k in data for k in required_keys):
            logger.warning("License settings file is incomplete.")
            return None
            
        # Verify signature
        sign_str = f"{data['signature']}|{data['activated']}|{data['role']}|{data['expiry_date']}|{data['seconds_remaining']}|{data['last_sync_real']}|{data['last_seen_time']}|{data.get('license_id') or ''}|{data.get('license_key') or ''}|{SECRET_SALT}"
        h = hashlib.sha256(sign_str.encode()).hexdigest()
        if h != data["sha256"]:
            logger.warning("License integrity verification failed.")
            return None
            
        return data
    except Exception:
        logger.error("License validation required.")
        return None

OBFUSCATED_BACKEND_URL = "aHR0cHM6Ly9waWthY2h1OTc1LnB5dGhvbmFueXdoZXJlLmNvbQ=="

def get_cloud_backend_url():
    url = os.environ.get("PDF2TALLY_CLOUD_URL")
    if url:
        return url.strip().rstrip("/")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        result = s.connect_ex(('127.0.0.1', 8000))
        s.close()
        if result == 0:
            return "http://127.0.0.1:8000"
    except Exception:
        pass
    try:
        decoded = base64.b64decode(OBFUSCATED_BACKEND_URL.encode()).decode("utf-8")
        return decoded.strip().rstrip("/")
    except Exception:
        return "http://127.0.0.1:8000"

def sync_with_cloud(retry_duration=5) -> dict:
    """
    Tries to connect to the cloud licensing server for up to retry_duration seconds.
    Uses the local cache license_id and machine signature to verify status.
    If it fails due to network/internet connection issues, falls back to local file cache.
    """
    sig = get_machine_signature()
    cache_data = load_local_license()
    
    # If we don't have a local license_id, we cannot auto-login
    license_id = cache_data.get("license_id") if cache_data else None
    
    if not license_id:
        with _cache_lock:
            _license_cache.update({
                "activated": False,
                "role": "USER",
                "message": "Unlicensed",
                "signature": sig,
                "error_type": None
            })
        return _license_cache

    url = f"{get_cloud_backend_url()}/login"
    start_time = time.time()
    last_error_type = None
    last_error_msg = "Could not reach licensing server."
    
    while True:
        try:
            response = requests.post(url, json={
                "license_id": license_id,
                "machine_hash": sig
            }, timeout=5)
            
            if response.status_code == 200:
                try:
                    res_data = response.json()
                except Exception:
                    res_data = {}
                is_active_cloud = res_data.get("authorized", False)
                
                with _cache_lock:
                    _license_cache.update({
                        "activated": is_active_cloud,
                        "role": "USER",
                        "message": res_data.get("message", "License verified active."),
                        "expiry_date": res_data.get("expires_at", "Lifetime"),
                        "seconds_remaining": res_data.get("seconds_remaining", -1),
                        "signature": sig,
                        "last_sync_monotonic": time.monotonic(),
                        "last_sync_real": time.time(),
                        "error_type": None,
                        "license_key": cache_data.get("license_key") if cache_data else None
                    })
                    
                    # Save to local persistent cache
                    save_local_license({
                        "signature": sig,
                        "activated": is_active_cloud,
                        "role": "USER",
                        "expiry_date": _license_cache["expiry_date"],
                        "seconds_remaining": _license_cache["seconds_remaining"],
                        "last_sync_real": _license_cache["last_sync_real"],
                        "last_seen_time": _license_cache["last_sync_real"],
                        "license_id": license_id,
                        "license_key": cache_data.get("license_key") if cache_data else None
                    })
                return _license_cache
            
            elif response.status_code == 403 or response.status_code == 404:
                # Expired or invalid or revoked
                try:
                    res_data = response.json() if response.content else {}
                except Exception:
                    res_data = {}
                msg = res_data.get("message", "License invalid or expired.")
                with _cache_lock:
                    _license_cache.update({
                        "activated": False,
                        "role": "USER",
                        "message": msg,
                        "signature": sig,
                        "last_sync_monotonic": time.monotonic(),
                        "last_sync_real": time.time(),
                        "error_type": "invalid",
                        "license_key": cache_data.get("license_key") if cache_data else None
                    })
                    if cache_data:
                        cache_data["activated"] = False
                        save_local_license(cache_data)
                return _license_cache
                
            elif response.status_code >= 500:
                last_error_type = "server"
                last_error_msg = f"Server issue (HTTP {response.status_code})"
                logger.error("License Verification Failed: Server-side issue (HTTP %d) for signature %s", response.status_code, sig)
            else:
                last_error_type = "server"
                last_error_msg = "Licensing server returned an error."
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_error_type = "internet"
            last_error_msg = "Internet connectivity issue."
            logger.error("License Verification Failed: Internet connectivity issue for signature %s: %s", sig, str(e))
            
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
    
    global _last_disk_read_time, _boot_sync_done
    now_monotonic = time.monotonic()
    
    with _cache_lock:
        is_mem_synced = (_license_cache["last_sync_monotonic"] > 0)
        
    # Reload from disk if not synced, forced, or if 10 seconds elapsed since last read
    if not is_mem_synced or force_refresh or (now_monotonic - _last_disk_read_time > 10):
        _last_disk_read_time = now_monotonic
        if not os.path.exists(LICENSE_FILE_PATH):
            with _cache_lock:
                _license_cache.update({
                    "activated": False,
                    "message": "Unlicensed",
                    "error_type": None,
                    "license_key": None
                })
        else:
            cache_data = load_local_license()
            if not cache_data:
                # File exists but is corrupted/tampered!
                with _cache_lock:
                    _license_cache.update({
                        "activated": False,
                        "message": "License integrity verification failed.",
                        "error_type": None,
                        "license_key": None
                    })
            elif cache_data.get("signature") == sig:
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
                        "message": "License active" if is_active else "License expired.",
                        "expiry_date": cache_data.get("expiry_date", "-"),
                        "seconds_remaining": seconds_remaining - elapsed if seconds_remaining != -1 else -1,
                        "signature": sig,
                        "last_sync_monotonic": time.monotonic(),
                        "last_sync_real": cache_data["last_sync_real"],
                        "error_type": None,
                        "license_key": cache_data.get("license_key")
                    })
                cache_data["last_seen_time"] = last_seen
                save_local_license(cache_data, update_memory=False)
            
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
            save_local_license(cache_data, update_memory=False)
            
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

