import os
import io
import re
import tempfile
from flask import Blueprint, request, jsonify, render_template, send_file, redirect, url_for
from datetime import datetime, date, timedelta

# Import core licensing modules
import licensing

# Import banking core modules
from services.pdf_reader import extract_text
from services.statement_validator import build_validation_report
from services.xml_generator import generate_tally_xml
from services.xlsx_viewer import export_xml_audit_workbook

# Import Ashramam Custom Modules
from parsers.cash_parser import parse_cash_workbook, load_lexicon, save_lexicon
from services.cash_validator import run_cash_audit
from services.cash_xlsx_writer import build_nested_tally_sheets
from services.cash_xml_generator import generate_ashramam_tally_xml

# Import custom logger
from services.logger import logger

routes_bp = Blueprint("routes", __name__)

# Global in-memory cache to hold generated file data for download
# Keys: "xml_bank", "xlsx_bank", "xml_cash", "xlsx_cash"
FILE_CACHE = {
    "xml_bank": None,
    "xlsx_bank": None,
    "xml_cash": None,
    "xlsx_cash": None,
    # Download file names
    "xml_bank_filename": "tally_import.xml",
    "xlsx_bank_filename": "statement_audit_viewer.xlsx",
    "xml_cash_filename": "Ashramam_Cash_Receipts.xml",
    "xlsx_cash_filename": "Tally_Nested_Sheets_Preview.xlsx"
}

# In-memory transaction storage for reprocessing
LAST_CONVERSION = {
    "bank_txns": None,
    "bank_type": None,
    "bank_opening_bal": 0.0,
    "bank_sanitized_text": "",
    "cash_file_bytes": None,
    "cash_cutoff_date": None
}

# -------------------------------------------------------------
# PAGE ROUTERS
# -------------------------------------------------------------
@routes_bp.route("/")
def index():
    return render_template("index.html")

@routes_bp.route("/activate")
def activate_page():
    status = licensing.check_activation()
    if status["activated"]:
        return redirect("/")
    return render_template("index.html")  # SPA handles rendering based on license status

# -------------------------------------------------------------
# LICENSE API
# -------------------------------------------------------------
# -------------------------------------------------------------
# LICENSE API (PROXIES TO CLOUD BACKEND)
# -------------------------------------------------------------
import requests

@routes_bp.route("/api/status", methods=["GET"])
def api_status():
    force = request.args.get("refresh", "false").lower() == "true"
    return jsonify(licensing.check_activation(force_refresh=force))

@routes_bp.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    admin_key = data.get("admin_key", "").strip()
    password = data.get("password", "").strip()
    
    if not email or not admin_key or not password:
        return jsonify({"success": False, "message": "Email, Admin Key, and Password are required."}), 400
        
    try:
        url = f"{licensing.get_cloud_backend_url()}/api/cloud/admin/login"
        resp = requests.post(url, json={
            "email": email,
            "admin_key": admin_key,
            "password": password
        }, timeout=10)
        
        if resp.status_code == 200:
            res_data = resp.json()
            # Cache admin credentials locally
            with licensing._cache_lock:
                licensing._license_cache["admin_token"] = res_data.get("token")
                licensing._license_cache["admin_email"] = email
                licensing._license_cache["role"] = "ADMIN"
                licensing._license_cache["activated"] = True
                licensing._license_cache["error_type"] = None
            return jsonify({"success": True, "role": "ADMIN"})
        else:
            try:
                msg = resp.json().get("message", "Authentication failed.")
            except Exception:
                msg = "Authentication failed."
            return jsonify({"success": False, "message": msg}), resp.status_code
    except Exception as e:
        return jsonify({"success": False, "message": f"Could not connect to licensing server: {str(e)}"}), 500

