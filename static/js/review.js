/**
 * Voucher Review Desk - Standalone Fullscreen JavaScript Engine
 * Focus Mode Client Implementation
 */

const reviewState = {
    xmlDoc: null,
    originalFileName: "",
    vouchers: [],
    filteredVouchers: [],
    selectedIds: new Set(),
    focusedIndex: -1,
    lastSelectedIndex: -1,
    rowHeight: 35,
    visibleCount: 15,
    showNarration: false,
    openingBalance: 0.00,
    manualOpeningBalance: null,
    uniqueLedgers: new Set(),
    statusFilter: "all",
    advLen1: true,
    advLen2: true,
    advLen3: true,
    advMinFreq: 2,
    cachedCompanyLedgers: [],
    activeCompanyName: ""
};

// Autocomplete navigation state
let autocompleteIndex = -1;

// -------------------------------------------------------------
// INITIALIZATION
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    // Initialize Theme
    const savedTheme = localStorage.getItem("review-theme");
    if (savedTheme === "night") {
        document.body.classList.add("night-theme");
        const btnIcon = document.getElementById("theme-toggle-icon");
        const btnText = document.getElementById("theme-toggle-text");
        if (btnIcon) btnIcon.textContent = "☀️";
        if (btnText) btnText.textContent = "Day Mode";
    }


    // Setup drag & drop dropzone
    const dropzone = document.getElementById("review-import-zone");
    if (dropzone) {
        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.style.background = "#ebf8ff";
            dropzone.style.borderColor = "#005ea5";
        });
        dropzone.addEventListener("dragleave", () => {
            dropzone.style.background = "#f8fafc";
            dropzone.style.borderColor = "#002d5a";
        });
        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.style.background = "#f8fafc";
            dropzone.style.borderColor = "#002d5a";
            
            const file = e.dataTransfer.files[0];
            if (file && file.name.endsWith(".xml")) {
                loadReviewXMLFile(file);
            }
        });
    }

    // Keyboard events handler
    document.addEventListener("keydown", handleGlobalKeydown);
    
    // Focus viewport
    const viewport = document.getElementById("review-virtual-viewport");
    if (viewport) {
        viewport.focus();
    }

    // Load cached companies list on load
    loadCachedCompanies();
});

// Helper currency formatter
function formatCurrency(val) {
    return "₹" + parseFloat(val).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// -------------------------------------------------------------
// FILE LOADING
// -------------------------------------------------------------
function handleReviewXMLSelect(event) {
    const file = event.target.files[0];
    if (file) {
        loadReviewXMLFile(file);
    }
}

function loadReviewXMLFile(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        loadReviewXML(e.target.result, file.name);
    };
    reader.readAsText(file);
}

function loadReviewXML(xmlString, fileName) {
    try {
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlString, "text/xml");
        
        // Basic check for valid XML structure
        if (xmlDoc.getElementsByTagName("parsererror").length > 0) {
            alert("Error parsing XML file. Please check if the file format is correct.");
            return;
        }

        reviewState.xmlDoc = xmlDoc;
        reviewState.originalFileName = fileName;

        // Parse Opening Balance
        let openingBalance = 0.00;
        const ledgerNodes = xmlDoc.getElementsByTagName("LEDGER");
        for (let j = 0; j < ledgerNodes.length; j++) {
            const lName = ledgerNodes[j].getAttribute("NAME") || "";
            if (lName.toLowerCase().includes("bank") || lName.toLowerCase().includes("sbi") || lName.toLowerCase().includes("bob")) {
                const opNode = ledgerNodes[j].querySelector("OPENINGBALANCE");
                if (opNode) {
                    const val = parseFloat(opNode.textContent || "0");
                    openingBalance = -val; // Tally debit opening balances are negative in XML
                }
            }
        }
        reviewState.openingBalance = openingBalance;
        reviewState.manualOpeningBalance = null;
        reviewState.statusFilter = "all";
        reviewState.showNarration = false;

        // Reset elements
        const particularsHeader = document.getElementById("col-header-particulars");
        if (particularsHeader) {
            particularsHeader.style.flex = "1";
            particularsHeader.style.width = "auto";
        }
        const narrationHeader = document.getElementById("col-header-narration");
        if (narrationHeader) {
            narrationHeader.style.display = "none";
        }
        const label = document.getElementById("btn-tally-narration-label");
        if (label) {
            label.textContent = "Show Narration";
        }

        // Parse Vouchers list
        const voucherNodes = xmlDoc.getElementsByTagName("VOUCHER");
        reviewState.vouchers = [];
        reviewState.selectedIds.clear();
        reviewState.focusedIndex = -1;
        reviewState.lastSelectedIndex = -1;
        reviewState.uniqueLedgers.clear();

        let bankName = "Unknown Bank";

        for (let i = 0; i < voucherNodes.length; i++) {
            const node = voucherNodes[i];
            const dateVal = (node.querySelector("DATE")?.textContent || "").trim();
            const vchType = (node.querySelector("VOUCHERTYPENAME")?.textContent || "").trim();
            const vchNo = (node.querySelector("VOUCHERNUMBER")?.textContent || "").trim();
            const narration = (node.querySelector("NARRATION")?.textContent || "").trim();

            const entries = node.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST");
            let particulars = "Suspense";
            let amount = 0.0;
            let type = "DEBIT";

            let bankDeemedPos = "Yes";
            entries.forEach(ent => {
                const ledger = (ent.querySelector("LEDGERNAME")?.textContent || "").trim();
                reviewState.uniqueLedgers.add(ledger);

                const rawAmt = parseFloat(ent.querySelector("AMOUNT")?.textContent || "0");

                // Particulars is the non-bank account ledger
                const isBank = ledger.toLowerCase().includes("bank") || ledger.toLowerCase().includes("sbi") || ledger.toLowerCase().includes("bob");
                if (!isBank) {
                    particulars = ledger;
                } else {
                    bankName = ledger;
                    amount = Math.abs(rawAmt);
                    // Standard sign mirroring for Debit vs Credit
                    const isPos = ent.querySelector("ISDEEMEDPOSITIVE")?.textContent || "Yes";
                    bankDeemedPos = isPos;
                }
            });

            // Bank is DeemedPositive YES -> Debit in Tally, DeemedPositive NO -> Credit in Tally
            if (bankDeemedPos.trim() === "Yes") {
                type = "DEBIT";
            } else {
                type = "CREDIT";
            }

            const isSuspense = particulars.toLowerCase().includes("suspense");
            reviewState.vouchers.push({
                id: i,
                node: node,
                date: dateVal.length === 8 ? `${dateVal.substring(6, 8)}-${dateVal.substring(4, 6)}-${dateVal.substring(0, 4)}` : dateVal,
                rawDate: dateVal,
                particulars: particulars,
                originallySuspense: true,
                narration: narration,
                vchType: vchType,
                vchNo: vchNo,
                debit: type === "DEBIT" ? amount : 0,
                credit: type === "CREDIT" ? amount : 0,
                modified: !isSuspense
            });
        }



        // Compile narration phrase frequencies once at import
        analyzeAllVoucherPhrases();

        // Update details
        document.getElementById("review-imported-filename").textContent = `Imported XML: ${fileName}`;
        const bankProfileEl = document.getElementById("review-bank-profile");
        if (bankProfileEl) {
            bankProfileEl.textContent = `Bank: ${bankName}`;
            bankProfileEl.setAttribute("title", `Ensure your company bank name matches this name: ${bankName}`);
        }
        reviewState.bankName = bankName;
        
        // Find min/max dates
        const sortedDates = reviewState.vouchers.map(v => v.rawDate).filter(Boolean).sort();
        if (sortedDates.length > 0) {
            const minD = sortedDates[0];
            const maxD = sortedDates[sortedDates.length - 1];
            const fromStr = `${minD.substring(0, 4)}-${minD.substring(4, 6)}-${minD.substring(6, 8)}`;
            const toStr = `${maxD.substring(0, 4)}-${maxD.substring(4, 6)}-${maxD.substring(6, 8)}`;
            document.getElementById("review-modal-from-date").value = fromStr;
            document.getElementById("review-modal-to-date").value = toStr;
            document.getElementById("review-current-period").textContent = `Period: ${minD.substring(6, 8)}/${minD.substring(4, 6)}/${minD.substring(0, 4)} to ${maxD.substring(6, 8)}/${maxD.substring(4, 6)}/${maxD.substring(0, 4)}`;
        }

        document.getElementById("review-import-zone").classList.add("hidden");
        document.getElementById("review-table-container").classList.remove("hidden");

        applyReviewFilters();
        updateReviewStats();
        
        // Focus table container
        document.getElementById("review-virtual-viewport").focus();

    } catch (err) {
        console.error("Error loading review desk XML:", err);
        alert("Failed to parse XML contents: " + err.message);
    }
}

