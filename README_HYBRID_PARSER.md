# Hybrid Generic / Generic Table Parser

This document outlines the extraction rules, column detection heuristics, row-by-row parsing logic, and table validation rules used by the **Generic Table** parsing engine.

---

## 1. Table Selection & Filtering Rules
When a PDF is uploaded to the Generic Table parser, `pdfplumber` extracts tables from Page 1. To bypass logos, header shapes, and other decorative vector graphics, the engine applies the following validation checks to select the correct transaction table:

1.  **Row Count Check**: The table must contain a header row and at least one transaction row (total rows $> 1$).
2.  **Column Count Check**: The table must have **at least 5 columns** (e.g., `SI`, `Date`, `Particulars`, `Amount`, `Balance`). Bank statements require at least 5 columns to represent standard transaction matrices.
3.  **Content Check**: The table must contain actual text values. Entirely empty tables, or boxes containing only whitespace/drawing lines (like the Union Bank logo box), are ignored.

> [!NOTE]
> **Decoy Table Bypassing**: If the first table detected on Page 1 is an empty box or a logo, the parser automatically skips it and continues scanning until it finds a table matching all of the rules above.

---

## 2. Column Auto-Mapping Heuristics
Once a valid table is selected, the parser inspects the header row (row index `0`) to auto-detect columns by matching cell text against these keyword lists:

| Mapped Field | Match Keywords (Case-Insensitive) |
| :--- | :--- |
| **Date** | `date`, `txn date`, `transaction date`, `value date`, `post date`, `txn. date`, `value dt`, `val dt` |
| **Narration** | `narration`, `description`, `particulars`, `remarks`, `details`, `transaction particulars` |
| **Debit** | `debit`, `withdrawal`, `withdrawals`, `dr`, `payment`, `payments`, `debit amount`, `amount (dr)` |
| **Credit** | `credit`, `deposit`, `deposits`, `cr`, `receipt`, `receipts`, `credit amount`, `amount (cr)` |
| **Balance** | `balance`, `closing balance`, `available balance`, `running balance`, `bal`, `running bal` |

---

## 3. Opening Balance Inference
If a `Balance` column is mapped, the engine automatically calculates the initial opening balance by backtracking from the first transaction row:

$$\text{Inferred Opening Balance} = \text{First Row Balance} + \text{First Row Debit} - \text{First Row Credit}$$

*   **Overdraft Support**: If the balance string contains indicators like `dr`, `od`, `-`, or `debit`, the parser treats the balance as a negative value.
*   **Single-Column Formats**: If Debit and Credit map to the same column, the parser inspects suffix labels (`dr`/`w`/`-` vs `cr`/`d`/`+`) to resolve the debit and credit components.

---

## 4. Transaction & Continuation Row Parsing
During parsing, the engine processes all tables page-by-page using the mapped columns:

### A. New Transaction Rows (Rows with Dates)
If a row contains a valid date in the `Date` column, it is treated as a new transaction. The date is standardized into `DD-MM-YYYY` using `parse_date` which supports formats like `DD-MM-YYYY`, `DD/MM/YYYY`, `DD-MMM-YYYY`, `YYYY-MM-DD`, etc.
*   **Debit Transactions**: Money leaving the bank (Cash out) is mapped to Tally as a **`CREDIT` (Payment)**.
*   **Credit Transactions**: Money entering the bank (Cash in) is mapped to Tally as a **`DEBIT` (Receipt)**.

### B. Continuation Rows (Rows without Dates)
If a row does not contain a date in the `Date` column but has text in the `Narration` column, the parser treats it as a continuation row. It cleans the text and appends it to the previous transaction's narration to compile multi-line descriptions:
```
[Txn 1] 01-05-2026 | UPIAB/020074062699/CR/THIRUVE
                     E/UBIN/9391652831-2@a          <-- Appended to Txn 1 Narration
```

---

## 5. Main Components in Codebase

*   **Core Parser**: [hybrid_parser.py](file:///c:/Users/pichi/Desktop/pdf2tally3_trial/pdf2tally/parsers/hybrid_parser.py) containing validation (`validate_pdf`), table extraction (`extract_and_preview_tables`), and row parsing (`parse_hybrid_transactions`).
*   **Routing Logic**: [routes_hybrid.py](file:///c:/Users/pichi/Desktop/pdf2tally3_trial/pdf2tally/routes_hybrid.py) managing the Flask endpoints for validation and conversion.
*   **XML Generation**: `services/xml_generator_hybrid_parser.py` converting transactions into Tally XML format.