@routes_bp.route("/api/admin/generate_key", methods=["POST"])
def api_admin_generate_key():
    # 1. Authorize: Check if local client session is Admin or Co-Admin
    status = licensing.check_activation()
    local_role = status.get("role")
    is_admin_logged_in = (licensing._license_cache.get("admin_token") is not None)
    is_coadmin = (local_role == "CO-ADMIN")
    
    if not is_admin_logged_in and not is_coadmin:
        return jsonify({"success": False, "message": "Unauthorized. Requires Admin or Co-Admin privileges."}), 403
        
    data = request.get_json() or {}
    target_sig = data.get("signature", "").strip().upper()
    role = data.get("role", "USER").strip().upper()
    duration = data.get("duration", "").strip().lower()
    
    if not target_sig:
        return jsonify({"success": False, "message": "Target machine signature is required."}), 400
        
    headers = {}
    if is_admin_logged_in:
        headers["Authorization"] = f"Bearer {licensing._license_cache.get('admin_token')}"
    elif is_coadmin:
        headers["X-Machine-Signature"] = status.get("signature")
        
    try:
        url = f"{licensing.get_cloud_backend_url()}/api/cloud/admin/licenses"
        resp = requests.post(url, json={
            "machine_signature": target_sig,
            "role": role,
            "duration": duration
        }, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            try:
                msg = resp.json().get("message", "Failed to register signature.")
            except Exception:
                msg = "Failed to register signature."
            return jsonify({"success": False, "message": msg}), resp.status_code
    except Exception as e:
        return jsonify({"success": False, "message": f"Connection error: {str(e)}"}), 500

@routes_bp.route("/api/admin/list_licenses", methods=["GET"])
def api_admin_list_licenses():
    status = licensing.check_activation()
    local_role = status.get("role")
    is_admin_logged_in = (licensing._license_cache.get("admin_token") is not None)
    is_coadmin = (local_role == "CO-ADMIN")
    
    if not is_admin_logged_in and not is_coadmin:
        return jsonify({"success": False, "message": "Unauthorized. Requires Admin or Co-Admin privileges."}), 403
        
    headers = {}
    if is_admin_logged_in:
        headers["Authorization"] = f"Bearer {licensing._license_cache.get('admin_token')}"
    elif is_coadmin:
        headers["X-Machine-Signature"] = status.get("signature")
        
    try:
        url = f"{licensing.get_cloud_backend_url()}/api/cloud/admin/licenses"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            return jsonify({"success": False, "message": "Failed to fetch registrations."}), resp.status_code
    except Exception as e:
        return jsonify({"success": False, "message": f"Connection error: {str(e)}"}), 500

@routes_bp.route("/api/admin/deactivate", methods=["POST"])
def api_admin_deactivate():
    status = licensing.check_activation()
    local_role = status.get("role")
    is_admin_logged_in = (licensing._license_cache.get("admin_token") is not None)
    is_coadmin = (local_role == "CO-ADMIN")
    
    if not is_admin_logged_in and not is_coadmin:
        return jsonify({"success": False, "message": "Unauthorized. Requires Admin or Co-Admin privileges."}), 403
        
    data = request.get_json() or {}
    target_sig = data.get("signature", "").strip().upper()
    
    if not target_sig:
        return jsonify({"success": False, "message": "Target machine signature is required."}), 400
        
    headers = {}
    if is_admin_logged_in:
        headers["Authorization"] = f"Bearer {licensing._license_cache.get('admin_token')}"
    elif is_coadmin:
        headers["X-Machine-Signature"] = status.get("signature")
        
    try:
        url = f"{licensing.get_cloud_backend_url()}/api/cloud/admin/deactivate"
        resp = requests.post(url, json={"machine_signature": target_sig}, headers=headers, timeout=10)
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            try:
                msg = resp.json().get("message", "Deactivation failed.")
            except Exception:
                msg = "Deactivation failed."
            return jsonify({"success": False, "message": msg}), resp.status_code
    except Exception as e:
        return jsonify({"success": False, "message": f"Connection error: {str(e)}"}), 500

@routes_bp.route("/api/activate", methods=["POST"])
def api_activate():
    # Force check license status from the cloud backend
    status = licensing.check_activation(force_refresh=True)
    return jsonify(status)

@routes_bp.route("/api/deactivate", methods=["POST"])
def api_deactivate():
    licensing.deactivate()
    return jsonify({"success": True, "message": "Logged out and deactivated successfully."})


# -------------------------------------------------------------
# CONVERSION API: BANK STATEMENT PDF
# -------------------------------------------------------------
@routes_bp.route("/api/convert_bank", methods=["POST"])
def api_convert_bank():
    try:
        # Clear previous bank cache instantly on new file upload attempt
        FILE_CACHE["xml_bank"] = None
        FILE_CACHE["xlsx_bank"] = None
        LAST_CONVERSION["bank_txns"] = None
        LAST_CONVERSION["bank_opening_bal"] = 0.0
        LAST_CONVERSION["bank_sanitized_text"] = ""

        # Check files
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file uploaded."}), 400
            
        uploaded_file = request.files["file"]
        bank_type = request.form.get("bank_type", "").strip()
        strategy_type = request.form.get("strategy_type", "Full bank statement").strip()
        cutoff_date_str = request.form.get("cutoff_date", "").strip()
        prev_balance_str = request.form.get("prev_balance", "").strip()
        
        debit_ledger = request.form.get("debit_ledger", "").strip()
        credit_ledger = request.form.get("credit_ledger", "").strip()
        
        prev_balance = None
        if prev_balance_str:
            try:
                prev_balance = float(prev_balance_str.replace(",", ""))
            except ValueError:
                pass
                
        if not bank_type:
            return jsonify({"success": False, "message": "Bank type is required."}), 400
            
        # Parse boundary date
        boundary_date = None
        if cutoff_date_str:
            try:
                boundary_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
                
        # Save temp file
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        uploaded_file.save(temp_path)
        
        try:
            # Extract PDF text matrix
            text = extract_text(temp_path)
            
            # Verify bank profile using dynamic configs
            from parsers.router import verify_bank_profile, route_to_parser, get_opening_balance_parser
            if not verify_bank_profile(bank_type, text):
                return jsonify({
                    "success": False, 
                    "message": f"Bank Profile Mismatch! The PDF content does not match the selected bank profile ({bank_type})."
                }), 400
                
            # Process strategies (Full bank statement, Incomplete statement (Continuation))
            from strategies import WholeChunk, ContinuationChunk
            
            # Resolve parser for opening balance dynamically!
            try:
                parse_opening_func = get_opening_balance_parser(bank_type)
            except Exception as parser_err:
                logger.error(f"Failed to resolve opening balance parser: {str(parser_err)}")
                return jsonify({"success": False, "message": str(parser_err)}), 400
            
            if strategy_type == "Full bank statement":
                sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
                transactions = route_to_parser(bank_type, sanitized_text, opening_balance=opening_bal)
                if opening_bal is None:
                    opening_bal = 0.00
            elif strategy_type == "Incomplete statement (Continuation)":
                if not boundary_date:
                    boundary_date = date(2025, 4, 1)
                sanitized_text, _ = ContinuationChunk.process_strategy(text, parse_opening_func, bank_type, boundary_date)
                
                # In incomplete mode, we parse all transactions and pass prev_balance
                transactions = route_to_parser(bank_type, text, opening_balance=prev_balance)
                # Filter parsed transactions by boundary date
                filtered_txns = []
                for txn in transactions:
                    try:
                        txn_date = datetime.strptime(txn["gl_date"], "%d-%m-%Y").date()
                        if txn_date >= boundary_date:
                            filtered_txns.append(txn)
                    except Exception:
                        pass
                transactions = filtered_txns
                opening_bal = prev_balance if prev_balance is not None else 0.00
            else:
                sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
                transactions = route_to_parser(bank_type, sanitized_text, opening_balance=opening_bal)
                if opening_bal is None:
                    opening_bal = 0.00
            
            if not transactions:
                return jsonify({"success": False, "message": "No valid transaction rows found in PDF statement."}), 400
                
            # Cache inputs for reprocessing ledger names
            LAST_CONVERSION["bank_txns"] = transactions
            LAST_CONVERSION["bank_type"] = bank_type
            LAST_CONVERSION["bank_opening_bal"] = opening_bal
            LAST_CONVERSION["bank_sanitized_text"] = sanitized_text
            
            # Build initial preview with ledger names
            if not debit_ledger:
                debit_ledger = "BANK OF BARODA" if "BOB" in bank_type else "STATE BANK OF INDIA"
            if not credit_ledger:
                credit_ledger = "Suspense"
                
            # Generate XML & Excel
            xml_text = generate_tally_xml(
                transactions, 
                output_path=None, 
                bank_ledger=debit_ledger, 
                suspense_ledger=credit_ledger, 
                opening_balance=opening_bal
            )
            
            validation_report = build_validation_report(
                sanitized_text, 
                transactions, 
                xml_text, 
                debit_ledger, 
                credit_ledger
            )
            
            # Create Excel audit workbook
            fd_xlsx, temp_xlsx = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd_xlsx)
            export_xml_audit_workbook(xml_text, temp_xlsx, bank_ledger=debit_ledger, suspense_ledger=credit_ledger)
            with open(temp_xlsx, "rb") as f:
                xlsx_data = f.read()
            try:
                os.remove(temp_xlsx)
            except Exception:
                pass
                
            # Update cache
            FILE_CACHE["xml_bank"] = xml_text.encode("utf-8")
            FILE_CACHE["xlsx_bank"] = xlsx_data
            
            # Setup file names
            prefix = "BOB" if "BOB" in bank_type else "SBI"
            FILE_CACHE["xml_bank_filename"] = f"{prefix}_tally_import.xml"
            FILE_CACHE["xlsx_bank_filename"] = f"{prefix}_statement_audit_viewer.xlsx"
            
            # Formulate response
            return jsonify({
                "success": True,
                "report": validation_report,
                "debit_ledger": debit_ledger,
                "credit_ledger": credit_ledger
            })
            
        finally:
            # Cleanup PDF
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Bank statement conversion failed: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Conversion error: {str(e)}"}), 500

