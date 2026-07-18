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
