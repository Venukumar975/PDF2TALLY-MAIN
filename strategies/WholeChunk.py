def process_strategy(extracted_text, parse_opening_func):
    """
    Whole Document Strategy: Keep full text timeline and parse opening balance normally.
    """
    print("-> Strategy Executing: Processing entire document with standalone opening balance.")
    opening_bal = parse_opening_func(extracted_text)
    return extracted_text, opening_bal