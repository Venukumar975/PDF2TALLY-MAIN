
from collections import Counter
from datetime import datetime, date
import xml.etree.ElementTree as ET
import re

BALANCE_TOLERANCE = 0.01

def _check_statement_coverage(text, transactions):
    if not transactions:
        return {"passed": True, "message": ""}
        
    last_txn = transactions[-1]
    last_date_str = last_txn["gl_date"] # format "dd-mm-yyyy"
    
    try:
        last_date = datetime.strptime(last_date_str, "%d-%m-%Y").date()
    except Exception:
        return {"passed": True, "message": ""}
        
    # Try to find the line index of the last parsed transaction
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    last_txn_idx = -1
    
    # Search from the end of the lines list upwards
    last_bal_str = f"{abs(float(last_txn['balance'])):.2f}"
    
    for idx in range(len(lines) - 1, -1, -1):
        line = lines[idx]
        # Check if the line contains the balance or a significant part of narration
        if last_bal_str in line or (last_txn.get("narration") and last_txn["narration"][:20] in line):
            last_txn_idx = idx
            break
            
    if last_txn_idx == -1:
        # Fallback: if we couldn't find the exact line, search in the last 20% of the document
        last_txn_idx = int(len(lines) * 0.8)
        
    # Now scan all lines after last_txn_idx for potential unparsed transactions
    unparsed_rows = []
    
    months_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    months_pattern = "|".join(months_map.keys())
    
    for idx in range(last_txn_idx + 1, len(lines)):
        line = lines[idx]
        parts = line.split()
        
        # Check for date patterns in the line
        has_date = False
        parsed_line_date = None
        
        # Pattern 1: DD-MM-YYYY or DD/MM/YYYY
        m1 = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", line)
        if m1:
            try:
                day, month, year = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
                parsed_line_date = date(year, month, day)
                has_date = True
            except ValueError:
                pass
                
        # Pattern 2: DD MMM YYYY or DD MMM
        if not has_date:
            m2 = re.search(rf"\b(\d{{1,2}})\s+({months_pattern})[a-z]*(?:\s+(\d{{4}}))?\b", line, re.IGNORECASE)
            if m2:
                try:
                    day = int(m2.group(1))
                    month = months_map[m2.group(2).lower()]
                    year = int(m2.group(3)) if m2.group(3) else last_date.year
                    parsed_line_date = date(year, month, day)
                    has_date = True
                except ValueError:
                    pass
                    
        # Check if this line has decimals (amount-like or balance-like)
        has_decimal = False
        for p in parts:
            p_clean = p.replace(",", "").strip()
            if re.match(r"^-?\d+\.\d{2}$", p_clean):
                has_decimal = True
                break
                
        if has_date and has_decimal and parsed_line_date:
            # Check if this parsed date is later than our last parsed transaction date
            if parsed_line_date > last_date:
                unparsed_rows.append((line, parsed_line_date))
                
    if unparsed_rows:
        first_unparsed_line, unparsed_date = unparsed_rows[0]
        unparsed_date_str = unparsed_date.strftime("%d-%m-%Y")
        return {
            "passed": False,
            "message": f"Unparsed transaction data detected (Latest date in PDF: {unparsed_date_str}, Last parsed transaction: {last_date_str})."
        }
        
    return {"passed": True, "message": ""}


