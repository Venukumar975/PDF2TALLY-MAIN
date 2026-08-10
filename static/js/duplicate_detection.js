// -------------------------------------------------------------
// DUPLICATE VOUCHER DETECTION ISOLATED EXTENSION
// -------------------------------------------------------------

// Extend global state
reviewState.tallyVouchers = [];
reviewState.duplicateDetectionRun = false;
reviewState.showDuplicateStats = true;
reviewState.duplicatesDetected = false;

// 1. DYNAMIC DOM INTEGRATION & INITIALIZATION ON STARTUP
document.addEventListener("DOMContentLoaded", () => {
    // Inject duplicate panel into the table container
    const tableContainer = document.getElementById("review-table-container");
    const dupPanel = document.getElementById("duplicate-detection-panel");
    if (tableContainer && dupPanel) {
        tableContainer.insertBefore(dupPanel, tableContainer.firstChild);
    }
    
    // Inject match details modal to body
    const matchModal = document.getElementById("review-modal-match-details");
    if (matchModal) {
        document.body.appendChild(matchModal);
    }
    
    // Load duplicate autocomplete history
    loadDuplicateHistory();
    
    // Inject new table columns in header dynamically (Status, Matched Tally, Conf)
    const headerRow = document.getElementById("review-table-header");
    if (headerRow) {
        // Adjust credit header border-right to connect nicely
        const creditHeader = document.getElementById("col-header-credit");
        if (creditHeader) {
            creditHeader.style.borderRight = "1px solid #cccccc";
        }
        
        const statusHeader = document.createElement("div");
        statusHeader.id = "col-header-status";
        statusHeader.style = "width: 8%; flex-shrink: 0; padding: 8px; border-right: 1px solid #cccccc; box-sizing: border-box; overflow: hidden; text-overflow: ellipsis; display: none;";
        statusHeader.textContent = "Status";
        
        const matchedHeader = document.createElement("div");
        matchedHeader.id = "col-header-matched";
        matchedHeader.style = "width: 10%; flex-shrink: 0; padding: 8px; border-right: 1px solid #cccccc; box-sizing: border-box; overflow: hidden; text-overflow: ellipsis; display: none;";
        matchedHeader.textContent = "Matched Tally";
        
        const confHeader = document.createElement("div");
        confHeader.id = "col-header-conf";
        confHeader.style = "width: 6%; flex-shrink: 0; padding: 8px; box-sizing: border-box; overflow: hidden; text-overflow: ellipsis; display: none;";
        confHeader.textContent = "Conf";
        
        headerRow.appendChild(statusHeader);
        headerRow.appendChild(matchedHeader);
        headerRow.appendChild(confHeader);
    }
    
    // Inject the "Duplicate Check" toggle button in the actions sidebar
    const shortcutBtn = document.querySelector(".tally-btn-key");
    if (shortcutBtn) {
        const sidebar = shortcutBtn.parentNode;
        
        const dupBtn = document.createElement("button");
        dupBtn.className = "tally-btn-key";
        dupBtn.onclick = toggleDuplicateDetectionPanel;
        dupBtn.innerHTML = `
            <div class="tally-btn-shortcut">F8</div>
            <div class="tally-btn-label">Duplicate Check</div>
        `;
        sidebar.insertBefore(dupBtn, shortcutBtn);
    }
});

// 2. TOGGLE PANEL INTERFACE SUPPORT
function toggleDuplicateDetectionPanel() {
    const dupPanel = document.getElementById("duplicate-detection-panel");
    if (!dupPanel) return;
    
    const isHidden = dupPanel.classList.contains("hidden");
    
    // Toggle headers visibility
    const colHeaders = ["col-header-status", "col-header-matched", "col-header-conf"];
    
    if (isHidden) {
        // Show panel
        dupPanel.classList.remove("hidden");
        reviewState.duplicateDetectionRun = true;
        
        colHeaders.forEach(h => {
            const el = document.getElementById(h);
            if (el) el.style.display = "block";
        });
        
        // Show sidebar filter card and actions card if detection has results
        const filterCard = document.getElementById("dup-filter-card");
        const actionsContainer = document.getElementById("dup-report-actions-container");
        if (filterCard && reviewState.duplicatesDetected) {
            filterCard.classList.remove("hidden");
            if (actionsContainer) actionsContainer.classList.remove("hidden");
        }

        // Restore results container visibility if it contains active data/messages
        const resultsContainer = document.getElementById("dup-results-container");
        const statusMsg = document.getElementById("dup-status-message");
        const summarySec = document.getElementById("dup-summary-section");
        if (resultsContainer && ((statusMsg && statusMsg.style.display !== "none" && statusMsg.innerHTML !== "") || (summarySec && !summarySec.classList.contains("hidden")))) {
            if (reviewState.showDuplicateStats) {
                resultsContainer.classList.remove("hidden");
            } else {
                resultsContainer.classList.add("hidden");
            }
        }

        const compareTip = document.getElementById("dup-compare-tip");
        if (compareTip && ((statusMsg && statusMsg.style.display !== "none" && statusMsg.innerHTML !== "") || (summarySec && !summarySec.classList.contains("hidden")))) {
            if (reviewState.showDuplicateStats) {
                compareTip.classList.remove("hidden");
            } else {
                compareTip.classList.add("hidden");
            }
        }
        
        const toggleBtn = document.getElementById("btn-toggle-dup-stats");
        if (toggleBtn) {
            toggleBtn.textContent = reviewState.showDuplicateStats ? "Hide Stats" : "Show Stats";
        }
    } else {
        // Hide panel
        dupPanel.classList.add("hidden");
        reviewState.duplicateDetectionRun = false;
        
        const summarySec = document.getElementById("dup-summary-section");
        if (summarySec) summarySec.classList.add("hidden");

        const resultsContainer = document.getElementById("dup-results-container");
        if (resultsContainer) resultsContainer.classList.add("hidden");

        const compareTip = document.getElementById("dup-compare-tip");
        if (compareTip) compareTip.classList.add("hidden");
        
        colHeaders.forEach(h => {
            const el = document.getElementById(h);
            if (el) el.style.display = "none";
        });
        
        // Hide sidebar filter card and actions card
        const filterCard = document.getElementById("dup-filter-card");
        if (filterCard) filterCard.classList.add("hidden");
        const actionsContainer = document.getElementById("dup-report-actions-container");
        if (actionsContainer) actionsContainer.classList.add("hidden");
        
        // Reset state filter if set to duplicate status
        if (reviewState.statusFilter === "duplicate" || reviewState.statusFilter === "new") {
            reviewState.statusFilter = "all";
        }
    }
    
    applyReviewFilters();
    updateReviewStats();
    onReviewTableScroll();
}

