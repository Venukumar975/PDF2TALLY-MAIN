import re
from datetime import datetime

def slice_text_by_date(extracted_text, boundary_date_obj):
    """
    Slices Axis Bank text layers row-by-row.
    Drops any transactions falling strictly before the selected boundary date.
    """
    sliced_lines = []
    lines = extracted_text.split("\n")
    
    # Axis date format: DD-MM-YYYY (e.g. 15-11-2022)
    line_date_pattern = r"^(\d{2})-(\d{2})-(\d{4})"
    
    if isinstance(boundary_date_obj, datetime):
        target_dt = boundary_date_obj
    else:
        target_dt = datetime.combine(boundary_date_obj, datetime.min.time())

    for line in lines:
        stripped = line.strip()
        match = re.match(line_date_pattern, stripped)
        
        if match:
            try:
                line_date = datetime.strptime(match.group(0), "%d-%m-%Y")
                
                # If transaction date is older than target cutoff, slice it out
                if line_date < target_dt:
                    continue  
            except ValueError:
                pass  # Keep multi-line narrations safely
                
        sliced_lines.append(line)
        
    return "\n".join(sliced_lines)