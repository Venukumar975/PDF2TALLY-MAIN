import os
import uuid
import logging
import pdfplumber
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Heuristic mapping keyword lists (lowercase)
DATE_KEYWORDS = ['date', 'txn date', 'transaction date', 'value date', 'post date', 'txn. date', 'value dt', 'val dt']
NARRATION_KEYWORDS = ['narration', 'description', 'particulars', 'remarks', 'details', 'transaction particulars']
DEBIT_KEYWORDS = ['debit', 'withdrawal', 'withdrawals', 'dr', 'payment', 'payments', 'debit amount', 'withdrawal(dr)', 'amount (dr)', 'withdrwal']
CREDIT_KEYWORDS = ['credit', 'deposit', 'deposits', 'cr', 'receipt', 'receipts', 'credit amount', 'deposit(cr)', 'amount (cr)']
BALANCE_KEYWORDS = ['balance', 'closing balance', 'available balance', 'running balance', 'bal', 'running bal']

def validate_pdf(file_path) -> tuple:
    """
    Checks if the PDF contains readable text and is not just scanned images.
    Returns (True, "...") if valid, (False, "...") if scanned or unreadable.
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return False, "This PDF contains no pages."
            
            has_text = False
            for page in pdf.pages:
                txt = page.extract_text()
                if txt and len(txt.strip()) > 50: # Expect at least 50 chars of text matrix
                    has_text = True
                    break
                    
            if not has_text:
                return False, "This PDF cannot be interpreted automatically because it appears to be scanned or contains no extractable text."
                
            return True, "PDF validation succeeded."
    except Exception as e:
        logger.error(f"Error validating PDF: {e}")
        return False, f"Failed to read PDF file: {str(e)}"

def extract_and_preview_tables(file_path) -> dict:
    """
    Extracts the first table from the PDF for preview and runs heuristics
    to auto-infer the column mapping.
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            # Look for the first page that contains a valid table
            target_table = None
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    for t in tables:
                        # Ensure table has at least header + 1 row, and at least 5 columns
                        if t and len(t) > 1 and len(t[0]) >= 5:
                            # Verify the table actually contains text data (is not entirely blank)
                            has_text = any(
                                any(str(cell).strip() for cell in row if cell is not None)
                                for row in t
                            )
                            if has_text:
                                target_table = t
                                break
                if target_table:
                    break
            
            if not target_table:
                return {
                    "success": False,
                    "message": "No usable transaction tables were detected in the statement."
                }
            
            # Clean empty rows and whitespace from table cells
            cleaned_table = []
            for row in target_table:
                if any(cell is not None for cell in row):
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    # Check if the row contains actual text
                    if any(cell != "" for cell in cleaned_row):
                        cleaned_table.append(cleaned_row)
            
            if len(cleaned_table) < 2:
                return {
                    "success": False,
                    "message": "Extracted table contains insufficient rows."
                }
                
            headers = cleaned_table[0]
            preview_rows = cleaned_table[1:11] # first 10 transaction rows
            
            # Heuristic auto-mapping
            auto_mapping = {
                "date": -1,
                "narration": -1,
                "debit": -1,
                "credit": -1,
                "balance": -1
            }
            
            # Helper search
            def find_match(cell_txt, keywords):
                txt_clean = re.sub(r'[^a-z\s/()_]', '', cell_txt.lower())
                return any(k in txt_clean for k in keywords)

            for col_idx, header in enumerate(headers):
                header_clean = header.strip()
                if not header_clean:
                    continue
                    
                if auto_mapping["date"] == -1 and find_match(header_clean, DATE_KEYWORDS):
                    auto_mapping["date"] = col_idx
                elif auto_mapping["narration"] == -1 and find_match(header_clean, NARRATION_KEYWORDS):
                    auto_mapping["narration"] = col_idx
                elif auto_mapping["debit"] == -1 and find_match(header_clean, DEBIT_KEYWORDS):
                    auto_mapping["debit"] = col_idx
                elif auto_mapping["credit"] == -1 and find_match(header_clean, CREDIT_KEYWORDS):
                    auto_mapping["credit"] = col_idx
                elif auto_mapping["balance"] == -1 and find_match(header_clean, BALANCE_KEYWORDS):
                    auto_mapping["balance"] = col_idx
            
            # Heuristic Quality Validation
            col_count = len(headers)
            low_confidence = col_count < 4 or any(idx == -1 for idx in [auto_mapping["date"], auto_mapping["narration"]])
            
            return {
                "success": True,
                "headers": headers,
                "preview_rows": preview_rows,
                "auto_mapping": auto_mapping,
                "low_confidence": low_confidence,
                "col_count": col_count
            }
            
    except Exception as e:
        logger.error(f"Error extracting tables: {e}")
        return {
            "success": False,
            "message": f"Table extraction process encountered an error: {str(e)}"
        }

def clean_amount(val_str) -> float:
    """Helper to parse raw amount strings safely into float values."""
    if not val_str:
        return 0.0
    clean = re.sub(r'[^0-9.\-]', '', val_str.replace(',', '').strip())
    if not clean or clean == '.' or clean == '-':
        return 0.0
    try:
        return abs(float(clean))
    except ValueError:
        return 0.0

