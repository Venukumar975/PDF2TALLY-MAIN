import re
from datetime import datetime

def slice_text_by_date(extracted_text, boundary_date_obj):
    """
    Slices State Bank of India text layers, including wrapped multi-line dates.
    """
    sliced_lines = []
    lines = extracted_text.split("\n")
    
    # Matches SBI single or two digit layout headers: e.g., "1 Apr" or "10 May"
    line_date_pattern = r"^(\d{1,2})\s+([A-Za-z]{3})(?:\s+(\d{4}))?"
    current_year_fallback = "2025"
    
    if isinstance(boundary_date_obj, datetime):
        target_dt = boundary_date_obj
    else:
        target_dt = datetime.combine(boundary_date_obj, datetime.min.time())

    for line in lines:
        stripped = line.strip()
        match = re.match(line_date_pattern, stripped)
        
        if match:
            day = match.group(1)
            month = match.group(2)
            year = match.group(3) or current_year_fallback
            
            try:
                line_date = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                if line_date < target_dt:
                    continue  # Slice out historical row overlap
            except ValueError:
                pass
                
        sliced_lines.append(line)
        
    return "\n".join(sliced_lines)