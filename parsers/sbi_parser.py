import re
from datetime import datetime

BALANCE_TOLERANCE = 0.01

# ==============================================================================
# UPGRADED: DYNAMIC OPENING BALANCE EXTRACTOR
# ==============================================================================
def parse_opening_balance(text):
    """
    Extracts the opening balance, handling dynamic dates like 'Balance as on 1 Jan 2026'
    or standard static labels.
    """
    clean_text = text.replace("(cid:9)", " ")
    
    # Matches "Balance as on DD MMM YYYY : Amount" dynamically
    match1 = re.search(
        r"Balance\s+as\s+on\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s*:\s*&?([0-9,]+(?:\.\d+)?)",
        clean_text,
        re.IGNORECASE
    )
    if match1:
        return clean_amount(match1.group(1))
        
    # Fallback to general variations
    match2 = re.search(
        r"Balance\s+as\s+on\s+[^:]+:\s*&?([0-9,]+(?:\.\d+)?)",
        clean_text,
        re.IGNORECASE
    )
    if match2:
        return clean_amount(match2.group(1))
        
    match3 = re.search(
        r"Clear\s+Balance\s*:\s*([0-9,]+(?:\.\d+)?)",
        clean_text,
        re.IGNORECASE
    )
    if match3:
        return clean_amount(match3.group(1))
        
    return None


# ==============================================================================
# NEW STRATEGY: Corporate Tabular Layout with Branch Code (For your latest image)
# ==============================================================================
def parse_sbi_corporate_tabular_format(text):
    """
    Handles corporate variations containing columns: 
    [Txn Date] [Value Date] [Description] [Ref No] [Branch Code] [Debit] [Credit] [Balance]
    """
    transactions = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # Matches DD/MM/YYYY
    date_pattern = r"^\d{2}/\d{2}/\d{4}"
    
    i = 0
    while i < len(lines):
        line = lines[i]
        parts = line.split()
        
        if len(parts) >= 2 and re.match(date_pattern, parts[0]) and re.match(date_pattern, parts[1]):
            try:
                raw_txn_date, raw_val_date = parts[0], parts[1]
                
                # Normalize dates immediately for XML generator compatibility
                gl_date = datetime.strptime(raw_txn_date, "%d/%m/%Y").strftime("%d-%m-%Y")
                value_date = datetime.strptime(raw_val_date, "%d/%m/%Y").strftime("%d-%m-%Y")
                
                # Balance is reliably the final token
                balance = clean_amount(parts[-1])
                
                # ⚡ EXTRA COLUMN FIX:
                # Instead of slicing hard indices from the back, we collect ALL numerical values 
                # trailing after the dates, filtering out the balance itself.
                numeric_candidates = []
                for p in parts[2:]:
                    cleaned_val = re.sub(r"[^\d.]", "", p)
                    if cleaned_val and p != parts[-1]:  # Exclude the balance token
                        numeric_candidates.append(float(cleaned_val))
                
                # In this system format: 
                # Last value = transaction amount (Debit or Credit)
                # Second to last value (if exists) = Branch Code
                amount = numeric_candidates[-1] if numeric_candidates else 0.00
                
                # Clean up description arrays safely
                narration_pieces = [p for p in parts[2:-1] if p not in [parts[-2], parts[-3]]]
                
                # Multi-line description lookahead tracking loop
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_parts = next_line.split()
                    if not next_line or re.match(date_pattern, next_parts[0]):
                        break
                    if not any(k in next_line for k in ["Value Date", "Description", "Branch Code", "Balance"]):
                        narration_pieces.append(next_line)
                    j += 1
                
                transactions.append({
                    "gl_date": gl_date,
                    "value_date": value_date,
                    "narration": " ".join(narration_pieces),
                    "amount": amount,
                    "balance": balance,
                    "type": "UNKNOWN"
                })
                i = j - 1
            except Exception:
                pass
        i += 1
    return transactions