@routes_bp.route("/api/reprocess_bank", methods=["POST"])
def api_reprocess_bank():
    try:
        data = request.get_json() or {}
        debit_ledger = data.get("debit_ledger", "").strip()
        credit_ledger = data.get("credit_ledger", "").strip()
        
        transactions = LAST_CONVERSION.get("bank_txns")
        bank_type = LAST_CONVERSION.get("bank_type")
        opening_bal = LAST_CONVERSION.get("bank_opening_bal")
        sanitized_text = LAST_CONVERSION.get("bank_sanitized_text")
        
        if not transactions or not bank_type:
            return jsonify({"success": False, "message": "No active bank session found. Please upload file first."}), 400
            
        if not debit_ledger:
            debit_ledger = "BANK OF BARODA" if "BOB" in bank_type else "STATE BANK OF INDIA"
        if not credit_ledger:
            credit_ledger = "Suspense"
            
        # Re-generate files
        xml_text = generate_tally_xml(
            transactions, 
            output_path=None, 
            bank_ledger=debit_ledger, 
            suspense_ledger=credit_ledger, 
            opening_balance=opening_bal
        )
        
        validation_report = build_validation_report(
            sanitized_text, 
            transactions, 
            xml_text, 
            debit_ledger, 
            credit_ledger
        )
        
        # Create Excel audit workbook
        fd_xlsx, temp_xlsx = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd_xlsx)
        export_xml_audit_workbook(xml_text, temp_xlsx, bank_ledger=debit_ledger, suspense_ledger=credit_ledger)
        with open(temp_xlsx, "rb") as f:
            xlsx_data = f.read()
        try:
            os.remove(temp_xlsx)
        except Exception:
            pass
            
        # Update cache
        FILE_CACHE["xml_bank"] = xml_text.encode("utf-8")
        FILE_CACHE["xlsx_bank"] = xlsx_data
        
        return jsonify({
            "success": True,
            "report": validation_report,
            "debit_ledger": debit_ledger,
            "credit_ledger": credit_ledger
        })
        
    except Exception as e:
        logger.error(f"Reprocessing bank ledger names failed: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Reprocessing error: {str(e)}"}), 500

