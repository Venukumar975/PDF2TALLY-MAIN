# routes_hybrid.py
import os
import tempfile
import uuid
import datetime
from flask import request, jsonify
from routes_base import routes_bp, FILE_CACHE, LAST_CONVERSION
from services.logger import logger
from services.statement_validator import build_validation_report
from services.xlsx_viewer import export_xml_audit_workbook

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
        temp_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY', 'temp_uploads')
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
                    raw_bal_str = first_row[balance_idx]
                    bal_val = clean_amount(raw_bal_str)
                    
                    # Support negative/debit opening balance for loan/overdraft accounts
                    raw_lower = raw_bal_str.lower()
                    if 'dr' in raw_lower or 'od' in raw_lower or '-' in raw_lower or 'debit' in raw_lower:
                        bal_val = -abs(bal_val)
                    
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
            
        temp_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY', 'temp_uploads')
        pdf_path = os.path.join(temp_dir, f"temp_{temp_file_id}.pdf")
        
        if not os.path.exists(pdf_path):
            return jsonify({"success": False, "message": "Uploaded PDF file session has expired. Please upload again."}), 400
            
        boundary_date = None
        if strategy_type == "Incomplete statement (Continuation)" and cutoff_date_str:
            try:
                boundary_date = datetime.datetime.strptime(cutoff_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
                
        # Parse transactions using layout mapping
        from parsers.hybrid_parser import parse_hybrid_transactions
        transactions = parse_hybrid_transactions(pdf_path, mapping, boundary_date=boundary_date)
        
        if not transactions:
            return jsonify({"success": False, "message": "No valid transaction rows could be parsed using the selected mapping."}), 400
            
        # Save layout style locally if template configuration was checked
        if save_layout and layout_name:
            appdata_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
            os.makedirs(appdata_dir, exist_ok=True)
            layouts_path = os.path.join(appdata_dir, "saved_layouts.json")
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
        
        val_opening_bal = 0.00 if strategy_type == "Incomplete statement (Continuation)" else opening_balance
        
        # Generate Tally audit validation report
        validation_report = build_validation_report(
            sanitized_text,
            transactions,
            xml_text,
            bank_ledger,
            suspense_ledger,
            opening_balance=val_opening_bal
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
        appdata_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
        os.makedirs(appdata_dir, exist_ok=True)
        layouts_path = os.path.join(appdata_dir, "saved_layouts.json")
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


