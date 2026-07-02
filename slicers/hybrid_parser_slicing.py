import re
from datetime import datetime

def slice_text_by_date(extracted_text, boundary_date_obj):
    """
    Slices generic statement text layers row-by-row.
    Drops any lines containing transaction dates falling strictly before the selected boundary date.
    """
    sliced_lines = []
    lines = extracted_text.split("\n")
    
    # Common date format regex patterns (with slashes replaced by hyphens)
    patterns = [
        (r"^(\d{2})[-/](\d{2})[-/](\d{4})", "%d-%m-%Y"),       # DD-MM-YYYY or DD/MM/YYYY
        (r"^(\d{4})[-/](\d{2})[-/](\d{2})", "%Y-%m-%d"),       # YYYY-MM-DD or YYYY/MM/DD
        (r"^(\d{2})[-/]([A-Za-z]{3})[-/](\d{4})", "%d-%b-%Y"), # DD-MMM-YYYY
        (r"^(\d{2})[-/](\d{2})[-/](\d{2})\b", "%d-%m-%y")      # DD-MM-YY
    ]
    
    if isinstance(boundary_date_obj, datetime):
        target_dt = boundary_date_obj
    else:
        target_dt = datetime.combine(boundary_date_obj, datetime.min.time())
        
    for line in lines:
        stripped = line.strip()
        matched = False
        skip_line = False
        
        # Normalize slashes to hyphens to make regex comparison simpler
        normalized_stripped = stripped.replace("/", "-")
        
        for pattern, fmt in patterns:
            match = re.match(pattern, normalized_stripped)
            if match:
                matched = True
                try:
                    # Clean and parse matched date string
                    matched_str = match.group(0)
                    line_date = datetime.strptime(matched_str, fmt)
                    if line_date < target_dt:
                        skip_line = True
                    break
                except ValueError:
                    pass
                    
        if matched and skip_line:
            continue
            
        sliced_lines.append(line)
        
    return "\n".join(sliced_lines)
