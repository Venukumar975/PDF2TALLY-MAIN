# import json
# import sys

# from services.pdf_reader import extract_text

# # Importing your existing router functions without changing routers.py
# from parsers.router import route_to_parser, verify_bank_profile

# # Importing standalone opening balance parsers directly to handle the different logic
# from parsers.bob_parser import parse_opening_balance as parse_bob_opening
# from parsers.sbi_parser import parse_opening_balance as parse_sbi_opening

# # ─── 1. INTERACTIVE BANK SELECTION ──────────────────────────────────
# print("\n==================================================")
# print("          BANK STATEMENT IMPORT TOOL")
# print("==================================================")
# print("Select the bank profile to process:")
# print("1. Bank of Baroda (BOB)")
# print("2. State Bank of India (SBI)")
# choice = input("Enter option number (1 or 2): ").strip()

# if choice == "1":
#     selected_bank = "Bank of Baroda (BOB)"
#     BANK_LEDGER = "BANK OF BARODA"
#     parse_opening_func = parse_bob_opening
#     PDF_PATH = "uploads/131-1.pdf"  # Default test path for BoB
# elif choice == "2":
#     selected_bank = "State Bank of India (SBI)"
#     BANK_LEDGER = "STATE BANK OF INDIA"
#     parse_opening_func = parse_sbi_opening
#     PDF_PATH = "uploads/sbi_statement.pdf"  # Default test path for SBI
# else:
#     print("❌ Invalid option. Exiting execution loop.")
#     sys.exit(1)

# OUTPUT_XML_PATH = f"outputs/{choice}_tally_import.xml"
# OUTPUT_REPORT_PATH = f"outputs/{choice}_validation_report.json"
# OUTPUT_XLSX_PATH = f"outputs/{choice}_tally_view_accounting.xlsx"
# SUSPENSE_LEDGER = "Suspense"

# # ─── 2. READ RAW TEXT LAYER ─────────────────────────────────────────
# print(f"\n📖 Extracting text layer from: {PDF_PATH}...")
# extracted_text = extract_text(PDF_PATH)

# # Safety Gate: Use your router's verification logic to double-check keywords
# if not verify_bank_profile(selected_bank, extracted_text):
#     print(f"\n⚠️ WARNING: The text layout doesn't match the signature of: {selected_bank}")
#     confirm = input("Do you want to proceed anyway? (y/n): ").strip().lower()
#     if confirm != 'y':
#         print("❌ Operation cancelled by user.")
#         sys.exit(0)

# # ─── 3. EXECUTE TARGET PARSING FLOWS ────────────────────────────────
# print(f"⚙️ Running dynamic parsing modules for {selected_bank}...")

# # Extract opening balance dynamically using our local selection assignment
# opening_bal = parse_opening_func(extracted_text)

# # Route to transaction parser through routers.py (safely intact for Streamlit!)
# transactions = route_to_parser(selected_bank, extracted_text)

# # ─── 4. DOWNSTREAM PROCESSING PIPELINES ─────────────────────────────
# from services.xml_generator import generate_tally_xml
# from services.statement_validator import build_validation_report
# from services.xlsx_viewer import export_xml_audit_workbook

# print("🧱 Building Tally-compliant structural XML models...")
# xml_text = generate_tally_xml(
#     transactions,
#     OUTPUT_XML_PATH,
#     bank_ledger=BANK_LEDGER,
#     suspense_ledger=SUSPENSE_LEDGER,
#     opening_balance=opening_bal
# )

# print("📝 Compiling math alignment audit report profiles...")
# validation_report = build_validation_report(
#     extracted_text,
#     transactions,
#     xml_text,
#     BANK_LEDGER,
#     SUSPENSE_LEDGER,
# )

# with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as report_file:
#     json.dump(validation_report, report_file, indent=2)

# print("📊 Generating spreadsheet transaction history matrices...")
# export_xml_audit_workbook(
#     xml_text,
#     OUTPUT_XLSX_PATH,
#     bank_ledger=BANK_LEDGER,
#     suspense_ledger=SUSPENSE_LEDGER,
# )

