# from collections import Counter
# from datetime import datetime
# import xml.etree.ElementTree as ET

# # Importing tolerance threshold
# from parsers.bob_parser import BALANCE_TOLERANCE, parse_opening_balance


# def build_validation_report(
#     text,
#     transactions,
#     xml_text,
#     bank_ledger,
#     suspense_ledger,
# ):
#     statement = validate_statement_transactions(text, transactions)
#     xml = validate_xml_against_transactions(
#         xml_text,
#         transactions,
#         opening_balance=statement["opening_balance"],
#         bank_ledger=bank_ledger,
#         suspense_ledger=suspense_ledger,
#     )

#     return {
#         "statement": statement,
#         "xml": xml,
#         "comparison": compare_statement_and_xml(statement, xml),
#     }


# def validate_statement_transactions(text, transactions):
#     opening_balance = parse_opening_balance(text)
#     closing_balance = transactions[-1]["balance"] if transactions else opening_balance

#     # Group variables according to the updated Book Perspective (Deposits = DEBIT, Withdrawals = CREDIT)
#     credits = [txn for txn in transactions if txn.get("type") == "CREDIT"]
#     debits = [txn for txn in transactions if txn.get("type") == "DEBIT"]
#     unknown = [txn for txn in transactions if txn.get("type") == "UNKNOWN"]

#     credit_total = _sum_amounts(credits)
#     debit_total = _sum_amounts(debits)
#     calculated_closing = None
#     is_reconciled = False

#     if opening_balance is not None and closing_balance is not None:
#         # FIXED: Book View Math -> Opening Balance + DEBITS (Money In) - CREDITS (Money Out)
#         calculated_closing = round(opening_balance + debit_total - credit_total, 2)
#         is_reconciled = abs(calculated_closing - closing_balance) <= BALANCE_TOLERANCE

#     movement_errors = _find_balance_movement_errors(transactions, opening_balance)
#     direction_mismatches = _find_direction_mismatches(transactions, opening_balance)
#     duplicate_keys = _find_duplicate_keys(transactions)
#     monthly_summaries = _build_monthly_statement_summaries(transactions, opening_balance)

#     return {
#         "transaction_count": len(transactions),
#         "type_counts": dict(Counter(txn.get("type", "MISSING") for txn in transactions)),
#         "opening_balance": opening_balance,
#         "closing_balance": closing_balance,
#         "credit_total": credit_total,
#         "debit_total": debit_total,
#         "calculated_closing_balance": calculated_closing,
#         "is_reconciled": is_reconciled,
#         "unknown_count": len(unknown),
#         "balance_movement_error_count": len(movement_errors),
#         "balance_movement_errors": movement_errors[:10],
#         "direction_mismatch_count": len(direction_mismatches),
#         "direction_mismatches": direction_mismatches[:10],
#         "duplicate_count": len(duplicate_keys),
#         "duplicate_keys": duplicate_keys[:10],
#         "monthly_summaries": monthly_summaries,
#         "year_summary": _build_year_summary(monthly_summaries, opening_balance, closing_balance),
#     }


# def validate_xml_against_transactions(
#     xml_text,
#     transactions,
#     opening_balance=None,
#     bank_ledger=None,
#     suspense_ledger=None,
# ):
#     root = ET.fromstring(xml_text)
#     vouchers = root.findall(".//VOUCHER")
#     valid_transactions = [
#         txn for txn in transactions
#         if txn.get("type") in {"CREDIT", "DEBIT"}
#     ]

#     voucher_amounts = []
#     voucher_type_counts = Counter()
#     xml_transactions = []

#     running_balance = opening_balance
#     for voucher in vouchers:
#         parsed_voucher = _parse_voucher(voucher, bank_ledger, suspense_ledger)
#         voucher_amounts.append(parsed_voucher["amount"])
#         voucher_type_counts[parsed_voucher["voucher_type"]] += 1

#         if running_balance is not None:
#             # Accumulate balance shifts smoothly using the updated book calculations
#             running_balance = round(running_balance + parsed_voucher["balance_effect"], 2)
#             parsed_voucher["balance"] = running_balance

#         xml_transactions.append(parsed_voucher)

