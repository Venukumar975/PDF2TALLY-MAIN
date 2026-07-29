import requests
import xml.etree.ElementTree as ET
import re
from collections import defaultdict

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

def run_correct_analysis():
    tally_url = "http://localhost:9000"
    xml_request = """<ENVELOPE>
        <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>Export Data</TALLYREQUEST>
            <TYPE>Collection</TYPE>
            <ID>VoucherDuplicateCheckCollection</ID>
            <SVCURRENTCOMPANY>Tally Test</SVCURRENTCOMPANY>
        </HEADER>
        <BODY>
            <DESC>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE TYPE="Date">20250402</SVFROMDATE>
                    <SVTODATE TYPE="Date">20260331</SVTODATE>
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
    
    print("Querying Tally Prime directly...")
    r = requests.post(tally_url, data=xml_request)
    cleaned_content = clean_tally_xml(r.content)
    root = ET.fromstring(cleaned_content)
    
    vouchers = root.findall(".//VOUCHER")
    print(f"Total vouchers returned by Tally: {len(vouchers)}")
    
    monthly_data = defaultdict(lambda: {'count': 0, 'debit': 0.0, 'credit': 0.0})
    
    for vch in vouchers:
        vch_date = vch.findtext("DATE")
        if not vch_date or len(vch_date) != 8:
            continue
            
        # Filter by date range 20250402 to 20260331
        if vch_date < "20250402" or vch_date > "20260331":
            continue
            
        ym = vch_date[:6] # "202504"
        
        entries = vch.findall(".//ALLLEDGERENTRIES.LIST") + vch.findall(".//LEDGERENTRIES.LIST")
        parsed_entries = []
        for entry in entries:
            name = entry.findtext("LEDGERNAME", "").strip()
            amount_str = entry.findtext("AMOUNT", "0").strip()
            is_pos = entry.findtext("ISDEEMEDPOSITIVE", "Yes").strip()
            try:
                amt = float(amount_str)
            except ValueError:
                amt = 0.0
            parsed_entries.append({
                'ledger': name,
                'amount': amt,
                'is_deemed_positive': is_pos
            })
            
        # Resolve bank entry: STRICTLY "BOB" only (ignore "BANK OF BARODA")
        bank_entry = None
        for pe in parsed_entries:
            if pe['ledger'].upper() == "BOB":
                bank_entry = pe
                break
                    
        if not bank_entry:
            continue
            
        # Tally Debit has negative amount in Tally XML.
        # Tally Credit has positive amount in Tally XML.
        amt = abs(bank_entry['amount'])
        is_debit = bank_entry['amount'] < 0
        
        monthly_data[ym]['count'] += 1
        if is_debit:
            monthly_data[ym]['debit'] += amt
        else:
            monthly_data[ym]['credit'] += amt
            
    balance = 11968.42
    print("\nCorrect Monthly Analysis Summary:")
    print("--------------------------------------------------------------------------------")
    print(f"{'Month':<10} | {'Vouchers':<8} | {'Debit (In)':<15} | {'Credit (Out)':<15} | {'Closing Balance':<18}")
    print("--------------------------------------------------------------------------------")
    
    months_names = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr', '05': 'May', '06': 'Jun',
        '07': 'Jul', '08': 'Aug', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
    }
    
    for ym in sorted(monthly_data.keys()):
        m_info = monthly_data[ym]
        debit = m_info['debit']
        credit = m_info['credit']
        balance += debit - credit
        
        yr = ym[:4]
        mn = ym[4:]
        month_str = f"{months_names[mn]} {yr}"
        
        # Check sign of balance to append Dr/Cr
        bal_type = "Dr" if balance >= 0 else "Cr"
        bal_str = f"{abs(balance):,.2f} {bal_type}"
        
        print(f"{month_str:<10} | {m_info['count']:<8} | {debit:15,.2f} | {credit:15,.2f} | {bal_str:>18}")
    print("--------------------------------------------------------------------------------")

if __name__ == '__main__':
    run_correct_analysis()
