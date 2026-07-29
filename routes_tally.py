import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import request, jsonify
from routes_base import routes_bp
from services.logger import logger

# -------------------------------------------------------------
# TALLY PRIME LOCAL SYNCHRONIZATION ENDPOINTS
# -------------------------------------------------------------
@routes_bp.route("/api/tally/sync", methods=["POST"])
def api_tally_sync():
    data = request.get_json() or {}
    company_name = data.get("company_name", "").strip()
    
    if not company_name:
        return jsonify({"success": False, "message": "Company Name is required to synchronize ledgers."}), 400
        
    tally_url = "http://localhost:9000"
    
    def clean_tally_xml(content_bytes):
        text = content_bytes.decode("utf-8", errors="ignore")
        # Remove invalid XML character references (control characters < 32 except tab, LF, CR)
        def repl(match):
            ent = match.group(0)
            try:
                if ent.startswith("&#x"):
                    v = int(ent[3:-1], 16)
                else:
                    v = int(ent[2:-1])
                if v < 32 and v not in (9, 10, 13):
                    return ""
            except Exception:
                pass
            return ent
        cleaned = re.sub(r'&#x?[0-9a-fA-F]+;', repl, text)
        return cleaned.encode("utf-8", errors="ignore")

    # Step 2: Fetch the entire Ledgers list from Tally
    ledger_xml = """<ENVELOPE>
        <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>Export Data</TALLYREQUEST>
            <TYPE>Collection</TYPE>
            <ID>Ledger</ID>
        </HEADER>
        <BODY>
            <DESC>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </DESC>
        </BODY>
    </ENVELOPE>"""
    try:
        r = requests.post(tally_url, data=ledger_xml, timeout=8)
        if r.status_code != 200:
            return jsonify({"success": False, "message": f"Tally server responded with error code {r.status_code}."}), 400
        
        root = ET.fromstring(clean_tally_xml(r.content))
        ledgers = []
        
        # Parse ledger names in Tally's standard response
        for ledger_el in root.findall(".//LEDGER"):
            name = ledger_el.get("NAME") or ledger_el.findtext("NAME")
            if name:
                ledgers.append(name.strip())
                
        # Fallback check
        if not ledgers:
            for name_el in root.findall(".//NAME"):
                if name_el.text:
                    ledgers.append(name_el.text.strip())
                    
        ledgers = sorted(list(set(ledgers)))
        
        if not ledgers:
            return jsonify({"success": False, "message": f"Connected to Tally, but no ledgers were found in the active company '{company_name}'."}), 400
            
        # Step 3: Save results to local disk cache folder
        safe_company_name = re.sub(r'[\\/*?:"<>|]', "", company_name).strip()
        user_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
        companies_dir = os.path.join(user_dir, "tally_companies", safe_company_name)
        os.makedirs(companies_dir, exist_ok=True)
        
        cache_path = os.path.join(companies_dir, "tally_ledger_cache.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({
                "company_name": company_name,
                "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "ledgers": ledgers
            }, f, indent=4)
            
        return jsonify({
            "success": True,
            "message": f"Successfully synced {len(ledgers)} ledgers for company '{company_name}'!",
            "company_name": company_name,
            "ledgers": ledgers
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False, 
            "message": f"Could not connect to Tally Prime. Please ensure Tally Prime is running and local server is enabled on port 9000. Error: {str(e)}"
        }), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Tally synchronization failed: {str(e)}"}), 500


@routes_bp.route("/api/tally/companies", methods=["GET"])
def api_tally_companies():
    try:
        user_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
        companies_dir = os.path.join(user_dir, "tally_companies")
        if not os.path.exists(companies_dir):
            return jsonify({"success": True, "companies": []})
            
        companies = []
        for item in os.listdir(companies_dir):
            item_path = os.path.join(companies_dir, item)
            if os.path.isdir(item_path):
                cache_file = os.path.join(item_path, "tally_ledger_cache.json")
                if os.path.exists(cache_file):
                    import json
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)
                            companies.append({
                                "safe_name": item,
                                "display_name": cache_data.get("company_name", item),
                                "last_sync": cache_data.get("last_sync", "")
                            })
                    except Exception:
                        companies.append({
                            "safe_name": item,
                            "display_name": item,
                            "last_sync": ""
                        })
        return jsonify({"success": True, "companies": companies})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@routes_bp.route("/api/tally/company/<company_name>/ledgers", methods=["GET"])
