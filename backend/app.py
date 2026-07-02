import os
from datetime import datetime, timedelta
import uuid
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, License, Admin, RenewalRequest

app = Flask(__name__)
CORS(app)

# Database Configuration
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf2tally.db")
db_url = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Helper to calculate expires_at
def calculate_expiry(plan_name, duration_days, activated_at):
    plan = plan_name.lower().strip()
    if plan == 'lifetime':
        return None
    
    # Check for minutes in plan name or duration
    if 'min' in plan:
        try:
            # Extract number of minutes, e.g. "1min" -> 1
            minutes = int(''.join(filter(str.isdigit, plan)))
        except ValueError:
            minutes = 5
        return activated_at + timedelta(minutes=minutes)
    
    # Fallback to duration_days
    return activated_at + timedelta(days=duration_days)

# Seed default database values
def seed_database():
    with app.app_context():
        db.create_all()
        # Seed master admin if not exists
        master_email = os.environ.get("ADMIN_EMAIL", "pichikavenui5@gmail.com")
        master_username = master_email.split('@')[0]
        admin_exists = Admin.query.filter_by(username=master_username).first()
        if not admin_exists:
            hashed_pw = generate_password_hash("AdminPassword2026!")
            master_admin = Admin(
                admin_id=str(uuid.uuid4()),
                username=master_username,
                password_hash=hashed_pw,
                role="ADMIN",
                is_active=True
            )
            db.session.add(master_admin)
            db.session.commit()
            print(f"Master admin '{master_username}' seeded successfully.")

# Initialize and Seed
seed_database()

# -------------------------------------------------------------
# CLIENT API ENDPOINTS
# -------------------------------------------------------------

