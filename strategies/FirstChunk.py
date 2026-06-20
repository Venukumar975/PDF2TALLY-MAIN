def process_strategy(extracted_text, parse_opening_func):
    """
    First Chunk Strategy: Keep full text layer and parse opening balance normally.
    """
    print("➡️ Strategy Executing: Initializing first chunk of split series with starting balance.")
    opening_bal = parse_opening_func(extracted_text)
    return extracted_text, opening_bal