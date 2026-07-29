import requests
import xml.etree.ElementTree as ET
import re

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

def test():
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
                    <SVFROMDATE TYPE="Date">20260301</SVFROMDATE>
                    <SVTODATE TYPE="Date">20260301</SVTODATE>
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
    
    r = requests.post(tally_url, data=xml_request)
    cleaned_content = clean_tally_xml(r.content)
    root = ET.fromstring(cleaned_content)
    
    # Inspect first 5 vouchers to see different voucher types
    vouchers = root.findall(".//VOUCHER")
    if not vouchers:
        print("No vouchers found.")
        return
        
    for idx, vch in enumerate(vouchers[:5]):
        print(f"\n--- Voucher #{idx+1} ---")
        print(f"Vch Number: {vch.findtext('VOUCHERNUMBER')}")
        print(f"Vch Type: {vch.findtext('VOUCHERTYPENAME')}")
        print(f"Narration: {vch.findtext('NARRATION')}")
        
        entries = vch.findall(".//ALLLEDGERENTRIES.LIST") + vch.findall(".//LEDGERENTRIES.LIST")
        for entry in entries:
            name = entry.findtext("LEDGERNAME")
            amount = entry.findtext("AMOUNT")
            is_pos = entry.findtext("ISDEEMEDPOSITIVE")
            print(f"  Entry -> Ledger: {name}, Amount: {amount}, ISDEEMEDPOSITIVE: {is_pos}")

if __name__ == "__main__":
    test()