@app.route("/register-request", methods=["POST"])
def register_request():
    """
    Receives customer registration information and stores a pending request.
    """
    data = request.get_json() or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone_number = data.get("phone_number", "").strip()
    machine_hash = data.get("machine_hash", "").strip().upper()

    if not full_name or not email or not phone_number or not machine_hash:
        return jsonify({"success": False, "message": "All registration fields are required."}), 400

    try:
        # Check if this machine is already bound to any license in the database (Active, Expired, Revoked, etc.)
        existing_lic = License.query.filter_by(machine_hash=machine_hash).first()
        if existing_lic:
            return jsonify({"success": False, "message": f"This machine signature is already associated with a license key (Status: {existing_lic.status})."}), 400

        # Check if a registration request is already pending for this machine signature
        existing_pending = User.query.filter_by(machine_hash=machine_hash, license_id=None).first()
        if existing_pending:
            return jsonify({"success": False, "message": "A registration request is already pending for this machine signature."}), 400

        # Check if user already exists by email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # If the user has a license already, return details
            if existing_user.license_id:
                lic = License.query.get(existing_user.license_id)
                if lic and lic.status == 'Active':
                    return jsonify({
                        "success": True, 
                        "message": "User is already registered and activated.",
                        "status": "Active"
                    })
            return jsonify({
                "success": True, 
                "message": "Registration request is already pending approval.",
                "status": "Pending"
            })

        # Create new user record
        new_user = User(
            user_id=str(uuid.uuid4()),
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            machine_hash=machine_hash,
            license_id=None, # Pending approval
            registered_at=datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({
            "success": True, 
            "message": "Registration request successfully submitted. Waiting for Administrator Approval."
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server database error: {str(e)}"}), 500


@app.route("/activate-license", methods=["POST"])
def activate_license():
    """
    Binds and activates a license on the customer's machine signature.
    """
    data = request.get_json() or {}
    license_key = data.get("license_key", "").strip()
    machine_hash = data.get("machine_hash", "").strip().upper()

    if not license_key or not machine_hash:
        return jsonify({"success": False, "message": "License Key and Machine Hash are required."}), 400

    try:
        # Find license
        lic = License.query.filter_by(license_key=license_key).first()
        if not lic:
            return jsonify({"success": False, "message": "Invalid License Key."}), 404

        if lic.status == 'Revoked':
            return jsonify({"success": False, "message": "License deactivated. Please contact administrator."}), 403

        now = datetime.utcnow()
        if lic.status == 'Expired' or (lic.expires_at and now > lic.expires_at):
            lic.status = 'Expired'
            db.session.commit()
            return jsonify({"success": False, "message": "License expired. Please renew."}), 403

        # Bind machine fingerprint
        if lic.machine_hash and lic.machine_hash != machine_hash:
            return jsonify({"success": False, "message": "License is already in use by another device."}), 403

        # Prevent duplicate bindings of this machine signature to other active licenses
        if not lic.machine_hash:
            existing_binding = License.query.filter(
                License.machine_hash == machine_hash, 
                License.status.in_(['Active', 'Pending']),
                License.license_key != license_key
            ).first()
            if existing_binding:
                return jsonify({"success": False, "message": "This machine signature is already bound to an active license."}), 400

            lic.machine_hash = machine_hash
            lic.status = 'Active'
            lic.activated_at = now
            lic.expires_at = calculate_expiry(lic.plan_name, lic.duration_days, lic.activated_at)
        else:
            # Already activated on this machine - verify active state
            lic.status = 'Active'
            
        # Link to User
        matching_user = User.query.filter(db.or_(User.license_id == None, User.license_id == lic.license_id)).order_by(User.registered_at.desc()).first()
        if matching_user and not matching_user.license_id:
            matching_user.license_id = lic.license_id

        db.session.commit()

        # Calculate remaining duration
        remaining_seconds = -1
        if lic.expires_at:
            remaining_seconds = max(0, int((lic.expires_at - now).total_seconds()))

        return jsonify({
            "success": True,
            "activated": True,
            "license_id": lic.license_id,
            "plan_name": lic.plan_name,
            "expires_at": lic.expires_at.strftime("%Y-%m-%d %H:%M:%S") if lic.expires_at else "Lifetime",
            "seconds_remaining": remaining_seconds if lic.expires_at else -1,
            "message": "License activated successfully!"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server database error: {str(e)}"}), 500


@app.route("/login", methods=["POST"])
def login():
    """
    Verifies license status, plan validity, and machine hash match.
    """
    data = request.get_json() or {}
    license_id = data.get("license_id", "").strip()
    machine_hash = data.get("machine_hash", "").strip().upper()

    if not license_id or not machine_hash:
        return jsonify({"success": False, "message": "License ID and Machine Hash are required."}), 400

    try:
        # Find license (supports search by UUID license_id or license_key text)
        lic = License.query.filter(db.or_(License.license_id == license_id, License.license_key == license_id)).first()
        if not lic:
            return jsonify({"success": False, "message": "Invalid License Reference."}), 404

        now = datetime.utcnow()

        # Check Expiry
        if lic.expires_at and now > lic.expires_at:
            lic.status = 'Expired'
            db.session.commit()
            return jsonify({"success": False, "message": "Your subscription has expired."}), 403

        if lic.status != 'Active':
            return jsonify({"success": False, "message": f"License status is {lic.status}."}), 403

        if lic.machine_hash != machine_hash:
            return jsonify({"success": False, "message": "Unauthorized machine fingerprint."}), 403

        # Update last login time
        user = User.query.filter_by(license_id=lic.license_id).first()
        if user:
            user.last_login = now

        db.session.commit()

        # Calculate time remaining
        remaining_seconds = -1
        if lic.expires_at:
            remaining_seconds = max(0, int((lic.expires_at - now).total_seconds()))

        return jsonify({
            "success": True,
            "authorized": True,
            "plan_name": lic.plan_name,
            "expires_at": lic.expires_at.strftime("%Y-%m-%d %H:%M:%S") if lic.expires_at else "Lifetime",
            "seconds_remaining": remaining_seconds,
            "message": "Authentication successful."
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server database error: {str(e)}"}), 500


@app.route("/restore-license", methods=["POST"])
def restore_license():
    """
    Recovers license ID and details using customer's email and machine hash.
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    machine_hash = data.get("machine_hash", "").strip().upper()

    if not email or not machine_hash:
        return jsonify({"success": False, "message": "Email and Machine Hash are required."}), 400

    try:
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user or not user.license_id:
            return jsonify({"success": False, "message": "No active license associated with this email address."}), 404

        lic = License.query.get(user.license_id)
        if not lic:
            return jsonify({"success": False, "message": "Associated license record not found."}), 404

        if lic.machine_hash != machine_hash:
            return jsonify({"success": False, "message": "This email's license is bound to a different device signature."}), 403

        now = datetime.utcnow()
        if lic.expires_at and now > lic.expires_at:
            lic.status = 'Expired'
            db.session.commit()
            return jsonify({"success": False, "message": "The associated license has expired."}), 403

        if lic.status != 'Active':
            return jsonify({"success": False, "message": f"Associated license is currently {lic.status}."}), 403

        remaining_seconds = -1
        if lic.expires_at:
            remaining_seconds = max(0, int((lic.expires_at - now).total_seconds()))

        return jsonify({
            "success": True,
            "license_id": lic.license_id,
            "license_key": lic.license_key,
            "plan_name": lic.plan_name,
            "expires_at": lic.expires_at.strftime("%Y-%m-%d %H:%M:%S") if lic.expires_at else "Lifetime",
            "seconds_remaining": remaining_seconds,
            "message": "License successfully recovered!"
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Server database error: {str(e)}"}), 500


@app.route("/api/cloud/version", methods=["GET"])
def cloud_version():
    return jsonify({
        "version": "1.0.0-MVP",
        "status": "ready",
        "database": app.config['SQLALCHEMY_DATABASE_URI'].split(':')[0]
    })


@app.route("/request-renewal", methods=["POST"])
def request_renewal():
    """
    Creates a pending renewal request for an expired or active license.
    """
    data = request.get_json() or {}
    license_key = data.get("license_key", "").strip()
    machine_hash = data.get("machine_hash", "").strip().upper()

    if not license_key or not machine_hash:
        return jsonify({"success": False, "message": "License Key and Machine Hash are required."}), 400

    try:
        # Find license
        lic = License.query.filter_by(license_key=license_key).first()
        if not lic:
            return jsonify({"success": False, "message": "Invalid License Key."}), 404

        if lic.machine_hash and lic.machine_hash != machine_hash:
            return jsonify({"success": False, "message": "Device fingerprint mismatch."}), 403

        # Check if already pending
        existing = RenewalRequest.query.filter_by(license_id=lic.license_id, status='Pending').first()
        if existing:
            return jsonify({"success": True, "message": "Renewal request is already pending approval."})

        # Create new renewal request
        req = RenewalRequest(
            id=str(uuid.uuid4()),
            license_id=lic.license_id,
            status='Pending',
            requested_at=datetime.utcnow()
        )
        db.session.add(req)
        db.session.commit()
        return jsonify({"success": True, "message": "Renewal request submitted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Server database error: {str(e)}"}), 500




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