# ==============================================================================
# STRATEGY 2: Numeric Slash Standard Tabular Format (e.g., "11/01/2026")
# ==============================================================================
def parse_sbi_numeric_slashes_format(text):
    transactions = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    date_pattern = r"^\d{2}/\d{2}/\d{4}"
    
    i = 0
    while i < len(lines):
        line = lines[i]
        parts = line.split()
        
        if len(parts) >= 2 and re.match(date_pattern, parts[0]) and re.match(date_pattern, parts[1]):
            try:
                raw_val_date, raw_post_date = parts[0], parts[1]
                
                val_date = datetime.strptime(raw_val_date, "%d/%m/%Y").strftime("%d-%m-%Y")
                post_date = datetime.strptime(raw_post_date, "%d/%m/%Y").strftime("%d-%m-%Y")
                
                balance = clean_amount(parts[-1])
                
                possible_amounts = []
                for p in parts[-4:-1]: 
                    cleaned = re.sub(r"[^\d.]", "", p)
                    if cleaned and p != parts[-1]:
                        possible_amounts.append(float(cleaned))
                
                amount = possible_amounts[-1] if possible_amounts else 0.00
                narration_pieces = parts[2:-2]
                
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_parts = next_line.split()
                    if not next_line or re.match(date_pattern, next_parts[0]):
                        break
                    if not any(k in next_line for k in ["Value Date", "Post Date", "Details", "Balance"]):
                        narration_pieces.append(next_line)
                    j += 1
                
                transactions.append({
                    "gl_date": post_date,
                    "value_date": val_date,
                    "narration": " ".join(narration_pieces),
                    "amount": amount,
                    "balance": balance,
                    "type": "UNKNOWN"
                })
                i = j - 1
            except Exception:
                pass
        i += 1
    return transactions


# ==============================================================================
# STRATEGY 3: Textual Month Grid Format (e.g., "4 Jun 2025")
# ==============================================================================
def clean_and_parse_decimal(token):
    # Remove commas and clean up surrounding noise
    cleaned = token.replace(",", "").strip()
    # Ensure it is a valid number with two decimal places (allowing negative sign)
    if re.match(r"^-?\d+\.\d{2}$", cleaned):
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_sbi_textual_month_format(text):
    transactions = []
    raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # Pre-process: Stitch year back to date line if it wraps to the next line (e.g. 10 Nov / 2025)
    lines = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        parts = line.split()
        if len(parts) >= 4 and re.match(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{1,2}\s+[A-Za-z]{3}$", " ".join(parts[0:4])):
            if i + 1 < len(raw_lines):
                next_line = raw_lines[i + 1]
                next_parts = next_line.split()
                if len(next_parts) >= 2 and next_parts[0].isdigit() and len(next_parts[0]) == 4 and next_parts[1].isdigit() and len(next_parts[1]) == 4:
                    year_1 = next_parts[0]
                    year_2 = next_parts[1]
                    merged_line = f"{parts[0]} {parts[1]} {year_1} {parts[2]} {parts[3]} {year_2} " + " ".join(parts[4:])
                    lines.append(merged_line)
                    raw_lines[i + 1] = " ".join(next_parts[2:])
                    i += 1
                    continue
        lines.append(line)
        i += 1
        
    date_pattern = r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}"
    
    blocks = []
    current_block = None
    
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        # Check if line starts with two dates (Txn Date and Value Date)
        if len(parts) >= 6 and re.match(date_pattern, " ".join(parts[0:3])) and re.match(date_pattern, " ".join(parts[3:6])):
            if current_block:
                blocks.append(current_block)
            current_block = [line]
        else:
            if current_block:
                current_block.append(line)
                
    if current_block:
        blocks.append(current_block)
        
    for block in blocks:
        first_line = block[0]
        parts = first_line.split()
        
        try:
            txn_date_str = " ".join(parts[0:3])
            val_date_str = " ".join(parts[3:6])
            
            gl_date = datetime.strptime(txn_date_str, "%d %b %Y").strftime("%d-%m-%Y")
            value_date = datetime.strptime(val_date_str, "%d %b %Y").strftime("%d-%m-%Y")
            
            # Find amount and balance by searching the block lines from bottom to top
            balance = None
            amount = None
            amount_line_index = -1
            
            for idx in range(len(block) - 1, -1, -1):
                line_in_block = block[idx]
                line_parts = line_in_block.split()
                numeric_tokens = []
                for p in reversed(line_parts):
                    val = clean_and_parse_decimal(p)
                    if val is not None:
                        numeric_tokens.append(val)
                if len(numeric_tokens) >= 2:
                    balance = numeric_tokens[0]
                    amount = numeric_tokens[1]
                    amount_line_index = idx
                    break
            
            if balance is None or amount is None:
                continue
                
            # Collect narration pieces from all lines except the parts of the amount line that are numeric
            narration_pieces = []
            
            # Add description parts from the first line (excluding the dates and numeric tokens if amount is on first line)
            first_line_desc_parts = parts[6:]
            if amount_line_index == 0:
                first_line_desc_parts = [p for p in first_line_desc_parts if clean_and_parse_decimal(p) is None]
            narration_pieces.extend(first_line_desc_parts)
            
            # Add intermediate lines
            for idx in range(1, len(block)):
                if idx == amount_line_index:
                    # For the amount line, exclude the numeric tokens
                    line_parts = block[idx].split()
                    cleaned_parts = []
                    for p in line_parts:
                        if clean_and_parse_decimal(p) is None:
                            cleaned_parts.append(p)
                    if cleaned_parts:
                        narration_pieces.append(" ".join(cleaned_parts))
                elif idx < amount_line_index:
                    narration_pieces.append(block[idx])
                    
            transactions.append({
                "gl_date": gl_date,
                "value_date": value_date,
                "narration": " ".join([p for p in narration_pieces if p.strip()]),
                "amount": amount,
                "balance": balance,
                "type": "UNKNOWN"
            })
        except Exception:
            continue
            
    return transactions