// 3. KEYBOARD BINDINGS FOR SHORTCUTS (F8)
document.addEventListener("keydown", (e) => {
    if (e.key === "F8") {
        e.preventDefault();
        toggleDuplicateDetectionPanel();
    }
});

// 4. MONKEY-PATCHING REVIEW DESK FOR DYNAMIC OVERRIDES

// A. Filter Hook
const originalApplyReviewFilters = window.applyReviewFilters;
window.applyReviewFilters = function() {
    if (!reviewState.duplicateDetectionRun) {
        originalApplyReviewFilters.apply(this, arguments);
        return;
    }
    
    // Call original filtration logic first
    originalApplyReviewFilters.apply(this, arguments);
    
    // Filter on duplicate statuses (Duplicate / New)
    const statusVal = reviewState.statusFilter || "all";
    if (statusVal === "duplicate" || statusVal === "new") {
        reviewState.filteredVouchers = reviewState.filteredVouchers.filter(vch => {
            const currentStatus = vch.duplicateStatus || "New";
            if (statusVal === "duplicate" && currentStatus !== "Duplicate") return false;
            if (statusVal === "new" && currentStatus !== "New") return false;
            return true;
        });
    }
};

// B. Stats Override
const originalUpdateReviewStats = window.updateReviewStats;
window.updateReviewStats = function() {
    if (!reviewState.duplicateDetectionRun) {
        originalUpdateReviewStats.apply(this, arguments);
        return;
    }
    
    // Call original stats counter
    originalUpdateReviewStats.apply(this, arguments);
    
    // Set active CSS styles on sidebar buttons
    const btnTotal = document.getElementById("btn-stats-total");
    const btnModified = document.getElementById("btn-stats-modified");
    const btnSuspense = document.getElementById("btn-stats-suspense");
    const btnDupAll = document.getElementById("btn-stats-dup-all");
    const btnDupOnly = document.getElementById("btn-stats-dup-only");
    const btnNewOnly = document.getElementById("btn-stats-new-only");
    
    if (btnTotal) btnTotal.className = "stats-interactive-row";
    if (btnModified) btnModified.className = "stats-interactive-row";
    if (btnSuspense) btnSuspense.className = "stats-interactive-row";
    if (btnDupAll) btnDupAll.className = "stats-interactive-row";
    if (btnDupOnly) btnDupOnly.className = "stats-interactive-row";
    if (btnNewOnly) btnNewOnly.className = "stats-interactive-row";
    
    const currentStatus = reviewState.statusFilter || "all";
    if (currentStatus === "all") {
        if (btnTotal) btnTotal.classList.add("active-all");
        if (btnDupAll) btnDupAll.classList.add("active-all");
    } else if (currentStatus === "modified") {
        if (btnModified) btnModified.classList.add("active-modified");
    } else if (currentStatus === "suspense") {
        if (btnSuspense) btnSuspense.classList.add("active-suspense");
    } else if (currentStatus === "duplicate") {
        if (btnDupOnly) btnDupOnly.classList.add("active-dup");
    } else if (currentStatus === "new") {
        if (btnNewOnly) btnNewOnly.classList.add("active-suspense");
    }
};

// C. Stats Filter Toggle Hook
const originalToggleStatsFilter = window.toggleStatsFilter;
window.toggleStatsFilter = function(targetFilter) {
    if (!reviewState.duplicateDetectionRun || (targetFilter !== "duplicate" && targetFilter !== "new")) {
        originalToggleStatsFilter.apply(this, arguments);
        return;
    }
    reviewState.statusFilter = (reviewState.statusFilter === targetFilter) ? "all" : targetFilter;
    applyReviewFilters();
    updateReviewStats();
    onReviewTableScroll();
};

// D. Modal Close Hook
const originalCloseActiveModal = window.closeActiveModal;
window.closeActiveModal = function() {
    const el1 = document.getElementById("review-modal-match-details");
    if (el1 && !el1.classList.contains("hidden")) {
        closeReviewModal("match-details");
        return true;
    }
    const el2 = document.getElementById("review-modal-dup-report");
    if (el2 && !el2.classList.contains("hidden")) {
        closeDuplicateReportModal();
        return true;
    }
    return originalCloseActiveModal.apply(this, arguments);
};

// E. File Load Pre-fill Hook
const originalLoadReviewXML = window.loadReviewXML;
window.loadReviewXML = function(xmlText, fileName) {
    originalLoadReviewXML.apply(this, arguments);
    
    // Hide duplicate results when loading a new file
    const summarySec = document.getElementById("dup-summary-section");
    if (summarySec) summarySec.classList.add("hidden");
    const statusMsg = document.getElementById("dup-status-message");
    if (statusMsg) statusMsg.style.display = "none";
    const resultsContainer = document.getElementById("dup-results-container");
    if (resultsContainer) resultsContainer.classList.add("hidden");
    const compareTip = document.getElementById("dup-compare-tip");
    if (compareTip) compareTip.classList.add("hidden");
    const opInput = document.getElementById("dup-bal-opening-input");
    if (opInput) opInput.value = "0.00";
    
    reviewState.tallyVouchers = [];
    
    // Leave company and bank inputs empty
    const companyInput = document.getElementById("dup-company-name");
    if (companyInput) companyInput.value = "";
    
    const bankInput = document.getElementById("dup-bank-name");
    if (bankInput) bankInput.value = "";

    // Prefill duplicate check dates with the initial period dates once on load
    const periodFrom = document.getElementById("review-modal-from-date");
    const periodTo = document.getElementById("review-modal-to-date");
    const dupFrom = document.getElementById("dup-from-date");
    const dupTo = document.getElementById("dup-to-date");
    if (periodFrom && dupFrom) dupFrom.value = periodFrom.value;
    if (periodTo && dupTo) dupTo.value = periodTo.value;
};

