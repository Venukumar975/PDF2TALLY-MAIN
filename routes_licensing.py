# routes_licensing.py
import time
import requests
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import request, jsonify, render_template, redirect, url_for, session
from routes_base import routes_bp
import licensing
from services.logger import logger

@routes_bp.route("/")
def index():
    return render_template("index.html")

@routes_bp.route("/activate")
def activate_page():
    status = licensing.check_activation()
    if status["activated"]:
        return redirect("/")
    return render_template("index.html")  # SPA handles rendering based on license status

@routes_bp.route("/review")
def review_desk():
    return render_template("review.html")

# -------------------------------------------------------------
# LICENSE API
# -------------------------------------------------------------
# -------------------------------------------------------------
# LICENSE API (PROXIES TO CLOUD BACKEND)
# -------------------------------------------------------------
import os
import requests
import time

@routes_bp.route("/api/status", methods=["GET"])
def api_status():
    force = request.args.get("refresh", "false").lower() == "true"
    if force:
        session.pop("logged_out", None)
    elif session.get("logged_out"):
        return jsonify({
            "activated": False,
            "role": "USER",
            "message": "Logged out",
            "signature": licensing.get_machine_signature()
        })
    return jsonify(licensing.check_activation(force_refresh=force))

@routes_bp.route("/api/activate", methods=["POST"])
def api_activate():
    session.pop("logged_out", None)
    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key", "").strip()
    machine_hash = licensing.get_machine_signature()

    if not license_key:
        return jsonify({"success": False, "message": "License Key is required."}), 400

    try:
        url = f"{licensing.get_cloud_backend_url()}/login"
        resp = requests.post(url, json={
            "license_id": license_key,
            "machine_hash": machine_hash
        }, timeout=120)

        if resp.status_code == 200:
            res_data = resp.json()
            if res_data.get("success"):
                # Save locally
                licensing.save_local_license({
                    "signature": machine_hash,
                    "activated": True,
                    "role": "USER",
                    "expiry_date": res_data.get("expires_at"),
                    "seconds_remaining": res_data.get("seconds_remaining"),
                    "last_sync_real": time.time(),
                    "last_seen_time": time.time(),
                    "license_id": res_data.get("license_id"),
                    "license_key": license_key
                })
                # Sync cache in memory
                licensing.check_activation(force_refresh=True)
                return jsonify({
                    "success": True,
                    "activated": True,
                    "message": res_data.get("message", "License activated successfully!")
                })
            return jsonify({"success": False, "message": res_data.get("message", "Activation failed.")}), 400
        else:
            try:
                msg = resp.json().get("message", "Activation request failed.")
                if msg == "Invalid License Reference.":
                    msg = "License not found"
            except Exception:
                msg = "Activation request failed."
            return jsonify({"success": False, "message": msg}), resp.status_code

    except Exception as e:
        return jsonify({"success": False, "message": "Could not connect to licensing server."}), 500


@routes_bp.route("/api/restore-device", methods=["POST"])
def api_restore_device():
    import time
    import requests
    machine_hash = licensing.get_machine_signature()
    try:
        url = f"{licensing.get_cloud_backend_url()}/restore-license-by-machine"
        resp = requests.post(url, json={
            "machine_hash": machine_hash
        }, timeout=120)

        if resp.status_code == 200:
            res_data = resp.json()
            if res_data.get("success"):
                # Save locally to .lic file
                licensing.save_local_license({
                    "signature": machine_hash,
                    "activated": True,
                    "role": "USER",
                    "expiry_date": res_data.get("expires_at"),
                    "seconds_remaining": res_data.get("seconds_remaining"),
                    "last_sync_real": time.time(),
                    "last_seen_time": time.time(),
                    "license_id": res_data.get("license_id"),
                    "license_key": res_data.get("license_key")
                })
                # Sync cache in memory
                licensing.check_activation(force_refresh=True)
                return jsonify({
                    "success": True,
                    "activated": True,
                    "license_key": res_data.get("license_key"),
                    "message": "License successfully restored from cloud registry!"
                })
            return jsonify({"success": False, "message": "Failed to restore license."}), 400
        else:
            try:
                msg = resp.json().get("message", "Device has no active registered license.")
            except Exception:
                msg = "Device has no active registered license."
            return jsonify({"success": False, "message": msg}), resp.status_code
    except Exception as e:
        return jsonify({"success": False, "message": "Could not connect to licensing server."}), 500


@routes_bp.route("/api/register_request", methods=["POST"])
def api_register_request():
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone_number = data.get("phone_number", "").strip()
    machine_hash = licensing.get_machine_signature()

    if not full_name or not email or not phone_number:
        return jsonify({"success": False, "message": "Name, Email, and Phone Number are required."}), 400

    try:
        url = f"{licensing.get_cloud_backend_url()}/register-request"
        resp = requests.post(url, json={
            "full_name": full_name,
            "email": email,
            "phone_number": phone_number,
            "machine_hash": machine_hash
        }, timeout=120)
        
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            try:
                msg = resp.json().get("message", "Registration request failed.")
            except Exception:
                msg = "Registration request failed."
            return jsonify({"success": False, "message": msg}), resp.status_code

    except Exception as e:
        return jsonify({"success": False, "message": "Could not connect to licensing server."}), 500

@routes_bp.route("/api/deactivate", methods=["POST"])
def api_deactivate():
    session["logged_out"] = True
    licensing.deactivate()
    return jsonify({"success": True, "message": "Logged out successfully."})


