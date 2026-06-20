import os
import sys
import hashlib
import platform
import subprocess
import json
from datetime import datetime, date

SECRET_SALT = "PDF2TALLY_SECURE_OFFLINE_LICENSE_SALT_2026_@#$!"
LICENSE_FILE_PATH = os.path.expanduser("~/.pdf2tally.lic")

def get_machine_raw_identifiers():
    """Gathers raw hardware identifiers to form a unique hardware fingerprint."""
    identifiers = []
    try:
        if platform.system() == "Windows":
            # Motherboard UUID
            uuid_out = subprocess.check_output("wmic csproduct get uuid", shell=True).decode().strip().split("\n")
            if len(uuid_out) > 1:
                identifiers.append(uuid_out[1].strip())
            
            # CPU ID
            cpuid_out = subprocess.check_output("wmic cpu get processorid", shell=True).decode().strip().split("\n")
            if len(cpuid_out) > 1:
                identifiers.append(cpuid_out[1].strip())
                
            # BIOS Serial
            bios_out = subprocess.check_output("wmic bios get serialnumber", shell=True).decode().strip().split("\n")
            if len(bios_out) > 1:
                identifiers.append(bios_out[1].strip())
    except Exception:
        pass
        
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

def generate_activation_key_legacy(signature: str, expiry_date_str: str) -> str:
    """Generates a legacy activation key (ACT-YYYYMMDD-CHECKSUM)."""
    signature = signature.strip().upper()
    expiry_date_str = expiry_date_str.strip()
    payload = f"{signature}:{expiry_date_str}"
    raw_key = f"{payload}:{SECRET_SALT}"
    checksum = hashlib.sha256(raw_key.encode()).hexdigest()[:8].upper()
    return f"ACT-{expiry_date_str}-{checksum}"

def generate_activation_key_new(signature: str, role: str, expiry_str: str) -> str:
    """Generates a new activation key (ACT-ROLE-EXPIRY-CHECKSUM)."""
    signature = signature.strip().upper()
    role = role.strip().upper()
    expiry_str = expiry_str.strip().upper()
    payload = f"{signature}:{role}:{expiry_str}"
    raw_key = f"{payload}:{SECRET_SALT}"
    checksum = hashlib.sha256(raw_key.encode()).hexdigest()[:10].upper()
    return f"ACT-{role}-{expiry_str}-{checksum}"

def generate_activation_key(signature: str, expiry_or_role: str, expiry_str: str = None) -> str:
    """
    Overloaded activation key generator to maintain backward compatibility.
    Usage:
      generate_activation_key(signature, expiry_date_str) -> legacy format
      generate_activation_key(signature, role, expiry_str) -> new format
    """
    if expiry_str is None:
        return generate_activation_key_legacy(signature, expiry_or_role)
    else:
        return generate_activation_key_new(signature, expiry_or_role, expiry_str)

def verify_license_key(key: str) -> tuple:
    """
    Verifies if the activation key is valid for the current machine signature.
    Returns (is_valid, role, expiry_datetime, error_message)
    """
    key = key.strip().upper()
    parts = key.split("-")
    
    current_sig = get_machine_signature()
    
    if len(parts) == 3 and parts[0] == "ACT":
        # Legacy format: ACT-YYYYMMDD-CHECKSUM
        expiry_date_str = parts[1]
        checksum = parts[2]
        
        try:
            if expiry_date_str == "99991231":
                expiry_dt = None  # Lifetime
            else:
                expiry_dt = datetime.strptime(expiry_date_str, "%Y%m%d")
        except ValueError:
            return False, "USER", None, "Invalid expiry date in key."
            
        expected_key = generate_activation_key_legacy(current_sig, expiry_date_str)
        if key != expected_key:
            return False, "USER", None, "Key is not valid for this computer signature."
            
        return True, "USER", expiry_dt, None
        
    elif len(parts) == 4 and parts[0] == "ACT":
        # New format: ACT-ROLE-EXPIRY-CHECKSUM
        role = parts[1]
        expiry_str = parts[2]
        checksum = parts[3]
        
        if role not in ["USER", "ADMIN"]:
            return False, "USER", None, "Invalid role in key."
            
        expiry_dt = None
        if expiry_str not in ["LIFETIME", "99991231"]:
            try:
                expiry_ts = int(expiry_str)
                expiry_dt = datetime.fromtimestamp(expiry_ts)
            except ValueError:
                return False, "USER", None, "Invalid expiry timestamp in key."
                
        expected_key = generate_activation_key_new(current_sig, role, expiry_str)
        if key != expected_key:
            return False, "USER", None, "Key is not valid for this computer signature."
            
        return True, role, expiry_dt, None
        
    return False, "USER", None, "Invalid key structure."