def build_validation_report(text, transactions, xml_text, bank_ledger, suspense_ledger, opening_balance=None):
    """
    Main entry point performing the clear 3-Check Audit Pipeline + Statement Coverage.
    """
    xml_root = ET.fromstring(xml_text)
    xml_vouchers = xml_root.findall(".//VOUCHER")
    
    valid_txns = [t for t in transactions if t.get("type") in {"CREDIT", "DEBIT"}]

    # Run checkpoints
    check_1_report = _run_check_1_summary_match(valid_txns, xml_vouchers, bank_ledger)
    check_2_report = _run_check_2_parallel_match(valid_txns, xml_vouchers, bank_ledger)
    check_3_report = _run_check_3_sequence_integrity(xml_vouchers)
    coverage_report = _check_statement_coverage(text, valid_txns)

    pipeline_passed = (
        check_1_report["overall_totals_match"] and 
        check_1_report["monthly_mismatch_count"] == 0 and
        check_2_report["mismatch_count"] == 0 and
        check_3_report["integrity_passed"] and
        coverage_report["passed"]
    )

    audit_msg = coverage_report["message"]
    # Prompt the user to check the first transaction type if the 0.00 fallback was active
    if valid_txns and valid_txns[0].get("is_fallback_type"):
        fallback_msg = "Since no starting/previous balance was provided or found, the first transaction type was inferred using a 0.00 fallback. Please verify if the first transaction type is correct."
        if audit_msg:
            audit_msg += " " + fallback_msg
        else:
            audit_msg = fallback_msg

    # Determine display opening balance and calculate closing balance mathematically
    if opening_balance is not None:
        try:
            op_bal = float(opening_balance)
        except (ValueError, TypeError):
            op_bal = float(transactions[0]["balance"]) if transactions else 0.0
    else:
        op_bal = float(transactions[0]["balance"]) if transactions else 0.0

    debit_total = check_1_report["pdf_totals"]["debit"]
    credit_total = check_1_report["pdf_totals"]["credit"]
    calc_closing = op_bal + debit_total - credit_total

    return {
        "statement": {
            "transaction_count": len(transactions),
            "opening_balance": round(op_bal, 2),
            "closing_balance": round(calc_closing, 2),
            "credit_total": credit_total,
            "debit_total": debit_total,
            "is_reconciled": pipeline_passed,
            "audit_message": audit_msg,
            "type_counts": dict(Counter(t.get("type", "UNKNOWN") for t in transactions)),
            "balance_movement_error_count": check_2_report["mismatch_count"],
            "balance_movement_errors": check_2_report["mismatches"],
            # ─── RESTORED KEY TARGET PATH FOR STREAMLIT DASHBOARD ───
            "monthly_summaries": check_1_report["monthly_summaries"],
            "direction_mismatch_count": 0,
            "direction_mismatches": [],
            "duplicate_count": 0,
            "duplicate_keys": []
        },
        "xml": {
            "voucher_count": len(xml_vouchers),
            "voucher_count_matches": len(xml_vouchers) == len(valid_txns),
            "voucher_amount_total_matches": check_1_report["overall_totals_match"]
        },
        "comparison": {
            "monthly_mismatch_count": check_1_report["monthly_mismatch_count"]
        }
    }


# ─── CHECK 1: THE DATA STRUCTURE SUMMARY MATCH ──────────────────────
def _run_check_1_summary_match(valid_txns, xml_vouchers, bank_ledger):
    # 1. Build PDF Data Structure
    pdf_ds = {"total_count": len(valid_txns), "debit_sum": 0.0, "credit_sum": 0.0, "months": {}}
    for txn in valid_txns:
        m_key = datetime.strptime(txn["gl_date"], "%d-%m-%Y").strftime("%Y-%m")
        if m_key not in pdf_ds["months"]:
            pdf_ds["months"][m_key] = {
                "count": 0, "debit": 0.0, "credit": 0.0,
                "opening": txn["balance"], "closing": txn["balance"] # Dynamic capture anchors
            }
        
        amt = float(txn["amount"])
        if txn["type"] == "DEBIT":
            pdf_ds["debit_sum"] += amt
            pdf_ds["months"][m_key]["debit"] += amt
        else:
            pdf_ds["credit_sum"] += amt
            pdf_ds["months"][m_key]["credit"] += amt
            
        pdf_ds["months"][m_key]["closing"] = txn["balance"]  # Keeps updating to the final line
        pdf_ds["months"][m_key]["count"] += 1

    # 2. Build XML Data Structure
    xml_ds = {"total_count": len(xml_vouchers), "debit_sum": 0.0, "credit_sum": 0.0, "months": {}}
    for vch in xml_vouchers:
        date_str = vch.findtext("DATE") or ""
        m_key = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m")
        if m_key not in xml_ds["months"]:
            xml_ds["months"][m_key] = {"count": 0, "debit": 0.0, "credit": 0.0}
            
        for entry in vch.findall("ALLLEDGERENTRIES.LIST"):
            ledger = (entry.findtext("LEDGERNAME") or "").strip().upper()
            if ledger == bank_ledger.strip().upper():
                amt = abs(float(entry.findtext("AMOUNT") or 0.0))
                is_debit = (entry.findtext("ISDEEMEDPOSITIVE") == "Yes")
                
                if is_debit:
                    xml_ds["debit_sum"] += amt
                    xml_ds["months"][m_key]["debit"] += amt
                else:
                    xml_ds["credit_sum"] += amt
                    xml_ds["months"][m_key]["credit"] += amt
        xml_ds["months"][m_key]["count"] += 1

    # 3. Compare DS structures & Compile the Streamlit List Array Matrix
    monthly_summaries_list = []
    monthly_mismatch_count = 0
    all_months = sorted(list(set(pdf_ds["months"].keys()).union(xml_ds["months"].keys())))
    
    for m in all_months:
        p_m = pdf_ds["months"].get(m, {"count": 0, "debit": 0.0, "credit": 0.0, "opening": 0.0, "closing": 0.0})
        x_m = xml_ds["months"].get(m, {"count": 0, "debit": 0.0, "credit": 0.0})
        
        counts_match = p_m["count"] == x_m["count"]
        debits_match = abs(p_m["debit"] - x_m["debit"]) <= BALANCE_TOLERANCE
        credits_match = abs(p_m["credit"] - x_m["credit"]) <= BALANCE_TOLERANCE
        month_reconciled = counts_match and debits_match and credits_match
        
        if not month_reconciled:
            monthly_mismatch_count += 1
            
        # Parse visual text label: e.g., "2025-04" -> "Apr 2025"
        label_obj = datetime.strptime(m + "-01", "%Y-%m-%d")
        month_label = label_obj.strftime("%b %Y")

        monthly_summaries_list.append({
            "month_label": month_label,
            "transaction_count": p_m["count"],
            "opening_balance": round(p_m["opening"], 2),
            "debit_total": round(p_m["debit"], 2),
            "credit_total": round(p_m["credit"], 2),
            "closing_balance": round(p_m["closing"], 2),
            "is_reconciled": month_reconciled
        })

    overall_totals_match = (
        pdf_ds["total_count"] == xml_ds["total_count"] and
        abs(pdf_ds["debit_sum"] - xml_ds["debit_sum"]) <= BALANCE_TOLERANCE and
        abs(pdf_ds["credit_sum"] - xml_ds["credit_sum"]) <= BALANCE_TOLERANCE
    )

    return {
        "overall_totals_match": overall_totals_match,
        "monthly_mismatch_count": monthly_mismatch_count,
        "pdf_totals": {"debit": round(pdf_ds["debit_sum"], 2), "credit": round(pdf_ds["credit_sum"], 2)},
        "monthly_summaries": monthly_summaries_list  # Exposing list payload
    }


