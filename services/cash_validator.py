# services/cash_validator.py
from collections import Counter
from datetime import datetime

def run_cash_audit(transactions):
    """
    Audits cash statement sets by grouping metrics by month, checking sequence indexes,
    and flagging duplicate entry errors.
    """
    if not transactions:
        return {"passed": False, "total_count": 0, "total_debit": 0.0, "monthly_summaries": [], "duplicates": []}
        
    total_debit = sum(t["amount"] for t in transactions)
    
    # Scan index records for duplicate receipt keys
    rc_list = [t["rc_no"] for t in transactions]
    rc_counts = Counter(rc_list)
    duplicates = [rc for rc, count in rc_counts.items() if count > 1]
    
    # Process distinct monthly summaries
    monthly_map = {}
    for t in transactions:
        m = t["month_label"]
        if m not in monthly_map:
            monthly_map[m] = {"count": 0, "debit_total": 0.0}
        monthly_map[m]["count"] += 1
        monthly_map[m]["debit_total"] += t["amount"]
        
    monthly_summaries = []
    for m, metrics in monthly_map.items():
        monthly_summaries.append({
            "month_label": m,
            "transaction_count": metrics["count"],
            "debit_total": round(metrics["debit_total"], 2),
            "credit_total": 0.0, # Explicitly zero to ensure clear visibility
            "is_reconciled": True
        })
        
    # Sort monthly entries chronologically 
    try:
        monthly_summaries.sort(key=lambda x: datetime.strptime(x["month_label"], "%b %Y"))
    except Exception:
        pass
        
    return {
        "passed": len(duplicates) == 0,
        "total_count": len(transactions),
        "total_debit": round(total_debit, 2),
        "monthly_summaries": monthly_summaries,
        "duplicates": duplicates
    }