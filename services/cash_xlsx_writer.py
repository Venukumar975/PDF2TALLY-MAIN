# services/cash_xlsx_writer.py
import pandas as pd
import io

def build_nested_tally_sheets(transactions, cash_ledger="Cash", donation_ledger="Annadana Prasadam Donations Received"):
    """
    Compiles mapped transactions into an in-memory multi-sheet Excel package.
    Dynamically accepts custom ledger names from the UI form settings.
    """
    output = io.BytesIO()
    month_buckets = {}
    
    for t in transactions:
        m_key = t["month_label"].replace(" ", "_").upper()
        if m_key not in month_buckets:
            month_buckets[m_key] = []
            
        month_buckets[m_key].append({
            "Transaction Date": t["gl_date"],
            "Receipt Index No": t["rc_no"],
            "Donor (English Mapped)": t["donor_name"],
            "Amount (₹)": t["amount"],
            "Tally Voucher Type": "Receipt",
            "Debit Account (Cash Book)": cash_ledger,          # FIXED: Maps UI selection dynamically
            "Credit Account (Ledger Name)": donation_ledger,    # FIXED: Maps UI selection dynamically
            "Narration Generation": t["narration"]
        })
        
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for month_name, record_rows in month_buckets.items():
            df = pd.DataFrame(record_rows)
            sheet_title = month_name[:31] # Excel safety length boundary
            df.to_excel(writer, sheet_name=sheet_title, index=False)
            
            workbook = writer.book
            worksheet = writer.sheets[sheet_title]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
                
    return output.getvalue()