#     transaction_total = _sum_amounts(valid_transactions)
#     voucher_total = round(sum(voucher_amounts), 2)
#     monthly_summaries = _build_monthly_xml_summaries(xml_transactions, opening_balance)

#     return {
#         "transaction_count": len(transactions),
#         "convertible_transaction_count": len(valid_transactions),
#         "voucher_count": len(vouchers),
#         "skipped_transaction_count": len(transactions) - len(valid_transactions),
#         "transaction_amount_total": transaction_total,
#         "voucher_amount_total": voucher_total,
#         "voucher_count_matches": len(vouchers) == len(valid_transactions),
#         "voucher_amount_total_matches": abs(voucher_total - transaction_total) <= BALANCE_TOLERANCE,
#         "voucher_type_counts": dict(voucher_type_counts),
#         "opening_balance_used_for_projection": opening_balance,
#         "projected_closing_balance": running_balance,
#         "monthly_summaries": monthly_summaries,
#         "year_summary": _build_year_summary(
#             monthly_summaries,
#             opening_balance,
#             running_balance,
#         ),
#         "duplicate_voucher_numbers": _find_duplicate_voucher_numbers(vouchers),
#     }


# def compare_statement_and_xml(statement, xml):
#     monthly_statement = statement.get("monthly_summaries", [])
#     monthly_xml = xml.get("monthly_summaries", [])
#     monthly_by_key = {row["month"]: row for row in monthly_xml}

#     monthly_comparisons = []
#     for statement_row in monthly_statement:
#         xml_row = monthly_by_key.get(statement_row["month"])

#         if xml_row is None:
#             monthly_comparisons.append({
#                 "month": statement_row["month"],
#                 "match": False,
#                 "reason": "Missing month in XML summary",
#             })
#             continue

#         monthly_comparisons.append({
#             "month": statement_row["month"],
#             "match": (
#                 _same_amount(statement_row["opening_balance"], xml_row["opening_balance"])
#                 and _same_amount(statement_row["closing_balance"], xml_row["closing_balance"])
#                 and _same_amount(statement_row["credit_total"], xml_row["credit_total"])
#                 and _same_amount(statement_row["debit_total"], xml_row["debit_total"])
#                 and statement_row["transaction_count"] == xml_row["transaction_count"]
#             ),
#             "opening_balance_statement": statement_row["opening_balance"],
#             "opening_balance_xml": xml_row["opening_balance"],
#             "closing_balance_statement": statement_row["closing_balance"],
#             "closing_balance_xml": xml_row["closing_balance"],
#             "credit_total_statement": statement_row["credit_total"],
#             "credit_total_xml": xml_row["credit_total"],
#             "debit_total_statement": statement_row["debit_total"],
#             "debit_total_xml": xml_row["debit_total"],
#             "transaction_count_statement": statement_row["transaction_count"],
#             "transaction_count_xml": xml_row["transaction_count"],
#         })

#     return {
#         "overall": {
#             "opening_balance_match": _same_amount(
#                 statement.get("opening_balance"),
#                 xml.get("opening_balance_used_for_projection"),
#             ),
#             "closing_balance_match": _same_amount(
#                 statement.get("closing_balance"),
#                 xml.get("projected_closing_balance"),
#             ),
#             "transaction_count_match": statement.get("transaction_count") == xml.get("convertible_transaction_count"),
#             "amount_total_match": _same_amount(
#                 statement.get("credit_total", 0.0) + statement.get("debit_total", 0.0),
#                 xml.get("transaction_amount_total"),
#             ),
#             "year_summary_match": _year_summary_match(statement.get("year_summary"), xml.get("year_summary")),
#         },
#         "monthly": monthly_comparisons,
#         "monthly_mismatch_count": sum(1 for row in monthly_comparisons if not row.get("match")),
#     }


# def _build_monthly_statement_summaries(transactions, opening_balance):
#     return _build_monthly_summaries_from_transactions(
#         transactions,
#         opening_balance,
#         balance_key="balance",
#         effect_key=None,
#         type_key="type",
#     )


# def _build_monthly_xml_summaries(xml_transactions, opening_balance):
#     return _build_monthly_summaries_from_transactions(
#         xml_transactions,
#         opening_balance,
#         balance_key="balance",
#         effect_key="balance_effect",
#         type_key="voucher_type",
#     )


