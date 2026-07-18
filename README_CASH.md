# Ashramam Cash Receipts Ingestion Utility

This document outlines the expected Excel layout, column positions, date processing rules, name translations, and differences between the Cash Receipts utility and standard Bank Statement imports.

---

## 1. Sheet Structure & Physical Column Order
The cash parser reads **every sheet/tab** in the uploaded Excel workbook and parses the first **5 columns (Columns A to E)**. 

> [!NOTE]
> **Column Order**: The physical order of the columns **must be exact** because the parser processes rows by cell index (0 to 4), rather than matching headers by name.

| Column Index | Excel Column | Expected Field | Parsing / Cleaning Rules |
| :---: | :---: | :--- | :--- |
| **0** | **A** | **Date / Day** | Can be a full date (`dd.mm.yy`, `dd-mm-yyyy`) or a day number fragment (`02` or `2`). If blank, it carries forward the day of the previous row. |
| **1** | **B** | **Receipt No** | The unique receipt number (e.g. `2188`). **Must not be empty**, or the row will be skipped. |
| **2** | **C** | **Donor Name** | Written in Telugu or English. Telugu suffixes (`గారు`, `గారూ`) are automatically removed, and Telugu names are transliterated. |
| **3** | **D** | **Phone No** | Customer phone number. Ignored by the accounting engine (not saved in the vouchers list). |
| **4** | **E** | **Amount** | Total donation amount (₹). **Must not be empty**, or the row will be skipped. |

---

## 2. Date Processing Rules
To minimize data entry effort in Excel, the date column uses a smart inference engine:

1.  **Month Locking (Tab-Locked Month)**: 
    *   The parser looks at the **first valid row** of each sheet.
    *   It parses the date in Column A (e.g. `01.03.26`) to lock the **Year and Month** of the entire tab (e.g. March 2026).
2.  **Day Fragment Parsing**:
    *   If a row has a number (like `02` or `2`) in the Date column, the parser combines it with the locked month/year of the tab (creating `02-03-2026`).
3.  **Forward Date Carriage**:
    *   If the Date cell is empty, the parser carries forward the day from the previous row. This allows you to list a single date header once and leave subsequent rows blank until the date changes.

---

## 3. Telugu Name Transliteration & Lexicon Cache
*   **Transliteration**: Any Telugu text is processed through the **Aksharamukha** engine, transliterating it phonetically into English ASCII characters.
*   **Lexicon File**: A local cache file is stored under `~/.pdf2tally/telugu_mappings.json`.
    *   If a Telugu name or word (e.g. `శివార్పణం`) is translated, it is saved in this mapping file.
    *   Subsequent files will reuse the cached translation automatically instead of running the transliterator again.
    *   Phonetic accents/diacritics (like `ā`, `ś`, `ṇ`) are automatically stripped into clean English characters (e.g. `a`, `s`, `n`) to keep Tally ledger names clean.

---

## 4. Key Differences: Bank Statements vs. Cash Receipts

| Feature | Bank Statements | Ashramam Cash Receipts |
| :--- | :--- | :--- |
| **Input Formats** | PDF text files (SBI, BOB, etc.) or Bank Excel sheets | Standard Multi-Tab Excel Workbook |
| **Physical Column Order** | Flexible (mapped dynamically by header keywords) | **Strict** (columns A through E must match the expected index order) |
| **Voucher Types** | Hybrid: Debits (Payments) and Credits (Receipts) | **Exclusively Receipts** (Debit to Cash ledger, Credit to Donation ledger) |
| **Opening Balances** | Cumulative running balance rolled forward | Independent monthly balances (no opening balance roll-forward) |
| **Data Cleaning** | Cleans bank transaction descriptions | Transliterates Telugu donor names and cleans Telugu suffixes |
| **Missing Dates** | Bank PDFs print a date on every line | Excel sheet carries forward the date from the row above |
