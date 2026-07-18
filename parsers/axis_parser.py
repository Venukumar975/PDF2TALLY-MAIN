import re
from datetime import datetime

BALANCE_TOLERANCE = 0.01

def clean_amount(value):
    if not value or str(value).strip() in ["-", "–"]:
        return 0.00
    cleaned = re.sub(r"[^\d.]", "", str(value))
    return float(cleaned) if cleaned else 0.00

def parse_opening_balance(text):
    """
    Extracts opening balance, matching "OPENING BALANCE 12,054.86"
    """
    match = re.search(r"OPENING\s+BALANCE\s*[:\s]\s*([0-9,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if not match:
        return None
    return clean_amount(match.group(1))

def parse_transactions(text, opening_balance=None):
    """
    Extracts all transaction rows and compiles them into structured dictionaries.
    Handles multi-line description wrap-arounds automatically.
    """
    transactions = []
    lines = text.split("\n")
    is_fallback = False
    
    if opening_balance is None:
        opening_balance = parse_opening_balance(text)
        if opening_balance is None:
            opening_balance = 0.00
            is_fallback = True

    date_pattern = r"^\d{2}-\d{2}-\d{4}$"

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        parts = line.split()
        
        # Row must start with two valid dates (Transaction Date and Value Date)
        if len(parts) >= 6 and re.match(date_pattern, parts[0]) and re.match(date_pattern, parts[1]):
            try:
                gl_date = datetime.strptime(parts[0], "%d-%m-%Y").strftime("%d-%m-%Y")
                value_date = datetime.strptime(parts[1], "%d-%m-%Y").strftime("%d-%m-%Y")
                
                # Scan backwards for the DR/CR transaction type indicator
                dr_cr_index = -1
                for idx, token in enumerate(parts):
                    if idx > 1 and token in ("DR", "CR"):
                        dr_cr_index = idx
                        break
                
                if dr_cr_index == -1:
                    i += 1
                    continue
                
                # Amount is to the left of the DR/CR token; Balance is to the right
                amount = clean_amount(parts[dr_cr_index - 1])
                balance = clean_amount(parts[dr_cr_index + 1])
                
                # Particulars start at index 2 and end before the amount
                narration_pieces = parts[2:dr_cr_index - 1]
                
                # Multi-line narration tracking loop (look-ahead)
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    next_parts = next_line.split()
                    if not next_line or (len(next_parts) >= 1 and re.match(date_pattern, next_parts[0])):
                        break
                    # Avoid appending header/footer labels
                    if not any(k in next_line for k in ["Tran Date", "Particulars", "Balance(INR)", "CLOSING BALANCE", "Page"]):
                        narration_pieces.append(next_line)
                    j += 1
                
                transactions.append({
                    "gl_date": gl_date,
                    "value_date": value_date,
                    "narration": " ".join(narration_pieces),
                    "amount": amount,
                    "balance": balance,
                    "type": "UNKNOWN",
                    "bank_indicator": parts[dr_cr_index]
                })
                i = j - 1
            except Exception:
                pass
        i += 1

    determine_dr_cr(transactions, opening_balance, is_fallback)
    return transactions

def determine_dr_cr(transactions, opening_balance, is_fallback=False):
    previous_balance = opening_balance if opening_balance is not None else 0.00
    is_negative_loan = (opening_balance is not None and opening_balance < 0)
    
    for idx, txn in enumerate(transactions):
        if is_negative_loan:
            txn["balance"] = -abs(txn["balance"])
            
        current_balance = txn["balance"]
        balance_change = round(current_balance - previous_balance, 2)
        
        # Check if balance delta corresponds to amount (reconciliation validation)
        if abs(abs(balance_change) - txn["amount"]) <= BALANCE_TOLERANCE:
            if balance_change > 0:
                txn["type"] = "DEBIT"
            elif balance_change < 0:
                txn["type"] = "CREDIT"
            else:
                txn["type"] = "UNKNOWN"
        else:
            # Fallback to the printed DR/CR column
            indicator = txn.get("bank_indicator")
            if indicator == "CR":
                txn["type"] = "DEBIT"   # Money came in
            elif indicator == "DR":
                txn["type"] = "CREDIT"  # Money went out
            else:
                txn["type"] = "UNKNOWN"
                
        previous_balance = current_balance
    return transactions