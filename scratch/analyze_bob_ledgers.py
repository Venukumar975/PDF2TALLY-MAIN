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

def analyze():
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
    
    r = requests.post(tally_url, data=xml_request)
    cleaned_content = clean_tally_xml(r.content)
    root = ET.fromstring(cleaned_content)
    
    vouchers = root.findall(".//VOUCHER")
    
    print("Vouchers containing 'BOB' (exact ledger name):")
    count = 0
    for vch in vouchers:
        vch_date = vch.findtext("DATE")
        if not vch_date or len(vch_date) != 8:
            continue
        if vch_date < "20250402" or vch_date > "20260331":
            continue
            
        entries = vch.findall(".//ALLLEDGERENTRIES.LIST") + vch.findall(".//LEDGERENTRIES.LIST")
        has_bob = False
        for entry in entries:
            name = entry.findtext("LEDGERNAME", "").strip()
            if name.upper() == "BOB":
                has_bob = True
                break
                
        if not has_bob:
            continue
            
        count += 1
        print(f"\n#{count}: Date: {vch_date}, No: {vch.findtext('VOUCHERNUMBER')}, Type: {vch.findtext('VOUCHERTYPENAME')}")
        for entry in entries:
            name = entry.findtext("LEDGERNAME", "").strip()
            amount = entry.findtext("AMOUNT", "0").strip()
            is_pos = entry.findtext("ISDEEMEDPOSITIVE", "Yes").strip()
            print(f"  Entry -> Ledger: {name}, Amount: {amount}, ISDEEMEDPOSITIVE: {is_pos}")
            
        if count >= 30:
            print("\n... truncated after 30 vouchers ...")
            break

if __name__ == "__main__":
    analyze()
