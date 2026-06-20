import re
from datetime import datetime

def slice_text_by_date(extracted_text, boundary_date_obj):
    """
    Slices Bank of Baroda text layers row-by-row.
    Drops any transactions falling strictly before the selected boundary date.
    """
    sliced_lines = []
    lines = extracted_text.split("\n")
    
    # Matches the exact start of a standard BOB row: e.g., "01-04-2025" or "24-09-2025"
    line_date_pattern = r"^(\d{2})-(\d{2})-(\d{4})"
    
    # Ensure standard comparison across datetime formats safely
    if isinstance(boundary_date_obj, datetime):
        target_dt = boundary_date_obj
    else:
        target_dt = datetime.combine(boundary_date_obj, datetime.min.time())

    for line in lines:
        stripped = line.strip()
        match = re.match(line_date_pattern, stripped)
        
        if match:
            try:
                # Convert the line's matched date string to a true datetime object
                line_date = datetime.strptime(match.group(0), "%d-%m-%Y")
                
                # FIXED CRITICAL EDGE: If the row is strictly before the boundary window, slice it out
                if line_date < target_dt:
                    continue  
            except ValueError:
                pass  # Ignore line format exceptions to preserve multi-line narrations safely
                
        sliced_lines.append(line)
        
    return "\n".join(sliced_lines)