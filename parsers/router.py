# Import your existing BOB parser
from parsers.bob_parser import parse_transactions as parse_bob, parse_opening_balance as parse_bob_opening
from parsers.sbi_parser import parse_transactions as parse_sbi, parse_opening_balance as parse_sbi_opening

# Import slicers
from slicers.BOB_slicing import slice_text_by_date as bob_slice
from slicers.SBI_slicing import slice_text_by_date as sbi_slice

# Dictionary containing routing settings for every bank profile
# This central registry maps each bank profile to its verification keywords, 
# transaction parsing function, opening balance extractor function, and text slicing function.
# Adding a new bank only requires adding a configuration block here.
BANK_CONFIGS = {
    "Bank of Baroda (BOB)": {
        "required_keywords": ["baroda"],
        "parser_function": parse_bob,
        "opening_balance_function": parse_bob_opening,
        "slicer_function": bob_slice
    },
    "State Bank of India (SBI)": {
        "required_keywords": ["state bank", "sbi"],
        "parser_function": parse_sbi,
        "opening_balance_function": parse_sbi_opening,
        "slicer_function": sbi_slice
    },
    # 🚀 To add a new bank in the future, just add 5 clean lines here:
    # "HDFC Bank": {
    #     "required_keywords": ["hdfc"],
    #     "parser_function": parse_hdfc,
    #     "opening_balance_function": parse_hdfc_opening,
    #     "slicer_function": hdfc_slice
    # }
}

def verify_bank_profile(selected_bank_profile, extracted_text):
    """
    Checks if the selected bank profile actually matches the text in the PDF.
    Returns True if it matches, False otherwise.
    """
    text_lower = extracted_text.lower() if extracted_text else ""
    config = BANK_CONFIGS.get(selected_bank_profile)
    
    if not config:
        return False
        
    # Check if at least one required keyword for this bank is present in the text
    return any(keyword in text_lower for keyword in config["required_keywords"])


def route_to_parser(selected_bank_profile, extracted_text):
    """
    Dynamically executes the correct parser based on the selected bank profile.
    """
    config = BANK_CONFIGS.get(selected_bank_profile)
    
    if not config or not config["parser_function"]:
        raise NotImplementedError(f"The parsing module for '{selected_bank_profile}' is not implemented yet.")
        
    # Run and return the output of the selected bank parser
    return config["parser_function"](extracted_text)


def get_opening_balance_parser(selected_bank_profile):
    """
    Dynamically returns the opening balance parser function for the selected bank profile.
    """
    config = BANK_CONFIGS.get(selected_bank_profile)
    
    if not config or not config["opening_balance_function"]:
        raise NotImplementedError(f"The opening balance parser for '{selected_bank_profile}' is not implemented.")
        
    return config["opening_balance_function"]


def get_slicer_function(selected_bank_profile):
    """
    Dynamically returns the text slicing function (for Continuation Strategy) for the bank profile.
    """
    config = BANK_CONFIGS.get(selected_bank_profile)
    if not config:
        return None
    return config.get("slicer_function")