def load_license_data() -> dict:
    """Loads the license file from disk."""
    if not os.path.exists(LICENSE_FILE_PATH):
        return {}
    try:
        with open(LICENSE_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_license_data(data: dict):
    """Saves license data securely to disk."""
    try:
        with open(LICENSE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

MASTER_ADMIN_SIGNATURE = "6232-5DFF-EA95-C2F3"

def check_activation() -> dict:
    """
    Validates the local license activation state, checking for expiry and system clock tampering.
    Returns a status dictionary.
    """
    current_sig = get_machine_signature()
    
    # Auto-grant for master admin
    if current_sig == MASTER_ADMIN_SIGNATURE:
        return {
            "activated": True,
            "role": "ADMIN",
            "message": "Master Administrator (Auto-Authorized)",
            "expiry_date": "Lifetime",
            "days_remaining": 99999,
            "signature": current_sig
        }
        
    data = load_license_data()
    key = data.get("activation_key")
    last_run_str = data.get("last_run_date")
    
    if not key:
        return {"activated": False, "role": "USER", "message": "No license key found. Please activate.", "signature": current_sig}
        
    is_valid, role, expiry_dt, err = verify_license_key(key)
    if not is_valid:
        return {"activated": False, "role": "USER", "message": f"License verification failed: {err}", "signature": current_sig}
        
    now = datetime.now()
    
    # ─── CLOCK TAMPER DETECTION ───
    if last_run_str:
        try:
            if " " in last_run_str:
                last_run = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M:%S")
            else:
                last_run = datetime.strptime(last_run_str, "%Y-%m-%d")
            
            if now < last_run:
                return {
                    "activated": False,
                    "role": "USER",
                    "message": "Clock tampering detected! System clock has been rolled back.",
                    "signature": current_sig
                }
        except ValueError:
            pass
            
    # Check expiry
    if expiry_dt:
        if now > expiry_dt:
            return {"activated": False, "role": "USER", "message": f"License expired on {expiry_dt.strftime('%d-%b-%Y %H:%M:%S')}.", "signature": current_sig}
        
        seconds_remaining = (expiry_dt - now).total_seconds()
        days_remaining = seconds_remaining / 86400.0
        
        if seconds_remaining < 60:
            status_msg = f"License active (Expires in {int(seconds_remaining)} seconds)"
        elif seconds_remaining < 3600:
            status_msg = f"License active (Expires in {int(seconds_remaining / 60)} minutes)"
        else:
            status_msg = f"License active (Expires in {int(days_remaining)} days on {expiry_dt.strftime('%d-%b-%Y')})"
    else:
        days_remaining = 99999
        status_msg = "License active (Lifetime)"
        
    # Update last_run_date to now
    data["last_run_date"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_license_data(data)
    
    return {
        "activated": True,
        "role": role,
        "message": status_msg,
        "expiry_date": expiry_dt.strftime("%Y-%m-%d %H:%M:%S") if expiry_dt else "Lifetime",
        "days_remaining": round(days_remaining, 4),
        "signature": current_sig
    }

def activate(key: str) -> tuple:
    """
    Attempts to activate the application with a license key.
    Returns (success, message)
    """
    is_valid, role, expiry_dt, err = verify_license_key(key)
    if not is_valid:
        return False, err
        
    data = {
        "activation_key": key,
        "last_run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_license_data(data)
    return True, "Activation successful!"

def deactivate():
    """Removes the license file."""
    if os.path.exists(LICENSE_FILE_PATH):
        try:
            os.remove(LICENSE_FILE_PATH)
        except Exception:
            pass