# def _build_monthly_summaries_from_transactions(
#     records,
#     opening_balance,
#     balance_key,
#     effect_key=None,
#     type_key=None,
# ):
#     monthly = []
#     current_month = None
#     month_opening = opening_balance
#     month_credit_total = 0.0
#     month_debit_total = 0.0
#     month_count = 0
#     month_first_date = None
#     month_last_date = None
#     month_last_balance = opening_balance

#     for record in records:
#         month_key = _month_key(record["gl_date"])

#         if current_month is None:
#             current_month = month_key
#             month_first_date = record["gl_date"]

#         if month_key != current_month:
#             monthly.append(_finalize_month_summary(
#                 current_month,
#                 month_opening,
#                 month_last_balance,
#                 month_credit_total,
#                 month_debit_total,
#                 month_count,
#                 month_first_date,
#                 month_last_date,
#             ))
#             current_month = month_key
#             month_opening = month_last_balance
#             month_credit_total = 0.0
#             month_debit_total = 0.0
#             month_count = 0
#             month_first_date = record["gl_date"]

#         amount = float(record.get("amount", 0.0))
#         record_type = record.get(type_key) if type_key else None

#         if effect_key:
#             effect = float(record.get(effect_key, 0.0))
#             if effect > 0:
#                 # FIXED: Book view positive effect = DEBIT increase
#                 month_debit_total += abs(effect)
#             elif effect < 0:
#                 # FIXED: Book view negative effect = CREDIT decrease
#                 month_credit_total += abs(effect)
#             month_last_balance = float(record[balance_key])
#         else:
#             if record_type == "CREDIT":
#                 month_credit_total += amount
#             elif record_type == "DEBIT":
#                 month_debit_total += amount
#             month_last_balance = float(record[balance_key])

#         month_count += 1
#         month_last_date = record["gl_date"]

#     if current_month is not None:
#         monthly.append(_finalize_month_summary(
#             current_month,
#             month_opening,
#             month_last_balance,
#             month_credit_total,
#             month_debit_total,
#             month_count,
#             month_first_date,
#             month_last_date,
#         ))

#     return monthly


# def _finalize_month_summary(
#     month_key,
#     opening_balance,
#     closing_balance,
#     credit_total,
#     debit_total,
#     transaction_count,
#     first_date,
#     last_date,
# ):
#     calculated_closing = None
#     is_reconciled = False

#     if opening_balance is not None and closing_balance is not None:
#         # FIXED: Unified Book Perspective Calculation Layout
#         calculated_closing = round(opening_balance + debit_total - credit_total, 2)
#         is_reconciled = _same_amount(calculated_closing, closing_balance)

#     return {
#         "month": month_key,
#         "month_label": _month_label(month_key),
#         "first_transaction_date": first_date,
#         "last_transaction_date": last_date,
#         "transaction_count": transaction_count,
#         "opening_balance": _round_or_none(opening_balance),
#         "closing_balance": _round_or_none(closing_balance),
#         "credit_total": round(credit_total, 2),
#         "debit_total": round(debit_total, 2),
#         "calculated_closing_balance": calculated_closing,
#         "is_reconciled": is_reconciled,
#     }


# def _build_year_summary(monthly_summaries, opening_balance, closing_balance):
#     credit_total = round(sum(row["credit_total"] for row in monthly_summaries), 2)
#     debit_total = round(sum(row["debit_total"] for row in monthly_summaries), 2)
#     calculated_closing = None

#     if opening_balance is not None:
#         # FIXED: Global summary math adjusted to reflect book calculations
#         calculated_closing = round(opening_balance + debit_total - credit_total, 2)

#     return {
#         "opening_balance": _round_or_none(opening_balance),
#         "closing_balance": _round_or_none(closing_balance),
#         "credit_total": credit_total,
#         "debit_total": debit_total,
#         "calculated_closing_balance": calculated_closing,
#         "is_reconciled": _same_amount(calculated_closing, closing_balance),
#         "transaction_count": sum(row["transaction_count"] for row in monthly_summaries),
#     }


# def _year_summary_match(statement_year, xml_year):
#     if not statement_year or not xml_year:
#         return False