def parse_date(date_str) -> str:
    """Attempts to parse varied date strings into standardized DD-MM-YYYY format."""
    if not date_str:
        return None
        
    # Standardize spaces and strip time if a colon is present (e.g., '01-04-2025 12:30')
    date_clean = date_str.strip()
    if ":" in date_clean:
        parts = date_clean.split()
        date_clean = " ".join([p for p in parts if ":" not in p])
        
    date_clean = re.sub(r'[^a-zA-Z0-9/\-\s]', '', date_clean).strip()
    # Normalize multiple spaces/tabs to a single space
    date_clean = re.sub(r'\s+', ' ', date_clean)
    
    date_formats = [
        "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d/%b/%Y", "%d-%B-%Y", "%d/%B/%Y",
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y",
        "%d %b %Y", "%d %B %Y", "%d %m %Y", "%b %d %Y", "%B %d %Y",
        "%d %b %y", "%d %B %y", "%d %m %y"
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_clean, fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass
            
    return None

def parse_hybrid_transactions(file_path, mapping, boundary_date=None) -> list:
    """
    Iterates through all pages, extracts tables, and maps columns to standardized transaction objects.
    """
    date_idx = int(mapping.get("date", -1))
    narr_idx = int(mapping.get("narration", -1))
    narr_idx_2 = int(mapping.get("narration_2", -1))
    debit_idx = int(mapping.get("debit", -1))
    credit_idx = int(mapping.get("credit", -1))
    balance_idx = int(mapping.get("balance", -1))
    
    if date_idx == -1 or narr_idx == -1:
        logger.error("Mapping requires at least a Date and Narration column.")
        return []
        
    transactions = []
    
    # Calculate the maximum active column index dynamically
    active_indices = [idx for idx in [date_idx, narr_idx, narr_idx_2, debit_idx, credit_idx, balance_idx] if idx != -1]
    max_idx = max(active_indices) if active_indices else -1
    
    try:
        with pdfplumber.open(file_path) as pdf:
            # We first extract headers to skip duplicate header rows on subsequent pages
            first_header = None
            
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                        
                    for row_idx, row in enumerate(table):
                        # Clean cells
                        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        if not any(cell != "" for cell in cleaned_row):
                            continue
                            
                        # If it matches the header row, skip it
                        if first_header is None:
                            first_header = cleaned_row
                            continue
                        elif cleaned_row == first_header:
                            continue
                        
                        # Validate row length matches mapping requirements
                        if len(cleaned_row) <= max_idx:
                            continue
                            
                        raw_date = cleaned_row[date_idx]
                        parsed_dt_str = parse_date(raw_date)
                        
                        # Extract debit / credit amounts
                        raw_debit = cleaned_row[debit_idx] if debit_idx != -1 else ""
                        raw_credit = cleaned_row[credit_idx] if credit_idx != -1 else ""
                        raw_balance = cleaned_row[balance_idx] if balance_idx != -1 else ""
                        
                        debit_val = clean_amount(raw_debit)
                        credit_val = clean_amount(raw_credit)
                        balance_val = clean_amount(raw_balance)
                        # Support negative/debit balances for loan/overdraft accounts
                        raw_bal_lower = raw_balance.lower()
                        if 'dr' in raw_bal_lower or 'od' in raw_bal_lower or '-' in raw_bal_lower or 'debit' in raw_bal_lower:
                            balance_val = -abs(balance_val)
                        
                        if parsed_dt_str:
                            # Date filter check
                            if boundary_date:
                                try:
                                    dt = datetime.strptime(parsed_dt_str, "%d-%m-%Y").date()
                                    if dt < boundary_date:
                                        continue
                                except ValueError:
                                    continue
                                    
                            narration = cleaned_row[narr_idx]
                            if narr_idx_2 != -1 and len(cleaned_row) > narr_idx_2:
                                secondary_val = cleaned_row[narr_idx_2]
                                if secondary_val:
                                    narration += " | " + secondary_val
                            
                            # Handle single-column amounts with indicator labels
                            # e.g., if Debit and Credit are mapped to the same index
                            if debit_idx == credit_idx and debit_idx != -1:
                                val_str = cleaned_row[debit_idx].lower()
                                amt = clean_amount(val_str)
                                if 'dr' in val_str or 'w' in val_str or '-' in val_str:
                                    debit_val = amt
                                    credit_val = 0.0
                                elif 'cr' in val_str or 'd' in val_str or '+' in val_str:
                                    debit_val = 0.0
                                    credit_val = amt
                                else:
                                    # Default to debit if unlabelled
                                    debit_val = amt
                                    credit_val = 0.0
                                    
                            # Determine transaction type based on values
                            txn_type = "DEBIT" # money in (receipt)
                            amount_val = 0.0
                            
                            if debit_val > 0.0:
                                txn_type = "CREDIT" # payment (cash leaves bank)
                                amount_val = debit_val
                            elif credit_val > 0.0:
                                txn_type = "DEBIT" # receipt (cash enters bank)
                                amount_val = credit_val
                                
                            transactions.append({
                                "gl_date": parsed_dt_str,
                                "narration": narration,
                                "amount": amount_val,
                                "type": txn_type,
                                "balance": balance_val
                            })
                        else:
                            # Continuation row (no date) -> append narration to previous transaction if not noise
                            if transactions:
                                extra_narration = ""
                                if len(cleaned_row) > narr_idx and cleaned_row[narr_idx]:
                                    extra_narration = cleaned_row[narr_idx]
                                if narr_idx_2 != -1 and len(cleaned_row) > narr_idx_2 and cleaned_row[narr_idx_2]:
                                    if extra_narration:
                                        extra_narration += " | " + cleaned_row[narr_idx_2]
                                    else:
                                        extra_narration = cleaned_row[narr_idx_2]
                                        
                                if extra_narration and extra_narration.lower() not in {"narration", "description", "particulars", "remarks", "details"}:
                                    transactions[-1]["narration"] += " " + extra_narration
                        
        return transactions
    except Exception as e:
        logger.error(f"Error parsing transactions: {e}")
        return []
