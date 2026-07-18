# Voucher Review Desk: Technical Architecture & Code Blueprint

This document details the frontend layout, XML Ingestion pipeline, search filters, Tally integration, Monthly Analysis, and night-mode rendering mechanics of the **Voucher Review Desk** feature.

> [!NOTE]
> **Column Order**: The physical order of columns in your Excel sheet **does not matter** for either tool (e.g., you can have the date column before the GSTIN column). The parser looks up columns strictly by their header name, not by column position (A, B, C, etc.).

---

## 1. UI Layout & DOM Design

The desktop is built as a split-grid container resembling the layout of Tally Prime.

### Layout HTML Structure (Simplified)
```html
<div class="review-desktop">
    <!-- 1. Top Tally Status Header -->
    <div class="tally-header">
        <div class="tally-header-title">Voucher Review Desk</div>
        <div id="review-imported-filename">No XML Loaded</div>
        <button class="tally-header-close" onclick="closeReviewDesk()">Close ×</button>
    </div>

    <div class="review-workspace-body">
        <!-- 2. Main Ingestion & Table Grid Area -->
        <div class="review-table-area">
            <!-- Ingestion Dropzone -->
            <div id="review-import-zone" class="review-dropzone">
                <p>Drag and drop your generated Tally XML file here to inspect</p>
                <input type="file" id="review-xml-file-input" accept=".xml" onchange="handleReviewXMLSelect(event)">
            </div>
            
            <!-- Virtual Scroll Viewport for Table -->
            <div id="review-table-container" class="hidden" style="flex: 1; display: flex; flex-direction: column;">
                <div class="table-column-headers">
                    <!-- Column Header Labels -->
                </div>
                <div id="review-virtual-viewport" tabindex="0" style="overflow-y: auto; flex: 1; position: relative;">
                    <div id="review-virtual-spacer" style="position: absolute; top: 0; left: 0; right: 0;"></div>
                    <div id="review-table-content" style="position: absolute; top: 0; left: 0; right: 0;"></div>
                </div>
            </div>
        </div>

        <!-- 3. Right Sidebar - Tally Functional Keys -->
        <div class="tally-sidebar">
            <button class="tally-btn-key" onclick="openPeriodModal()">
                <span class="key-shortcut">F2</span><span class="key-label">Period</span>
            </button>
            <button class="tally-btn-key" onclick="openReplaceLedgerModal()">
                <span class="key-shortcut">Y</span><span class="key-label">Replace Ledger</span>
            </button>
            <button class="tally-btn-key" onclick="openMonthlyAnalysisModal()">
                <span class="key-shortcut">M</span><span class="key-label">Monthly Analysis</span>
            </button>
        </div>
    </div>
</div>
```

### Day & Night Mode Variables (CSS Theme Switching)
The desk switches colors dynamically using the class `.tally-night-mode` appended directly to the `body` tag:

```css
/* LIGHT MODE (Default) */
.review-desktop {
    background: #ffffff;
    color: #333333;
}
.tally-btn-key {
    background: #f7fafc;
    border-color: #000000;
    color: #000000;
}

/* DARK MODE (Night Mode / Tally Prime Dark Style) */
body.tally-night-mode .review-desktop {
    background: #111827; /* Dark slate gray */
    color: #f3f4f6;
}
body.tally-night-mode .review-workspace-body {
    background: #111827;
}
body.tally-night-mode .review-table-area {
    border-right-color: #374151;
}
body.tally-night-mode .review-row {
    border-bottom-color: #1f2937;
}
body.tally-night-mode .review-row:hover {
    background-color: #1f2937;
}
```

---

## 2. Ingestion & XML Parsing Pipeline

When a Tally XML file is loaded in the desk, it is parsed directly on the client side using the browser's native `DOMParser` object.

