from parsers.router import get_slicer_function

def process_strategy(extracted_text, parse_opening_func, bank_type, boundary_date_obj):
    """
    Continuation Strategy: Suppresses opening balance and routes raw text 
    directly to the bank-specific slicer modules.
    """
    print(f"-> Strategy Executing: Routing text layer to specialized {bank_type} slicing filters.")
    opening_bal = None  # Suppress opening balance for continuations
    
    slicer_func = get_slicer_function(bank_type)
    if slicer_func:
        sanitized_text = slicer_func(extracted_text, boundary_date_obj)
    else:
        # Fallback to unsliced text if no slicer is registered
        sanitized_text = extracted_text
        
    return sanitized_text, opening_bal