# routes_base.py
from flask import Blueprint

routes_bp = Blueprint("routes", __name__)

# Global in-memory cache to hold generated file data for download
# Keys: "xml_bank", "xlsx_bank", "xml_cash", "xlsx_cash", "json_gstr1"
FILE_CACHE = {
    "xml_bank": None,
    "xlsx_bank": None,
    "xml_cash": None,
    "xlsx_cash": None,
    "json_gstr1": None,
    "json_hsn": None,
    # Download file names
    "xml_bank_filename": "tally_import.xml",
    "xlsx_bank_filename": "statement_audit_viewer.xlsx",
    "xml_cash_filename": "Ashramam_Cash_Receipts.xml",
    "xlsx_cash_filename": "Tally_Nested_Sheets_Preview.xlsx",
    "json_gstr1_filename": "returns_gstr1.json",
    "json_hsn_filename": "returns_hsn.json"
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