### The XML Parsing Code (`loadReviewXML`)
```javascript
function loadReviewXML(xmlString, fileName) {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlString, "text/xml");
    
    reviewState.xmlDoc = xmlDoc;
    reviewState.originalFileName = fileName;

    // 1. Identify Cash / Bank ledger from the XML definition
    let bankName = "Unknown Account";
    const ledgerNodes = xmlDoc.getElementsByTagName("LEDGER");
    for (let j = 0; j < ledgerNodes.length; j++) {
        const lName = ledgerNodes[j].getAttribute("NAME") || "";
        // Match regex to identify Cash/Bank ledger type
        if (/bank|sbi|bob|axis|cash|hdfc|icici|tmb|idbi|pnb/i.test(lName)) {
            const opNode = ledgerNodes[j].querySelector("OPENINGBALANCE");
            if (opNode) {
                // Tally debit balances are negative in XML
                reviewState.openingBalance = -parseFloat(opNode.textContent || "0");
            }
        }
    }

    // 2. Parse individual Voucher transactions
    const voucherNodes = xmlDoc.getElementsByTagName("VOUCHER");
    reviewState.vouchers = [];
    
    for (let i = 0; i < voucherNodes.length; i++) {
        const node = voucherNodes[i];
        const dateVal = (node.querySelector("DATE")?.textContent || "").trim();
        const vchType = (node.querySelector("VOUCHERTYPENAME")?.textContent || "").trim();
        const vchNo = (node.querySelector("VOUCHERNUMBER")?.textContent || "").trim();
        const narration = (node.querySelector("NARRATION")?.textContent || "").trim();

        // Support both ledger entries tag styles
        const entries = node.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST");
        let particulars = "Suspense";
        let amount = 0.0;
        let type = "DEBIT";
        let bankDeemedPos = "Yes";

        entries.forEach(ent => {
            const ledger = (ent.querySelector("LEDGERNAME")?.textContent || "").trim();
            const rawAmt = parseFloat(ent.querySelector("AMOUNT")?.textContent || "0");
            
            // Check if this ledger represents the Cash/Bank account
            const isBank = /bank|sbi|bob|axis|cash|hdfc|icici|tmb|idbi|pnb/i.test(ledger);
            if (!isBank) {
                particulars = ledger; // The counter-ledger (Income / Expense / Party)
            } else {
                bankName = ledger;
                amount = Math.abs(rawAmt);
                bankDeemedPos = ent.querySelector("ISDEEMEDPOSITIVE")?.textContent || "Yes";
            }
        });

        // Determine if it was a Debit or Credit transaction based on bank side deemed sign
        if (bankDeemedPos.trim() === "Yes") {
            type = "DEBIT";  // Money came in (receipt)
        } else {
            type = "CREDIT"; // Money went out (payment)
        }

        reviewState.vouchers.push({
            id: i,
            node: node, // reference to DOM node for inline modifications
            date: dateVal, 
            particulars: particulars,
            narration: narration,
            vchType: vchType,
            vchNo: vchNo,
            debit: type === "DEBIT" ? amount : 0,
            credit: type === "CREDIT" ? amount : 0,
            modified: false
        });
    }
}
```

---

## 3. Search Filters & Bulk Actions

### A. Narration Keyword Filter
The standard narration filter (triggered via the UI search bar) allows users to search voucher narrations by text. Instead of doing exact string matches, the filter splits keywords by whitespace and constructs a flexible multi-word regex that allows matches even if there are multiple spaces between the words:

```javascript
// Triggered on narration input change / search confirmation
function confirmNarrationFilter() {
    const searchInput = document.getElementById("review-modal-narration-keyword");
    const val = searchInput.value.toLowerCase().trim();
    
    let narrationRegex = null;
    if (val) {
        // 1. Split keywords by whitespace
        const words = val.replace(/\s+/g, " ").split(" ").filter(Boolean);
        if (words.length > 0) {
            // 2. Escape special regex characters to prevent syntax errors
            const escapedWords = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
            // 3. Compile a regex joining words with flexible spacing (\s+)
            narrationRegex = new RegExp(escapedWords.join("\\s+"), "i");
        }
    }
    
    // 4. Verify matches exist before closing modal
    if (narrationRegex) {
        const tempFiltered = reviewState.vouchers.filter(vch => narrationRegex.test(vch.narration));
        if (tempFiltered.length === 0) {
            alert(`No results found for keyword: "${searchInput.value}"`);
            searchInput.focus();
            return;
        }
    }
    
    closeReviewModal("narration");
    applyReviewFilters(); // Runs filteredVouchers update and redraws grid
}
```

---

### B. Advanced Phrase Frequency Filter (Profiling)
The Advanced Filter is an automated text-mining system. It profiles all transactions, identifies highly repetitive patterns, and helps users isolate common groups of transaction types (like interest credits, card charges, or specific UPI users) for bulk ledger mappings.

#### 1. Stop-Words Definition & Normalization
To prevent system terms (like `upi`, `neft`, state/account codes) from clogging the frequency count, the filter utilizes a `Set` of stop-words and normalizes characters:

```javascript
const NARRATION_STOP_WORDS = new Set([
    "upi", "imps", "neft", "rtgs", "txn", "txnid", "payment", "transfer",
    "received", "receive", "credit", "credited", "debit", "debited", "bank",
    "ref", "reference", "to", "from", "by", "via", "cr", "dr", "trf",
    "account", "a/c", "upiid", "mobile", "transaction", "pay", "collect",
    "merchant", "online", "offline", "cash", "atm", "fund", "number", "id", "payme"
]);

function normalizeNarration(text) {
    if (!text) return "";
    let clean = text.toLowerCase();
    // Replace all special character symbols with whitespace
    const separators = /[\/\\\-_\@\.\,\:\;\(\)\[\]\{\}\|\+\=\*\#\%\&\'\"\?\!\<\>]/g;
    clean = clean.replace(separators, " ");
    clean = clean.replace(/\s+/g, " ");
    return clean.trim();
}

function isValidWord(word) {
    if (!word || word.length <= 1) return false;
    if (/^\d+$/.test(word)) {
        return /^\d{10}$/.test(word); // Keep 10-digit phone numbers, skip short digit strings
    }
    return !NARRATION_STOP_WORDS.has(word);
}
```

#### 2. Word Tokenization & Frequency Analysis
The system tokenizes each narration into single-word, two-word, and three-word phrases sequentially, counting their frequency occurrences across the active filter list:

```javascript
function generatePhrasesFromNarration(normalizedText) {
    if (!normalizedText) return [];
    const words = normalizedText.split(" ");
    const phrases = [];
    
    for (let i = 0; i < words.length; i++) {
        const w1 = words[i];
        
        // Single word token
        if (isValidWord(w1)) {
            phrases.push(w1);
            
            // Double word token
            if (i + 1 < words.length) {
                const w2 = words[i + 1];
                if (isValidWord(w2)) {
                    phrases.push(`${w1} ${w2}`);
                    
                    // Triple word token
                    if (i + 2 < words.length) {
                        const w3 = words[i + 2];
                        if (isValidWord(w3)) {
                            phrases.push(`${w1} ${w2} ${w3}`);
                        }
                    }
                }
            }
        }
    }
    return phrases;
}

function analyzeAllVoucherPhrases() {
    const freqMap = {};
    const baseSet = (reviewState.periodFilteredVouchers && reviewState.periodFilteredVouchers.length > 0) ?
        reviewState.periodFilteredVouchers :
        reviewState.vouchers;
        
    baseSet.forEach(vch => {
        if (!vch.normalizedNarration) {
            vch.normalizedNarration = normalizeNarration(vch.narration);
        }
        
        const phrases = generatePhrasesFromNarration(vch.normalizedNarration);
        const uniquePhrasesForVch = new Set(phrases); // Count only once per transaction
        
        uniquePhrasesForVch.forEach(phrase => {
            freqMap[phrase] = (freqMap[phrase] || 0) + 1;
        });
    });
    
    reviewState.phraseFrequencies = Object.keys(freqMap).map(phrase => {
        const wordCount = phrase.split(" ").length;
        return {
            phrase: phrase,
            count: freqMap[phrase],
            length: wordCount
        };
    });
    
    // Sort descending by occurrence counts
    reviewState.phraseFrequencies.sort((a, b) => b.count - a.count);
}
```

#### 3. Filtering the Phrase List
In the UI, the parsed phrase results are dynamically drawn inside the Advanced Filter list. Users can toggle minimum occurrence limits and filter by length checkboxes:

```javascript
function renderAdvancedPhrases() {
    const searchVal = document.getElementById("review-modal-advanced-search").value.toLowerCase().trim();
    const minFreq = parseInt(document.getElementById("review-modal-advanced-minfreq").value, 10) || 2;
    
    const showLen1 = document.getElementById("review-modal-advanced-len1").checked;
    const showLen2 = document.getElementById("review-modal-advanced-len2").checked;
    const showLen3 = document.getElementById("review-modal-advanced-len3").checked;
    
    const container = document.getElementById("review-modal-advanced-list");
    if (!container) return;
    
    const filteredPhrases = reviewState.phraseFrequencies.filter(item => {
        if (item.count < minFreq) return false;
        if (searchVal && !item.phrase.includes(searchVal)) return false;
        
        // Filter by word length criteria
        if (item.length === 1 && !showLen1) return false;
        if (item.length === 2 && !showLen2) return false;
        if (item.length === 3 && !showLen3) return false;
        
        return true;
    });

    // Draw elements inside 'container' with onClick triggers pointing to selectAdvancedPhrase(phrase)
}
```