// -------------------------------------------------------------
// FILTER IMPLEMENTATION
// -------------------------------------------------------------
function applyReviewFilters() {
    const statusVal = reviewState.statusFilter || "all";
    const ledgerVal = document.getElementById("review-modal-ledger-select").value;
    const searchVal = document.getElementById("review-modal-narration-keyword").value.toLowerCase().trim();
    
    const fromVal = document.getElementById("review-modal-from-date").value.replace(/-/g, "");
    const toVal = document.getElementById("review-modal-to-date").value.replace(/-/g, "");
    
    // 1. Calculate Period filtered vouchers (For Voucher Stats)
    reviewState.periodFilteredVouchers = reviewState.vouchers.filter(vch => {
        // Date range filter
        if (fromVal && vch.rawDate < fromVal) return false;
        if (toVal && vch.rawDate > toVal) return false;
        return true;
    });

    // Helper to escape regex special characters
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Build flexible spacing regex if narration keyword is entered
    let narrationRegex = null;
    if (searchVal) {
        const words = searchVal.replace(/\s+/g, " ").split(" ").filter(Boolean);
        if (words.length > 0) {
            const escapedWords = words.map(w => escapeRegExp(w));
            narrationRegex = new RegExp(escapedWords.join("\\s+"), "i");
        }
    }
    
    // 2. Calculate Final filtered vouchers (For grid rendering and Filtration Stats)
    reviewState.filteredVouchers = reviewState.periodFilteredVouchers.filter(vch => {
        // Status filter
        if (statusVal === "suspense" && !vch.particulars.toLowerCase().includes("suspense")) {
            return false;
        }
        if (statusVal === "modified" && !vch.modified) {
            return false;
        }

        // Ledger filter
        if (ledgerVal !== "all" && vch.particulars !== ledgerVal) {
            return false;
        }
        
        // Narration keyword filter
        if (narrationRegex && !narrationRegex.test(vch.narration)) {
            return false;
        }

        // Advanced phrase filter
        if (reviewState.advancedPhraseFilter) {
            if (!vch.normalizedNarration) {
                vch.normalizedNarration = normalizeNarration(vch.narration);
            }
            if (!vch.normalizedNarration.includes(reviewState.advancedPhraseFilter)) {
                return false;
            }
        }
        
        return true;
    });
    
    // Reset focus index if it exceeds filtered count
    if (reviewState.focusedIndex >= reviewState.filteredVouchers.length) {
        reviewState.focusedIndex = reviewState.filteredVouchers.length - 1;
    }
    
    onReviewTableScroll();
    updateReviewStats();
}

// -------------------------------------------------------------
// VIRTUAL TABLE RENDERER
// -------------------------------------------------------------
function onReviewTableScroll() {
    const viewport = document.getElementById("review-virtual-viewport");
    const spacer = document.getElementById("review-virtual-spacer");
    const content = document.getElementById("review-virtual-content");
    const header = document.getElementById("review-table-header");
    
    if (!viewport || !spacer || !content) return;
    
    if (header) {
        header.style.width = "100%";
        header.scrollLeft = viewport.scrollLeft;
    }
    spacer.style.width = "100%";
    content.style.width = "100%";
    
    const count = reviewState.filteredVouchers.length;
    spacer.style.height = `${count * reviewState.rowHeight}px`;
    
    const scrollTop = viewport.scrollTop;
    const viewportHeight = viewport.clientHeight;
    reviewState.visibleCount = Math.ceil(viewportHeight / reviewState.rowHeight);
    
    const startIndex = Math.max(0, Math.floor(scrollTop / reviewState.rowHeight) - 2);
    const endIndex = Math.min(count, startIndex + reviewState.visibleCount + 5);
    
    let html = "";
    for (let i = startIndex; i < endIndex; i++) {
        const vch = reviewState.filteredVouchers[i];
        const isSelected = reviewState.selectedIds.has(vch.id);
        const isFocused = (reviewState.focusedIndex === i);
        
        const bgClass = isSelected ? "tally-selected" : "";
        const borderStyle = isFocused ? "outline: 2px solid #002d5a; outline-offset: -2px; z-index: 5;" : "";
        
        const debitText = vch.debit > 0 ? formatCurrency(vch.debit) : "-";
        const creditText = vch.credit > 0 ? formatCurrency(vch.credit) : "-";
        
        const modStyle = vch.modified ? "color: #2ecc71; font-weight: bold;" : "";
        
        const particularsCellStyles = reviewState.showNarration ?
            "width: 11%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-weight: 500; box-sizing: border-box;" :
            "flex: 1; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-weight: 500; box-sizing: border-box;";
            
        const narrationCellStyles = reviewState.showNarration ?
            "flex: 1; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box; display: block;" :
            "display: none;";
            
        html += `
            <div class="review-row ${bgClass}" onclick="onReviewRowClick(event, ${i})" style="display: flex; height: ${reviewState.rowHeight}px; align-items: center; border-bottom: 1px solid #eeeeee; font-size: 0.78rem; position: absolute; top: ${i * reviewState.rowHeight}px; left: 0; right: 0; cursor: pointer; user-select: none; ${borderStyle} ${modStyle}">
                <div style="width: 7%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.date}</div>
                <div style="${particularsCellStyles}" title="${vch.particulars}">${vch.particulars}</div>
                <div style="${narrationCellStyles}" title="${vch.narration}">${vch.narration}</div>
                <div style="width: 6%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.vchType}</div>
                <div style="width: 7%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.vchNo}</div>
                <div style="width: 9%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #10b981; box-sizing: border-box;">${debitText}</div>
                <div style="width: 9%; flex-shrink: 0; padding: 6px 8px; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #ef4444; box-sizing: border-box;">${creditText}</div>
            </div>
        `;
    }
    
    content.innerHTML = html;
}