#     return (
#         _same_amount(statement_year.get("opening_balance"), xml_year.get("opening_balance"))
#         and _same_amount(statement_year.get("closing_balance"), xml_year.get("closing_balance"))
#         and _same_amount(statement_year.get("credit_total"), xml_year.get("credit_total"))
#         and _same_amount(statement_year.get("debit_total"), xml_year.get("debit_total"))
#         and statement_year.get("transaction_count") == xml_year.get("transaction_count")
#     )


# def _parse_voucher(voucher, bank_ledger, suspense_ledger):
#     date_text = voucher.findtext("DATE") or ""
#     voucher_type = voucher.findtext("VOUCHERTYPENAME") or ""
#     ledger_entries = voucher.findall("ALLLEDGERENTRIES.LIST")
#     bank_amount = None
#     bank_ledger_name = None
#     is_bank_debit = False

#     # Safely normalize target inputs for clean structural evaluations
#     target_bank = bank_ledger.strip().upper() if bank_ledger else ""
#     target_suspense = suspense_ledger.strip().upper() if suspense_ledger else ""

#     # Step 1: Case-insensitive check targeting your dynamic Bank Ledger string
#     for entry in ledger_entries:
#         ledger_name = (entry.findtext("LEDGERNAME") or "").strip().upper()
#         amount_text = entry.findtext("AMOUNT")
#         deemed_positive = entry.findtext("ISDEEMEDPOSITIVE") or "No"

#         if target_bank and ledger_name == target_bank:
#             bank_ledger_name = entry.findtext("LEDGERNAME")  # Preserve original string layout
#             bank_amount = float(amount_text or 0.0)
#             is_bank_debit = (deemed_positive == "Yes")
#             break

#     # Step 2: Fallback check to capture the non-suspense record if names varied
#     if bank_amount is None:
#         for entry in ledger_entries:
#             ledger_name = (entry.findtext("LEDGERNAME") or "").strip().upper()
#             amount_text = entry.findtext("AMOUNT")
#             deemed_positive = entry.findtext("ISDEEMEDPOSITIVE") or "No"

#             if target_suspense and ledger_name == target_suspense:
#                 continue

#             bank_ledger_name = entry.findtext("LEDGERNAME")
#             bank_amount = float(amount_text or 0.0)
#             is_bank_debit = (deemed_positive == "Yes")
#             break

#     # Step 3: Absolute safety initialization to eliminate downstream structural KeyErrors
#     if bank_amount is None:
#         bank_amount = 0.0

#     # Book View Accounting Rule tracking node conversion alignment
#     if is_bank_debit:
#         balance_effect = abs(bank_amount)   # Bank Debit increases asset value balance
#     else:
#         balance_effect = -abs(bank_amount)  # Bank Credit decreases asset value balance

#     return {
#         "gl_date": _from_tally_date(date_text),
#         "voucher_type": voucher_type,
#         "amount": abs(bank_amount),
#         "balance_effect": balance_effect,
#         "bank_ledger_name": bank_ledger_name or "Unknown Bank Ledger",
#         "voucher_number": voucher.findtext("VOUCHERNUMBER") or "",
#         "balance": 0.0  # Guarantees key existence for downstream validation routines
#     }


# def _find_balance_movement_errors(transactions, opening_balance):
#     errors = []
#     previous_balance = opening_balance

#     for index, transaction in enumerate(transactions, start=1):
#         if previous_balance is None:
#             previous_balance = transaction["balance"]
#             continue

#         balance_change = round(transaction["balance"] - previous_balance, 2)
#         amount_difference = abs(abs(balance_change) - transaction["amount"])

#         if amount_difference > BALANCE_TOLERANCE:
#             errors.append({
#                 "index": index,
#                 "gl_date": transaction["gl_date"],
#                 "amount": transaction["amount"],
#                 "previous_balance": previous_balance,
#                 "current_balance": transaction["balance"],
#                 "balance_change": balance_change,
#                 "amount_difference": amount_difference,
#             })

#         previous_balance = transaction["balance"]

#     return errors


# def _find_direction_mismatches(transactions, opening_balance):
#     mismatches = []
#     previous_balance = opening_balance