# ==============================================================================
# STRATEGY 4: Legacy Textual Wrapped Line Format
# ==============================================================================
def parse_sbi_legacy_wrapped_format(text):
    transactions = []
    text = text.replace("(cid:9)", " ")
    lines = text.split("\n")

    full_line_pattern = r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}"
    wrapped_date_pattern = r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{1,2}\s+[A-Za-z]{3}"

    num_lines = len(lines)
    i = 0

    while i < num_lines:
        line = lines[i].strip()
        parts = line.split()

        is_full_line = bool(re.match(full_line_pattern, line))
        is_wrapped_line = bool(re.match(wrapped_date_pattern, line))

        if not (is_full_line or is_wrapped_line):
            i += 1
            continue

        try:
            if is_wrapped_line and not is_full_line:
                if i + 1 < num_lines:
                    next_line = lines[i + 1].strip()
                    next_parts = next_line.split()
                    if len(next_parts) >= 2 and next_parts[0].isdigit() and len(next_parts[0]) == 4:
                        parts = parts[0:2] + [next_parts[0]] + parts[2:4] + [next_parts[1]] + parts[4:]
                        lines[i + 1] = " ".join(next_parts[2:])
            
            if len(parts) < 8:
                i += 1
                continue

            gl_date = datetime.strptime(f"{parts[0]} {parts[1]} {parts[2]}", "%d %b %Y").strftime("%d-%m-%Y")
            value_date = datetime.strptime(f"{parts[3]} {parts[4]} {parts[5]}", "%d %b %Y").strftime("%d-%m-%Y")

            balance = clean_amount(parts[-1])
            amount = clean_amount(parts[-2])
            narration_pieces = parts[6:-2]

            j = i + 1
            while j < num_lines:
                next_line = lines[j].strip()
                if not next_line or any(k in next_line for k in ["Txn Date", "Date No.", "Balance as on"]):
                    j += 1
                    continue
                if re.match(full_line_pattern, next_line) or re.match(wrapped_date_pattern, next_line):
                    break
                narration_pieces.append(next_line)
                j += 1

            transactions.append({
                "gl_date": gl_date,
                "value_date": value_date,
                "narration": " ".join(narration_pieces),
                "amount": amount,
                "balance": balance,
                "type": "UNKNOWN"
            })
            i = j
        except Exception:
            i += 1
            continue

    return transactions


# ==============================================================================
# UTILITIES & RECONCILIATION
# ==============================================================================
def clean_amount(value):
    if not value or str(value).strip() in ["-", "–"]:
        return 0.00
    cleaned = re.sub(r"[^\d.]", "", str(value))
    return float(cleaned) if cleaned else 0.00


