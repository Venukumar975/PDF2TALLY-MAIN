import os
import json
import time
import hmac
import hashlib
from threading import Lock
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# Indian Standard Time (IST) Zone
IST = timezone(timedelta(hours=5, minutes=30))

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
db_lock = Lock()

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "CLOUD_BACKEND_SECRET_KEY_PDF2TALLY_2026")

def get_now_ist():
    return datetime.now(IST)

def load_db():
    with db_lock:
        if not os.path.exists(DB_FILE):
            default_data = {
                "licenses": [],
                "admins": []
            }
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            return default_data
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"licenses": [], "admins": []}

def save_db(data):
    with db_lock:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False

# Initialize and seed default Master Admin if empty
def seed_db():
    db = load_db()
    if not db.get("admins"):
        default_email = os.environ.get("ADMIN_EMAIL", "admin@pdf2tally.com")
        default_key = os.environ.get("ADMIN_KEY", "ADM-SUPER-SECURE-2026")
        default_password = os.environ.get("ADMIN_PASSWORD", "AdminPassword2026!")
        
        master_admin = {
            "email": default_email,
            "admin_key": default_key,
            "password_hash": generate_password_hash(default_password),
            "role": "ADMIN",
            "is_active": True,
            "created_at": get_now_ist().strftime("%Y-%m-%d %H:%M:%S")
        }
        db["admins"].append(master_admin)
        save_db(db)
        print("Master Admin successfully seeded in JSON store.")

seed_db()

# Admin Stateless Token Utilities
def generate_admin_token(email):
    ts = str(int(time.time()))
    msg = f"{email}:{ts}"
    sig = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}:{sig}"

def verify_admin_token(token):
    if not token:
        return False, None
    parts = token.split(":")
    if len(parts) != 3:
        return False, None
    email, ts, sig = parts
    try:
        # Token valid for 24 hours
        if time.time() - int(ts) > 86400:
            return False, None
    except ValueError:
        return False, None
    
    expected_msg = f"{email}:{ts}"
    expected_sig = hmac.new(SECRET_KEY.encode(), expected_msg.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected_sig):
        return True, email
    return False, None

def authenticate_request(req):
    """
    Returns (role, identifier_or_email) or (None, None).
    Role can be 'ADMIN' or 'CO-ADMIN'.
    """
    # 1. Check Admin authorization header
    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        is_valid, email = verify_admin_token(token)
        if is_valid:
            # Double check if admin is active in db
            db = load_db()
            for adm in db.get("admins", []):
                if adm.get("email") == email and adm.get("is_active"):
                    return "ADMIN", email
    
    # 2. Check Co-Admin machine signature (X-Machine-Signature)
    sig = req.headers.get("X-Machine-Signature") or (req.json.get("coadmin_signature") if req.is_json else None)
    if sig:
        sig = sig.strip().upper()
        db = load_db()
        for lic in db.get("licenses", []):
            if lic.get("machine_signature") == sig:
                if lic.get("role") == "CO-ADMIN" and lic.get("is_active"):
                    # Check expiry
                    expiry_str = lic.get("expiry_time")
                    if expiry_str:
                        expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
                        if get_now_ist() > expiry:
                            continue
                    return "CO-ADMIN", sig
                    
    return None, None

# -------------------------------------------------------------
# CLIENT API
# -------------------------------------------------------------
@app.route("/api/cloud/verify", methods=["POST"])
def verify_license():
    data = request.get_json() or {}
    sig = data.get("machine_signature", "").strip().upper()
    if not sig:
        return jsonify({"activated": False, "message": "Machine signature is required."}), 400
        
    db = load_db()
    license_record = None
    for lic in db.get("licenses", []):
        if lic.get("machine_signature") == sig:
            license_record = lic
            break
            
    if not license_record:
        return jsonify({
            "activated": False,
            "role": "USER",
            "message": "Device not registered. Please contact your administrator.",
            "signature": sig
        })
        
    if not license_record.get("is_active", True):
        return jsonify({
            "activated": False,
            "role": license_record.get("role", "USER"),
            "message": "This license has been deactivated by the administrator.",
            "signature": sig
        })
        
    expiry_str = license_record.get("expiry_time")
    now = get_now_ist()
    
    if expiry_str:
        try:
            expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        except ValueError:
            return jsonify({"activated": False, "message": "Corrupted license expiry details on cloud server."}), 500
            
        if now > expiry_dt:
            # Automatically flag as inactive in data store
            license_record["is_active"] = False
            save_db(db)
            return jsonify({
                "activated": False,
                "role": license_record.get("role", "USER"),
                "message": f"License expired on {expiry_dt.strftime('%d-%b-%Y %H:%M:%S')}.",
                "signature": sig
            })
            
        seconds_remaining = int((expiry_dt - now).total_seconds())
    else:
        seconds_remaining = -1  # Lifetime
        expiry_dt = None
        
    return jsonify({
        "activated": True,
        "role": license_record.get("role", "USER"),
        "message": "License verified active.",
        "expiry_date": expiry_str if expiry_str else "Lifetime",
        "seconds_remaining": seconds_remaining,
        "signature": sig
    })

