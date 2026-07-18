

# parsers/cash_parser.py
import pandas as pd
from datetime import datetime
import re
import json
import os
from aksharamukha import transliterate
from services.logger import logger

PERSISTENT_DIR = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
os.makedirs(PERSISTENT_DIR, exist_ok=True)
MAPPING_FILE = os.path.join(PERSISTENT_DIR, "telugu_mappings.json")

def load_lexicon():
    default_lexicon = {
        "గారూ": "Garu", "గారు": "Garu", "గుప్తదానం": "Anonymous Donation",
        "శివార్పణం": "Shivarpanam", "సువార్పణం": "Suvarpanam"
    }
    
    # Bundle fallback: if persistent doesn't exist, try copying from bundled mappings
    if not os.path.exists(MAPPING_FILE):
        import sys
        if hasattr(sys, '_MEIPASS'):
            bundled_file = os.path.join(sys._MEIPASS, "telugu_mappings.json")
        else:
            bundled_file = "telugu_mappings.json"
            
        if os.path.exists(bundled_file):
            import shutil
            try:
                shutil.copy(bundled_file, MAPPING_FILE)
            except Exception:
                pass
                
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_lexicon
    return default_lexicon

def save_lexicon(lexicon_data):
    try:
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(lexicon_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def strip_diacritics_inline(text):
    """
    Directly catches and replaces custom ISO/IAST phonetic markers 
    with standard plain English ASCII characters.
    """
    if not text:
        return text
    replacements = {
        'ā': 'a', 'ā́': 'a', 'ā̀': 'a', 'ā̂': 'a',
        'ē': 'e', 'ḗ': 'e', 'ḕ': 'e', 'ē̂': 'e',
        'ī': 'i', 'ī́': 'i', 'ī̀': 'i', 'ī̂': 'i',
        'ō': 'o', 'ṓ': 'o', 'ō̂': 'o',
        'ū': 'u', 'ū́': 'u', 'ū̀': 'u', 'ū̂': 'u',
        'ṃ': 'm', 'ṁ': 'm', 'ṅ': 'n', 'ñ': 'n', 'ṇ': 'n',
        'ś': 's', 'ṣ': 's', 
        'ṭ': 't', 'ḍ': 'd', 'ṛ': 'r', 'ḷ': 'l', '̱': ''
    }
    cleaned = text
    for special_char, plain_char in replacements.items():
        cleaned = cleaned.replace(special_char, plain_char)
        cleaned = cleaned.replace(special_char.upper(), plain_char.upper())
    return cleaned

def check_is_flagged(english_text):
    if not english_text:
        return False
    # Check if any un-stripped diacritic markers are still hanging out
    if any(ord(c) > 127 or c in "āēīōūṃṁṅñṇśṣṭḍṛḷ̱" for c in english_text.lower()):
        return True
    words = english_text.split()
    if any(len(w) > 15 for w in words):
        return True
    return False

def clean_telugu_name(text):
    if not isinstance(text, str) or not text.strip():
        return "Unknown Person", False
        
    raw_input = text.strip()
    raw_input = raw_input.replace("గారూ", "").replace("గారు", "")
    raw_input = raw_input.replace("-", " ").replace("—", " ")
    raw_input = re.sub(r'\s+', ' ', raw_input).strip()
    
    lexicon = load_lexicon()
    
    # 1. Check exact cache match
    if raw_input in lexicon:
        cached_val = lexicon[raw_input]
        # Force a safety pass over your cache entries to clean up pre-existing accents
        cleaned_cached_val = strip_diacritics_inline(cached_val)
        
        # if cleaned_cached_val != cached_val:
        #     lexicon[raw_input] = cleaned_cached_val
        #     save_lexicon(lexicon)
        # If the cached version still has flags, force it to be reviewed again
        if check_is_flagged(cached_val):
            return cleaned_cached_val, True
        return cleaned_cached_val, False
        
    words = raw_input.split()
    translated_words = []
    triggered_fallback = False
    
    for word in words:
        if word in lexicon:
            translated_words.append(lexicon[word])
        else:
            sub_word = word
            for k, v in lexicon.items():
                if k in sub_word and k != sub_word:
                    sub_word = sub_word.replace(k, v)
            
            if any(ord(c) > 127 for c in sub_word):
                triggered_fallback = True
                telugu_segment = "".join([c for c in sub_word if ord(c) > 127])
                english_initials = "".join([c for c in sub_word if ord(c) <= 127])
                
                try:
                    transliterated_segment = transliterate.process('Telugu', 'ISO', telugu_segment)
                except Exception as trans_err:
                    logger.error(
                        f"Aksharamukha transliteration failed for segment '{telugu_segment}': {str(trans_err)}. "
                        "Using fallback original text."
                    )
                    transliterated_segment = telugu_segment
                sub_word = (english_initials + " " + transliterated_segment).strip()
                
                # Save the individual word translation immediately to the lexicon
                word_clean = strip_diacritics_inline(sub_word).title()
                if word not in lexicon:
                    lexicon[word] = word_clean
                    save_lexicon(lexicon)
                
            translated_words.append(sub_word)
            
    raw_transliterated_name = " ".join(translated_words).strip()
    raw_transliterated_name = re.sub(r'(?i)\bgaru\b|\bgarū\b', '', raw_transliterated_name).strip()
    
    # Check for special characters/long words BEFORE stripping them out
    should_flag_user = check_is_flagged(raw_transliterated_name)
            
    # Now create the clean standard version for the accounting engine fallback
    final_name = strip_diacritics_inline(raw_transliterated_name)
    
    final_name = re.sub(r'\s+', ' ', final_name).title()
    
    if triggered_fallback:
        return final_name, True
        
    return final_name, should_flag_user

def parse_cash_workbook(file_stream, start_date_cutoff=None):
    """
    Parses workbook rows sequentially.
    If start_date_cutoff (datetime.date) is provided, skips any transaction dated before it.
    """
    logger.info(f"parse_cash_workbook: Starting Excel cash ledger conversion (Date Cutoff: {start_date_cutoff}).")
    all_transactions = []
    
    try:
        xl = pd.ExcelFile(file_stream)
        logger.info(f"parse_cash_workbook: Excel file loaded successfully. Sheet names: {xl.sheet_names}")
    except Exception as xl_err:
        logger.error(f"parse_cash_workbook: Failed to open Excel file. Error: {str(xl_err)}", exc_info=True)
        raise

    flagged_audit_records = {}
    all_names_map = {}
    cutoff_dt = None
    if start_date_cutoff:
        cutoff_dt = datetime.combine(start_date_cutoff, datetime.min.time())
    
    for sheet_name in xl.sheet_names:
        logger.info(f"parse_cash_workbook: Reading sheet '{sheet_name}'...")
        try:
            df = xl.parse(sheet_name, header=None).dropna(how='all').reset_index(drop=True)
        except Exception as sheet_err:
            logger.error(f"parse_cash_workbook: Failed to parse sheet '{sheet_name}'. Error: {str(sheet_err)}", exc_info=True)
            continue
            
        if df.shape[1] < 5:
            logger.warning(f"parse_cash_workbook: Sheet '{sheet_name}' skipped - column count ({df.shape[1]}) is less than 5.")
            continue
            
        df = df.iloc[:, :5]

        # --- TAB-LOCKED MONTH INFERENCE ---
        first_valid_row = None
        for idx, row in df.iterrows():
            vals = list(row.values)
            row_str = " ".join(map(str, vals)).lower()
            if "date" in row_str or "amount" in row_str:
                continue
            if pd.notna(vals[0]) and pd.notna(vals[1]) and pd.notna(vals[4]):
                first_valid_row = vals
                break
                
        if first_valid_row is None:
            logger.warning(f"parse_cash_workbook: Sheet '{sheet_name}' has no valid initial row to infer reference date.")
            continue
            
        raw_ref_date = first_valid_row[0]
        parsed_ref_dt = None
        
        if isinstance(raw_ref_date, datetime):
            parsed_ref_dt = raw_ref_date
        else:
            clean_ref_str = re.sub(r'[-./\s]+', '-', str(raw_ref_date).strip())
            for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y"):
                try:
                    parsed_ref_dt = datetime.strptime(clean_ref_str, fmt)
                    break
                except ValueError:
                    continue
                    
        if not parsed_ref_dt:
            logger.warning(f"parse_cash_workbook: Sheet '{sheet_name}' reference date '{raw_ref_date}' could not be parsed. Skipping sheet.")
            continue
            
        locked_month_label = parsed_ref_dt.strftime("%b %Y")
        logger.info(f"parse_cash_workbook: Sheet '{sheet_name}' inferred reference month: {locked_month_label}")
        
        # Track the running day across rows to carry forward blank date cells
        running_row_day = parsed_ref_dt.day
        sheet_tx_count = 0
        
        for idx, row in df.iterrows():
            vals = list(row.values)
            if pd.isna(vals[1]) and pd.isna(vals[4]):
                continue
            if pd.isna(vals[1]) or pd.isna(vals[4]):
                continue

            row_str = " ".join(map(str, vals)).lower()
            if "date" in row_str or "rc.no" in row_str or "amount" in row_str:
                continue

            try:
                # --- PROCESS DYNAMIC ROW DAY ---
                raw_cell_0 = vals[0]
                
                if isinstance(raw_cell_0, datetime):
                    running_row_day = raw_cell_0.day
                elif pd.notna(raw_cell_0) and str(raw_cell_0).strip():
                    clean_date_digits = re.sub(r'[-./\s]+', '-', str(raw_cell_0).strip())
                    is_date_fragment = bool(re.match(r'^\d+$|^\d+-\d+$|^\d+-\d+-$', clean_date_digits))
                    
                    if not is_date_fragment:
                        for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
                            try:
                                dt = datetime.strptime(clean_date_digits, fmt)
                                running_row_day = dt.day
                                break
                            except ValueError:
                                continue
                    else:
                        try:
                            day_match = re.search(r'\d+', clean_date_digits)
                            if day_match:
                                running_row_day = int(day_match.group())
                        except ValueError:
                            pass

                try:
                    current_txn_dt = parsed_ref_dt.replace(day=running_row_day)
                except Exception:
                    current_txn_dt = parsed_ref_dt

                # --- FILTRATION BOUNDARY CHECK ---
                if cutoff_dt and current_txn_dt < cutoff_dt:
                    continue 

                raw_name_cell = str(vals[2]).strip() if pd.notna(vals[2]) else ""
                
                # Clean the Telugu name suffix before processing and displaying in the UI
                clean_telugu = raw_name_cell.replace("గారూ", "").replace("గారు", "")
                clean_telugu = clean_telugu.replace("-", " ").replace("—", " ")
                clean_telugu = re.sub(r'\s+', ' ', clean_telugu).strip()
                
                english_name, is_name_flagged = clean_telugu_name(clean_telugu)
                
                # Save to master mapping list for the complete inspection window
                if clean_telugu:
                    all_names_map[clean_telugu] = english_name
                    
                if is_name_flagged or check_is_flagged(english_name):
                    flagged_audit_records[clean_telugu] = english_name

                # Parse receipt number and amount safely
                try:
                    rc_no = str(int(float(vals[1])))
                except Exception:
                    rc_no = str(vals[1]).strip()

                try:
                    amount = int(float(str(vals[4]).replace(",", "")))
                except Exception:
                    amount = 0

                all_transactions.append({
                    "gl_date": current_txn_dt.strftime("%d-%m-%Y"),
                    "month_label": locked_month_label,
                    "rc_no": rc_no,
                    "raw_telugu_name": clean_telugu,
                    "donor_name": english_name,
                    "amount": amount,
                    "narration": f"being donation received rt no : {rc_no} from {english_name}",
                    "type": "DEBIT"
                })
                sheet_tx_count += 1

            except Exception as row_err:
                logger.error(
                    f"parse_cash_workbook: Error processing sheet '{sheet_name}' at row index {idx}. "
                    f"Values: {vals}. Error: {str(row_err)}", exc_info=True
                )
                # Re-raise to fail conversion but now the log tells us exactly where we failed
                raise

        logger.info(f"parse_cash_workbook: Finished sheet '{sheet_name}'. Successfully parsed {sheet_tx_count} transactions.")
                
    logger.info(
        f"parse_cash_workbook: Completed cash workbook conversion. "
        f"Total transactions parsed: {len(all_transactions)}, flagged names: {len(flagged_audit_records)}"
    )
    return all_transactions, flagged_audit_records , all_names_map