// F. Table Rows Custom Scroll Rendering Override
window.onReviewTableScroll = function() {
    if (!reviewState.duplicateDetectionRun) {
        // Fallback to original layout
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
        return;
    }
    
    // Duplicate Detection layout implementation
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
        let rowStyle = "";
        
        if (!isSelected) {
            if (vch.duplicateStatus === "Duplicate") {
                rowStyle = document.body.classList.contains("night-theme") ? 
                    "background-color: #451a03 !important; color: #fde68a;" : 
                    "background-color: #fffbeb !important; color: #b45309; border-top: 1px solid #fde047; border-bottom: 1px solid #fde047;";
            }
        }
        
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
            
        const statusCellStyles = "width: 8%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;";
        const matchedCellStyles = "width: 10%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;";
        const confCellStyles = "width: 6%; flex-shrink: 0; padding: 6px 8px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;";
        
        const matchedVchLink = vch.matchedTallyVchNo !== "--" && vch.matchedTallyVchNo ? 
            `<a href="#" onclick="event.preventDefault(); openMatchDetailsDialog(${vch.id});" style="color: #005ea5; font-weight: 600; text-decoration: underline;">#${vch.matchedTallyVchNo}</a>` : 
            "--";
            
        const confText = vch.confidenceScore > 0 ? `${vch.confidenceScore}%` : "--";
            
        html += `
            <div class="review-row ${bgClass}" onclick="onReviewRowClick(event, ${i})" style="display: flex; height: ${reviewState.rowHeight}px; align-items: center; border-bottom: 1px solid #eeeeee; font-size: 0.78rem; position: absolute; top: ${i * reviewState.rowHeight}px; left: 0; right: 0; cursor: pointer; user-select: none; ${borderStyle} ${modStyle} ${rowStyle}">
                <div style="width: 7%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.date}</div>
                <div style="${particularsCellStyles}" title="${vch.particulars}">${vch.particulars}</div>
                <div style="${narrationCellStyles}" title="${vch.narration}">${vch.narration}</div>
                <div style="width: 6%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.vchType}</div>
                <div style="width: 7%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.vchNo}</div>
                <div style="width: 9%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #10b981; box-sizing: border-box;">${debitText}</div>
                <div style="width: 9%; flex-shrink: 0; padding: 6px 8px; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #ef4444; box-sizing: border-box; border-right: 1px solid #eeeeee;">${creditText}</div>
                <div style="${statusCellStyles}">${vch.duplicateStatus || "New"}</div>
                <div style="${matchedCellStyles}">${matchedVchLink}</div>
                <div style="${confCellStyles}">${confText}</div>
            </div>
        `;
    }
    content.innerHTML = html;
};

// -------------------------------------------------------------
// CORE ALGORITHMIC HELPERS
// -------------------------------------------------------------

function parseDateString(str) {
    if (!str) return null;
    if (str.includes("-")) {
        const parts = str.split("-");
        if (parts.length === 3) {
            return new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
        }
    } else if (str.length === 8) {
        return new Date(parseInt(str.substring(0, 4), 10), parseInt(str.substring(4, 6), 10) - 1, parseInt(str.substring(6, 8), 10));
    }
    return null;
}

function formatTallyDate(dateStr) {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    return `${dateStr.substring(6, 8)}-${dateStr.substring(4, 6)}-${dateStr.substring(0, 4)}`;
}

function calculateNarrationSimilarity(str1, str2) {
    const tokens1 = new Set(str1.toLowerCase().split(/\s+/).filter(w => w.length > 2));
    const tokens2 = new Set(str2.toLowerCase().split(/\s+/).filter(w => w.length > 2));
    if (tokens1.size === 0 || tokens2.size === 0) return 0;
    
    let intersection = 0;
    tokens1.forEach(t => {
        if (tokens2.has(t)) intersection++;
    });
    
    return intersection / Math.max(tokens1.size, tokens2.size);
}

// -------------------------------------------------------------
// ACTIONS & API CALLS
// -------------------------------------------------------------

async function importTallyVouchers() {
    const companyName = document.getElementById("dup-company-name").value.trim();
    const bankName = document.getElementById("dup-bank-name").value.trim();
    const fromDate = document.getElementById("dup-from-date").value;
    const toDate = document.getElementById("dup-to-date").value;
    const statusText = document.getElementById("dup-import-status-text");
    
    if (!companyName) {
        alert("Please enter a Tally Company Name.");
        return;
    }
    if (!bankName) {
        alert("Please enter a Bank Ledger Name.");
        return;
    }
    
    if (statusText) {
        statusText.style.display = "inline-block";
        statusText.style.color = "#005ea5";
        statusText.innerHTML = "⌛ Connecting to Tally Prime and importing vouchers...";
    }
    
    try {
        const response = await fetch("/api/tally/vouchers", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                company_name: companyName,
                bank_name: bankName,
                from_date: fromDate,
                to_date: toDate
            })
        });
        
        const result = await response.json();
        if (result.success) {
            reviewState.tallyVouchers = result.vouchers || [];
            
            // Hide results container if previously shown from another ledger
            const resultsContainer = document.getElementById("dup-results-container");
            if (resultsContainer) resultsContainer.classList.add("hidden");
            const filterCard = document.getElementById("dup-filter-card");
            if (filterCard) filterCard.classList.add("hidden");
            const actionsContainer = document.getElementById("dup-report-actions-container");
            if (actionsContainer) actionsContainer.classList.add("hidden");
            
            reviewState.duplicatesDetected = false;
            
            if (statusText) {
                statusText.style.color = "#16a34a";
                let fromFormatted = "--";
                let toFormatted = "--";
                if (fromDate) {
                    const fromParts = fromDate.split("-");
                    fromFormatted = `${fromParts[2]}/${fromParts[1]}/${fromParts[0]}`;
                }
                if (toDate) {
                    const toParts = toDate.split("-");
                    toFormatted = `${toParts[2]}/${toParts[1]}/${toParts[0]}`;
                }
                statusText.innerHTML = `✓ Imported <b>${reviewState.tallyVouchers.length}</b> Tally vouchers (<b>${result.company_name}</b>) successfully for <b>${fromFormatted} to ${toFormatted}</b>.`;
            }
            
            // Save successful company and bank name to history
            fetch("/api/tally/duplicate-history", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    company_name: companyName,
                    bank_name: bankName
                })
            }).then(() => {
                loadDuplicateHistory();
            }).catch(err => console.error("Failed to save duplicate history:", err));
        } else {
            if (statusText) {
                statusText.style.color = "#ef4444";
                statusText.textContent = `❌ Error: ${result.message}`;
            }
        }
    } catch (err) {
        if (statusText) {
            statusText.style.color = "#ef4444";
            statusText.textContent = `❌ System Error: ${err.message}`;
        }
    }
}