# -------------------------------------------------------------
# ADMIN AUTHENTICATION
# -------------------------------------------------------------
@app.route("/api/cloud/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    admin_key = data.get("admin_key", "").strip()
    password = data.get("password", "").strip()
    
    if not email or not admin_key or not password:
        return jsonify({"success": False, "message": "Email, Admin Key, and Password are all required."}), 400
        
    db = load_db()
    matched_admin = None
    for adm in db.get("admins", []):
        if adm.get("email") == email:
            matched_admin = adm
            break
            
    if not matched_admin or matched_admin.get("admin_key") != admin_key or not matched_admin.get("is_active"):
        return jsonify({"success": False, "message": "Invalid credentials or inactive admin account."}), 401
        
    if not check_password_hash(matched_admin.get("password_hash"), password):
        return jsonify({"success": False, "message": "Invalid password."}), 401
        
    token = generate_admin_token(email)
    return jsonify({
        "success": True,
        "token": token,
        "role": "ADMIN",
        "email": email
    })

# -------------------------------------------------------------
# LICENSE & ROLE MANAGEMENT (CRUD)
# -------------------------------------------------------------
@app.route("/api/cloud/admin/licenses", methods=["GET"])
def list_licenses():
    role, identifier = authenticate_request(request)
    if not role:
        return jsonify({"success": False, "message": "Unauthorized access."}), 403
        
    db = load_db()
    now = get_now_ist()
    
    active_licenses = []
    deactivated_licenses = []
    
    for lic in db.get("licenses", []):
        expiry_str = lic.get("expiry_time")
        is_active = lic.get("is_active", True)
        
        # Calculate dynamic remaining time in seconds
        seconds_remaining = -1
        if is_active and expiry_str:
            try:
                expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
                if now > expiry_dt:
                    is_active = False
                    lic["is_active"] = False
                    seconds_remaining = 0
                else:
                    seconds_remaining = int((expiry_dt - now).total_seconds())
            except ValueError:
                pass
        
        lic_data = {
            "machine_signature": lic.get("machine_signature"),
            "activation_key": lic.get("activation_key"),
            "role": lic.get("role"),
            "expiry_time": expiry_str if expiry_str else "Lifetime",
            "seconds_remaining": seconds_remaining,
            "created_at": lic.get("created_at"),
            "created_by": lic.get("created_by")
        }
        
        if is_active:
            active_licenses.append(lic_data)
        else:
            deactivated_licenses.append(lic_data)
            
    # Save db back in case automatic expiry occurred
    save_db(db)
    
    return jsonify({
        "success": True,
        "active_count": len(active_licenses),
        "active_licenses": active_licenses,
        "deactivated_licenses": deactivated_licenses
    })

@app.route("/api/cloud/admin/licenses", methods=["POST"])
def register_license():
    role, identifier = authenticate_request(request)
    if not role:
        return jsonify({"success": False, "message": "Unauthorized access."}), 403
        
    data = request.get_json() or {}
    target_sig = data.get("machine_signature", "").strip().upper()
    target_role = data.get("role", "USER").strip().upper()
    duration = data.get("duration", "").strip().lower()
    
    if not target_sig:
        return jsonify({"success": False, "message": "Target machine signature is required."}), 400
        
    if target_role not in ["USER", "CO-ADMIN"]:
        return jsonify({"success": False, "message": "Invalid role. Must be USER or CO-ADMIN."}), 400
        
    # Enforce Co-Admin restrictions: Co-Admins can only create USER licenses
    if role == "CO-ADMIN" and target_role != "USER":
        return jsonify({"success": False, "message": "Co-Admins are only authorized to create Standard USER licenses."}), 403
        
    db = load_db()
    
    # Strictly check if signature is already registered (either active or deactivated)
    for lic in db.get("licenses", []):
        if lic.get("machine_signature") == target_sig:
            return jsonify({"success": False, "message": "This machine signature is already registered."}), 409
            
    # Calculate Expiry
    now = get_now_ist()
    if duration == "1min":
        expiry_dt = now + timedelta(minutes=1)
    elif duration == "5min":
        expiry_dt = now + timedelta(minutes=5)
    elif duration == "1day":
        expiry_dt = now + timedelta(days=1)
    elif duration == "1week":
        expiry_dt = now + timedelta(days=7)
    elif duration == "1month":
        expiry_dt = now + timedelta(days=30)
    elif duration == "4month":
        expiry_dt = now + timedelta(days=120)
    elif duration == "1year":
        expiry_dt = now + timedelta(days=365)
    elif duration == "lifetime":
        expiry_dt = None
    else:
        return jsonify({"success": False, "message": f"Unsupported duration: {duration}"}), 400
        
    expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S") if expiry_dt else None
    
    # Generate human-friendly reference activation key
    checksum = hashlib.sha256(f"{target_sig}:{target_role}:{expiry_str or 'LIFETIME'}:{SECRET_KEY}".encode()).hexdigest()[:8].upper()
    activation_key = f"ACT-{target_role}-{checksum}"
    
    new_license = {
        "machine_signature": target_sig,
        "activation_key": activation_key,
        "role": target_role,
        "expiry_time": expiry_str,
        "is_active": True,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "created_by": identifier
    }
    
    db["licenses"].append(new_license)
    save_db(db)
    
    return jsonify({
        "success": True,
        "message": "License created successfully.",
        "license": {
            "machine_signature": target_sig,
            "activation_key": activation_key,
            "role": target_role,
            "expiry_time": expiry_str or "Lifetime"
        }
    })

@app.route("/api/cloud/admin/deactivate", methods=["POST"])
def deactivate_license():
    role, identifier = authenticate_request(request)
    if not role:
        return jsonify({"success": False, "message": "Unauthorized access."}), 403
        
    data = request.get_json() or {}
    target_sig = data.get("machine_signature", "").strip().upper()
    
    if not target_sig:
        return jsonify({"success": False, "message": "Target machine signature is required."}), 400
        
    db = load_db()
    license_record = None
    for lic in db.get("licenses", []):
        if lic.get("machine_signature") == target_sig:
            license_record = lic
            break
            
    if not license_record:
        return jsonify({"success": False, "message": "License not found."}), 404
        
    # Enforce Co-Admin restrictions: Co-Admins can only deactivate USER licenses
    if role == "CO-ADMIN" and license_record.get("role") != "USER":
        return jsonify({"success": False, "message": "Co-Admins are only authorized to deactivate USER licenses."}), 403
        
    license_record["is_active"] = False
    save_db(db)
    
    return jsonify({
        "success": True,
        "message": f"Successfully deactivated license for signature {target_sig}."
    })

# -------------------------------------------------------------
# ADMIN MANAGEMENT (ONLY ACCESSIBLE BY ADMINS)
# -------------------------------------------------------------
@app.route("/api/cloud/admin/create_admin", methods=["POST"])
def create_admin():
    role, identifier = authenticate_request(request)
    if role != "ADMIN":
        return jsonify({"success": False, "message": "Unauthorized. Requires Administrator status."}), 403
        
    data = request.get_json() or {}
    new_email = data.get("email", "").strip()
    new_key = data.get("admin_key", "").strip()
    new_password = data.get("password", "").strip()
    
    if not new_email or not new_key or not new_password:
        return jsonify({"success": False, "message": "Email, Admin Key, and Password are all required."}), 400
        
    db = load_db()
    for adm in db.get("admins", []):
        if adm.get("email") == new_email:
            return jsonify({"success": False, "message": "An Admin account with this email already exists."}), 409
        if adm.get("admin_key") == new_key:
            return jsonify({"success": False, "message": "An Admin account with this Admin Key already exists."}), 409
            
    new_adm = {
        "email": new_email,
        "admin_key": new_key,
        "password_hash": generate_password_hash(new_password),
        "role": "ADMIN",
        "is_active": True,
        "created_at": get_now_ist().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    db["admins"].append(new_adm)
    save_db(db)
    
    return jsonify({
        "success": True,
        "message": f"Successfully created new Admin account for {new_email}."
    })

@app.route("/api/cloud/admin/deactivate_admin", methods=["POST"])
def deactivate_admin():
    role, identifier = authenticate_request(request)
    if role != "ADMIN":
        return jsonify({"success": False, "message": "Unauthorized. Requires Administrator status."}), 403
        
    data = request.get_json() or {}
    target_email = data.get("email", "").strip()
    
    if not target_email:
        return jsonify({"success": False, "message": "Email is required."}), 400
        
    # Prevent self-deactivation if only one admin is active
    db = load_db()
    active_admins = [adm for adm in db.get("admins", []) if adm.get("is_active")]
    
    if len(active_admins) <= 1 and target_email == identifier:
        return jsonify({"success": False, "message": "Cannot deactivate the last active Admin account."}), 400
        
    target_record = None
    for adm in db.get("admins", []):
        if adm.get("email") == target_email:
            target_record = adm
            break
            
    if not target_record:
        return jsonify({"success": False, "message": "Admin account not found."}), 404
        
    target_record["is_active"] = False
    save_db(db)
    
    return jsonify({
        "success": True,
        "message": f"Successfully deactivated Admin account {target_email}."
    })

@app.route("/api/cloud/admin/list_admins", methods=["GET"])
def list_admins():
    role, identifier = authenticate_request(request)
    if role != "ADMIN":
        return jsonify({"success": False, "message": "Unauthorized. Requires Administrator status."}), 403
        
    db = load_db()
    admin_list = []
    for adm in db.get("admins", []):
        admin_list.append({
            "email": adm.get("email"),
            "admin_key": adm.get("admin_key"),
            "is_active": adm.get("is_active"),
            "created_at": adm.get("created_at")
        })
        
    return jsonify({
        "success": True,
        "admins": admin_list
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