def apply_tally_rules(transactions, opening_balance=None, is_fallback=False):
    if not transactions:
        return transactions

    previous_balance = opening_balance if opening_balance is not None else 0.00

    for idx in range(len(transactions)):
        curr_bal = transactions[idx]["balance"]
        delta = round(curr_bal - previous_balance, 2)
        
        if idx == 0 and is_fallback:
            transactions[idx]["is_fallback_type"] = True
            
        if delta > 0:
            transactions[idx]["type"] = "DEBIT"
        elif delta < 0:
            transactions[idx]["type"] = "CREDIT"
        else:
            transactions[idx]["type"] = "DEBIT" if transactions[idx]["amount"] > 0 else "CREDIT"
            
        previous_balance = curr_bal
            
    return transactions


def validate_reconciliation(transactions):
    if len(transactions) < 2:
        return True
    
    errors = 0
    for idx in range(1, len(transactions)):
        prev_bal = transactions[idx - 1]["balance"]
        curr_bal = transactions[idx]["balance"]
        amt = transactions[idx]["amount"]
        txn_type = transactions[idx]["type"]
        
        expected_bal = prev_bal + amt if txn_type == "DEBIT" else prev_bal - amt
        if abs(round(curr_bal - expected_bal, 2)) > BALANCE_TOLERANCE:
            errors += 1
            
    return (errors / len(transactions)) < 0.25


# ==============================================================================
# CENTRAL ENTRANCE ORCHESTRATOR
# ==============================================================================
def parse_any_sbi_statement_to_tally(raw_extracted_text, opening_balance=None):
    """Orchestrates parsing sequentially across the fallback matrix list."""
    is_fallback = False
    if opening_balance is None:
        opening_balance = parse_opening_balance(raw_extracted_text)
        if opening_balance is None:
            opening_balance = 0.00
            is_fallback = True
            
    parser_strategies = [
        {"name": "Corporate Branch Code Tabular Parser", "func": parse_sbi_corporate_tabular_format},
        {"name": "Numeric Slash Tabular Parser", "func": parse_sbi_numeric_slashes_format},
        {"name": "Textual Month Tabular Parser", "func": parse_sbi_textual_month_format},
        {"name": "Legacy Wrapped Line Parser", "func": parse_sbi_legacy_wrapped_format}
    ]
    
    for strategy in parser_strategies:
        try:
            extracted_txns = strategy["func"](raw_extracted_text)
            if not extracted_txns:
                continue
                
            processed_txns = apply_tally_rules(extracted_txns, opening_balance=opening_balance, is_fallback=is_fallback)
            
            if validate_reconciliation(processed_txns):
                return processed_txns
                
        except Exception:
            continue
            
    return []

def parse_transactions(text, opening_balance=None):
    return parse_any_sbi_statement_to_tally(text, opening_balance=opening_balance)

# import re
# from datetime import datetime

# BALANCE_TOLERANCE = 0.01

# def parse_transactions(text):
#     transactions = []
    
#     # Pre-process: Clean out those annoying cid font-encoding tags before parsing
#     text = text.replace("(cid:9)", " ")
#     lines = text.split("\n")
#     opening_balance = parse_opening_balance(text)

#     # ─── THE NEW TWO-STAGE DATE REGEX PATTERN MATCHING ────────────────────
#     # Pattern A matches full single-line dates: "9 May 2025" or "10 May 2025"
#     full_line_pattern = r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}"
#     # Pattern B matches broken wrapped lines: "10 May 10 May"
#     wrapped_date_pattern = r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{1,2}\s+[A-Za-z]{3}"
#     # ───────────────────────────────────────────────────────────────────────

#     num_lines = len(lines)
#     i = 0

#     while i < num_lines:
#         line = lines[i].strip()
#         parts = line.split()

#         is_full_line = bool(re.match(full_line_pattern, line))
#         is_wrapped_line = bool(re.match(wrapped_date_pattern, line))

#         # If it doesn't match either pattern, step down to the next line
#         if not (is_full_line or is_wrapped_line):
#             i += 1
#             continue

#         try:
#             # ─── CASE 1: THE DATE IS WRAPPED ONTO THE NEXT LINE (e.g., 10 May) ───
#             if is_wrapped_line and not is_full_line:
#                 # Look ahead at the next line to find the years "2025 2025"
#                 if i + 1 < num_lines:
#                     next_line = lines[i + 1].strip()
#                     next_parts = next_line.split()
                    