def api_tally_company_ledgers(company_name):
    try:
        import re
        import json
        safe_company_name = re.sub(r'[\\/*?:"<>|]', "", company_name).strip()
        user_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
        cache_path = os.path.join(user_dir, "tally_companies", safe_company_name, "tally_ledger_cache.json")
        
        if not os.path.exists(cache_path):
            return jsonify({"success": False, "message": f"Company '{company_name}' is not in local cache."}), 404
            
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            
        return jsonify({
            "success": True,
            "company_name": cache_data.get("company_name"),
            "last_sync": cache_data.get("last_sync"),
            "ledgers": cache_data.get("ledgers", [])
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@routes_bp.route("/api/tally/vouchers", methods=["POST"])
def api_tally_vouchers():
    try:
        data = request.get_json() or {}
        company_name = data.get("company_name", "").strip()
        bank_name = data.get("bank_name", "").strip().upper()
        from_date = data.get("from_date", "").strip()
        to_date = data.get("to_date", "").strip()
        
        if not company_name:
            return jsonify({"success": False, "message": "Company Name is required."}), 400
        if not from_date or not to_date:
            return jsonify({"success": False, "message": "From and To dates are required."}), 400
            
        tally_url = "http://localhost:9000"
        
        # Convert YYYY-MM-DD to YYYYMMDD
        from_date_tally = from_date.replace("-", "")
        to_date_tally = to_date.replace("-", "")
        
        def clean_tally_xml(content_bytes):
            text = content_bytes.decode("utf-8", errors="ignore")
            def repl(match):
                ent = match.group(0)
                try:
                    if ent.startswith("&#x"):
                        v = int(ent[3:-1], 16)
                    else:
                        v = int(ent[2:-1])
                    if v < 32 and v not in (9, 10, 13):
                        return ""
                except Exception:
                    pass
                return ent
            cleaned = re.sub(r'&#x?[0-9a-fA-F]+;', repl, text)
            return cleaned.encode("utf-8", errors="ignore")

        xml_request = f"""<ENVELOPE>
            <HEADER>
                <VERSION>1</VERSION>
                <TALLYREQUEST>Export Data</TALLYREQUEST>
                <TYPE>Collection</TYPE>
                <ID>VoucherDuplicateCheckCollection</ID>
                <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
            </HEADER>
            <BODY>
                <DESC>
                    <STATICVARIABLES>
                        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        <SVFROMDATE TYPE="Date">{from_date_tally}</SVFROMDATE>
                        <SVTODATE TYPE="Date">{to_date_tally}</SVTODATE>
                    </STATICVARIABLES>
                    <TDL>
                        <TDLMESSAGE>
                            <COLLECTION NAME="VoucherDuplicateCheckCollection" ISMODIFY="No">
                                <TYPE>Voucher</TYPE>
                                <FETCH>DATE, VOUCHERNUMBER, VOUCHERTYPENAME, NARRATION, ALLLEDGERENTRIES</FETCH>
                            </COLLECTION>
                        </TDLMESSAGE>
                    </TDL>
                </DESC>
            </BODY>
        </ENVELOPE>"""

        r = requests.post(tally_url, data=xml_request, timeout=12)
        if r.status_code != 200:
            return jsonify({"success": False, "message": f"Tally server responded with status {r.status_code}."}), 400
            
        root = ET.fromstring(clean_tally_xml(r.content))
        vouchers = root.findall(".//VOUCHER")
        
        parsed_vouchers = []
        for vch in vouchers:
            vch_no = vch.findtext("VOUCHERNUMBER", "").strip()
            date_val = vch.findtext("DATE", "").strip()
            vch_type = vch.findtext("VOUCHERTYPENAME", "").strip()
            narration = vch.findtext("NARRATION", "").strip()
            
            # Skip invalid/empty vouchers
            if not vch_no and not date_val:
                continue
                
            entries = vch.findall(".//ALLLEDGERENTRIES.LIST") + vch.findall(".//LEDGERENTRIES.LIST")
            
            # Find the bank entry matching our filter or a general pattern
            bank_entry = None
            party_entries = []
            has_requested_bank = False
            
            for ent_el in entries:
                ledger_name = ent_el.findtext("LEDGERNAME", "").strip()
                amount_str = ent_el.findtext("AMOUNT", "0").strip()
                is_pos = ent_el.findtext("ISDEEMEDPOSITIVE", "Yes").strip()
                
                try:
                    amt = abs(float(amount_str))
                except ValueError:
                    amt = 0.0
                    
                is_bank_pattern = bool(re.search(r'bank|sbi|bob|axis|cash|hdfc|icici|tmb|idbi|pnb', ledger_name, re.I))
                
                is_target_bank = False
                if bank_name:
                    is_target_bank = (ledger_name.upper() == bank_name)
                    if is_target_bank:
                        has_requested_bank = True
                
                if (is_target_bank or is_bank_pattern) and not bank_entry:
                    bank_entry = {
                        "ledger": ledger_name,
                        "amount": amt,
                        "is_deemed_positive": is_pos
                    }
                else:
                    party_entries.append({
                        "ledger": ledger_name,
                        "amount": amt,
                        "is_deemed_positive": is_pos
                    })
                    
            if bank_name and not has_requested_bank:
                continue
                
            if not bank_entry and entries:
                first_el = entries[0]
                ledger_name = first_el.findtext("LEDGERNAME", "").strip()
                amount_str = first_el.findtext("AMOUNT", "0").strip()
                is_pos = first_el.findtext("ISDEEMEDPOSITIVE", "Yes").strip()
                try:
                    amt = abs(float(amount_str))
                except ValueError:
                    amt = 0.0
                bank_entry = {
                    "ledger": ledger_name,
                    "amount": amt,
                    "is_deemed_positive": is_pos
                }
                party_entries = []
                for ent_el in entries[1:]:
                    l_name = ent_el.findtext("LEDGERNAME", "").strip()
                    a_str = ent_el.findtext("AMOUNT", "0").strip()
                    i_pos = ent_el.findtext("ISDEEMEDPOSITIVE", "Yes").strip()
                    try:
                        a_val = abs(float(a_str))
                    except ValueError:
                        a_val = 0.0
                    party_entries.append({
                        "ledger": l_name,
                        "amount": a_val,
                        "is_deemed_positive": i_pos
                    })
            
            if not bank_entry:
                continue
                
            if len(party_entries) == 1:
                particulars = party_entries[0]["ledger"]
            elif len(party_entries) > 1:
                particulars = ", ".join([p["ledger"] for p in party_entries])
            else:
                particulars = "Suspense"
                
            txn_type = "DEBIT" if bank_entry["is_deemed_positive"] == "Yes" else "CREDIT"
            txn_amount = bank_entry["amount"]
            
            parsed_vouchers.append({
                "vch_no": vch_no,
                "date": date_val,
                "vch_type": vch_type,
                "amount": txn_amount,
                "type": txn_type,
                "narration": narration,
                "particulars": particulars
            })
            
        return jsonify({
            "success": True,
            "company_name": company_name,
            "vouchers": parsed_vouchers
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False, 
            "message": f"Could not connect to Tally Prime. Ensure it is running and local server port 9000 is enabled. Error: {str(e)}"
        }), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Tally query failed: {str(e)}"}), 500


@routes_bp.route("/api/tally/duplicate-history", methods=["GET"])
def api_tally_duplicate_history():
    try:
        user_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
        history_path = os.path.join(user_dir, "duplicate_history.json")
        if not os.path.exists(history_path):
            return jsonify({"success": True, "companies": [], "bank_ledgers": []})
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({
            "success": True,
            "companies": data.get("companies", []),
            "bank_ledgers": data.get("bank_ledgers", [])
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@routes_bp.route("/api/tally/duplicate-history", methods=["POST"])
def api_tally_save_duplicate_history():
    try:
        req_data = request.get_json() or {}
        company = req_data.get("company_name", "").strip()
        bank = req_data.get("bank_name", "").strip()
        
        user_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
        os.makedirs(user_dir, exist_ok=True)
        history_path = os.path.join(user_dir, "duplicate_history.json")
        
        history = {"companies": [], "bank_ledgers": []}
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
                
        if "companies" not in history:
            history["companies"] = []
        if "bank_ledgers" not in history:
            history["bank_ledgers"] = []
            
        updated = False
        if company and company not in history["companies"]:
            history["companies"].append(company)
            updated = True
        if bank and bank not in history["bank_ledgers"]:
            history["bank_ledgers"].append(bank)
            updated = True
            
        if updated:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4)
                
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