// -------------------------------------------------------------
// STATISTICS UPDATES
// -------------------------------------------------------------
function updateReviewStats() {
    // If periodFilteredVouchers is not initialized yet (e.g. at startup before load)
    if (!reviewState.periodFilteredVouchers) {
        reviewState.periodFilteredVouchers = [...reviewState.vouchers];
    }

    // 1. Update Voucher Stats (based on periodFilteredVouchers)
    const vchTotal = reviewState.periodFilteredVouchers.length;
    const vchModified = reviewState.periodFilteredVouchers.filter(v => v.modified).length;
    const vchSuspense = reviewState.periodFilteredVouchers.filter(v => v.particulars.toLowerCase().includes("suspense")).length;
    
    document.getElementById("review-stat-total").textContent = vchTotal;
    document.getElementById("review-stat-modified").textContent = vchModified;
    document.getElementById("review-stat-suspense").textContent = vchSuspense;
    
    // Toggle active highlights on stats buttons based on reviewState.statusFilter
    const btnTotal = document.getElementById("btn-stats-total");
    const btnModified = document.getElementById("btn-stats-modified");
    const btnSuspense = document.getElementById("btn-stats-suspense");
    
    if (btnTotal) btnTotal.className = "stats-interactive-row";
    if (btnModified) btnModified.className = "stats-interactive-row";
    if (btnSuspense) btnSuspense.className = "stats-interactive-row";
    
    const currentStatus = reviewState.statusFilter || "all";
    if (currentStatus === "all") {
        if (btnTotal) btnTotal.classList.add("active-all");
    } else if (currentStatus === "modified") {
        if (btnModified) btnModified.classList.add("active-modified");
    } else if (currentStatus === "suspense") {
        if (btnSuspense) btnSuspense.classList.add("active-suspense");
    }
    
    // 2. Update Filtration Stats (based on final filteredVouchers)
    const ledgerVal = document.getElementById("review-modal-ledger-select").value;
    const searchVal = document.getElementById("review-modal-narration-keyword").value.trim();
    
    const isFiltered = (searchVal !== "" || reviewState.advancedPhraseFilter);
    const filterStatsCard = document.getElementById("review-filtration-stats");
    
    // Manage active phrase badge
    const activePhraseContainer = document.getElementById("filter-active-phrase-container");
    const activePhraseLabel = document.getElementById("filter-active-phrase-label");
    if (reviewState.advancedPhraseFilter) {
        if (activePhraseLabel) activePhraseLabel.textContent = `Phrase: ${reviewState.advancedPhraseFilter}`;
        if (activePhraseContainer) activePhraseContainer.classList.remove("hidden");
    } else {
        if (activePhraseContainer) activePhraseContainer.classList.add("hidden");
    }
    
    if (isFiltered) {
        const filTotal = reviewState.filteredVouchers.length;
        const filModified = reviewState.filteredVouchers.filter(v => v.modified).length;
        const filSuspense = reviewState.filteredVouchers.filter(v => v.particulars.toLowerCase().includes("suspense")).length;
        
        document.getElementById("filter-stat-total").textContent = filTotal;
        document.getElementById("filter-stat-modified").textContent = filModified;
        document.getElementById("filter-stat-suspense").textContent = filSuspense;
        
        if (filterStatsCard) {
            filterStatsCard.classList.remove("hidden");
        }
    } else {
        if (filterStatsCard) {
            filterStatsCard.classList.add("hidden");
        }
    }
}

function toggleStatsFilter(targetFilter) {
    if (targetFilter === "all") {
        reviewState.statusFilter = "all";
    } else if (targetFilter === "modified") {
        reviewState.statusFilter = (reviewState.statusFilter === "modified") ? "all" : "modified";
    } else if (targetFilter === "suspense") {
        reviewState.statusFilter = (reviewState.statusFilter === "suspense") ? "all" : "suspense";
    }
    applyReviewFilters();
}

// -------------------------------------------------------------
// MAPPINGS CACHE APPLICATION
// -------------------------------------------------------------


// -------------------------------------------------------------
// VOUCHER SELECTION ACTIONS
// -------------------------------------------------------------
function onReviewRowClick(event, index) {
    const vch = reviewState.filteredVouchers[index];
    if (!vch) return;
    
    if (event.ctrlKey) {
        // Toggle selection
        if (reviewState.selectedIds.has(vch.id)) {
            reviewState.selectedIds.delete(vch.id);
        } else {
            reviewState.selectedIds.add(vch.id);
        }
    } else if (event.shiftKey && reviewState.lastSelectedIndex !== -1) {
        // Range selection
        reviewState.selectedIds.clear();
        const start = Math.min(reviewState.lastSelectedIndex, index);
        const end = Math.max(reviewState.lastSelectedIndex, index);
        for (let j = start; j <= end; j++) {
            const cur = reviewState.filteredVouchers[j];
            if (cur) reviewState.selectedIds.add(cur.id);
        }
    } else {
        // Single selection
        reviewState.selectedIds.clear();
        reviewState.selectedIds.add(vch.id);
    }
    
    reviewState.focusedIndex = index;
    reviewState.lastSelectedIndex = index;
    
    onReviewTableScroll();
}

function updateVoucherLedger(vch, newLedgerName, triggerXMLUpdate = true) {
    vch.particulars = newLedgerName;
    vch.modified = true;
    
    if (triggerXMLUpdate && reviewState.xmlDoc) {
        // Update PARTYLEDGERNAME tag under VOUCHER
        const partyLedNameNode = vch.node.querySelector("PARTYLEDGERNAME");
        if (partyLedNameNode) {
            partyLedNameNode.textContent = newLedgerName;
        }

        const entries = vch.node.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST");
        entries.forEach(ent => {
            const ledNameNode = ent.querySelector("LEDGERNAME");
            if (ledNameNode) {
                const currentName = ledNameNode.textContent || "";
                const isBank = currentName.toLowerCase().includes("bank") || currentName.toLowerCase().includes("sbi") || currentName.toLowerCase().includes("bob");
                if (!isBank) {
                    ledNameNode.textContent = newLedgerName;
                }
            }
        });
    }
}