# # ─── 5. TERMINAL METRICS REPORTING ──────────────────────────────────
# print("\n" + "="*50)
# print(f"      TELEMETRY SUMMARY FOR: {selected_bank}")
# print("="*50)
# print("Transactions Processed:           ", len(transactions))
# print("Assigned Bank Ledger:             ", BANK_LEDGER)
# print("XML Output Path:                  ", OUTPUT_XML_PATH)
# print("Spreadsheet Output Path:          ", OUTPUT_XLSX_PATH)
# print("-"*50)

# statement_validation = validation_report["statement"]
# xml_validation = validation_report["xml"]
# comparison_validation = validation_report["comparison"]

# print("Statement Opening Balance:        ", statement_validation["opening_balance"])
# print("Statement Closing Balance:        ", statement_validation["closing_balance"])
# print("Total Book Receipts (Debits):     ", statement_validation["debit_total"])
# print("Total Book Payments (Credits):    ", statement_validation["credit_total"])
# print("Is System Math Reconciled:        ", "✅ YES" if statement_validation["is_reconciled"] else "❌ NO")
# print("Row Mismatches / Errors Found:    ", statement_validation["balance_movement_error_count"])
# print("XML Voucher Count Generated:      ", xml_validation["voucher_count"])
# print("Voucher Count Match Verification: ", "✅ MATCHED" if xml_validation["voucher_count_matches"] else "❌ MISMATCHED")
# print("Voucher Amount Sum Match:         ", "✅ MATCHED" if xml_validation["voucher_amount_total_matches"] else "❌ MISMATCHED")
# print("Monthly Bucket Mismatches:        ", comparison_validation["monthly_mismatch_count"])
# print("="*50 + "\n")

# if statement_validation["balance_movement_errors"]:
#     print("❌ Parallel Matching Failures / Mismatches (First 10):")
#     for error in statement_validation["balance_movement_errors"]:
#         print(f"  - Row Index {error['index']} on Date {error['gl_date']}: Amount {error['amount']} "
#               f"mismatched between PDF ({error['previous_balance']}) and XML ({error['current_balance']}).")
#     print()

import json
import sys

from services.pdf_reader import extract_text
from parsers.router import route_to_parser, verify_bank_profile

# Standalone Opening Balance Parsers
from parsers.bob_parser import parse_opening_balance as parse_bob_opening
from parsers.sbi_parser import parse_opening_balance as parse_sbi_opening

# Dynamic Modular Strategies
from strategies import WholeChunk, FirstChunk, ContinuationChunk

# ─── 1. INTERACTIVE BANK SELECTION ──────────────────────────────────
print("\n==================================================")
print("          BANK STATEMENT IMPORT TOOL")
print("==================================================")
print("Select the bank profile to process:")
print("1. Bank of Baroda (BOB)")
print("2. State Bank of India (SBI)")
choice = input("Enter option number (1 or 2): ").strip()

if choice == "1":
    selected_bank = "Bank of Baroda (BOB)"
    BANK_LEDGER = "BANK OF BARODA"
    parse_opening_func = parse_bob_opening
    PDF_PATH = "uploads/131-1.pdf"
elif choice == "2":
    selected_bank = "State Bank of India (SBI)"
    BANK_LEDGER = "STATE BANK OF INDIA"
    parse_opening_func = parse_sbi_opening
    PDF_PATH = "uploads/sbi_statement.pdf"
else:
    print("❌ Invalid option. Exiting execution loop.")
    sys.exit(1)

# ─── 2. READ RAW TEXT LAYER ─────────────────────────────────────────
print(f"\n📖 Extracting text layer from: {PDF_PATH}...")
extracted_text = extract_text(PDF_PATH)

if not verify_bank_profile(selected_bank, extracted_text):
    print(f"\n⚠️ WARNING: The text layout doesn't match the signature of: {selected_bank}")
    confirm = input("Do you want to proceed anyway? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Operation cancelled by user.")
        sys.exit(0)

