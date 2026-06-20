# services/cash_xml_generator.py
from datetime import datetime
import xml.etree.ElementTree as ET

def generate_ashramam_tally_xml(transactions, cash_ledger="Cash", donation_ledger="Annadana Prasadam Donations Received"):
    """
    Generates a standalone Tally Prime compliant XML string exclusively for Ashramam Cash Receipts.
    Maps: Cash Account (Debited - ISDEEMEDPOSITIVE='Yes'), Donation Account (Credited - ISDEEMEDPOSITIVE='No')
    """
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
    for ledger_name, parent in [(donation_ledger, "Indirect Incomes"), (cash_ledger, "Cash-in-Hand")]:
        tally_msg = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        ledger = ET.SubElement(tally_msg, "LEDGER", {"NAME": ledger_name, "ACTION": "Create"})
        ET.SubElement(ledger, "NAME").text = ledger_name
        ET.SubElement(ledger, "PARENT").text = parent

    # Chronological sort logic
    def get_sort_key(t):
        try:
            return datetime.strptime(t["gl_date"], "%d-%m-%Y")
        except Exception:
            return datetime.min
            
    sorted_txns = sorted(transactions, key=get_sort_key)

    for idx, txn in enumerate(sorted_txns, start=1):
        parsed_dt = datetime.strptime(txn["gl_date"], "%d-%m-%Y")
        date_value = parsed_dt.strftime("%Y%m%d")
        amount = round(float(txn["amount"]), 2)
        
        # Voucher structure identification format code matching your mother's rules
        voucher_number = f"RC-{date_value}-{idx:05d}"

        tally_msg = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
        vch = ET.SubElement(tally_msg, "VOUCHER", {"VCHTYPE": "Receipt", "ACTION": "Create", "OBJVIEW": "Accounting Voucher View"})

        ET.SubElement(vch, "DATE").text = date_value
        ET.SubElement(vch, "VOUCHERTYPENAME").text = "Receipt"
        ET.SubElement(vch, "VOUCHERNUMBER").text = voucher_number
        ET.SubElement(vch, "REFERENCE").text = voucher_number
        ET.SubElement(vch, "PARTYLEDGERNAME").text = donation_ledger
        ET.SubElement(vch, "NARRATION").text = txn["narration"]
        ET.SubElement(vch, "PERSISTEDVIEW").text = "Accounting Voucher View"

        # 1. Cash Book Entry (DEBIT -> Money comes in)
        cash_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(cash_entry, "LEDGERNAME").text = cash_ledger
        ET.SubElement(cash_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(cash_entry, "ISLASTDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(cash_entry, "ISPARTYLEDGER").text = "No"
        ET.SubElement(cash_entry, "AMOUNT").text = f"-{amount:.2f}"

        # 2. Donation Income Entry (CREDIT -> Tracking Indirect Income)
        donation_entry = ET.SubElement(vch, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(donation_entry, "LEDGERNAME").text = donation_ledger
        ET.SubElement(donation_entry, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(donation_entry, "ISLASTDEEMEDPOSITIVE").text = "No"
        ET.SubElement(donation_entry, "ISPARTYLEDGER").text = "Yes"
        ET.SubElement(donation_entry, "AMOUNT").text = f"{amount:.2f}"

    # Indent configuration layouts formatting
    _indent(envelope)
    xml_text = ET.tostring(envelope, encoding="unicode", short_empty_elements=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_text

def _indent(elem, level=0):
    spacing = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip(): elem.text = spacing + "  "
        for child in elem: _indent(child, level + 1)
        if not elem.tail or not elem.tail.strip(): elem.tail = spacing
    elif level and (not elem.tail or not elem.tail.strip()): elem.tail = spacing