// -------------------------------------------------------------
// DUPLICATE VOUCHER DETECTION ISOLATED EXTENSION
// -------------------------------------------------------------

// Extend global state
reviewState.tallyVouchers = [];
reviewState.duplicateDetectionRun = false;

// 1. DYNAMIC DOM INTEGRATION & INITIALIZATION ON STARTUP
document.addEventListener("DOMContentLoaded", () => {
    // Inject duplicate panel into the table container
    const tableContainer = document.getElementById("review-table-container");
    const dupPanel = document.getElementById("duplicate-detection-panel");
    if (tableContainer && dupPanel) {
        tableContainer.insertBefore(dupPanel, tableContainer.firstChild);
    }
    
    // Inject sidebar filter card below the main stats box
    const totalBtn = document.getElementById("btn-stats-total");
    if (totalBtn) {
        const statsBox = totalBtn.parentNode;
        if (statsBox && statsBox.parentNode) {
            const dupFilterCard = document.getElementById("dup-filter-card");
            if (dupFilterCard) {
                statsBox.parentNode.insertBefore(dupFilterCard, statsBox.nextSibling);
            }
        }
    }
    
    // Inject match details modal to body
    const matchModal = document.getElementById("review-modal-match-details");
    if (matchModal) {
        document.body.appendChild(matchModal);
    }
    
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
        
        // Show sidebar filter card if detection has results
        const filterCard = document.getElementById("dup-filter-card");
        if (filterCard) filterCard.classList.remove("hidden");
    } else {
        // Hide panel
        dupPanel.classList.add("hidden");
        reviewState.duplicateDetectionRun = false;
        
        const summarySec = document.getElementById("dup-summary-section");
        if (summarySec) summarySec.classList.add("hidden");
        
        colHeaders.forEach(h => {
            const el = document.getElementById(h);
            if (el) el.style.display = "none";
        });
        
        // Hide sidebar filter card
        const filterCard = document.getElementById("dup-filter-card");
        if (filterCard) filterCard.classList.add("hidden");
        
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
        if (btnDupOnly) btnDupOnly.classList.add("active-modified");
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
    const el = document.getElementById("review-modal-match-details");
    if (el && !el.classList.contains("hidden")) {
        closeReviewModal("match-details");
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
    
    reviewState.tallyVouchers = [];
    
    // Set default company name input if available in dropdown
    const companySelect = document.getElementById("review-company-select");
    const companyInput = document.getElementById("dup-company-name");
    if (companyInput && companySelect) {
        companyInput.value = companySelect.value || "";
    }
    
    // Identify bank ledger from input bankName
    const bankInput = document.getElementById("dup-bank-name");
    if (bankInput) {
        const bankName = reviewState.originalFileName || "";
        let defaultBank = "BANK OF BARODA";
        if (bankName.toLowerCase().includes("sbi") || bankName.toLowerCase().includes("state")) {
            defaultBank = "STATE BANK OF INDIA";
        } else if (bankName.toLowerCase().includes("axis")) {
            defaultBank = "AXIS BANK";
        }
        bankInput.value = defaultBank;
    }

    // Prefill dates
    if (reviewState.vouchers && reviewState.vouchers.length > 0) {
        const sortedDates = [...reviewState.vouchers].map(v => v.date).sort();
        if (sortedDates.length > 0) {
            const minD = sortedDates[0];
            const maxD = sortedDates[sortedDates.length - 1];
            
            function toISODate(dStr) {
                const parts = dStr.split("-");
                if (parts.length === 3) {
                    return `${parts[2]}-${parts[1]}-${parts[0]}`;
                }
                return "";
            }
            
            const dupFrom = document.getElementById("dup-from-date");
            const dupTo = document.getElementById("dup-to-date");
            if (dupFrom) dupFrom.value = toISODate(minD);
            if (dupTo) dupTo.value = toISODate(maxD);
        }
    }
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
                    "background-color: #14532d !important; color: #bbf7d0;" : 
                    "background-color: #d1fae5 !important; color: #065f46;";
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
    const statusMsg = document.getElementById("dup-status-message");
    
    if (!companyName) {
        alert("Please enter a Tally Company Name.");
        return;
    }
    if (!fromDate || !toDate) {
        alert("Please select From and To dates.");
        return;
    }
    
    if (statusMsg) {
        statusMsg.style.display = "block";
        statusMsg.style.background = "#ebf8ff";
        statusMsg.style.color = "#005ea5";
        statusMsg.style.border = "1px solid #bae6fd";
        statusMsg.innerHTML = "⌛ Connecting to Tally Prime and importing vouchers...";
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
            
            if (statusMsg) {
                statusMsg.style.background = "#f0fdf4";
                statusMsg.style.color = "#16a34a";
                statusMsg.style.border = "1px solid #bbf7d0";
                
                const fromParts = fromDate.split("-");
                const toParts = toDate.split("-");
                const fromFormatted = `${fromParts[2]}/${fromParts[1]}/${fromParts[0]}`;
                const toFormatted = `${toParts[2]}/${toParts[1]}/${toParts[0]}`;
                
                statusMsg.innerHTML = `✓ Company Imported Successfully: <b>${result.company_name}</b><br/>Number of vouchers imported: <b>${reviewState.tallyVouchers.length}</b><br/>Date Range: <b>${fromFormatted} to ${toFormatted}</b>`;
            }
        } else {
            if (statusMsg) {
                statusMsg.style.background = "#fef2f2";
                statusMsg.style.color = "#ef4444";
                statusMsg.style.border = "1px solid #fecaca";
                statusMsg.innerHTML = `❌ Error: ${result.message}`;
            }
        }
    } catch (err) {
        if (statusMsg) {
            statusMsg.style.background = "#fef2f2";
            statusMsg.style.color = "#ef4444";
            statusMsg.style.border = "1px solid #fecaca";
            statusMsg.innerHTML = `❌ System Error: ${err.message}`;
        }
    }
}

function detectDuplicates() {
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
    
    const matchVchType = document.getElementById("dup-cond-vchtype").checked;
    const matchNarration = document.getElementById("dup-cond-narration").checked;
    const matchParticulars = document.getElementById("dup-cond-particulars").checked;
    
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
    
    // Toggle sidebar filters card visibility
    const filterCard = document.getElementById("dup-filter-card");
    if (filterCard) filterCard.classList.remove("hidden");
    
    // Calculate and display statistics counts
    const totalCount = reviewState.vouchers.length;
    const dupCount = reviewState.vouchers.filter(v => v.duplicateStatus === "Duplicate").length;
    const newCount = reviewState.vouchers.filter(v => v.duplicateStatus === "New").length;
    
    document.getElementById("dup-stat-imported").textContent = totalCount;
    document.getElementById("dup-stat-duplicate").textContent = dupCount;
    document.getElementById("dup-stat-new").textContent = newCount;
    
    // Calculate opening/closing balances based on duplicates
    const opBal = reviewState.openingBalance || 0.00;
    let cumulativeDupBal = opBal;
    
    reviewState.vouchers.forEach(vch => {
        if (vch.duplicateStatus === "Duplicate") {
            cumulativeDupBal += (vch.debit || 0.0) - (vch.credit || 0.0);
        }
    });
    
    document.getElementById("dup-bal-opening").textContent = formatCurrency(opBal);
    document.getElementById("dup-bal-closing").textContent = formatCurrency(cumulativeDupBal);
    
    const summarySec = document.getElementById("dup-summary-section");
    if (summarySec) summarySec.classList.remove("hidden");
    
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
    
    const matchVchType = document.getElementById("dup-cond-vchtype").checked;
    const matchNarration = document.getElementById("dup-cond-narration").checked;
    const matchParticulars = document.getElementById("dup-cond-particulars").checked;
    
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