function detectDuplicates() {
    const companyName = document.getElementById("dup-company-name").value.trim();
    const bankName = document.getElementById("dup-bank-name").value.trim();

    if (!companyName) {
        alert("Please enter a Tally Company Name.");
        return;
    }
    if (!bankName) {
        alert("Please enter a Bank Ledger Name.");
        return;
    }

    if (!reviewState.tallyVouchers || reviewState.tallyVouchers.length === 0) {
        alert("Please import Tally data first by clicking 'Import Tally Data'.");
        return;
    }
    
    let dateTolerance = 0;
    const tolRadios = document.getElementsByName("dup-date-tolerance");
    for (let r of tolRadios) {
        if (r.checked) {
            dateTolerance = parseInt(r.value, 10);
            break;
        }
    }
    
    const matchVchType = false;
    const matchNarration = false;
    const matchParticulars = false;
    
    const usedTallyNos = new Set();
    
    reviewState.vouchers.forEach(imp => {
        imp.duplicateStatus = "New";
        imp.matchedTallyVchNo = "--";
        imp.confidenceScore = 0;
        imp.matchReason = [];
        imp.matchedTallyVch = null;
        
        const impAmt = imp.debit > 0 ? imp.debit : imp.credit;
        const impType = imp.debit > 0 ? "DEBIT" : "CREDIT";
        const impDate = parseDateString(imp.date);
        
        let bestMatch = null;
        let bestScore = 0;
        let bestReasons = [];
        
        reviewState.tallyVouchers.forEach(tally => {
            if (usedTallyNos.has(tally.vch_no)) return;
            
            if (Math.abs(tally.amount - impAmt) > 0.01) return;
            if (tally.type !== impType) return;
            
            const tallyDate = parseDateString(formatTallyDate(tally.date));
            if (!impDate || !tallyDate) return;
            const diffDays = Math.abs(tallyDate - impDate) / (1000 * 60 * 60 * 24);
            if (diffDays > dateTolerance) return;
            
            let score = 50;
            let reasons = ["Amount matched", "Debit/Credit matched"];
            
            if (diffDays === 0) {
                score += 20;
                reasons.push("Exact date matched");
            } else {
                score += 10;
                reasons.push(`Date matched within ±${diffDays} day(s)`);
            }
            
            const vchTypeMatches = tally.vch_type.toLowerCase() === imp.vchType.toLowerCase();
            if (matchVchType) {
                if (!vchTypeMatches) return;
                score += 10;
                reasons.push("Voucher type matched");
            } else if (vchTypeMatches) {
                score += 5;
                reasons.push("Voucher type matched (bonus)");
            }
            
            const sim = calculateNarrationSimilarity(tally.narration, imp.narration);
            const narrationMatches = sim >= 0.3 || 
                                     tally.narration.toLowerCase().includes(imp.narration.toLowerCase()) || 
                                     imp.narration.toLowerCase().includes(tally.narration.toLowerCase());
            if (matchNarration) {
                if (!narrationMatches) return;
                score += 10;
                reasons.push("Narration matched");
            } else if (narrationMatches) {
                score += 5;
                reasons.push("Narration matched (bonus)");
            }
            
            const particularsMatches = tally.particulars.toLowerCase() === imp.particulars.toLowerCase() || 
                                         tally.particulars.toLowerCase().includes(imp.particulars.toLowerCase()) ||
                                         imp.particulars.toLowerCase().includes(tally.particulars.toLowerCase());
            if (matchParticulars) {
                if (!particularsMatches) return;
                score += 10;
                reasons.push("Particulars matched");
            } else if (particularsMatches) {
                score += 5;
                reasons.push("Particulars matched (bonus)");
            }
            
            score = Math.min(100, score);
            if (score > bestScore) {
                bestScore = score;
                bestMatch = tally;
                bestReasons = reasons;
            }
        });
        
        // Threshold: If amount, type and date (within tolerance) are matched, it's a Duplicate.
        if (bestMatch && bestScore >= 50) {
            usedTallyNos.add(bestMatch.vch_no);
            imp.duplicateStatus = "Duplicate";
            imp.matchedTallyVchNo = bestMatch.vch_no;
            imp.confidenceScore = bestScore;
            imp.matchReason = bestReasons;
            imp.matchedTallyVch = bestMatch;
        }
    });
    
    reviewState.duplicatesDetected = true;
    
    // Toggle sidebar filters card and actions container visibility
    const filterCard = document.getElementById("dup-filter-card");
    if (filterCard) filterCard.classList.remove("hidden");
    
    const actionsContainer = document.getElementById("dup-report-actions-container");
    if (actionsContainer) actionsContainer.classList.remove("hidden");
    
    const toggleBtn = document.getElementById("btn-toggle-dup-stats");
    if (toggleBtn) {
        toggleBtn.textContent = reviewState.showDuplicateStats ? "Hide Stats" : "Show Stats";
    }
    
    // Calculate and display statistics counts
    const totalCount = reviewState.vouchers.length;
    const dupCount = reviewState.vouchers.filter(v => v.duplicateStatus === "Duplicate").length;
    const newCount = reviewState.vouchers.filter(v => v.duplicateStatus === "New").length;
    
    document.getElementById("dup-stat-imported").textContent = totalCount;
    document.getElementById("dup-stat-duplicate").textContent = dupCount;
    document.getElementById("dup-stat-new").textContent = newCount;
    
    // Calculate opening/closing balances based on duplicates
    const opInput = document.getElementById("dup-bal-opening-input");
    if (opInput) {
        if (reviewState.manualOpeningBalance !== null) {
            opInput.value = reviewState.manualOpeningBalance.toFixed(2);
        } else {
            opInput.value = (reviewState.openingBalance || 0.00).toFixed(2);
        }
    }
    
    updateDupBalances();
    
    const compareTip = document.getElementById("dup-compare-tip");
    if (compareTip) {
        if (reviewState.showDuplicateStats) {
            compareTip.classList.remove("hidden");
        } else {
            compareTip.classList.add("hidden");
        }
    }
    
    const resultsContainer = document.getElementById("dup-results-container");
    if (resultsContainer) {
        if (reviewState.showDuplicateStats) {
            resultsContainer.classList.remove("hidden");
        } else {
            resultsContainer.classList.add("hidden");
        }
    }
    
    const summarySec = document.getElementById("dup-summary-section");
    if (summarySec) {
        if (reviewState.showDuplicateStats) {
            summarySec.classList.remove("hidden");
        } else {
            summarySec.classList.add("hidden");
        }
    }
    
    applyReviewFilters();
    onReviewTableScroll();
}