# -------------------------------------------------------------
# CONVERSION API: ASHRAMAM CASH RECEIPTS LEDGER
# -------------------------------------------------------------
@routes_bp.route("/api/convert_cash", methods=["POST"])
def api_convert_cash():
    try:
        # Clear previous cash cache instantly on new file upload attempt
        FILE_CACHE["xml_cash"] = None
        FILE_CACHE["xlsx_cash"] = None
        LAST_CONVERSION["cash_file_bytes"] = None

        # Check files
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file uploaded."}), 400
            
        uploaded_file = request.files["file"]
        cutoff_date_str = request.form.get("cutoff_date", "").strip()
        debit_ledger = request.form.get("debit_ledger", "Cash").strip()
        credit_ledger = request.form.get("credit_ledger", "Annadana Prasadam Donations Received").strip()
        
        # Parse boundary date
        boundary_date = None
        if cutoff_date_str:
            try:
                boundary_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
                
        # Read file bytes in memory so we can re-process if lexicon updates
        file_bytes = uploaded_file.read()
        LAST_CONVERSION["cash_file_bytes"] = file_bytes
        LAST_CONVERSION["cash_cutoff_date"] = boundary_date
        
        # Ingest cash workbook
        file_stream = io.BytesIO(file_bytes)
        transactions, flagged_map, master_names_map = parse_cash_workbook(file_stream, start_date_cutoff=boundary_date)
        
        # Run validations
        audit_report = run_cash_audit(transactions)
        
        # Build preview files
        xml_text = generate_ashramam_tally_xml(transactions, cash_ledger=debit_ledger, donation_ledger=credit_ledger)
        excel_preview = build_nested_tally_sheets(transactions, cash_ledger=debit_ledger, donation_ledger=credit_ledger)
        
        # Cache file downloads
        FILE_CACHE["xml_cash"] = xml_text.encode("utf-8")
        FILE_CACHE["xlsx_cash"] = excel_preview
        
        return jsonify({
            "success": True,
            "report": audit_report,
            "flagged_names": flagged_map,
            "master_names": master_names_map,
            "debit_ledger": debit_ledger,
            "credit_ledger": credit_ledger
        })
        
    except ValueError as val_err:
        return jsonify({"success": False, "message": f"Validation failed: {str(val_err)}"}), 400
    except Exception as e:
        logger.error(f"Ashramam ledger conversion failed: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Conversion error: {str(e)}"}), 500

