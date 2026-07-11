import os
import json
import io
import re
import tempfile
import time
import requests
from flask import Blueprint, request, jsonify, render_template, send_file, redirect, url_for, session
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
# Keys: "xml_bank", "xlsx_bank", "xml_cash", "xlsx_cash", "json_gstr1"
FILE_CACHE = {
    "xml_bank": None,
    "xlsx_bank": None,
    "xml_cash": None,
    "xlsx_cash": None,
    "json_gstr1": None,
    # Download file names
    "xml_bank_filename": "tally_import.xml",
    "xlsx_bank_filename": "statement_audit_viewer.xlsx",
    "xml_cash_filename": "Ashramam_Cash_Receipts.xml",
    "xlsx_cash_filename": "Tally_Nested_Sheets_Preview.xlsx",
    "json_gstr1_filename": "returns_gstr1.json"
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

@routes_bp.route("/review")
def review_desk():
    return render_template("review.html")

# -------------------------------------------------------------
# LICENSE API
# -------------------------------------------------------------
# -------------------------------------------------------------
# LICENSE API (PROXIES TO CLOUD BACKEND)
# -------------------------------------------------------------
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
        url = f"{licensing.get_cloud_backend_url()}/activate-license"
        resp = requests.post(url, json={
            "license_key": license_key,
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
                if prev_balance is not None:
                    opening_bal = prev_balance
                transactions = route_to_parser(bank_type, sanitized_text, opening_balance=opening_bal)
                if opening_bal is None:
                    opening_bal = 0.00
                xml_opening_bal = opening_bal
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
                xml_opening_bal = None  # Do NOT include opening balance in XML for continuation strategy
            else:
                sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
                transactions = route_to_parser(bank_type, sanitized_text, opening_balance=opening_bal)
                if opening_bal is None:
                    opening_bal = 0.00
                xml_opening_bal = opening_bal
            
            if not transactions:
                return jsonify({"success": False, "message": "No valid transaction rows found in PDF statement."}), 400
                
            # Cache inputs for reprocessing ledger names
            LAST_CONVERSION["bank_txns"] = transactions
            LAST_CONVERSION["bank_type"] = bank_type
            LAST_CONVERSION["bank_opening_bal"] = xml_opening_bal
            LAST_CONVERSION["bank_sanitized_text"] = sanitized_text
            
            # Build initial preview with ledger names
            if not debit_ledger:
                if "BOB" in bank_type:
                    debit_ledger = "BANK OF BARODA"
                elif "Axis" in bank_type:
                    debit_ledger = "AXIS BANK"
                else:
                    debit_ledger = "STATE BANK OF INDIA"
            if not credit_ledger:
                credit_ledger = "Suspense"
                
            # Generate XML & Excel
            xml_text = generate_tally_xml(
                transactions, 
                output_path=None, 
                bank_ledger=debit_ledger, 
                suspense_ledger=credit_ledger, 
                opening_balance=xml_opening_bal
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
            prefix = "BOB" if "BOB" in bank_type else ("AXIS" if "Axis" in bank_type else "SBI")
            FILE_CACHE["xml_bank_filename"] = f"{prefix}_tally_import.xml"
            FILE_CACHE["xlsx_bank_filename"] = f"{prefix}_statement_audit_viewer.xlsx"
            
            # Formulate response
            return jsonify({
                "success": True,
                "report": validation_report,
                "debit_ledger": debit_ledger,
                "credit_ledger": credit_ledger,
                "transactions": transactions
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
            if "BOB" in bank_type:
                debit_ledger = "BANK OF BARODA"
            elif "Axis" in bank_type:
                debit_ledger = "AXIS BANK"
            else:
                debit_ledger = "STATE BANK OF INDIA"
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
            "credit_ledger": credit_ledger,
            "transactions": transactions
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
# CONVERSION API: GSTR-1 OFFLINE JSON
# -------------------------------------------------------------
@routes_bp.route("/api/convert_gstr1", methods=["POST"])
def api_convert_gstr1():
    try:
        # Clear previous GSTR-1 cache
        FILE_CACHE["json_gstr1"] = None
        
        # Check files
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file uploaded."}), 400
            
        uploaded_file = request.files["file"]
        gstin_input = request.form.get("supplier_gstin", "").strip()
        fp_input = request.form.get("fp", "").strip()
        
        if not gstin_input:
            return jsonify({"success": False, "message": "Supplier GSTIN is required."}), 400
        if not fp_input:
            return jsonify({"success": False, "message": "Financial Period (fp) is required."}), 400
            
        filename = uploaded_file.filename.lower()
        file_bytes = uploaded_file.read()
        
        import pandas as pd
        
        # Parse spreadsheet using pandas
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='b2b', header=3)
        else:
            csv_data = file_bytes.decode('utf-8', errors='ignore')
            df = pd.read_csv(io.StringIO(csv_data))
            
        # Clean columns
        df.columns = df.columns.str.strip()
        
        # Validate columns
        required_cols = ['GSTIN/UIN of Recipient', 'Invoice Number', 'Invoice date', 'Invoice Value', 'Place Of Supply', 'Taxable Value', 'Rate']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            return jsonify({"success": False, "message": f"Missing required column(s): {', '.join(missing_cols)}"}), 400
            
        # 1. Initialize the GSTR-1 structure
        gst_json = {
            "gstin": gstin_input,
            "fp": fp_input,
            "version": "GST3.2.2",
            "hash": "hash",
            "b2b": [],
            "nil": {
                "inv": [
                    {"sply_ty": "INTRB2B", "expt_amt": 0, "nil_amt": 0, "ngsup_amt": 0},
                    {"sply_ty": "INTRAB2B", "expt_amt": 0, "nil_amt": 0, "ngsup_amt": 0},
                    {"sply_ty": "INTRB2C", "expt_amt": 0, "nil_amt": 0, "ngsup_amt": 0},
                    {"sply_ty": "INTRAB2C", "expt_amt": 0, "nil_amt": 0, "ngsup_amt": 0}
                ]
            }
        }
        
        supplier_state = gstin_input[:2]
        
        # 2. Group records by Recipient's GSTIN and then process invoices
        grouped_ctin = df.groupby('GSTIN/UIN of Recipient')
        
        # To display preview stats
        total_taxable = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0
        total_invoice_val = 0.0
        invoice_count = 0
        recipient_count = 0
        invoices_preview = []
        
        for ctin, ctin_group in grouped_ctin:
            ctin_str = str(ctin).strip()
            if not ctin_str or len(ctin_str) < 5 or "total" in ctin_str.lower() or ctin_str == 'nan':
                continue
                
            recipient_count += 1
            b2b_entry = {
                "ctin": ctin_str,
                "inv": []
            }
            
            # Group by Invoice Number to consolidate multi-rate items
            grouped_inv = ctin_group.groupby('Invoice Number')
            
            for inum, inv_group in grouped_inv:
                inum_str = str(inum).strip()
                if not inum_str or inum_str == 'nan':
                    continue
                    
                first_row = inv_group.iloc[0]
                invoice_count += 1
                
                # Safe Date Parsing
                raw_date = first_row['Invoice date']
                if isinstance(raw_date, datetime):
                    formatted_date = raw_date.strftime('%d-%m-%Y')
                elif pd.api.types.is_datetime64_any_dtype(inv_group['Invoice date']):
                    formatted_date = pd.to_datetime(raw_date).strftime('%d-%m-%Y')
                else:
                    raw_date_str = str(raw_date).strip()
                    try:
                        parsed_date = datetime.strptime(raw_date_str, '%d-%b-%y')
                    except ValueError:
                        try:
                            parsed_date = datetime.strptime(raw_date_str, '%d-%m-%Y')
                        except ValueError:
                            parsed_date = pd.to_datetime(raw_date_str)
                    formatted_date = parsed_date.strftime('%d-%m-%Y')
                
                # Identify POS numeric prefix and zero-pad to exactly 2 digits
                pos_full = str(first_row['Place Of Supply']).strip()
                raw_pos = pos_full.split('-')[0].strip()
                if raw_pos.endswith('.0'):
                    raw_pos = raw_pos[:-2]
                pos_code = raw_pos.zfill(2)
                
                # Clean RCM input
                raw_rc = str(first_row['Reverse Charge']).strip().upper() if 'Reverse Charge' in first_row else 'N'
                rchrg_flag = "Y" if "Y" in raw_rc else "N"
                
                # Flexible Invoice Type checking (Regular, SEZ with/without payment, Deemed Exports, Bonded Warehouse)
                raw_inv_type = str(first_row['Invoice Type']).strip().lower() if 'Invoice Type' in first_row else 'regular'
                if "sez" in raw_inv_type and "without" in raw_inv_type:
                    inv_type_code = "SEWOP"
                elif "sez" in raw_inv_type:
                    inv_type_code = "SEWP"
                elif "deemed" in raw_inv_type:
                    inv_type_code = "DE"
                elif "cbw" in raw_inv_type or "bonded" in raw_inv_type:
                    inv_type_code = "CBW"
                else:
                    inv_type_code = "R"
                
                invoice_entry = {
                    "inum": inum_str,
                    "idt": formatted_date,
                    "val": float(first_row['Invoice Value']),
                    "pos": pos_code,
                    "rchrg": rchrg_flag,
                    "inv_typ": inv_type_code, 
                    "itms": []
                }
                
                # Stats calculation
                inv_taxable_sum = 0.0
                inv_cgst_sum = 0.0
                inv_sgst_sum = 0.0
                inv_igst_sum = 0.0
                
                item_num = 1
                for idx, row in inv_group.iterrows():
                    txval = float(row['Taxable Value'])
                    rate = float(row['Rate'])
                    
                    # Format rate: integer if whole number, float if decimal
                    rate_val = int(rate) if rate.is_integer() else rate
                    
                    total_tax = round((txval * rate) / 100, 2)
                    
                    # Safe cess fallback
                    cess_val = 0.0
                    if 'Cess Amount' in row and pd.notna(row['Cess Amount']):
                        cess_val = float(row['Cess Amount'])
                    
                    itm_det = {
                        "txval": txval,
                        "rt": rate_val,
                        "csamt": cess_val
                    }
                    
                    inv_taxable_sum += txval
                    
                    # Apply state tax distribution rule
                    if pos_code == supplier_state:
                        camt = round(total_tax / 2, 2)
                        samt = round(total_tax / 2, 2)
                        itm_det["camt"] = camt
                        itm_det["samt"] = samt
                        inv_cgst_sum += camt
                        inv_sgst_sum += samt
                    else:
                        itm_det["iamt"] = total_tax
                        inv_igst_sum += total_tax
                        
                    invoice_entry["itms"].append({
                        "num": item_num,
                        "itm_det": itm_det
                    })
                    item_num += 1
                
                total_taxable += inv_taxable_sum
                total_cgst += inv_cgst_sum
                total_sgst += inv_sgst_sum
                total_igst += inv_igst_sum
                total_invoice_val += float(first_row['Invoice Value'])
                
                invoices_preview.append({
                    "ctin": ctin_str,
                    "inum": inum_str,
                    "idt": formatted_date,
                    "val": float(first_row['Invoice Value']),
                    "txval": round(inv_taxable_sum, 2),
                    "cgst": round(inv_cgst_sum, 2),
                    "sgst": round(inv_sgst_sum, 2),
                    "igst": round(inv_igst_sum, 2),
                    "pos": pos_code,
                    "rchrg": rchrg_flag
                })
                
                b2b_entry["inv"].append(invoice_entry)
                
            gst_json["b2b"].append(b2b_entry)
            
        # Serialize to JSON and cache
        json_output = json.dumps(gst_json, indent=4)
        FILE_CACHE["json_gstr1"] = json_output.encode("utf-8")
        FILE_CACHE["json_gstr1_filename"] = f"returns_{fp_input}_{gstin_input}_offline.json"
        
        return jsonify({
            "success": True,
            "summary": {
                "total_taxable": round(total_taxable, 2),
                "total_cgst": round(total_cgst, 2),
                "total_sgst": round(total_sgst, 2),
                "total_igst": round(total_igst, 2),
                "total_invoice_val": round(total_invoice_val, 2),
                "invoice_count": invoice_count,
                "recipient_count": recipient_count
            },
            "invoices": invoices_preview
        })
        
    except Exception as e:
        logger.error(f"GSTR-1 conversion failed: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Conversion error: {str(e)}"}), 500

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
    # Valid file types: "xml_bank", "xlsx_bank", "xml_cash", "xlsx_cash", "json_gstr1"
    if file_type not in FILE_CACHE or FILE_CACHE[file_type] is None:
        return f"<h3>Error: No generated output file found for Type '{file_type}'. Convert a statement first.</h3>", 404
        
    data = FILE_CACHE[file_type]
    filename = FILE_CACHE.get(f"{file_type}_filename", "output_file")
    
    if "xml" in file_type:
        mimetype = "application/xml"
    elif "json" in file_type:
        mimetype = "application/json"
    else:
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return send_file(
        io.BytesIO(data),
        mimetype=mimetype,
        download_name=filename,
        as_attachment=True
    )


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
@routes_bp.route("/api/hybrid/validate-and-extract", methods=["POST"])
def api_hybrid_validate_and_extract():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    uploaded_file = request.files["file"]
    
    # Save temp file
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    uploaded_file.save(temp_path)
    
    try:
        import uuid
        import shutil
        from parsers.hybrid_parser import validate_pdf, extract_and_preview_tables
        
        # 1. Validate PDF character stream (is text-based)
        is_valid, err_msg = validate_pdf(temp_path)
        if not is_valid:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"success": False, "message": err_msg}), 400
            
        # 2. Extract first valid table for user verification
        res = extract_and_preview_tables(temp_path)
        if not res.get("success"):
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"success": False, "message": res.get("message", "Failed to extract table structure.")}), 400
            
        # Create temp_uploads directory inside user home folder to hold file session
        temp_dir = os.path.expanduser("~/.pdf2tally/temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_id = str(uuid.uuid4())
        saved_temp_path = os.path.join(temp_dir, f"temp_{temp_file_id}.pdf")
        shutil.copy(temp_path, saved_temp_path)
        
        # Clean up temporary upload file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # Calculate opening balance from first row if Balance column is mapped
        inferred_op_balance = 0.0
        preview_rows = res.get("preview_rows", [])
        auto_mapping = res.get("auto_mapping", {})
        
        balance_idx = int(auto_mapping.get("balance", -1))
        debit_idx = int(auto_mapping.get("debit", -1))
        credit_idx = int(auto_mapping.get("credit", -1))
        
        if balance_idx != -1 and len(preview_rows) > 0:
            first_row = preview_rows[0]
            if len(first_row) > balance_idx:
                try:
                    from parsers.hybrid_parser import clean_amount
                    bal_val = clean_amount(first_row[balance_idx])
                    
                    deb_val = 0.0
                    if debit_idx != -1 and len(first_row) > debit_idx:
                        deb_val = clean_amount(first_row[debit_idx])
                        
                    cred_val = 0.0
                    if credit_idx != -1 and len(first_row) > credit_idx:
                        cred_val = clean_amount(first_row[credit_idx])
                        
                    # Handle single-column indicator check
                    if debit_idx == credit_idx and debit_idx != -1:
                        val_str = first_row[debit_idx].lower()
                        amt = clean_amount(val_str)
                        if 'dr' in val_str or 'w' in val_str or '-' in val_str:
                            deb_val = amt
                            cred_val = 0.0
                        elif 'cr' in val_str or 'd' in val_str or '+' in val_str:
                            deb_val = 0.0
                            cred_val = amt
                        else:
                            deb_val = amt
                            cred_val = 0.0
                            
                    inferred_op_balance = bal_val + deb_val - cred_val
                except Exception:
                    pass
                    
        return jsonify({
            "success": True,
            "temp_file_id": temp_file_id,
            "headers": res.get("headers", []),
            "preview_rows": preview_rows,
            "auto_mapping": auto_mapping,
            "low_confidence": res.get("low_confidence", True),
            "col_count": res.get("col_count", 0),
            "inferred_opening_balance": round(inferred_op_balance, 2)
        })
        
    except Exception as e:
        logger.error(f"Error in validate-and-extract API: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@routes_bp.route("/api/hybrid/parse", methods=["POST"])
def api_hybrid_parse():
    try:
        import json
        import shutil
        
        data = request.get_json(silent=True) or {}
        temp_file_id = data.get("temp_file_id", "").strip()
        mapping = data.get("mapping", {})
        bank_ledger = data.get("bank_ledger", "").strip() or "Generic Bank"
        suspense_ledger = data.get("suspense_ledger", "").strip() or "Suspense"
        opening_balance = float(data.get("opening_balance", 0.00))
        save_layout = bool(data.get("save_layout", False))
        layout_name = data.get("layout_name", "").strip()
        strategy_type = data.get("strategy_type", "Full bank statement").strip()
        cutoff_date_str = data.get("cutoff_date", "").strip()
        
        if not temp_file_id:
            return jsonify({"success": False, "message": "Temp File ID is required."}), 400
            
        temp_dir = os.path.expanduser("~/.pdf2tally/temp_uploads")
        pdf_path = os.path.join(temp_dir, f"temp_{temp_file_id}.pdf")
        
        if not os.path.exists(pdf_path):
            return jsonify({"success": False, "message": "Uploaded PDF file session has expired. Please upload again."}), 400
            
        boundary_date = None
        if strategy_type == "Incomplete statement (Continuation)" and cutoff_date_str:
            try:
                boundary_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
                
        # Parse transactions using layout mapping
        from parsers.hybrid_parser import parse_hybrid_transactions
        transactions = parse_hybrid_transactions(pdf_path, mapping, boundary_date=boundary_date)
        
        if not transactions:
            return jsonify({"success": False, "message": "No valid transaction rows could be parsed using the selected mapping."}), 400
            
        # Save layout style locally if template configuration was checked
        if save_layout and layout_name:
            layouts_path = os.path.join(os.path.dirname(__file__), "templates", "saved_layouts.json")
            layouts_data = {}
            if os.path.exists(layouts_path):
                try:
                    with open(layouts_path, "r", encoding="utf-8") as f:
                        layouts_data = json.load(f)
                except Exception:
                    layouts_data = {}
            
            # Extract current headers
            from parsers.hybrid_parser import extract_and_preview_tables
            headers = []
            preview_res = extract_and_preview_tables(pdf_path)
            headers = preview_res.get("headers", [])
            
            layouts_data[layout_name] = {
                "layout_name": layout_name,
                "mapping": mapping,
                "headers": headers,
                "col_count": len(headers)
            }
            
            with open(layouts_path, "w", encoding="utf-8") as f:
                json.dump(layouts_data, f, indent=4)
                
        # Cache outputs for reprocessing ledger names
        FILE_CACHE["xml_bank"] = None
        FILE_CACHE["xlsx_bank"] = None
        
        # Read text layer for audit report logs
        from services.pdf_reader import extract_text
        sanitized_text = ""
        try:
            raw_text = extract_text(pdf_path)
            if strategy_type == "Incomplete statement (Continuation)" and boundary_date:
                from slicers.hybrid_parser_slicing import slice_text_by_date
                sanitized_text = slice_text_by_date(raw_text, boundary_date)
            else:
                sanitized_text = raw_text
        except Exception:
            sanitized_text = ""
            
        xml_opening_balance = None if strategy_type == "Incomplete statement (Continuation)" else opening_balance
        
        LAST_CONVERSION["bank_txns"] = transactions
        LAST_CONVERSION["bank_type"] = "Hybrid Generic"
        LAST_CONVERSION["bank_opening_bal"] = xml_opening_balance
        LAST_CONVERSION["bank_sanitized_text"] = sanitized_text
        
        # Generate Tally XML with Hybrid Parser XML Compiler
        from services.xml_generator_hybrid_parser import generate_tally_xml_hybrid
        xml_text = generate_tally_xml_hybrid(
            transactions,
            bank_ledger=bank_ledger,
            suspense_ledger=suspense_ledger,
            opening_balance=xml_opening_balance
        )
        
        FILE_CACHE["xml_bank"] = xml_text.encode("utf-8")
        FILE_CACHE["xml_bank_filename"] = f"generic_tally_import.xml"
        
        # Generate Tally audit validation report
        validation_report = build_validation_report(
            sanitized_text,
            transactions,
            xml_text,
            bank_ledger,
            suspense_ledger
        )
        
        # Generate Excel audit workbook
        fd_xlsx, temp_xlsx = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd_xlsx)
        export_xml_audit_workbook(xml_text, temp_xlsx, bank_ledger=bank_ledger, suspense_ledger=suspense_ledger)
        
        with open(temp_xlsx, "rb") as f_in:
            FILE_CACHE["xlsx_bank"] = f_in.read()
        FILE_CACHE["xlsx_bank_filename"] = f"generic_statement_audit_viewer.xlsx"
        
        # Cleanup temporary files
        try:
            if os.path.exists(temp_xlsx):
                os.remove(temp_xlsx)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass
            
        return jsonify({
            "success": True,
            "message": "Generic bank statement converted successfully!",
            "report": validation_report,
            "transactions": transactions
        })
        
    except Exception as e:
        logger.error(f"Error in hybrid parse API: {e}")
        return jsonify({"success": False, "message": f"Server parsing error: {str(e)}"}), 500


@routes_bp.route("/api/hybrid/layouts", methods=["GET"])
def api_hybrid_layouts():
    try:
        import json
        layouts_path = os.path.join(os.path.dirname(__file__), "templates", "saved_layouts.json")
        layouts_data = {}
        if os.path.exists(layouts_path):
            try:
                with open(layouts_path, "r", encoding="utf-8") as f:
                    layouts_data = json.load(f)
            except Exception:
                layouts_data = {}
        return jsonify({"success": True, "layouts": list(layouts_data.values())})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@routes_bp.route("/api/detect-opening-balance", methods=["POST"])
def api_detect_opening_balance():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    uploaded_file = request.files["file"]
    bank_type = request.form.get("bank_type", "").strip()
    
    if not bank_type:
        return jsonify({"success": False, "message": "Bank type is required."}), 400
        
    # Save temp file
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    uploaded_file.save(temp_path)
    
    try:
        from services.pdf_reader import extract_text
        from parsers.router import get_opening_balance_parser
        
        # If hybrid, extract table and calculate opening balance
        if bank_type == "Hybrid Generic":
            from parsers.hybrid_parser import extract_and_preview_tables, clean_amount
            res = extract_and_preview_tables(temp_path)
            inferred_op_balance = 0.0
            if res.get("success"):
                preview_rows = res.get("preview_rows", [])
                auto_mapping = res.get("auto_mapping", {})
                balance_idx = int(auto_mapping.get("balance", -1))
                debit_idx = int(auto_mapping.get("debit", -1))
                credit_idx = int(auto_mapping.get("credit", -1))
                
                if balance_idx != -1 and len(preview_rows) > 0:
                    first_row = preview_rows[0]
                    if len(first_row) > balance_idx:
                        bal_val = clean_amount(first_row[balance_idx])
                        
                        deb_val = 0.0
                        if debit_idx != -1 and len(first_row) > debit_idx:
                            deb_val = clean_amount(first_row[debit_idx])
                            
                        cred_val = 0.0
                        if credit_idx != -1 and len(first_row) > credit_idx:
                            cred_val = clean_amount(first_row[credit_idx])
                            
                        # Handle single-column check
                        if debit_idx == credit_idx and debit_idx != -1:
                            val_str = first_row[debit_idx].lower()
                            amt = clean_amount(val_str)
                            if 'dr' in val_str or 'w' in val_str or '-' in val_str:
                                deb_val = amt
                                cred_val = 0.0
                            elif 'cr' in val_str or 'd' in val_str or '+' in val_str:
                                deb_val = 0.0
                                cred_val = amt
                            else:
                                deb_val = amt
                                cred_val = 0.0
                                
                        inferred_op_balance = bal_val + deb_val - cred_val
            op_bal = inferred_op_balance
        else:
            text = extract_text(temp_path)
            parse_opening_func = get_opening_balance_parser(bank_type)
            op_bal = parse_opening_func(text)
            

        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify({
            "success": True,
            "opening_balance": op_bal if op_bal is not None else 0.00
        })
    except Exception as e:
        logger.error(f"Error detecting opening balance: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/review/save", methods=["POST"])
def api_review_save():
    try:
        data = request.get_json(silent=True) or {}
        xml_text = data.get("xml", "").strip()
        debit_ledger = data.get("debit_ledger", "").strip() or "Generic Bank"
        credit_ledger = data.get("credit_ledger", "").strip() or "Suspense"
        original_filename = data.get("filename", "").strip() or "tally_import.xml"
        
        if not xml_text:
            return jsonify({"success": False, "message": "XML content is required."}), 400
            
        # Determine target default filename for Save As
        if original_filename.endswith(".xml"):
            base_name = original_filename[:-4]
            default_filename = f"{base_name}_reviewed.xml"
        else:
            default_filename = f"{original_filename}_reviewed.xml"

        # 1. Trigger Native File Dialog
        file_path = None
        
        # Fallback 1: Try pywebview's active window dialog
        try:
            import webview
            active_win = webview.active_window()
            if active_win:
                res = active_win.create_file_dialog(
                    dialog_type=webview.SAVE_DIALOG,
                    file_types=("XML files (*.xml)", "All files (*.*)"),
                    save_filename=default_filename
                )
                if res:
                    if isinstance(res, (list, tuple)):
                        file_path = res[0]
                    else:
                        file_path = res
        except Exception as e:
            logger.warning(f"Failed to use pywebview file dialog: {e}")
            
        # Fallback 2: Tkinter filedialog
        if not file_path:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".xml",
                    filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
                    initialfile=default_filename,
                    title="Save XML As..."
                )
                root.destroy()
            except Exception as e:
                logger.error(f"Failed to use Tkinter file dialog: {e}")

        # If user cancelled selection
        if not file_path:
            return jsonify({"success": False, "cancelled": True, "message": "Save action cancelled by user."})

        # 2. Save XML to selected file path
        with open(file_path, "w", encoding="utf-8") as f_out:
            f_out.write(xml_text)
            
        # 3. Update in-memory XML cache
        FILE_CACHE["xml_bank"] = xml_text.encode("utf-8")
        
        # 4. Regenerate Excel audit workbook in-memory
        import tempfile
        fd_xlsx, temp_xlsx = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd_xlsx)
        
        try:
            from services.xlsx_viewer import export_xml_audit_workbook
            export_xml_audit_workbook(xml_text, temp_xlsx, bank_ledger=debit_ledger, suspense_ledger=credit_ledger)
            with open(temp_xlsx, "rb") as f_in:
                FILE_CACHE["xlsx_bank"] = f_in.read()
        finally:
            if os.path.exists(temp_xlsx):
                os.remove(temp_xlsx)
                
        return jsonify({
            "success": True, 
            "message": f"File saved successfully as:\n{os.path.basename(file_path)}",
            "saved_path": file_path
        })
    except Exception as e:
        logger.error(f"Error in review save API: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

# Import Tally sub-routing endpoints
import routes_tally