// -------------------------------------------------------------
// KEYBOARD COMMAND HANDLERS
// -------------------------------------------------------------
function handleGlobalKeydown(e) {
    // If user is focused on dialog inputs, disable shortcut triggers
    const activeEl = document.activeElement;
    const isInput = activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "SELECT");
    
    if (isInput) {
        if (e.key === "Escape") {
            // Escape exits the active filter modal
            closeActiveModal();
        } else if (e.key === "Enter") {
            // Enter key confirms active modal
            confirmActiveModal();
        } else if (activeEl.id === "review-modal-new-ledger") {
            handleAutocompleteKeydown(e);
        }
        return;
    }
    
    // Virtual table navigation keys
    if (e.key === "ArrowUp") {
        e.preventDefault();
        navigateFocus(-1, e.shiftKey);
    } else if (e.key === "ArrowDown") {
        e.preventDefault();
        navigateFocus(1, e.shiftKey);
    } else if (e.key === "PageUp") {
        e.preventDefault();
        navigateFocus(-8, e.shiftKey);
    } else if (e.key === "PageDown") {
        e.preventDefault();
        navigateFocus(8, e.shiftKey);
    } else if (e.key === "Home") {
        e.preventDefault();
        navigateFocus(-reviewState.filteredVouchers.length, e.shiftKey);
    } else if (e.key === "End") {
        e.preventDefault();
        navigateFocus(reviewState.filteredVouchers.length, e.shiftKey);
    } else if (e.key === " ") {
        // Spacebar toggles row selection
        e.preventDefault();
        toggleFocusedSelection();
    } else if (e.key === "Delete") {
        e.preventDefault();
        deleteSelectedVouchers();
    }
    
    // Tally Shortcuts
    if (e.key === "F2") {
        e.preventDefault();
        openPeriodModal();
    } else if (e.key === "F4") {
        e.preventDefault();
        openLedgerFilterModal();
    } else if (e.key === "5") {
        e.preventDefault();
        toggleReviewNarrationFromBtn();
    } else if (e.key === "6") {
        e.preventDefault();
        openNarrationFilterModal();
    } else if (e.key === "y" || e.key === "Y") {
        e.preventDefault();
        openReplaceLedgerModal();
    } else if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        openMonthlyAnalysisModal();
    } else if (e.key === "a" || e.key === "A") {
        e.preventDefault();
        openAdvancedFilterModal();
    } else if ((e.key === "s" || e.key === "S" || e.key === "e" || e.key === "E") && e.ctrlKey) {
        e.preventDefault();
        saveReviewXML();
    } else if (e.key === "Escape") {
        e.preventDefault();
        
        // First check if any active modal is open and close it
        if (closeActiveModal()) {
            return;
        }
        
        const ledgerVal = document.getElementById("review-modal-ledger-select").value;
        const searchVal = document.getElementById("review-modal-narration-keyword").value.trim();
        const currentStatus = reviewState.statusFilter || "suspense";
        
        const isFiltered = (ledgerVal !== "all" || searchVal !== "" || currentStatus !== "suspense" || reviewState.advancedPhraseFilter);
        
        if (isFiltered) {
            // Reset all active filtrations
            document.getElementById("review-modal-narration-keyword").value = "";
            document.getElementById("review-modal-ledger-select").value = "all";
            reviewState.statusFilter = "suspense"; // Default back to Suspense only
            reviewState.advancedPhraseFilter = null; // Clear advanced filter
            applyReviewFilters();
        }
    }
}

function navigateFocus(offset, shiftKey) {
    if (reviewState.filteredVouchers.length === 0) return;
    
    let oldFocus = reviewState.focusedIndex;
    let newFocus = oldFocus + offset;
    if (newFocus < 0) newFocus = 0;
    if (newFocus >= reviewState.filteredVouchers.length) {
        newFocus = reviewState.filteredVouchers.length - 1;
    }
    
    if (oldFocus === newFocus) return;
    
    reviewState.focusedIndex = newFocus;
    
    if (shiftKey) {
        if (reviewState.shiftAnchorIndex === undefined || reviewState.shiftAnchorIndex === -1) {
            reviewState.shiftAnchorIndex = oldFocus;
        }
        // Select range from anchor to newFocus
        reviewState.selectedIds.clear();
        const start = Math.min(reviewState.shiftAnchorIndex, newFocus);
        const end = Math.max(reviewState.shiftAnchorIndex, newFocus);
        for (let j = start; j <= end; j++) {
            const v = reviewState.filteredVouchers[j];
            if (v) reviewState.selectedIds.add(v.id);
        }
    } else {
        reviewState.shiftAnchorIndex = -1;
    }
    
    // Scroll viewport to show focused row
    const viewport = document.getElementById("review-virtual-viewport");
    if (viewport) {
        const rowTop = newFocus * reviewState.rowHeight;
        const rowBottom = rowTop + reviewState.rowHeight;
        const viewTop = viewport.scrollTop;
        const viewBottom = viewTop + viewport.clientHeight;
        
        if (rowTop < viewTop) {
            viewport.scrollTop = rowTop;
        } else if (rowBottom > viewBottom) {
            viewport.scrollTop = rowBottom - viewport.clientHeight;
        }
    }
    
    onReviewTableScroll();
}

function toggleFocusedSelection() {
    if (reviewState.focusedIndex === -1) return;
    const vch = reviewState.filteredVouchers[reviewState.focusedIndex];
    if (!vch) return;
    
    if (reviewState.selectedIds.has(vch.id)) {
        reviewState.selectedIds.delete(vch.id);
    } else {
        reviewState.selectedIds.add(vch.id);
    }
    onReviewTableScroll();
}

// -------------------------------------------------------------
// FILTER / SETTING MODALS POPUPS
// -------------------------------------------------------------
function closeReviewModal(modalKey) {
    const modal = document.getElementById(`review-modal-${modalKey}`);
    if (modal) {
        modal.classList.add("hidden");
    }
    // Return focus to table viewport
    document.getElementById("review-virtual-viewport").focus();
}

function closeActiveModal() {
    const modals = ["period", "ledger", "narration", "replace", "monthly", "advanced", "exit-confirm", "sync"];
    let closedAny = false;
    modals.forEach(m => {
        const el = document.getElementById(`review-modal-${m}`);
        if (el && !el.classList.contains("hidden")) {
            closeReviewModal(m);
            closedAny = true;
        }
    });
    return closedAny;
}