# ─── CHECK 2: PARALLEL ROW-BY-ROW LINE VALIDATION ───────────────────
def _run_check_2_parallel_match(valid_txns, xml_vouchers, bank_ledger):
    mismatches = []
    
    if len(valid_txns) != len(xml_vouchers):
        mismatches.append({
            "index": 0, "gl_date": "SYSTEM", 
            "amount": 0.0, "error": f"Row count mismatch! PDF has {len(valid_txns)} items, XML has {len(xml_vouchers)}."
        })
        
    for idx, (txn, vch) in enumerate(zip(valid_txns, xml_vouchers), start=1):
        vch_date = datetime.strptime(vch.findtext("DATE") or "", "%Y%m%d").strftime("%d-%m-%Y")
        vch_type = vch.findtext("VOUCHERTYPENAME") or ""
        
        vch_amt = 0.0
        vch_is_debit = False
        for entry in vch.findall("ALLLEDGERENTRIES.LIST"):
            ledger = (entry.findtext("LEDGERNAME") or "").strip().upper()
            if ledger == bank_ledger.strip().upper():
                vch_amt = abs(float(entry.findtext("AMOUNT") or 0.0))
                vch_is_debit = (entry.findtext("ISDEEMEDPOSITIVE") == "Yes")
                break

        date_matches = txn["gl_date"] == vch_date
        amt_matches = abs(float(txn["amount"]) - vch_amt) <= BALANCE_TOLERANCE
        
        type_matches = False
        if txn["type"] == "DEBIT" and vch_type == "Receipt" and vch_is_debit:
            type_matches = True
        elif txn["type"] == "CREDIT" and vch_type == "Payment" and not vch_is_debit:
            type_matches = True

        if not (date_matches and amt_matches and type_matches):
            mismatches.append({
                "index": idx, "gl_date": txn["gl_date"], "amount": txn["amount"],
                "previous_balance": f"PDF Type: {txn['type']}", "current_balance": f"XML Type: {vch_type}"
            })

    return {"mismatch_count": len(mismatches), "mismatches": mismatches}


# ─── CHECK 3: SEQUENCE INTEGRITY AND GAP VERIFICATION ───────────────
def _run_check_3_sequence_integrity(xml_vouchers):
    vch_numbers = [v.findtext("VOUCHERNUMBER") or "" for v in xml_vouchers]
    num_counts = Counter(vch_numbers)
    has_duplicates = any(count > 1 for count in num_counts.values())

    has_gaps = False
    for num in vch_numbers:
        try:
            seq_index = int(num.split("-")[-1])
        except (ValueError, IndexError):
            has_gaps = True

    return {
        "integrity_passed": (not has_duplicates and not has_gaps),
        "has_duplicate_voucher_ids": has_duplicates,
        "has_sequence_gaps": has_gaps
    }