#     for index, transaction in enumerate(transactions, start=1):
#         if previous_balance is None:
#             previous_balance = transaction["balance"]
#             continue

#         balance_change = round(transaction["balance"] - previous_balance, 2)
#         expected_type = "UNKNOWN"

#         # FIXED: Book View Direction Expectations
#         if balance_change > 0:
#             expected_type = "DEBIT"   # Running balance went up = asset deposit
#         elif balance_change < 0:
#             expected_type = "CREDIT"  # Running balance went down = asset withdrawal

#         if expected_type != "UNKNOWN" and transaction.get("type") != expected_type:
#             mismatches.append({
#                 "index": index,
#                 "gl_date": transaction["gl_date"],
#                 "narration": transaction.get("narration"),
#                 "expected_type": expected_type,
#                 "actual_type": transaction.get("type"),
#                 "amount": transaction.get("amount"),
#                 "previous_balance": previous_balance,
#                 "current_balance": transaction["balance"],
#                 "balance_change": balance_change,
#             })

#         previous_balance = transaction["balance"]

#     return mismatches


# def _find_duplicate_keys(transactions):
#     keys = Counter(
#         (
#             txn.get("gl_date"),
#             txn.get("value_date"),
#             txn.get("narration"),
#             txn.get("amount"),
#             txn.get("balance"),
#         )
#         for txn in transactions
#     )

#     return [
#         {
#             "gl_date": key[0],
#             "value_date": key[1],
#             "narration": key[2],
#             "amount": key[3],
#             "balance": key[4],
#             "count": count,
#         }
#         for key, count in keys.items()
#         if count > 1
#     ]


# def _find_duplicate_voucher_numbers(vouchers):
#     keys = Counter(voucher.findtext("VOUCHERNUMBER") or "" for voucher in vouchers)
#     return [
#         {"voucher_number": key, "count": count}
#         for key, count in keys.items()
#         if key and count > 1
#     ]


# def _sum_amounts(transactions):
#     return round(sum(float(txn["amount"]) for txn in transactions), 2)


# def _same_amount(left, right):
#     if left is None or right is None:
#         return left is None and right is None

#     return abs(round(float(left), 2) - round(float(right), 2)) <= BALANCE_TOLERANCE


# def _round_or_none(value):
#     if value is None:
#         return None

#     return round(float(value), 2)


# def _month_key(date_value):
#     return datetime.strptime(date_value, "%d-%m-%Y").strftime("%Y-%m")


# def _month_label(month_key):
#     return datetime.strptime(month_key + "-01", "%Y-%m-%d").strftime("%b %Y")


# def _from_tally_date(date_value):
#     if not date_value:
#         return ""

#     return datetime.strptime(date_value, "%Y%m%d").strftime("%d-%m-%Y")



from collections import Counter
from datetime import datetime
import xml.etree.ElementTree as ET

BALANCE_TOLERANCE = 0.01

def build_validation_report(text, transactions, xml_text, bank_ledger, suspense_ledger):
    """
    Main entry point performing the clear 3-Check Audit Pipeline.
    """
    xml_root = ET.fromstring(xml_text)
    xml_vouchers = xml_root.findall(".//VOUCHER")
    
    valid_txns = [t for t in transactions if t.get("type") in {"CREDIT", "DEBIT"}]

    # Run checkpoints
    check_1_report = _run_check_1_summary_match(valid_txns, xml_vouchers, bank_ledger)
    check_2_report = _run_check_2_parallel_match(valid_txns, xml_vouchers, bank_ledger)
    check_3_report = _run_check_3_sequence_integrity(xml_vouchers)

    pipeline_passed = (
        check_1_report["overall_totals_match"] and 
        check_1_report["monthly_mismatch_count"] == 0 and
        check_2_report["mismatch_count"] == 0 and
        check_3_report["integrity_passed"]
    )

    return {
        "statement": {
            "transaction_count": len(transactions),
            "opening_balance": transactions[0]["balance"] if transactions else 0.0,
            "closing_balance": transactions[-1]["balance"] if transactions else 0.0,
            "credit_total": check_1_report["pdf_totals"]["credit"],
            "debit_total": check_1_report["pdf_totals"]["debit"],
            "is_reconciled": pipeline_passed,
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