function confirmActiveModal() {
    const modals = [
        { id: "review-modal-period", confirm: confirmPeriodFilter },
        { id: "review-modal-ledger", confirm: confirmLedgerFilter },
        { id: "review-modal-narration", confirm: confirmNarrationFilter },
        { id: "review-modal-replace", confirm: confirmReplaceLedger }
    ];
    for (const m of modals) {
        const el = document.getElementById(m.id);
        if (el && !el.classList.contains("hidden")) {
            m.confirm();
            break;
        }
    }
}

// F2 Period Modal
function openPeriodModal() {
    const modal = document.getElementById("review-modal-period");
    if (!modal) return;
    modal.classList.remove("hidden");
    const input = document.getElementById("review-modal-from-date");
    setTimeout(() => input.focus(), 80);
}

function confirmPeriodFilter() {
    const fromInput = document.getElementById("review-modal-from-date").value;
    const toInput = document.getElementById("review-modal-to-date").value;
    
    const minD = fromInput.replace(/-/g, "");
    const maxD = toInput.replace(/-/g, "");
    
    if (minD && maxD) {
        document.getElementById("review-current-period").textContent = `Period: ${minD.substring(6, 8)}/${minD.substring(4, 6)}/${minD.substring(0, 4)} to ${maxD.substring(6, 8)}/${maxD.substring(4, 6)}/${maxD.substring(0, 4)}`;
    }
    
    closeReviewModal("period");
    applyReviewFilters();
}

// F4 Ledger Modal
function openLedgerFilterModal() {
    const modal = document.getElementById("review-modal-ledger");
    if (!modal) return;
    
    // Prefill unique options in ledger select dropdown
    const select = document.getElementById("review-modal-ledger-select");
    const currentVal = select.value;
    select.innerHTML = '<option value="all">All Ledgers</option>';
    
    const sorted = Array.from(reviewState.uniqueLedgers).sort();
    sorted.forEach(l => {
        const opt = document.createElement("option");
        opt.value = l;
        opt.textContent = l;
        select.appendChild(opt);
    });
    
    select.value = currentVal;
    modal.classList.remove("hidden");
    setTimeout(() => select.focus(), 80);
}

function confirmLedgerFilter() {
    closeReviewModal("ledger");
    applyReviewFilters();
}

// 5 Toggling Narration
function toggleReviewNarrationFromBtn() {
    reviewState.showNarration = !reviewState.showNarration;
    
    const narrationHeader = document.getElementById("col-header-narration");
    const particularsHeader = document.getElementById("col-header-particulars");
    
    if (reviewState.showNarration) {
        if (narrationHeader) {
            narrationHeader.style.display = "block";
            narrationHeader.style.flex = "1";
            narrationHeader.style.width = "auto";
        }
        if (particularsHeader) {
            particularsHeader.style.flex = "none";
            particularsHeader.style.width = "11%";
        }
    } else {
        if (narrationHeader) {
            narrationHeader.style.display = "none";
        }
        if (particularsHeader) {
            particularsHeader.style.flex = "1";
            particularsHeader.style.width = "auto";
        }
    }
    
    const label = document.getElementById("btn-tally-narration-label");
    if (label) {
        label.textContent = reviewState.showNarration ? "Hide Narration" : "Show Narration";
    }
    
    onReviewTableScroll();
}

// 6 Narration search Modal
function openNarrationFilterModal() {
    const modal = document.getElementById("review-modal-narration");
    if (!modal) return;
    modal.classList.remove("hidden");
    const input = document.getElementById("review-modal-narration-keyword");
    setTimeout(() => input.focus(), 80);
}

function confirmNarrationFilter() {
    const searchInput = document.getElementById("review-modal-narration-keyword");
    const val = searchInput.value.toLowerCase().trim();
    
    if (val) {
        const words = val.replace(/\s+/g, " ").split(" ").filter(Boolean);
        if (words.length > 0) {
            const escaped = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
            const regex = new RegExp(escaped.join("\\s+"), "i");
            const tempFiltered = reviewState.vouchers.filter(vch => regex.test(vch.narration));
            if (tempFiltered.length === 0) {
                alert(`No results found for keyword: "${searchInput.value}"`);
                searchInput.focus();
                return;
            }
        }
    }
    
    closeReviewModal("narration");
    applyReviewFilters();
}

// Y Replace Ledger modal & Autocomplete autocomplete
function openReplaceLedgerModal() {
    if (reviewState.selectedIds.size === 0) {
        alert("Please select at least one voucher row to overwrite ledgers.");
        return;
    }
    const modal = document.getElementById("review-modal-replace");
    if (!modal) return;
    
    document.getElementById("review-modal-replace-count").textContent = reviewState.selectedIds.size;
    document.getElementById("review-modal-new-ledger").value = "";
    
    // Prefill target ledger input with the particulars name of the first selected voucher
    const firstId = Array.from(reviewState.selectedIds)[0];
    const firstVch = reviewState.vouchers.find(v => v.id === firstId);
    const defTarget = firstVch ? firstVch.particulars : "Suspense";
    document.getElementById("review-modal-target-ledger").value = defTarget;
    
    modal.classList.remove("hidden");
    setTimeout(() => document.getElementById("review-modal-new-ledger").focus(), 80);
}

function confirmReplaceLedger() {
    const newLedgerName = document.getElementById("review-modal-new-ledger").value.trim();
    const targetLedgerName = document.getElementById("review-modal-target-ledger").value.trim();
    
    if (!newLedgerName) {
        alert("Please enter a replace ledger name.");
        return;
    }
    
    let replaceCount = 0;
    reviewState.vouchers.forEach(vch => {
        if (reviewState.selectedIds.has(vch.id)) {
            const isMatch = (targetLedgerName === "*") || (vch.particulars.toLowerCase() === targetLedgerName.toLowerCase());
            if (isMatch) {
                updateVoucherLedger(vch, newLedgerName, true);
                
                replaceCount++;
            }
        }
    });
    
    closeReviewModal("replace");
    
    applyReviewFilters();
    updateReviewStats();
    
    alert(`Successfully replaced ledger in ${replaceCount} voucher(s).`);
}

function showLedgerAutocompleteModal() {
    filterLedgerAutocompleteModal();
}

function filterLedgerAutocompleteModal() {
    const input = document.getElementById("review-modal-new-ledger");
    const list = document.getElementById("review-modal-ledger-autocomplete-list");
    if (!input || !list) return;
    
    // Disable autocomplete dropdown entirely if no company is loaded
    if (!reviewState.activeCompanyName) {
        list.classList.add("hidden");
        return;
    }
    
    const query = input.value.toLowerCase().trim();
    list.innerHTML = "";
    autocompleteIndex = -1;
    
    // Options are unique ledgers from Tally XML, or cached Tally company ledgers if loaded
    let options = new Set(reviewState.uniqueLedgers);
    if (reviewState.cachedCompanyLedgers && reviewState.cachedCompanyLedgers.length > 0) {
        options = new Set(reviewState.cachedCompanyLedgers);
    }
    
    const matches = Array.from(options).filter(opt => opt.toLowerCase().includes(query)).sort();
    
    if (matches.length > 0) {
        matches.forEach(item => {
            const div = document.createElement("div");
            div.className = "ledger-autocomplete-item";
            div.textContent = item;
            div.onclick = () => {
                input.value = item;
                list.classList.add("hidden");
            };
            list.appendChild(div);
        });
        list.classList.remove("hidden");
    } else {
        list.classList.add("hidden");
    }
}

