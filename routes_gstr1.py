# routes_gstr1.py
import json
import io
import re
from flask import request, jsonify
import pandas as pd
from routes_base import routes_bp, FILE_CACHE
from services.logger import logger
from datetime import datetime

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
        
        # Read header row index (1-based from UI, default to 4)
        header_row_raw = request.form.get("header_row", "4").strip()
        header_idx = int(header_row_raw) - 1 if header_row_raw.isdigit() else 3

        # Parse spreadsheet using pandas
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='b2b', header=header_idx)
        else:
            csv_data = file_bytes.decode('utf-8', errors='ignore')
            df = pd.read_csv(io.StringIO(csv_data), header=header_idx)
            
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
            "version": "GST3.2.4",
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
# GSTR-1 STANDALONE HSN OFFLINE JSON
# -------------------------------------------------------------
@routes_bp.route("/api/convert_hsn", methods=["POST"])
def api_convert_hsn():
    try:
        def clean_num(x):
            return int(x) if x.is_integer() else round(x, 2)

        # Clear previous HSN cache
        FILE_CACHE["json_hsn"] = None
        
        # Check files
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file uploaded."}), 400
            
        uploaded_file = request.files["file"]
        gstin_input = request.form.get("supplier_gstin", "").strip().upper()
        fp_input = request.form.get("fp", "").strip()
        
        if not gstin_input or len(gstin_input) != 15:
            return jsonify({"success": False, "message": "Please enter a valid 15-character Supplier GSTIN."}), 400
        if not fp_input or len(fp_input) != 6 or not fp_input.isdigit():
            return jsonify({"success": False, "message": "Please enter a valid Financial Period in MMYYYY format (e.g. 082025)."}), 400
            
        filename = uploaded_file.filename.lower()
        # Read header row index (1-based from UI, default to 4)
        header_row_raw = request.form.get("header_row", "4").strip()
        header_idx = int(header_row_raw) - 1 if header_row_raw.isdigit() else 3

        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file, header=header_idx)
        else:
            df = pd.read_excel(uploaded_file, sheet_name="hsn", header=header_idx)
            
        # Clean column names by stripping whitespace
        df.columns = [str(col).strip() for col in df.columns]
        
        logger.info(f"Loaded HSN DataFrame shape: {df.shape}")
        logger.info(f"HSN DataFrame columns: {list(df.columns)}")
        
        # Rename common variations to standard column names
        rename_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ["hsn", "hsn code", "hsn/sac"]:
                rename_map[col] = "HSN"
                
            elif col_lower in ["description", "desc"]:
                rename_map[col] = "Description"
                
            elif col_lower == "uqc":
                rename_map[col] = "UQC"
                
            elif col_lower in ["total quantity", "quantity", "qty", "total qty"]:
                rename_map[col] = "Total Quantity"
                
            elif col_lower in ["total value", "value","total val"]:
                rename_map[col] = "Total Value"
                
            elif col_lower in ["taxable value", "taxable amount"]:
                rename_map[col] = "Taxable Value"
                
            elif col_lower in ["integrated tax amount", "igst", "igst amount", "integrated tax", "integrated tax amount"]:
                rename_map[col] = "Integrated Tax Amount"
                
            elif col_lower in ["central tax amount", "cgst", "cgst amount", "central tax", "central tax amount"]:
                rename_map[col] = "Central Tax Amount"
                
            elif col_lower in ["state/ut tax amount", "sgst", "sgst amount", "sgst/utgst", "state/ut tax", "state tax", "state tax amount", "state/ut tax amount"]:
                rename_map[col] = "State/UT Tax Amount"
                
            elif col_lower in ["cess amount", "cess", "cess tax"]:
                rename_map[col] = "Cess"
                
            elif col_lower in ["rate", "rt", "tax rate"]:
                rename_map[col] = "Rate"
                
        df = df.rename(columns=rename_map)
        logger.info(f"Normalized HSN DataFrame columns: {list(df.columns)}")
        
        hsn_list = []
        b2b_hsn_list = []
        b2c_hsn_list = []
        current_sply_ty = "B2B"  # Default start state
        
        total_qty = 0.0
        total_taxable = 0.0
        total_taxes = 0.0
        total_val = 0.0
        hsn_count = 0
        
        for idx, row in df.iterrows():
            hsn_raw = str(row.get('HSN', '')).strip()
            
            # Switch supply type dynamically when encountering section divider rows
            if "b2c supplies" in hsn_raw.lower():
                current_sply_ty = "B2C"
                continue
            elif "b2b supplies" in hsn_raw.lower():
                current_sply_ty = "B2B"
                continue
                
            if not hsn_raw or hsn_raw == 'nan' or "total" in hsn_raw.lower():
                continue
                
            # Clean HSN code decimals from pandas
            if hsn_raw.endswith('.0'):
                hsn_raw = hsn_raw[:-2]
            # Zero-pad if leading zeros were dropped (HSNs must be 4, 6, or 8 digits)
            if len(hsn_raw) in [3, 5, 7]:
                hsn_raw = hsn_raw.zfill(len(hsn_raw) + 1)
                
            desc = str(row.get('Description', '')).strip() if pd.notna(row.get('Description')) else ""
            if desc == 'nan':
                desc = ""
                
            raw_uqc = str(row.get('UQC', '')).strip() if pd.notna(row.get('UQC')) else "OTH"
            if raw_uqc == 'nan' or not raw_uqc:
                raw_uqc = "OTH"
            uqc = raw_uqc.split('-')[0].strip()
            
            qty = float(row.get('Total Quantity', 0.0)) if pd.notna(row.get('Total Quantity')) else 0.0
            val = float(row.get('Total Value', 0.0)) if pd.notna(row.get('Total Value')) else 0.0
            txval = float(row.get('Taxable Value', 0.0)) if pd.notna(row.get('Taxable Value')) else 0.0
            
            iamt = float(row.get('Integrated Tax Amount', 0.0)) if pd.notna(row.get('Integrated Tax Amount')) else 0.0
            camt = float(row.get('Central Tax Amount', 0.0)) if pd.notna(row.get('Central Tax Amount')) else 0.0
            samt = float(row.get('State/UT Tax Amount', 0.0)) if pd.notna(row.get('State/UT Tax Amount')) else 0.0
            cess = float(row.get('Cess', 0.0)) if pd.notna(row.get('Cess')) else 0.0
            
            rate_raw = str(row.get('Rate', '0.0')).strip()
            rate_clean = re.sub(r'[^\d\.]', '', rate_raw)
            rt = float(rate_clean) if rate_clean else 0.0
            
            hsn_entry = {
                "num": len(b2b_hsn_list) + 1 if current_sply_ty == "B2B" else len(b2c_hsn_list) + 1,
                "hsn_sc": hsn_raw,
                "desc": desc,
                "uqc": uqc,
                "qty": clean_num(qty),
                "rt": clean_num(rt),
                "txval": clean_num(txval),
                "iamt": clean_num(iamt),
                "samt": clean_num(samt),
                "camt": clean_num(camt),
                "csamt": clean_num(cess)
            }
            
            if current_sply_ty == "B2B":
                b2b_hsn_list.append(hsn_entry)
            else:
                b2c_hsn_list.append(hsn_entry)
                
            # Keep a copy with sply_ty for UI preview rendering
            ui_entry = hsn_entry.copy()
            ui_entry["sply_ty"] = current_sply_ty
            ui_entry["val"] = clean_num(val)
            hsn_list.append(ui_entry)
            
            total_qty += qty
            total_taxable += txval
            total_taxes += (camt + samt + iamt)
            total_val += val
            hsn_count += 1
            
        gst_json = {
            "gstin": gstin_input,
            "fp": fp_input,
            "version": "GST3.2.4",
            "hash": "hash",
            "hsn": {
                "hsn_b2b": b2b_hsn_list,
                "hsn_b2c": b2c_hsn_list
            }
        }
        
        # Serialize and cache HSN output
        json_output = json.dumps(gst_json, indent=4)
        FILE_CACHE["json_hsn"] = json_output.encode("utf-8")
        FILE_CACHE["json_hsn_filename"] = f"returns_hsn_{fp_input}_{gstin_input}_offline.json"
        
        return jsonify({
            "success": True,
            "summary": {
                "total_qty": round(total_qty, 2),
                "total_taxable": round(total_taxable, 2),
                "total_taxes": round(total_taxes, 2),
                "total_val": round(total_val, 2),
                "hsn_count": hsn_count
            },
            "hsn_data": hsn_list
        })
        
    except Exception as e:
        logger.error(f"GSTR-1 HSN conversion failed: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Conversion error: {str(e)}"}), 500

# -------------------------------------------------------------
# LEXICON MANAGING API
# -------------------------------------------------------------