function openMatchDetailsDialog(vchId) {
    const impVch = reviewState.vouchers.find(v => v.id === vchId);
    if (!impVch || !impVch.matchedTallyVch) return;
    
    const tallyVch = impVch.matchedTallyVch;
    
    document.getElementById("match-details-confidence").textContent = `${impVch.confidenceScore}%`;
    
    const fields = [
        { label: "Date", imp: impVch.date, tally: formatTallyDate(tallyVch.date), match: impVch.matchReason.some(r => r.toLowerCase().includes("date")) },
        { label: "Voucher Type", imp: impVch.vchType, tally: tallyVch.vch_type, match: impVch.matchReason.some(r => r.toLowerCase().includes("type")) },
        { label: "Amount", imp: formatCurrency(impVch.debit > 0 ? impVch.debit : impVch.credit), tally: formatCurrency(tallyVch.amount), match: true },
        { label: "Debit/Credit", imp: impVch.debit > 0 ? "DEBIT" : "CREDIT", tally: tallyVch.type, match: true },
        { label: "Narration", imp: impVch.narration, tally: tallyVch.narration, match: impVch.matchReason.some(r => r.toLowerCase().includes("narration")) },
        { label: "Particulars", imp: impVch.particulars, tally: tallyVch.particulars, match: impVch.matchReason.some(r => r.toLowerCase().includes("particulars")) }
    ];
    
    let html = "";
    fields.forEach(f => {
        html += `
            <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; align-items: center;">
                <span style="font-weight: bold; color: #475569;">${f.label}</span>
                <span style="word-break: break-all; color: #0f172a;" title="${f.imp}">${f.imp || "--"}</span>
                <span style="word-break: break-all; color: #0f172a;" title="${f.tally}">${f.tally || "--"}</span>
            </div>
        `;
    });
    document.getElementById("match-comparison-rows").innerHTML = html;
    
    let reasonsHtml = "";
    impVch.matchReason.forEach(r => {
        reasonsHtml += `<li style="color: #16a34a; font-weight: bold;">✓ ${r}</li>`;
    });
    
    const matchVchType = false;
    const matchNarration = false;
    const matchParticulars = false;
    
    if (tallyVch.vch_type.toLowerCase() !== impVch.vchType.toLowerCase() && matchVchType) {
        reasonsHtml += `<li style="color: #ef4444; font-weight: bold;">✗ Voucher Type different (${impVch.vchType} vs ${tallyVch.vch_type})</li>`;
    }
    if (calculateNarrationSimilarity(tallyVch.narration, impVch.narration) < 0.3 && matchNarration) {
        reasonsHtml += `<li style="color: #ef4444; font-weight: bold;">✗ Narration different</li>`;
    }
    if (tallyVch.particulars.toLowerCase() !== impVch.particulars.toLowerCase() && matchParticulars) {
        reasonsHtml += `<li style="color: #ef4444; font-weight: bold;">✗ Particulars different</li>`;
    }
    
    document.getElementById("match-reasons-list").innerHTML = reasonsHtml;
    document.getElementById("review-modal-match-details").classList.remove("hidden");
}

function updateDupBalances() {
    const opInput = document.getElementById("dup-bal-opening-input");
    const opBalVal = opInput ? (parseFloat(opInput.value) || 0.00) : 0.00;
    
    reviewState.manualOpeningBalance = opBalVal;
    
    let dupTotalDebit = 0.00;
    let dupTotalCredit = 0.00;
    
    reviewState.vouchers.forEach(vch => {
        if (vch.duplicateStatus === "Duplicate") {
            dupTotalDebit += (vch.debit || 0.0);
            dupTotalCredit += (vch.credit || 0.0);
        }
    });
    
    const closingBal = opBalVal + dupTotalDebit - dupTotalCredit;
    
    const dupStatDebit = document.getElementById("dup-stat-debit");
    const dupStatCredit = document.getElementById("dup-stat-credit");
    const dupBalClosing = document.getElementById("dup-bal-closing");
    
    if (dupStatDebit) dupStatDebit.textContent = formatCurrency(dupTotalDebit);
    if (dupStatCredit) dupStatCredit.textContent = formatCurrency(dupTotalCredit);
    if (dupBalClosing) dupBalClosing.textContent = formatCurrency(closingBal);
}
window.updateDupBalances = updateDupBalances;