function handleAutocompleteKeydown(e) {
    const list = document.getElementById("review-modal-ledger-autocomplete-list");
    const input = document.getElementById("review-modal-new-ledger");
    if (!list || list.classList.contains("hidden")) return;
    
    const items = list.querySelectorAll(".ledger-autocomplete-item");
    if (items.length === 0) return;
    
    if (e.key === "ArrowDown") {
        e.preventDefault();
        autocompleteIndex = (autocompleteIndex + 1) % items.length;
        highlightAutocompleteItem(items);
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        autocompleteIndex = (autocompleteIndex - 1 + items.length) % items.length;
        highlightAutocompleteItem(items);
    } else if (e.key === "Enter" && autocompleteIndex !== -1) {
        e.preventDefault();
        input.value = items[autocompleteIndex].textContent;
        list.classList.add("hidden");
    }
}

function highlightAutocompleteItem(items) {
    items.forEach((item, index) => {
        if (index === autocompleteIndex) {
            item.classList.add("active");
            item.scrollIntoView({ block: "nearest" });
        } else {
            item.classList.remove("active");
        }
    });
}

// Hide autocomplete suggestions on outer click
document.addEventListener("click", (e) => {
    const list = document.getElementById("review-modal-ledger-autocomplete-list");
    const input = document.getElementById("review-modal-new-ledger");
    if (list && e.target !== input && e.target !== list) {
        list.classList.add("hidden");
    }
});

function openMonthlyAnalysisModal() {
    const modal = document.getElementById("review-modal-monthly");
    if (!modal) return;
    
    // Set initial balance input value based on current file opening balance or manual override
    const opBalInput = document.getElementById("review-monthly-opbal-input");
    if (opBalInput) {
        if (reviewState.manualOpeningBalance !== null) {
            opBalInput.value = reviewState.manualOpeningBalance;
        } else {
            const val = (reviewState.openingBalance !== null && reviewState.openingBalance !== undefined) ? 
                reviewState.openingBalance : 0.00;
            opBalInput.value = val;
        }
    }
    
    updateMonthlyAnalysisBalances();
    modal.classList.remove("hidden");
}

function updateMonthlyAnalysisBalances() {
    const opBalInput = document.getElementById("review-monthly-opbal-input");
    const opBalVal = opBalInput ? (parseFloat(opBalInput.value) || 0.00) : 0.00;
    
    // Save to manual override state so it persists across close/reopen
    if (opBalInput) {
        reviewState.manualOpeningBalance = opBalVal;
    }
    
    // Sort reviewState vouchers chronologically to roll forward balance
    const sortedVch = [...reviewState.vouchers].sort((a, b) => a.rawDate.localeCompare(b.rawDate));
    
    // Monthly aggregations map
    const monthlyRollup = {};
    
    sortedVch.forEach(vch => {
        if (vch.rawDate.length !== 8) return;
        const year = vch.rawDate.substring(0, 4);
        const month = vch.rawDate.substring(4, 6);
        const monthKey = `${year}-${month}`; // e.g. "2025-04"
        
        if (!monthlyRollup[monthKey]) {
            monthlyRollup[monthKey] = { debit: 0, credit: 0, count: 0 };
        }
        
        monthlyRollup[monthKey].debit += (vch.debit || 0);
        monthlyRollup[monthKey].credit += (vch.credit || 0);
        monthlyRollup[monthKey].count++;
    });
    
    const tbody = document.getElementById("review-monthly-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    
    let cumulativeBalance = opBalVal;
    
    const sortedMonthKeys = Object.keys(monthlyRollup).sort();
    
    sortedMonthKeys.forEach(mKey => {
        const item = monthlyRollup[mKey];
        cumulativeBalance += item.debit - item.credit;
        
        // Convert monthKey "2025-04" to Month Name "Apr 2025"
        const [yr, mn] = mKey.split("-");
        const dt = new Date(parseInt(yr), parseInt(mn) - 1, 1);
        const monthName = dt.toLocaleString('en-US', { month: 'short', year: 'numeric' });
        
        const row = document.createElement("tr");
        row.style.borderBottom = "1px solid #e2e8f0";
        
        row.innerHTML = `
            <td style="padding: 8px; font-weight: 500; color: #2d3748;">${monthName}</td>
            <td style="padding: 8px; text-align: right; color: #4a5568;">${item.count}</td>
            <td style="padding: 8px; text-align: right; color: #16a34a;">${formatCurrency(item.debit)}</td>
            <td style="padding: 8px; text-align: right; color: #e53e3e;">${formatCurrency(item.credit)}</td>
            <td style="padding: 8px; text-align: right; font-weight: bold; color: #2d3748;">${formatCurrency(cumulativeBalance)}</td>
        `;
        tbody.appendChild(row);
    });
}

// -------------------------------------------------------------
// XML EXPORTER AND EXIT HANDLERS
// -------------------------------------------------------------
async function saveReviewXML(exitAfterSave = false) {
    if (!reviewState.xmlDoc) {
        alert("No active XML document loaded.");
        return;
    }
    
    // Serialise DOM object back to text
    const serializer = new XMLSerializer();
    const xmlString = serializer.serializeToString(reviewState.xmlDoc);
    
    const saveBtn = document.getElementById("btn-tally-save");
    const saveLabel = document.getElementById("btn-tally-save-label");
    const saveShortcut = saveBtn ? saveBtn.querySelector(".tally-btn-shortcut") : null;
    let originalShortcut = "Ctrl+S";
    let originalLabel = "Save";
    if (saveLabel) originalLabel = saveLabel.textContent;
    if (saveShortcut) originalShortcut = saveShortcut.textContent;
    
    if (saveBtn) {
        if (saveShortcut) saveShortcut.textContent = "...";
        if (saveLabel) saveLabel.textContent = "Saving...";
        saveBtn.disabled = true;
    }
    
    try {
        const response = await fetch("/api/review/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                xml: xmlString,
                debit_ledger: reviewState.bankName || "Generic Bank",
                credit_ledger: "Suspense",
                filename: reviewState.originalFileName || "tally_import.xml"
            })
        });
        
        const result = await response.json();
        if (result.success) {
            alert(result.message);
            if (exitAfterSave) {
                window.location.href = "/#license-tab";
            }
        } else if (result.cancelled) {
            console.log("Save cancelled:", result.message);
        } else {
            alert("Failed to save changes: " + result.message);
        }
    } catch (err) {
        console.error("Error saving review XML:", err);
        alert("An error occurred while saving: " + err.message);
    } finally {
        if (saveBtn) {
            if (saveShortcut) saveShortcut.textContent = originalShortcut;
            if (saveLabel) saveLabel.textContent = originalLabel;
            saveBtn.disabled = false;
        }
    }
}