@routes_bp.route("/api/reprocess_cash", methods=["POST"])
def api_reprocess_cash():
    try:
        data = request.get_json() or {}
        debit_ledger = data.get("debit_ledger", "Cash").strip()
        credit_ledger = data.get("credit_ledger", "Annadana Prasadam Donations Received").strip()
        
        file_bytes = LAST_CONVERSION.get("cash_file_bytes")
        boundary_date = LAST_CONVERSION.get("cash_cutoff_date")
        
        if not file_bytes:
            return jsonify({"success": False, "message": "No active ledger session. Please upload file first."}), 400
            
        file_stream = io.BytesIO(file_bytes)
        transactions, flagged_map, master_names_map = parse_cash_workbook(file_stream, start_date_cutoff=boundary_date)
        
        audit_report = run_cash_audit(transactions)
        
        # Re-generate downloads
        xml_text = generate_ashramam_tally_xml(transactions, cash_ledger=debit_ledger, donation_ledger=credit_ledger)
        excel_preview = build_nested_tally_sheets(transactions, cash_ledger=debit_ledger, donation_ledger=credit_ledger)
        
        # Cache updates
        FILE_CACHE["xml_cash"] = xml_text.encode("utf-8")
        FILE_CACHE["xlsx_cash"] = excel_preview
        
        return jsonify({
            "success": True,
            "report": audit_report,
            "flagged_names": flagged_map,
            "master_names": master_names_map,
            "debit_ledger": debit_ledger,
            "credit_ledger": credit_ledger
        })
        
    except Exception as e:
        logger.error(f"Reprocessing cash ledger failed: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Reprocessing error: {str(e)}"}), 500

# -------------------------------------------------------------
# LEXICON MANAGING API
# -------------------------------------------------------------
@routes_bp.route("/api/lexicon", methods=["GET"])
def api_get_lexicon():
    return jsonify(load_lexicon())

