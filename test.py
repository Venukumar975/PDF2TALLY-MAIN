import sys
from datetime import datetime, date
from services.pdf_reader import extract_text
from parsers.sbi_parser import parse_transactions

def test_new_continuation_logic():
    print("[TEST] Extracting text...")
    text = extract_text("sbi_statement.pdf")
    
    boundary = date(2025, 6, 10)
    print(f"[TEST] Parsing full transactions first...")
    full_txns = parse_transactions(text)
    
    print(f"[TEST] Filtering transactions from {boundary} onwards...")
    txns = []
    for t in full_txns:
        t_date = datetime.strptime(t["gl_date"], "%d-%m-%Y").date()
        if t_date >= boundary:
            txns.append(t)
            
    print(f"[TEST] Filtered transaction count: {len(txns)}")
    if txns:
        print("\nFirst 5 parsed transactions (should start with 10-06-2025 and have correct types):")
        for t in txns[:5]:
            print(t)
    else:
        print("[FAIL] No transactions matched.")

if __name__ == "__main__":
    test_new_continuation_logic()
