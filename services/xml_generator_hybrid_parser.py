from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

DEFAULT_BANK_LEDGER = "Generic Bank"
DEFAULT_SUSPENSE_LEDGER = "Suspense"

def generate_tally_xml_hybrid(
    transactions,
    output_path=None,
    bank_ledger=DEFAULT_BANK_LEDGER,
    suspense_ledger=DEFAULT_SUSPENSE_LEDGER,
    opening_balance=None,
):
    envelope = ET.Element("ENVELOPE")
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"

    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")

    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = "Vouchers"
    ET.SubElement(request_desc, "STATICVARIABLES")

    request_data = ET.SubElement(import_data, "REQUESTDATA")

    # Add Ledgers to the top of the request payload
    _add_ledger(request_data, suspense_ledger, "Current Liabilities")
    _add_ledger(request_data, bank_ledger, "Bank Accounts", opening_balance)

    # Timeline sorting
    def get_sort_key(txn):
        try:
            return datetime.strptime(txn["gl_date"], "%d-%m-%Y")
        except (ValueError, KeyError):
            return datetime.min

    sorted_transactions = sorted(transactions, key=get_sort_key)

    # Extract dynamic acronym prefix
    bank_prefix = "".join([word[0] for word in bank_ledger.split() if word.isalpha()]).upper()
    if not bank_prefix:
        bank_prefix = "GEN"

    for index, transaction in enumerate(sorted_transactions, start=1):
        if transaction.get("type") not in {"CREDIT", "DEBIT"}:
            continue

        _add_voucher(
            request_data,
            transaction,
            index,
            bank_ledger,
            suspense_ledger,
            bank_prefix,
        )

    _indent(envelope)
    xml_text = ET.tostring(envelope, encoding="unicode", short_empty_elements=False)
    xml_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_text

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(xml_text, encoding="utf-8")

    return xml_text


def _add_ledger(request_data, ledger_name, parent_name, opening_balance=None):
    tally_message = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
    ledger = ET.SubElement(tally_message, "LEDGER", {"NAME": ledger_name, "ACTION": "Create"})
    ET.SubElement(ledger, "NAME").text = ledger_name
    ET.SubElement(ledger, "PARENT").text = parent_name
    ET.SubElement(ledger, "ISBILLWISEON").text = "No"
    ET.SubElement(ledger, "ISCOSTCENTRESON").text = "No"
    
    op_bal = opening_balance if opening_balance is not None else 0.00
    tally_op_bal = -op_bal
    ET.SubElement(ledger, "OPENINGBALANCE").text = f"{tally_op_bal:.2f}"


def _add_voucher(request_data, transaction, index, bank_ledger, suspense_ledger, bank_prefix):
    voucher_type = "Payment" if transaction["type"] == "CREDIT" else "Receipt"
    amount = round(float(transaction["amount"]), 2)
    date_value = _format_tally_date(transaction["gl_date"])
    narration = transaction.get("narration") or "Generic Statement Entry"
    voucher_number = f"{bank_prefix}-{date_value}-{index:05d}"

    tally_message = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
    voucher = ET.SubElement(
        tally_message,
        "VOUCHER",
        {
            "VCHTYPE": voucher_type,
            "ACTION": "Create",
            "OBJVIEW": "Accounting Voucher View",
        },
    )

    ET.SubElement(voucher, "DATE").text = date_value
    ET.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
    ET.SubElement(voucher, "VOUCHERNUMBER").text = voucher_number
    ET.SubElement(voucher, "REFERENCE").text = voucher_number
    ET.SubElement(voucher, "PARTYLEDGERNAME").text = suspense_ledger
    ET.SubElement(voucher, "NARRATION").text = narration
    ET.SubElement(voucher, "PERSISTEDVIEW").text = "Accounting Voucher View"

    if transaction["type"] == "CREDIT":
        _add_ledger_entry(voucher, bank_ledger, amount, is_debit=False, is_party_ledger=False)
        _add_ledger_entry(voucher, suspense_ledger, amount, is_debit=True, is_party_ledger=True)
    else:
        _add_ledger_entry(voucher, suspense_ledger, amount, is_debit=False, is_party_ledger=True)
        _add_ledger_entry(voucher, bank_ledger, amount, is_debit=True, is_party_ledger=False)


def _add_ledger_entry(voucher, ledger_name, amount, is_debit, is_party_ledger):
    entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
    ET.SubElement(entry, "LEDGERNAME").text = ledger_name
    ET.SubElement(entry, "ISDEEMEDPOSITIVE").text = "Yes" if is_debit else "No"
    ET.SubElement(entry, "ISLASTDEEMEDPOSITIVE").text = "Yes" if is_debit else "No"
    ET.SubElement(entry, "ISPARTYLEDGER").text = "Yes" if is_party_ledger else "No"
    ET.SubElement(entry, "AMOUNT").text = _tally_amount(amount, is_debit)


def _tally_amount(amount, is_debit):
    signed_amount = -amount if is_debit else amount
    return f"{signed_amount:.2f}"


def _format_tally_date(date_value):
    parsed_date = datetime.strptime(date_value, "%d-%m-%Y")
    return parsed_date.strftime("%Y%m%d")


def _indent(element, level=0):
    spacing = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = spacing + "  "
        for child in element:
            _indent(child, level + 1)
        if not element.tail or not element.tail.strip():
            element.tail = spacing
    elif level and (not element.tail or not element.tail.strip()):
        element.tail = spacing