function deleteSelectedVouchers() {
    if (reviewState.selectedIds.size === 0) {
        alert("Please select at least one voucher to delete.");
        return;
    }
    
    const confirmDelete = confirm(`Are you sure you want to delete the ${reviewState.selectedIds.size} selected voucher(s)?`);
    if (!confirmDelete) return;
    
    // 1. Remove XML nodes from the DOM
    reviewState.vouchers.forEach(vch => {
        if (reviewState.selectedIds.has(vch.id)) {
            if (vch.node && vch.node.parentNode) {
                vch.node.parentNode.removeChild(vch.node);
            }
        }
    });
    
    // 2. Filter out deleted vouchers from the javascript state array
    reviewState.vouchers = reviewState.vouchers.filter(vch => !reviewState.selectedIds.has(vch.id));
    
    // 3. Reset selection and focused indices
    reviewState.selectedIds.clear();
    reviewState.focusedIndex = -1;
    reviewState.lastSelectedIndex = -1;
    
    // 4. Update the review filters and stats
    applyReviewFilters();
    updateReviewStats();
    onReviewTableScroll();
}

function openExitConfirmation() {
    // Escape or X click opens Exit Confirmation Dialog modal
    const exitModal = document.getElementById("review-modal-exit-confirm");
    if (exitModal) {
        exitModal.classList.remove("hidden");
    }
}

function closeExitConfirmation() {
    const exitModal = document.getElementById("review-modal-exit-confirm");
    if (exitModal) {
        exitModal.classList.add("hidden");
    }
    // Refocus data grid viewport
    document.getElementById("review-virtual-viewport").focus();
}

function confirmExitReview(action) {
    if (action === "export") {
        // Save work by posting back to the server
        saveReviewXML(true);
    } else if (action === "exit") {
        // Exit without saving modifications
        window.location.href = "/#license-tab";
    }
}

// -------------------------------------------------------------
// ADVANCED NARRATION ANALYSIS & PHRASE FREQUENCY FILTER
// -------------------------------------------------------------

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
    const separators = /[\/\\\-_\@\.\,\:\;\(\)\[\]\{\}\|\+\=\*\#\%\&\'\"\?\!\<\>]/g;
    clean = clean.replace(separators, " ");
    clean = clean.replace(/\s+/g, " ");
    return clean.trim();
}

function isValidWord(word) {
    if (!word || word.length <= 1) return false;
    if (/^\d+$/.test(word)) {
        return /^\d{10}$/.test(word); // keep only 10-digit numbers (phone numbers)
    }
    return !NARRATION_STOP_WORDS.has(word);
}