async function loadDuplicateHistory() {
    try {
        const response = await fetch("/api/tally/duplicate-history");
        const data = await response.json();
        if (data.success) {
            const companyDatalist = document.getElementById("dup-company-history-list");
            const bankDatalist = document.getElementById("dup-bank-history-list");
            
            if (companyDatalist && data.companies) {
                companyDatalist.innerHTML = "";
                data.companies.forEach(company => {
                    const option = document.createElement("option");
                    option.value = company;
                    companyDatalist.appendChild(option);
                });
            }
            if (bankDatalist && data.bank_ledgers) {
                bankDatalist.innerHTML = "";
                data.bank_ledgers.forEach(bank => {
                    const option = document.createElement("option");
                    option.value = bank;
                    bankDatalist.appendChild(option);
                });
            }
        }
    } catch (err) {
        console.error("Failed to load duplicate check autocomplete history:", err);
    }
}
window.loadDuplicateHistory = loadDuplicateHistory;

// -------------------------------------------------------------
// RECONCILIATION REPORT MODAL LOGIC
// -------------------------------------------------------------

function toggleDuplicateStatsVisibility() {
    reviewState.showDuplicateStats = !reviewState.showDuplicateStats;
    const resultsContainer = document.getElementById("dup-results-container");
    const compareTip = document.getElementById("dup-compare-tip");
    const toggleBtn = document.getElementById("btn-toggle-dup-stats");
    
    if (reviewState.showDuplicateStats) {
        const statusMsg = document.getElementById("dup-status-message");
        const summarySec = document.getElementById("dup-summary-section");
        if (resultsContainer && ((statusMsg && statusMsg.style.display !== "none" && statusMsg.innerHTML !== "") || (summarySec && !summarySec.classList.contains("hidden")))) {
            resultsContainer.classList.remove("hidden");
        }
        if (compareTip && ((statusMsg && statusMsg.style.display !== "none" && statusMsg.innerHTML !== "") || (summarySec && !summarySec.classList.contains("hidden")))) {
            compareTip.classList.remove("hidden");
        }
        if (toggleBtn) toggleBtn.textContent = "Hide Stats";
    } else {
        if (resultsContainer) resultsContainer.classList.add("hidden");
        if (compareTip) compareTip.classList.add("hidden");
        if (toggleBtn) toggleBtn.textContent = "Show Stats";
    }
}
window.toggleDuplicateStatsVisibility = toggleDuplicateStatsVisibility;

function getYearMonthKey(dateObj) {
    if (!dateObj) return null;
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
}

function getFormattedMonthName(yearMonthKey) {
    const [y, m] = yearMonthKey.split("-");
    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];
    return `${monthNames[parseInt(m, 10) - 1]} ${y}`;
}