@routes_bp.route("/api/lexicon/update", methods=["POST"])
def api_update_lexicon():
    try:
        data = request.get_json() or {}
        updates = data.get("updates", {}) # format: { "telugu_name": "english_name" }
        deletes = data.get("deletes", [])  # list of telugu keys to delete
        
        lexicon = load_lexicon()
        updated_count = 0
        
        # Helper function to save both macro and micro split tokens (matches Streamlit dual-layer logic)
        def save_dual_layer_tokens(telugu_phrase, english_phrase, lexicon_dict):
            has_updates = False
            
            # Layer 1: Macro
            if lexicon_dict.get(telugu_phrase) != english_phrase:
                lexicon_dict[telugu_phrase] = english_phrase
                has_updates = True
                
            # Layer 2: Micro split words (only if word count matches 1-to-1)
            t_words = telugu_phrase.strip().split()
            e_words = english_phrase.strip().split()
            if len(t_words) == len(e_words):
                for tw, ew in zip(t_words, e_words):
                    if lexicon_dict.get(tw) != ew:
                        lexicon_dict[tw] = ew
                        has_updates = True
            return has_updates

        # Process deletes (cleaning keys to match lookup format)
        for k in deletes:
            k_cleaned = k.strip().replace("గారూ", "").replace("గారు", "").replace("-", " ").replace("—", " ")
            k_cleaned = re.sub(r'\s+', ' ', k_cleaned).strip()
            
            # Delete both original and cleaned versions if they exist
            for del_key in (k, k_cleaned):
                if del_key in lexicon:
                    del lexicon[del_key]
                    updated_count += 1
                
        # Process updates (cleaning keys to match lookup format)
        for telugu_key, english_val in updates.items():
            telugu_key = telugu_key.strip()
            telugu_key = telugu_key.replace("గారూ", "").replace("గారు", "")
            telugu_key = telugu_key.replace("-", " ").replace("—", " ")
            telugu_key = re.sub(r'\s+', ' ', telugu_key).strip()
            
            english_val = english_val.strip()
            if telugu_key and english_val:
                if save_dual_layer_tokens(telugu_key, english_val, lexicon):
                    updated_count += 1
                    
        if updated_count > 0:
            save_lexicon(lexicon)
            
        return jsonify({"success": True, "message": f"Successfully updated {updated_count} mapping(s)."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/lexicon/clean", methods=["POST"])
def api_clean_lexicon():
    try:
        lexicon = load_lexicon()
        initial_count = len(lexicon)
        
        # Keep only Telugu keys and discard keys that have multiple words (spaces) after cleaning
        cleaned_lexicon = {}
        removed_english_count = 0
        removed_fullname_count = 0
        
        for k, v in lexicon.items():
            k = str(k)
            # Check for Telugu characters
            if not any('\u0c00' <= char <= '\u0c7f' for char in k):
                removed_english_count += 1
                continue
                
            # Clean key exactly like clean_telugu_name does
            k_clean = k.strip().replace("గారూ", "").replace("గారు", "")
            k_clean = k_clean.replace("-", " ").replace("—", " ")
            k_clean = re.sub(r'\s+', ' ', k_clean).strip()
            
            # If key contains multiple words (spaces), it is a full-name mapping
            if len(k_clean.split()) > 1:
                removed_fullname_count += 1
                continue
                
            # Clean value (case-insensitive strip of all garu spelling variants)
            v_clean = v.strip()
            v_clean = re.sub(r'(?i)\bgaru\b|\bgarū\b|\bgaaru\b|\bgaarū\b', '', v_clean).strip()
            v_clean = re.sub(r'\s+', ' ', v_clean).strip()
            
            if k_clean and v_clean:
                cleaned_lexicon[k_clean] = v_clean
                
        total_removed = initial_count - len(cleaned_lexicon)
        
        if total_removed > 0:
            save_lexicon(cleaned_lexicon)
            logger.info(
                f"api_clean_lexicon: Cleaned lexicon. Removed {removed_english_count} English-to-English mappings "
                f"and {removed_fullname_count} full-name mappings."
            )
            
        return jsonify({
            "success": True,
            "message": f"Successfully cleaned dictionary. Removed {removed_english_count} English-to-English mapping(s) and {removed_fullname_count} full-name mapping(s)."
        })
    except Exception as e:
        logger.error(f"Failed to clean lexicon: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

# -------------------------------------------------------------
# FILE DOWNLOAD ROUTER
# -------------------------------------------------------------
@routes_bp.route("/api/download/<file_type>", methods=["GET"])
def api_download(file_type):
    # Valid file types: "xml_bank", "xlsx_bank", "xml_cash", "xlsx_cash"
    if file_type not in FILE_CACHE or FILE_CACHE[file_type] is None:
        return f"<h3>Error: No generated output file found for Type '{file_type}'. Convert a statement first.</h3>", 404
        
    data = FILE_CACHE[file_type]
    filename = FILE_CACHE.get(f"{file_type}_filename", "output_file")
    
    mimetype = "application/xml" if "xml" in file_type else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return send_file(
        io.BytesIO(data),
        mimetype=mimetype,
        download_name=filename,
        as_attachment=True
    )