---

### C. Replace Ledger Action (Bulk Mapping)
Allows replacing counter-party ledgers in bulk. This directly updates both the local UI state and the raw XML DOM node:

```javascript
function replaceLedgerForSelected(newLedgerName) {
    reviewState.selectedIds.forEach(id => {
        const vch = reviewState.vouchers.find(v => v.id === id);
        if (!vch) return;

        // 1. Update UI display state
        vch.particulars = newLedgerName;
        vch.modified = true;

        // 2. Direct modification on XML DOM tree nodes
        const partyLedNameNode = vch.node.querySelector("PARTYLEDGERNAME");
        if (partyLedNameNode) {
            partyLedNameNode.textContent = newLedgerName;
        }

        const entries = vch.node.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST");
        entries.forEach(ent => {
            const ledNameNode = ent.querySelector("LEDGERNAME");
            if (ledNameNode) {
                const currentName = ledNameNode.textContent || "";
                // Replace ONLY the non-cash ledger
                const isBank = /bank|sbi|bob|axis|cash|hdfc|icici|tmb|idbi|pnb/i.test(currentName);
                if (!isBank) {
                    ledNameNode.textContent = newLedgerName;
                }
            }
        });
    });
}
```

---

## 4. Monthly Analysis Engine

Calculates aggregate transaction summaries dynamically grouped by calendar month.

### Balance Calculation (Rolling vs. Independent)
*   **Standard Banks**: Rolled forward cumulatively starting from the account opening balance.
*   **Ashramam Cash Receipts**: Displays monthly totals independently (resets to 0 or manual base balance for each calendar month).

```javascript
function updateMonthlyAnalysisBalances() {
    const opBalVal = parseFloat(document.getElementById("review-monthly-opbal-input")?.value || "0.00");
    const isCashOnly = (reviewState.bankName || "").toLowerCase() === "cash";
    
    // Sort transactions chronologically
    const sortedVch = [...reviewState.vouchers].sort((a, b) => a.date.localeCompare(b.date));
    const monthlyRollup = {};

    sortedVch.forEach(vch => {
        const monthKey = vch.date.substring(0, 7); // "YYYY-MM"
        if (!monthlyRollup[monthKey]) {
            monthlyRollup[monthKey] = { debit: 0, credit: 0, count: 0 };
        }
        monthlyRollup[monthKey].debit += (vch.debit || 0);
        monthlyRollup[monthKey].credit += (vch.credit || 0);
        monthlyRollup[monthKey].count++;
    });

    let cumulativeBalance = opBalVal;
    
    Object.keys(monthlyRollup).sort().forEach(mKey => {
        const item = monthlyRollup[mKey];
        let displayBalance;

        if (isCashOnly) {
            // Ashramam mode: Reset balance calculation for each independent month
            displayBalance = opBalVal + item.debit - item.credit;
        } else {
            // Bank Mode: Cumulative rolled-forward balance
            cumulativeBalance += item.debit - item.credit;
            displayBalance = cumulativeBalance;
        }
        
        // Append row showing 'displayBalance' in Monthly Analysis table
    });
}
```

---

## 5. Tally Sync & Save Mechanisms

### Save API Flow
Saving does not use local desktop downloads. Instead, the modified XML DOM tree on the client side is serialized back to a text string, sent via HTTP POST to Flask's local cache `/api/review/save`, and then downloaded natively by the browser.

```javascript
async function saveReviewXML(exitAfterSave = false) {
    // 1. Serialize the modified XML DOM tree back to text
    const serializer = new XMLSerializer();
    const xmlText = serializer.serializeToString(reviewState.xmlDoc);

    // 2. POST the XML to Flask backend
    const response = await fetch("/api/review/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            xml_data: xmlText,
            filename: reviewState.originalFileName
        })
    });
    
    const result = await response.json();
    if (result.success) {
        // Trigger browser client-side download using a Blob
        const blob = new Blob([xmlText], { type: "text/xml" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = reviewState.originalFileName || "tally_export.xml";
        link.click();
        
        if (exitAfterSave) {
            closeReviewDesk();
        }
    }
}
```
