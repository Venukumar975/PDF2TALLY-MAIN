import re
from typing import List

BALANCE_TOLERANCE = 0.01


def parse_transactions(text, opening_balance=None):

    transactions = [] # This list holds the processed transactions so they can be directly converted to Tally-XML.

    lines = text.split("\n")
    
    is_fallback = False
    if opening_balance is None:
        opening_balance = parse_opening_balance(text)
        if opening_balance is None:
            opening_balance = 0.00
            is_fallback = True
    
    """ 
    Now Our Opening_balance will hold a pure floating pt no like -12800.0 or 12800.0 depending on Cr/Dr.
    
    """
    pattern = (
        r"^\d{2}-\d{2}-\d{4}\s+\d{2}-\d{2}-\d{4}"
    )
    """ 
    02-04-2025 01-04-2025 UPI/7741$$$$$$7/08:52:23/UPI/########@ybl/Paym 3,000.00 14,968.42Cr CDCI CDCI
    
    So the above variable pattern  is used to only filter the transactions from bank statment like if we were able
    to find 2 dates at the start of a new line then that line is considered as a transaction
    Eg;
     `01-05-2025 06-08-2025 ###############` => this is considered since Our regex matches the dates
     ` Page 4 01-05-2025 06-08-2025 ###############` => this is avoided since the new line didnt started with a date ( but with Page 4 so it is avaoided).
    """
    for line in lines:

        line = line.strip() # Removing extra white spaces on left and right of our transaction.

        if not re.match(pattern, line):
            continue

        parts = line.split() 
        
        """" 
        Let's say the parser finds this valid line:
        "01-04-2026   01-04-2026   IMPS/610214/WAGES/MNG   5,000.00   1,45,000.00Cr"
         
        When Python executes line.split(), it strips out all those extra spaces and
        chops the line into a clean list of individual text pieces (called "tokens"):
        
        parts = [
                    "01-04-2026",             # parts[0]   -- this is the gl date
                    "01-04-2026",             # parts[1]   -- this is value date
                    "IMPS/610214/WAGES/MNG",  # parts[2]   -- this is the Narration
                    "5,000.00",               # parts[3]   -- this is either Credit / Debit 
                    "1,45,000.00Cr"           # parts[4]   -- this is our balance
                ]
         
        """

        try:

            gl_date = parts[0]
            value_date = parts[1]

            balance_token = None 

            for p in reversed(parts):

                if p.endswith("Cr") or p.endswith("Dr"):

                    balance_token = p
                    break
                

            if not balance_token:  # IF the transaction didnt have any balance then we wont consider this transaction as valid and we will skip it.
                continue
            
            """ 
            The above for loop tries to find the balance col like it tries to find "12800.90 Cr" and once
            it finds it passes it to clean_balance to convert it to a clean float value.
            """

            balance = clean_balance(balance_token) # We get a clean Pure floating pt no ( its sign depends whether it is Cr/Dr .)

            balance_index = parts.index(balance_token) # Now we will infer the index position of balance indx , so since in BOB the transaction amount is just before balance we can get that using this ind.

            amount = clean_amount(
                parts[balance_index - 1]
            ) # Getting transaction amount using balance ind ( it doesnt have Cr/Dr ) so we just pass it to `clean_amount`.

            narration = " ".join(
                 parts[2:balance_index - 1]
             ) # simply picking up the narration -> parts[2:3]
            

            transactions.append({

                "gl_date": gl_date,

                "value_date": value_date,

                "narration": narration,

                "amount": amount,

                "balance": balance
            })

        except Exception:
            continue

    determine_dr_cr(transactions, opening_balance, is_fallback=is_fallback) # params are list , float -> transactions

    return transactions 


def clean_amount(value):

    value = value.replace(",", "")
    value = value.replace("Cr", "")
    value = value.replace("Dr", "")
    value = value.strip()

    return float(value)


def clean_balance(value):

    amount = clean_amount(value) # Now our actual balance say "12,800 Cr" gets converted to pure value ( floating point ) => 12800.0 , also strips whitespace or any commas.

    if value.strip().lower().endswith("dr"): # Now if the value is ending with "dr" then it means `DEBIT`(according to bank) so for our customer it is Credit , So its positive.
        return -amount # Tally reads negative floats as Debit entries

    return amount # If it is "cr" then it means opp of what we assumed above.So negative.# Tally reads positive floats as Credit entries


def parse_opening_balance(text):

    match = re.search(
        r"Opening Balance\s*:\s*([0-9,]+(?:\.\d+)?\s*(?:Cr|Dr)?)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = match.group(1) # group(1) gives us the value like "12,800 Cr" ( the actual balance ).
    return clean_balance(value) # Now sending this balance for further processing. We get pure Real number like 12800.00 or -12800.0 ( These are not Strings but floating pt no's )


def extract_bank_ledger_name(text):

    match = re.search(
        r"Account No\s*:\s*\d+\s+([^\n\r]+)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    name = match.group(1).strip()
    name = re.sub(r"^(?:INR|USD|AED|SAR)\s+", "", name, flags=re.IGNORECASE)

    return name or None


def determine_dr_cr(transactions: list, opening_balance: float, is_fallback=False) -> list:
    if not transactions:
        return transactions

    # If opening_balance is None, default to 0.00 so math doesn't break
    previous_balance = opening_balance if opening_balance is not None else 0.00
    is_negative_loan = (opening_balance is not None and opening_balance < 0)
    
    for idx, txn in enumerate(transactions): # Iteration over nested list of transactions
        if is_negative_loan:
            txn["balance"] = -abs(txn["balance"])
            
        if idx == 0 and is_fallback:
            txn["is_fallback_type"] = True
        """  
        [
            {
                gl_date:--,
                value_date:--,
                narration:"--",
                amount:--'
                balance:---
            },
            {
                gl_date:---,
                value_date:---,
                narration:"--",
                amount:--'
                balance:---
            },...
        ]
        """

        current_balance = txn["balance"]

        # Calculate row difference
        balance_change = round(current_balance - previous_balance, 2)

        if abs(abs(balance_change) - txn["amount"]) > BALANCE_TOLERANCE:
            txn["type"] = "UNKNOWN"
        elif balance_change > 0:
            # Tally Book perspective: An upward balance shift means money came in -> DEBIT
            txn["type"] = "DEBIT"
        elif balance_change < 0:
            # Tally Book perspective: A downward balance shift means money went out -> CREDIT
            txn["type"] = "CREDIT"
        else:
            txn["type"] = "UNKNOWN"

        previous_balance = current_balance

    return transactions