function openDuplicateReportModal() {
    const companyName = document.getElementById("dup-company-name").value.trim() || "--";
    const bankName = document.getElementById("dup-bank-name").value.trim() || "--";
    const fromDate = document.getElementById("dup-from-date").value;
    const toDate = document.getElementById("dup-to-date").value;
    
    let formattedFrom = "--";
    let formattedTo = "--";
    if (fromDate) {
        const parts = fromDate.split("-");
        formattedFrom = `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    if (toDate) {
        const parts = toDate.split("-");
        formattedTo = `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    
    document.getElementById("rep-meta-company-ledger").textContent = `${companyName} / ${bankName}`;
    document.getElementById("rep-meta-period").textContent = `${formattedFrom} to ${formattedTo}`;
    
    let openingBalance = 0.00;
    if (reviewState.manualOpeningBalance !== null && reviewState.manualOpeningBalance !== undefined) {
        openingBalance = parseFloat(reviewState.manualOpeningBalance) || 0.00;
    } else if (reviewState.openingBalance !== null && reviewState.openingBalance !== undefined) {
        openingBalance = parseFloat(reviewState.openingBalance) || 0.00;
    }
    
    // Sync the duplicate check input
    const opInput = document.getElementById("dup-bal-opening-input");
    if (opInput) {
        opInput.value = openingBalance.toFixed(2);
    }
    
    document.getElementById("rep-stat-opening").textContent = formatCurrency(openingBalance);
    
    const appTotal = reviewState.vouchers.length;
    const tallyTotal = reviewState.tallyVouchers.length;
    
    let dupCount = 0;
    let dupDebit = 0.00;
    let dupCredit = 0.00;
    
    reviewState.vouchers.forEach(vch => {
        if (vch.duplicateStatus === "Duplicate") {
            dupCount++;
            dupDebit += (vch.debit || 0.00);
            dupCredit += (vch.credit || 0.00);
        }
    });
    
    const closingBalance = openingBalance + dupDebit - dupCredit;
    
    document.getElementById("rep-stat-debit").textContent = formatCurrency(dupDebit);
    document.getElementById("rep-stat-credit").textContent = formatCurrency(dupCredit);
    document.getElementById("rep-stat-closing").textContent = formatCurrency(closingBalance);
    document.getElementById("rep-stat-app-total").textContent = appTotal;
    document.getElementById("rep-stat-tally-total").textContent = tallyTotal;
    document.getElementById("rep-stat-duplicate").textContent = dupCount;
    
    const monthsData = {};
    
    const getMonthKeyAndInit = (dateStr) => {
        const dt = parseDateString(dateStr);
        if (!dt) return null;
        const key = getYearMonthKey(dt);
        if (!monthsData[key]) {
            monthsData[key] = {
                appCount: 0, appDebit: 0.0, appCredit: 0.0,
                tallyCount: 0, tallyDebit: 0.0, tallyCredit: 0.0,
                dupCount: 0, dupDebit: 0.0, dupCredit: 0.0
            };
        }
        return key;
    };
    
    reviewState.vouchers.forEach(vch => {
        const key = getMonthKeyAndInit(vch.date);
        if (key) {
            monthsData[key].appCount++;
            monthsData[key].appDebit += (vch.debit || 0.0);
            monthsData[key].appCredit += (vch.credit || 0.0);
            
            if (vch.duplicateStatus === "Duplicate") {
                monthsData[key].dupCount++;
                monthsData[key].dupDebit += (vch.debit || 0.0);
                monthsData[key].dupCredit += (vch.credit || 0.0);
            }
        }
    });
    
    reviewState.tallyVouchers.forEach(tally => {
        const formattedDate = formatTallyDate(tally.date);
        const key = getMonthKeyAndInit(formattedDate);
        if (key) {
            monthsData[key].tallyCount++;
            if (tally.type === "DEBIT") {
                monthsData[key].tallyDebit += tally.amount;
            } else if (tally.type === "CREDIT") {
                monthsData[key].tallyCredit += tally.amount;
            }
        }
    });
    
    const sortedKeys = Object.keys(monthsData).sort();
    
    let runningClosingApp = openingBalance;
    let runningClosingTally = openingBalance;
    let runningClosingDup = openingBalance;
    
    let totalAppCount = 0;
    let totalAppDebit = 0.00;
    let totalAppCredit = 0.00;
    
    let totalTallyCount = 0;
    let totalTallyDebit = 0.00;
    let totalTallyCredit = 0.00;
    
    let totalDupCount = 0;
    let totalDupDebit = 0.00;
    let totalDupCredit = 0.00;
    
    let cardsHtml = "";
    
    if (sortedKeys.length === 0) {
        cardsHtml = `<div style="padding: 30px; text-align: center; color: #64748b; font-weight: bold; font-size: 0.9rem; background: #ffffff; border-radius: 8px; border: 1px solid #cbd5e0;">No data available. Please import Tally data first.</div>`;
    } else {
        sortedKeys.forEach(key => {
            const data = monthsData[key];
            const monthName = getFormattedMonthName(key);
            
            runningClosingApp = runningClosingApp + data.appDebit - data.appCredit;
            runningClosingTally = runningClosingTally + data.tallyDebit - data.tallyCredit;
            runningClosingDup = runningClosingDup + data.dupDebit - data.dupCredit;
            
            totalAppCount += data.appCount;
            totalAppDebit += data.appDebit;
            totalAppCredit += data.appCredit;
            
            totalTallyCount += data.tallyCount;
            totalTallyDebit += data.tallyDebit;
            totalTallyCredit += data.tallyCredit;
            
            totalDupCount += data.dupCount;
            totalDupDebit += data.dupDebit;
            totalDupCredit += data.dupCredit;
            
            let matchText = "";
            if (data.appCount === 0) {
                if (data.tallyCount > 0) {
                    matchText = "Tally Only";
                } else {
                    matchText = "No Data";
                }
            } else {
                matchText = `${data.dupCount} / ${data.appCount} Matched`;
            }
            
            cardsHtml += `
                <div class="rep-month-card" style="background: #ffffff; border: 1px solid #cbd5e0; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <div class="rep-month-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; margin-bottom: 2px;">
                        <span style="font-size: 0.95rem; font-weight: bold; color: #002d5a;">${monthName}</span>
                        <span class="rep-month-badge" style="background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 0.7rem; border: 1px solid #bae6fd;">${matchText}</span>
                    </div>
                    
                    <!-- Columns Grid -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                        <!-- Column 1: Imported XML -->
                        <div class="rep-month-col rep-month-col-bank" style="background: #f8fafc; padding: 8px 10px; border-radius: 6px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 2px;">
                            <span style="font-size: 0.65rem; font-weight: bold; color: #475569; text-transform: uppercase;">Imported XML</span>
                            <div style="font-size: 0.76rem; color: #0f172a; margin-top: 2px;">Total Vouchers: <strong>${data.appCount}</strong></div>
                            <div style="font-size: 0.76rem; color: #16a34a;">Total Debit: <strong>${data.appDebit > 0 ? formatCurrency(data.appDebit) : "-"}</strong></div>
                            <div style="font-size: 0.76rem; color: #ef4444;">Total Credit: <strong>${data.appCredit > 0 ? formatCurrency(data.appCredit) : "-"}</strong></div>
                            <div style="font-size: 0.78rem; color: #0f172a; margin-top: 2px; border-top: 1px dashed #cbd5e0; padding-top: 2px;">
                                XML Closing Bal: <strong>${formatCurrency(runningClosingApp)}</strong>
                            </div>
                        </div>
                        
                        <!-- Column 2: Imported from Tally Prime -->
                        <div class="rep-month-col rep-month-col-tally" style="background: #f0fdfa; padding: 8px 10px; border-radius: 6px; border: 1px solid #ccfbf1; display: flex; flex-direction: column; gap: 2px;">
                            <span style="font-size: 0.65rem; font-weight: bold; color: #0d9488; text-transform: uppercase;">Data from Tally Prime</span>
                            <div style="font-size: 0.76rem; color: #0f172a; margin-top: 2px;">Total Vouchers: <strong>${data.tallyCount}</strong></div>
                            <div style="font-size: 0.76rem; color: #16a34a;">Total Debit: <strong>${data.tallyDebit > 0 ? formatCurrency(data.tallyDebit) : "-"}</strong></div>
                            <div style="font-size: 0.76rem; color: #ef4444;">Total Credit: <strong>${data.tallyCredit > 0 ? formatCurrency(data.tallyCredit) : "-"}</strong></div>
                            <div style="font-size: 0.78rem; color: #0f172a; margin-top: 2px; border-top: 1px dashed #cbd5e0; padding-top: 2px;">
                                Tally Closing Bal: <strong>${formatCurrency(runningClosingTally)}</strong>
                            </div>
                        </div>
                        
                        <!-- Column 3: Reconciled Stats -->
                        <div class="rep-month-col rep-month-col-rec" style="background: #fffbeb; padding: 8px 10px; border-radius: 6px; border: 1px solid #fef3c7; display: flex; flex-direction: column; gap: 2px;">
                            <span style="font-size: 0.65rem; font-weight: bold; color: #b45309; text-transform: uppercase;">Reconciliation Stats</span>
                            <div style="font-size: 0.76rem; color: #0f172a; margin-top: 2px;">Duplicate Vouchers: <strong>${data.dupCount}</strong></div>
                            <div style="font-size: 0.76rem; color: #0f172a;">Duplicate Debit: <strong style="color: #16a34a;">${data.dupDebit > 0 ? formatCurrency(data.dupDebit) : "-"}</strong></div>
                            <div style="font-size: 0.76rem; color: #0f172a;">Duplicate Credit: <strong style="color: #ef4444;">${data.dupCredit > 0 ? formatCurrency(data.dupCredit) : "-"}</strong></div>
                            <div style="font-size: 0.78rem; color: #0f172a; margin-top: 2px; border-top: 1px dashed #cbd5e0; padding-top: 2px;">
                                Dup Closing Bal: <strong style="color: #0f172a;">${formatCurrency(runningClosingDup)}</strong>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // Compute final aggregates
        const finalXMLClosing = openingBalance + totalAppDebit - totalAppCredit;
        const finalTallyClosing = openingBalance + totalTallyDebit - totalTallyCredit;
        const finalDupClosing = openingBalance + totalDupDebit - totalDupCredit;
        
        // Append Grand Totals Card at the end
        cardsHtml += `
            <div class="rep-month-card final-report-card" style="background: #f8fafc; border: 2px solid #002d5a; border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 15px;">
                <!-- Header -->
                <div class="rep-month-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #002d5a; padding-bottom: 6px; margin-bottom: 4px;">
                    <span style="font-size: 1.05rem; font-weight: 800; color: #002d5a; text-transform: uppercase; letter-spacing: 0.5px;">⭐ GRAND TOTAL / FINAL RECONCILIATION</span>
                    <span class="rep-month-badge" style="background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 12px; font-weight: 800; font-size: 0.72rem; border: 1px solid #bbf7d0;">Reconciliation Summary</span>
                </div>
                
                <!-- Columns Grid -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                    <!-- Column 1: Imported XML -->
                    <div class="rep-month-col rep-month-col-bank" style="background: #e2e8f0; padding: 10px; border-radius: 6px; border: 1.5px solid #cbd5e0; display: flex; flex-direction: column; gap: 3px;">
                        <span style="font-size: 0.68rem; font-weight: 800; color: #334155; text-transform: uppercase;">Imported XML (Grand Totals)</span>
                        <div style="font-size: 0.78rem; color: #0f172a; margin-top: 2px;">Total Vouchers: <strong>${totalAppCount}</strong></div>
                        <div style="font-size: 0.78rem; color: #16a34a;">Total Debit: <strong>${totalAppDebit > 0 ? formatCurrency(totalAppDebit) : "-"}</strong></div>
                        <div style="font-size: 0.78rem; color: #ef4444;">Total Credit: <strong>${totalAppCredit > 0 ? formatCurrency(totalAppCredit) : "-"}</strong></div>
                        <div style="font-size: 0.82rem; color: #0f172a; margin-top: 4px; border-top: 1.5px solid #94a3b8; padding-top: 4px;">
                            XML Final Closing: <strong style="font-size: 0.85rem;">${formatCurrency(finalXMLClosing)}</strong>
                        </div>
                    </div>
                    
                    <!-- Column 2: Imported from Tally Prime -->
                    <div class="rep-month-col rep-month-col-tally" style="background: #ccfbf1; padding: 10px; border-radius: 6px; border: 1.5px solid #99f6e4; display: flex; flex-direction: column; gap: 3px;">
                        <span style="font-size: 0.68rem; font-weight: 800; color: #0f766e; text-transform: uppercase;">Data from Tally Prime (Grand Totals)</span>
                        <div style="font-size: 0.78rem; color: #0f172a; margin-top: 2px;">Total Vouchers: <strong>${totalTallyCount}</strong></div>
                        <div style="font-size: 0.78rem; color: #16a34a;">Total Debit: <strong>${totalTallyDebit > 0 ? formatCurrency(totalTallyDebit) : "-"}</strong></div>
                        <div style="font-size: 0.78rem; color: #ef4444;">Total Credit: <strong>${totalTallyCredit > 0 ? formatCurrency(totalTallyCredit) : "-"}</strong></div>
                        <div style="font-size: 0.82rem; color: #0f172a; margin-top: 4px; border-top: 1.5px solid #5dd8c4; padding-top: 4px;">
                            Tally Final Closing: <strong style="font-size: 0.85rem;">${formatCurrency(finalTallyClosing)}</strong>
                        </div>
                    </div>
                    
                    <!-- Column 3: Reconciliation Stats -->
                    <div class="rep-month-col rep-month-col-rec" style="background: #fef3c7; padding: 10px; border-radius: 6px; border: 1.5px solid #fde047; display: flex; flex-direction: column; gap: 3px;">
                        <span style="font-size: 0.68rem; font-weight: 800; color: #92400e; text-transform: uppercase;">Reconciliation Grand Totals</span>
                        <div style="font-size: 0.78rem; color: #0f172a; margin-top: 2px;">Duplicate Vouchers: <strong>${totalDupCount}</strong></div>
                        <div style="font-size: 0.78rem; color: #0f172a;">Duplicate Debit: <strong style="color: #16a34a;">${totalDupDebit > 0 ? formatCurrency(totalDupDebit) : "-"}</strong></div>
                        <div style="font-size: 0.78rem; color: #0f172a;">Duplicate Credit: <strong style="color: #ef4444;">${totalDupCredit > 0 ? formatCurrency(totalDupCredit) : "-"}</strong></div>
                        <div style="font-size: 0.82rem; color: #0f172a; margin-top: 4px; border-top: 1.5px solid #d97706; padding-top: 4px;">
                            Dup Final Closing: <strong style="font-size: 0.85rem;">${formatCurrency(finalDupClosing)}</strong>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    document.getElementById("rep-monthly-cards-container").innerHTML = cardsHtml;
    
    document.body.style.overflow = "hidden";
    document.getElementById("review-modal-dup-report").classList.remove("hidden");
}
window.openDuplicateReportModal = openDuplicateReportModal;

function closeDuplicateReportModal() {
    document.body.style.overflow = "";
    document.getElementById("review-modal-dup-report").classList.add("hidden");
}
window.closeDuplicateReportModal = closeDuplicateReportModal;