function generatePhrasesFromNarration(normalizedText) {
    if (!normalizedText) return [];
    const words = normalizedText.split(" ");
    const phrases = [];
    
    for (let i = 0; i < words.length; i++) {
        const w1 = words[i];
        
        // Single word
        if (isValidWord(w1)) {
            phrases.push(w1);
            
            // Two-word phrase
            if (i + 1 < words.length) {
                const w2 = words[i + 1];
                if (isValidWord(w2)) {
                    phrases.push(`${w1} ${w2}`);
                    
                    // Three-word phrase
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
    
    const statusVal = reviewState.statusFilter || "all";
    const sourceSet = baseSet.filter(vch => {
        if (statusVal === "suspense" && !vch.particulars.toLowerCase().includes("suspense")) return false;
        if (statusVal === "modified" && !vch.modified) return false;
        return true;
    });
    
    sourceSet.forEach(vch => {
        if (!vch.normalizedNarration) {
            vch.normalizedNarration = normalizeNarration(vch.narration);
        }
        
        const phrases = generatePhrasesFromNarration(vch.normalizedNarration);
        const uniquePhrases = new Set(phrases);
        
        uniquePhrases.forEach(phrase => {
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
    
    // Sort descending by count
    reviewState.phraseFrequencies.sort((a, b) => b.count - a.count);
}

function openAdvancedFilterModal() {
    const modal = document.getElementById("review-modal-advanced");
    if (!modal) return;
    
    // Dynamically calculate phrase frequencies on active period/status set
    analyzeAllVoucherPhrases();
    
    document.getElementById("review-modal-advanced-search").value = "";
    document.getElementById("review-modal-advanced-minfreq").value = reviewState.advMinFreq.toString();
    document.getElementById("review-modal-advanced-len1").checked = reviewState.advLen1;
    document.getElementById("review-modal-advanced-len2").checked = reviewState.advLen2;
    document.getElementById("review-modal-advanced-len3").checked = reviewState.advLen3;
    
    modal.classList.remove("hidden");
    renderAdvancedPhrases();
    
    setTimeout(() => document.getElementById("review-modal-advanced-search").focus(), 80);
}

function renderAdvancedPhrases() {
    const searchVal = document.getElementById("review-modal-advanced-search").value.toLowerCase().trim();
    const minFreq = parseInt(document.getElementById("review-modal-advanced-minfreq").value, 10) || 2;
    
    const showLen1 = document.getElementById("review-modal-advanced-len1").checked;
    const showLen2 = document.getElementById("review-modal-advanced-len2").checked;
    const showLen3 = document.getElementById("review-modal-advanced-len3").checked;
    
    // Persist active settings in reviewState
    reviewState.advMinFreq = minFreq;
    reviewState.advLen1 = showLen1;
    reviewState.advLen2 = showLen2;
    reviewState.advLen3 = showLen3;
    
    const container = document.getElementById("review-modal-advanced-list");
    if (!container) return;
    
    if (!reviewState.phraseFrequencies) {
        container.innerHTML = `<div style="padding: 8px; color: #718096; font-style: italic; text-align: center; font-size: 0.76rem;">No phrases analyzed yet.</div>`;
        return;
    }
    
    const filtered = reviewState.phraseFrequencies.filter(item => {
        if (item.length === 1 && !showLen1) return false;
        if (item.length === 2 && !showLen2) return false;
        if (item.length === 3 && !showLen3) return false;
        if (item.count < minFreq) return false;
        if (searchVal && !item.phrase.includes(searchVal)) return false;
        return true;
    });
    
    if (filtered.length === 0) {
        container.innerHTML = `<div style="padding: 8px; color: #718096; text-align: center; font-size: 0.76rem;">No matches found.</div>`;
        return;
    }
    
    const currentStatus = reviewState.statusFilter || "suspense";
    let badgeStyle = "color: #002d5a; background: #e6f2ff;"; // default blue for 'all'
    if (currentStatus === "suspense") {
        badgeStyle = "color: #e53e3e; background: #fed7d7;"; // red
    } else if (currentStatus === "modified") {
        badgeStyle = "color: #16a34a; background: #c6f6d5;"; // green
    }
    
    let html = "";
    filtered.forEach(item => {
        // Safe string escaping for Javascript onClick attribute
        const safePhrase = item.phrase.replace(/'/g, "\\'");
        html += `
            <div class="stats-interactive-row" onclick="selectAdvancedPhrase('${safePhrase}')" style="padding: 6px 8px; cursor: pointer; border-radius: 3px; display: flex; justify-content: space-between; align-items: center; font-size: 0.76rem; border-bottom: 1px dashed #e2e8f0; transition: background 0.1s;">
                <span style="font-weight: 500; color: #2d3748;">${item.phrase}</span>
                <strong style="${badgeStyle} padding: 2px 6px; border-radius: 10px; font-size: 0.68rem; font-weight: bold;">${item.count}</strong>
            </div>
        `;
    });
    container.innerHTML = html;
}

function selectAdvancedPhrase(phrase) {
    reviewState.advancedPhraseFilter = phrase;
    closeReviewModal("advanced");
    applyReviewFilters();
}

function clearAdvancedPhraseFilter() {
    reviewState.advancedPhraseFilter = null;
    applyReviewFilters();
}


// -------------------------------------------------------------
// TALLY INTEGRATION & COMPANY LEDGER CACHING
// -------------------------------------------------------------
async function loadCachedCompanies() {
    try {
        const res = await fetch("/api/tally/companies");
        const data = await res.json();
        if (data.success) {
            const select = document.getElementById("review-company-select");
            if (!select) return;
            
            // Keep the default option
            select.innerHTML = '<option value="">-- No Company Loaded --</option>';
            
            data.companies.forEach(company => {
                const opt = document.createElement("option");
                opt.value = company.safe_name;
                opt.textContent = company.display_name;
                select.appendChild(opt);
            });
            
            // If there is an active company in state, pre-select it
            if (reviewState.activeCompanyName) {
                select.value = reviewState.activeCompanyName;
            }
        }
    } catch (err) {
        console.error("Failed to load cached companies list:", err);
    }
}

async function onReviewCompanyChange() {
    const select = document.getElementById("review-company-select");
    if (!select) return;
    
    const companyName = select.value;
    if (!companyName) {
        reviewState.cachedCompanyLedgers = [];
        reviewState.activeCompanyName = "";
        return;
    }
    
    try {
        const res = await fetch(`/api/tally/company/${encodeURIComponent(companyName)}/ledgers`);
        const data = await res.json();
        if (data.success) {
            reviewState.cachedCompanyLedgers = data.ledgers || [];
            reviewState.activeCompanyName = companyName;
        } else {
            alert(`Error loading company ledgers: ${data.message}`);
            select.value = "";
            reviewState.cachedCompanyLedgers = [];
            reviewState.activeCompanyName = "";
        }
    } catch (err) {
        alert(`System error loading company ledgers: ${err.message}`);
        select.value = "";
        reviewState.cachedCompanyLedgers = [];
        reviewState.activeCompanyName = "";
    }
}

function openSyncTallyModal() {
    const modal = document.getElementById("review-modal-sync");
    if (!modal) return;
    
    document.getElementById("sync-company-name-input").value = "";
    const statusDiv = document.getElementById("sync-tally-status");
    if (statusDiv) {
        statusDiv.style.display = "none";
        statusDiv.className = "";
        statusDiv.innerHTML = "";
    }
    
    modal.classList.remove("hidden");
}

async function submitTallySync() {
    const companyInput = document.getElementById("sync-company-name-input");
    const companyName = companyInput ? companyInput.value.trim() : "";
    const statusDiv = document.getElementById("sync-tally-status");
    const submitBtn = document.getElementById("btn-tally-sync-submit");
    
    if (!companyName) {
        if (statusDiv) {
            statusDiv.style.display = "block";
            statusDiv.style.background = "#fef2f2";
            statusDiv.style.color = "#ef4444";
            statusDiv.style.border = "1px solid #fecaca";
            statusDiv.innerHTML = "❌ Error: Company Name is required to sync.";
        }
        return;
    }
    
    if (statusDiv) {
        statusDiv.style.display = "block";
        statusDiv.style.background = "#ebf8ff";
        statusDiv.style.color = "#005ea5";
        statusDiv.style.border = "1px solid #bae6fd";
        statusDiv.innerHTML = "⌛ Connecting to Tally Prime on port 9000...";
    }
    
    if (submitBtn) submitBtn.disabled = true;
    
    try {
        const res = await fetch("/api/tally/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ company_name: companyName })
        });
        const data = await res.json();
        
        if (data.success) {
            if (statusDiv) {
                statusDiv.style.background = "#f0fdf4";
                statusDiv.style.color = "#16a34a";
                statusDiv.style.border = "1px solid #bbf7d0";
                statusDiv.innerHTML = `✓ Sync complete! Cached ${data.ledgers.length} ledgers for '${data.company_name}'.`;
            }
            
            // Reload the dropdown and select the newly synced company
            reviewState.activeCompanyName = data.company_name;
            await loadCachedCompanies();
            
            // Auto-load ledgers for the company
            reviewState.cachedCompanyLedgers = data.ledgers || [];
            
            // Close modal after a short delay so the user sees the success state
            setTimeout(() => {
                closeReviewModal("sync");
            }, 1500);
        } else {
            if (statusDiv) {
                statusDiv.style.background = "#fef2f2";
                statusDiv.style.color = "#ef4444";
                statusDiv.style.border = "1px solid #fecaca";
                statusDiv.innerHTML = `❌ Error: ${data.message}`;
            }
        }
    } catch (err) {
        if (statusDiv) {
            statusDiv.style.background = "#fef2f2";
            statusDiv.style.color = "#ef4444";
            statusDiv.style.border = "1px solid #fecaca";
            statusDiv.innerHTML = `❌ System Error: ${err.message}`;
        }
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

function toggleTheme() {
    const body = document.body;
    const btnIcon = document.getElementById("theme-toggle-icon");
    const btnText = document.getElementById("theme-toggle-text");
    
    if (body.classList.contains("night-theme")) {
        body.classList.remove("night-theme");
        localStorage.setItem("review-theme", "day");
        if (btnIcon) btnIcon.textContent = "🌙";
        if (btnText) btnText.textContent = "Night Mode";
    } else {
        body.classList.add("night-theme");
        localStorage.setItem("review-theme", "night");
        if (btnIcon) btnIcon.textContent = "☀️";
        if (btnText) btnText.textContent = "Day Mode";
    }
}
