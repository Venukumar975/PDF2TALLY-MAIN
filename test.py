import sys
from services.pdf_reader import extract_text
from parsers.sbi_parser import parse_transactions

def test_sbi_parsing():
    print("[TEST] Extracting text from sbi_statement.pdf...")
    try:
        text = extract_text("sbi_statement.pdf")
        if not text:
            print("[FAIL] No text extracted from PDF.")
            return
        
        print(f"[TEST] Text length: {len(text)} characters.")
        
        print("[TEST] Parsing transactions...")
        txns = parse_transactions(text)
        
        print(f"[TEST] Successfully parsed {len(txns)} transactions!")
        if txns:
            print("\nFirst 3 transactions:")
            for t in txns[:3]:
                print(t)
            print("\nLast 3 transactions:")
            for t in txns[-3:]:
                print(t)
        else:
            print("[FAIL] Parser returned zero transactions.")
            
    except Exception as e:
        print(f"[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sbi_parsing()