# -------------------------------------------------------------
# CONVERSION API: BANK STATEMENT PDF
# -------------------------------------------------------------
@routes_bp.route("/api/request-renewal", methods=["POST"])
def api_request_renewal():
    data = request.get_json(silent=True) or {}
    license_key = data.get("license_key", "").strip()
    if not license_key:
        lic_cache = licensing.load_local_license()
        if lic_cache:
            license_key = lic_cache.get("license_key", "")
            
    machine_hash = licensing.get_machine_signature()

    if not license_key:
        return jsonify({"success": False, "message": "License Key could not be determined."}), 400

    try:
        url = f"{licensing.get_cloud_backend_url()}/request-renewal"
        resp = requests.post(url, json={
            "license_key": license_key,
            "machine_hash": machine_hash
        }, timeout=10)
        
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            try:
                msg = resp.json().get("message", "Failed to submit renewal request.")
            except Exception:
                msg = "Failed to submit renewal request."
            return jsonify({"success": False, "message": msg}), resp.status_code
    except Exception as e:
        logger.error(f"Renewal request failed: {e}")
        return jsonify({"success": False, "message": "Could not connect to licensing server."}), 500


# -------------------------------------------------------------
# HYBRID GENERIC PARSER ENDPOINTS
# -------------------------------------------------------------


@routes_bp.route("/api/check-version", methods=["GET"])
def api_check_version():
    try:
        render_url = "https://pdf2tally-backend.onrender.com"
        url = f"{render_url}/version?app_type=trial"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # If download_url is relative, make it absolute using the main server domain
            dl_url = data.get("download_url", "")
            if dl_url.startswith("/"):
                data["download_url"] = f"{render_url.strip().rstrip('/')}{dl_url}"
            return jsonify(data)
        return jsonify({"success": False, "message": "Failed to contact version server."}), resp.status_code
    except Exception as e:
        logger.error(f"Version check failed: {e}")
        return jsonify({"success": False, "message": "Could not connect to version server."}), 500


@routes_bp.route("/api/submit-support", methods=["POST"])
def api_submit_support():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        subject_type = data.get("subject_type", "").strip()
        message = data.get("message", "").strip()
        signature = data.get("signature", "").strip()
        attachments = data.get("attachments", [])
        
        if not email or not phone or not subject_type or not message:
            return jsonify({"success": False, "message": "All fields are required."}), 400
            
        # 1. Fetch SMTP credentials dynamically from Render over secure HTTPS
        render_url = "https://pdf2tally-backend.onrender.com"
        creds_resp = requests.get(f"{render_url}/get-support-creds", timeout=15)
        
        if creds_resp.status_code != 200:
            return jsonify({"success": False, "message": "Failed to retrieve support credentials from cloud server."}), 500
            
        creds_data = creds_resp.json()
        smtp_user = creds_data.get("smtp_user", "support.pdf2tally@gmail.com")
        smtp_pass = creds_data.get("smtp_pass", "").strip()
        
        if not smtp_pass:
            return jsonify({"success": False, "message": "Support email credentials are not configured on the Render server."}), 500
            
        # 2. Construct the email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = smtp_user  # Send to the support email itself
        msg['Subject'] = f"[PDF2Tally Support] {subject_type} - {email}"
        
        # HTML body
        body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f7fafc;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="background: #8b5cf6; padding: 20px; color: #ffffff; text-align: center;">
                    <h2 style="margin: 0; font-size: 1.5rem;">New Support Ticket</h2>
                </div>
                <div style="padding: 25px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; border-bottom: 1px solid #edf2f7; width: 35%; color: #4a5568;">Name</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #edf2f7; color: #2d3748;">{name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; border-bottom: 1px solid #edf2f7; color: #4a5568;">Email</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #edf2f7;"><a href="mailto:{email}" style="color: #8b5cf6; text-decoration: none;">{email}</a></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; border-bottom: 1px solid #edf2f7; color: #4a5568;">Phone Number</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #edf2f7; color: #2d3748;">{phone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; border-bottom: 1px solid #edf2f7; color: #4a5568;">Category</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #edf2f7; font-weight: bold; color: #7c3aed;">{subject_type}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; border-bottom: 1px solid #edf2f7; color: #4a5568;">Machine Signature</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #edf2f7; font-family: monospace; color: #ef4444; font-weight: bold;">{signature}</td>
                        </tr>
                    </table>
                    
                    <h3 style="color: #4a5568; margin-top: 25px; margin-bottom: 10px; border-bottom: 2px solid #8b5cf6; padding-bottom: 5px;">Message Details</h3>
                    <div style="background: #f7fafc; padding: 15px; border-radius: 6px; border-left: 4px solid #8b5cf6; white-space: pre-wrap; color: #2d3748; font-size: 0.95rem; font-family: inherit;">
{message}
                    </div>
                </div>
                <div style="background: #edf2f7; padding: 15px; text-align: center; font-size: 0.8rem; color: #718096;">
                    Submitted via PDF2Tally Help Desk.
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        # Attach files
        for attachment in attachments:
            filename = attachment.get("filename", "attachment")
            content_b64 = attachment.get("content", "")
            if not content_b64:
                continue
                
            try:
                file_data = base64.b64decode(content_b64)
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)
            except Exception as e:
                logger.error(f"Error attaching file {filename} locally: {e}")
                
        # 3. Connect to Gmail SMTP directly from the local device client
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        return jsonify({"success": True, "message": "Support request sent successfully!"})
        
    except requests.RequestException as e:
        logger.error(f"Local support network connection error: {e}")
        return jsonify({"success": False, "message": "Network connection failed. Please check your internet connection and try again."}), 503
    except smtplib.SMTPException as e:
        logger.error(f"Local support SMTP sending failed: {e}")
        return jsonify({"success": False, "message": "Failed to connect to the mail server. Please check your internet connection."}), 503
    except Exception as e:
        logger.error(f"Local support unexpected error: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred while sending your request. Please try again later."}), 500