#                     # Confirm the next line starts with two 4-digit years
#                     if len(next_parts) >= 2 and next_parts[0].isdigit() and len(next_parts[0]) == 4:
#                         # Stitch the year back into our current parts list manually!
#                         # Converts ["10", "May", "10", "May", ...] 
#                         # Into ["10", "May", "2025", "10", "May", "2025", ...]
#                         year_1 = next_parts[0]
#                         year_2 = next_parts[1]
                        
#                         parts = parts[0:2] + [year_1] + parts[2:4] + [year_2] + parts[4:]
                        
#                         # Remove the year tokens from the next line so look-ahead doesn't catch them as narration noise
#                         lines[i + 1] = " ".join(next_parts[2:])
            
#             # Now `parts` contains a completely unified layout, regardless of how it started!
#             if len(parts) < 8:
#                 i += 1
#                 continue

#             # Reconstruct standard date formatting
#             gl_date_str = f"{parts[0]} {parts[1]} {parts[2]}"
#             val_date_str = f"{parts[3]} {parts[4]} {parts[5]}"

#             gl_date = datetime.strptime(gl_date_str, "%d %b %Y").strftime("%d-%m-%Y")
#             value_date = datetime.strptime(val_date_str, "%d %b %Y").strftime("%d-%m-%Y")

#             # Extract final balance values from the right side edge tokens
#             balance_token = parts[-1]
#             amount_token = parts[-2]

#             balance = clean_amount(balance_token)
#             amount = clean_amount(amount_token)

#             # Gather narration pieces from the current line
#             narration_pieces = parts[6:-2]

#             # ─── LOOK-AHEAD TRACKING FOR MULTI-LINE DESCRIPTIONS ───
#             j = i + 1
#             while j < num_lines:
#                 next_line = lines[j].strip()
                
#                 if not next_line or any(k in next_line for k in ["Txn Date", "Date No.", "Balance as on"]):
#                     j += 1
#                     continue
                
#                 # Stop if the next line is the start of a completely new transaction
#                 if re.match(full_line_pattern, next_line) or re.match(wrapped_date_pattern, next_line):
#                     break
                
#                 narration_pieces.append(next_line)
#                 j += 1

#             full_narration = " ".join(narration_pieces)

#             transactions.append({
#                 "gl_date": gl_date,
#                 "value_date": value_date,
#                 "narration": full_narration,
#                 "amount": amount,
#                 "balance": balance
#             })

#             i = j  # Fast-forward our main loop index pointer cleanly

#         except Exception:
#             i += 1
#             continue

#     determine_dr_cr(transactions, opening_balance)
#     return transactions


# def clean_amount(value):
#     value = value.replace(",", "")
#     value = value.replace("Cr", "")
#     value = value.replace("Dr", "")
#     value = value.strip()
#     return float(value)


# def parse_opening_balance(text):
#     clean_text = text.replace("(cid:9)", " ")
#     match = re.search(
#         r"Balance\s+as\s+on\s+[^:]+:\s*([0-9,]+(?:\.\d+)?)",
#         clean_text,
#         re.IGNORECASE
#     )
#     if not match:
#         return 0.00
#     return clean_amount(match.group(1))


# def determine_dr_cr(transactions: list, opening_balance: float) -> list:
#     if not transactions:
#         return transactions

#     previous_balance = opening_balance if opening_balance is not None else 0.00
    
#     for txn in transactions:
#         current_balance = txn["balance"]
#         balance_change = round(current_balance - previous_balance, 2)

#         if abs(abs(balance_change) - txn["amount"]) > BALANCE_TOLERANCE:
#             if balance_change > 0:
#                 txn["type"] = "DEBIT"
#             elif balance_change < 0:
#                 txn["type"] = "CREDIT"
#             else:
#                 txn["type"] = "UNKNOWN"
#         elif balance_change > 0:
#             txn["type"] = "DEBIT" 
#         elif balance_change < 0:
#             txn["type"] = "CREDIT" 
#         else:
#             txn["type"] = "UNKNOWN"

#         previous_balance = current_balance

#     return transactions