import requests

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
    print("Response Status Code:", r.status_code)
    print("Raw XML Response (first 4000 chars):")
    print(r.text[:4000])

if __name__ == "__main__":
    test()