# ─── 3. STRATEGY SELECTION ──────────────────────────────────────────
print("\n" + "-"*50)
print("            STATEMENT CHUNK INGESTION STRATEGY")
print("-"*50)
print("How should this PDF be handled?")
print("1. Whole Document (Full complete standalone tracking timeline)")
print("2. First Chunk (First block of a split statement series)")
print("3. Next Chunk / Continuity Continuation Block (Overlapping data extension)")
strategy = input("Select Ingestion Strategy option (1, 2, or 3): ").strip()

# Route dynamically to the selected script object model
if strategy == "1":
    sanitized_text, opening_bal = WholeChunk.process_strategy(extracted_text, parse_opening_func)
elif strategy == "2":
    sanitized_text, opening_bal = FirstChunk.process_strategy(extracted_text, parse_opening_func)
elif strategy == "3":
    sanitized_text, opening_bal = ContinuationChunk.process_strategy(extracted_text, parse_opening_func)
else:
    print("❌ Invalid strategy profile option selected. Exiting pipeline loop.")
    sys.exit(1)

# ─── 4. RUN ALL PARSING AND DOWNSTREAM PIPELINES ────────────────────
print(f"\n⚙️ Running dynamic parsing modules for {selected_bank}...")
transactions = route_to_parser(selected_bank, sanitized_text)

OUTPUT_XML_PATH = f"outputs/{choice}_tally_import.xml"
OUTPUT_REPORT_PATH = f"outputs/{choice}_validation_report.json"
OUTPUT_XLSX_PATH = f"outputs/{choice}_tally_view_accounting.xlsx"
SUSPENSE_LEDGER = "Suspense"

from services.xml_generator import generate_tally_xml
from services.statement_validator import build_validation_report
from services.xlsx_viewer import export_xml_audit_workbook

print("🧱 Building Tally-compliant structural XML models...")
xml_text = generate_tally_xml(
    transactions,
    OUTPUT_XML_PATH,
    bank_ledger=BANK_LEDGER,
    suspense_ledger=SUSPENSE_LEDGER,
    opening_balance=opening_bal
)

print("📝 Compiling math alignment audit report profiles...")
validation_report = build_validation_report(
    sanitized_text,
    transactions,
    xml_text,
    BANK_LEDGER,
    SUSPENSE_LEDGER,
)

with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as report_file:
    json.dump(validation_report, report_file, indent=2)

print("📊 Generating spreadsheet transaction history matrices...")
export_xml_audit_workbook(
    xml_text,
    OUTPUT_XLSX_PATH,
    bank_ledger=BANK_LEDGER,
    suspense_ledger=SUSPENSE_LEDGER,
)

# ─── 5. TERMINAL DASHBOARD TELEMETRY REPORTING ──────────────────────
print("\n" + "="*50)
print(f"      TELEMETRY SUMMARY FOR: {selected_bank}")
print("="*50)
print("Transactions Processed:           ", len(transactions))
print("Assigned Bank Ledger:             ", BANK_LEDGER)
print("XML Output Path:                  ", OUTPUT_XML_PATH)
print("Spreadsheet Output Path:          ", OUTPUT_XLSX_PATH)
print("-"*50)

statement_validation = validation_report["statement"]
xml_validation = validation_report["xml"]

print("Statement Opening Balance:        ", statement_validation["opening_balance"])
print("Statement Closing Balance:        ", statement_validation["closing_balance"])
print("Statement Opening Balance Entered:", "SUPPRESSED (None)" if opening_bal is None else opening_bal)
print("Total Book Receipts (Debits):     ", statement_validation["debit_total"])
print("Total Book Payments (Credits):    ", statement_validation["credit_total"])
print("Is System Math Reconciled:        ", "✅ YES" if statement_validation["is_reconciled"] else "❌ NO")
print("Row Mismatches / Errors Found:    ", statement_validation["balance_movement_error_count"])
print("XML Voucher Count Generated:      ", xml_validation["voucher_count"])
print("Voucher Count Match Verification: ", "✅ MATCHED" if xml_validation["voucher_count_matches"] else "❌ MISMATCHED")
print("Voucher Amount Sum Match:         ", "✅ MATCHED" if xml_validation["voucher_amount_total_matches"] else "❌ MISMATCHED")
print("="*50 + "\n")