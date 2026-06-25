// static/js/app.js

// Global application state
const state = {
    activated: false,
    signature: "",
    role: "USER",
    activeTab: "bank-tab",
    files: {
        bank: null,
        cash: null
    },
    lexicon: {},
    cashSession: {
        flaggedNames: {},
        masterNames: {},
        debitLedger: "Cash",
        creditLedger: "Annadana Prasadam Donations Received"
    }
};

// ==========================================
// INITIALIZATION & ROUTING
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    checkLicenseStatus(true);
    setupDragAndDrop("bank");
    setupDragAndDrop("cash");
    
    // Auto-update debit ledger name when bank selection changes
    const bankTypeSelect = document.getElementById("bank-type-select");
    const debitLedgerInput = document.getElementById("bank-debit-ledger");
    if (bankTypeSelect && debitLedgerInput) {
        const updateLedgerDefault = () => {
            const val = bankTypeSelect.value;
            if (val.includes("BOB")) {
                debitLedgerInput.value = "BANK OF BARODA";
                debitLedgerInput.placeholder = "e.g. BANK OF BARODA";
            } else {
                debitLedgerInput.value = "STATE BANK OF INDIA";
                debitLedgerInput.placeholder = "e.g. STATE BANK OF INDIA";
            }
        };
        bankTypeSelect.addEventListener("change", updateLedgerDefault);
        updateLedgerDefault(); // Sync on initial load
    }
    
    // Hash routing for SPA tabs
    window.addEventListener("hashchange", handleRouting);
    if (!window.location.hash) {
        window.location.hash = "#bank-tab";
    } else {
        handleRouting();
    }

    // Trigger date picker popup when clicking anywhere inside a date input
    document.addEventListener("click", (e) => {
        if (e.target && e.target.type === "date") {
            try {
                e.target.showPicker();
            } catch (err) {
                console.log("showPicker() not supported in this window environment", err);
            }
        }
    });

    // Periodically check license status every 15 seconds to enforce expiry
    setInterval(() => {
        checkLicenseStatus();
    }, 15000);
});

function handleRouting() {
    const hash = window.location.hash || "#bank-tab";
    const tabId = hash.substring(1);
    switchTab(tabId);
}

function switchTab(tabId) {
    if (!state.activated && tabId !== "license-tab") {
        return; // Lock interface if not activated
    }
    
    // Admin tab guard
    if (tabId === "admin-tab" && state.role !== "ADMIN") {
        return; // Restrict access to admin tab
    }
    
    // Update active tab in state
    state.activeTab = tabId;
    
    // Update nav items
    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
        if (item.getAttribute("href") === `#${tabId}`) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });
    
    // Update tab panes
    document.querySelectorAll(".tab-pane").forEach(pane => {
        if (pane.id === tabId) {
            pane.classList.remove("hidden");
        } else {
            pane.classList.add("hidden");
        }
    });
    
    // Specific tab loads
    if (tabId === "lexicon-tab") {
        loadLexiconManager();
    } else if (tabId === "license-tab") {
        updateLicenseTabDetails();
    } else if (tabId === "admin-tab") {
        const targetInput = document.getElementById("admin-target-sig");
        if (targetInput) {
            if (!targetInput.value) {
                targetInput.value = state.signature;
            }
            checkTargetSignatureRoleLock(targetInput.value);
            if (!targetInput.dataset.listenerAdded) {
                targetInput.addEventListener("input", (e) => {
                    checkTargetSignatureRoleLock(e.target.value);
                });
                targetInput.dataset.listenerAdded = "true";
            }
        }
    }
}

function switchSubTab(subTabId) {
    document.querySelectorAll(".subtab-pane").forEach(pane => {
        if (pane.id === subTabId) {
            pane.classList.remove("hidden");
            pane.classList.add("active");
        } else {
            pane.classList.add("hidden");
            pane.classList.remove("active");
        }
    });
    document.querySelectorAll(".tabs-sub .btn-subtab").forEach(btn => {
        if (btn.getAttribute("onclick").includes(subTabId)) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

// ==========================================
// DRAG & DROP FILE UPLOADERS
// ==========================================
function setupDragAndDrop(type) {
    const dropzone = document.getElementById(`${type}-dropzone`);
    const fileInput = document.getElementById(`${type}-file-input`);
    
    // Stop bubble event from triggering dragzone click twice
    if (fileInput) {
        fileInput.addEventListener("click", (e) => e.stopPropagation());
    }
    
    // Click to browse (ignoring bubbled input click events)
    dropzone.addEventListener("click", (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });
    
    // Drag events
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dragover");
        }, false);
    });
    
    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dragover");
        }, false);
    });
    
    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(type);
        }
    }, false);
}

function handleFileSelect(type) {
    const fileInput = document.getElementById(`${type}-file-input`);
    const fileBadge = document.getElementById(`${type}-file-badge`);
    const fileNameSpan = document.getElementById(`${type}-file-name`);
    const dropzoneText = document.querySelector(`#${type}-dropzone .dropzone-text`);
    
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        state.files[type] = file;
        fileNameSpan.textContent = file.name;
        
        fileBadge.classList.remove("hidden");
        dropzoneText.classList.add("hidden");
        
        // Hide previous results card immediately when a new file is selected
        const resultsContainer = document.getElementById(`${type}-results`);
        if (resultsContainer) {
            resultsContainer.classList.add("hidden");
        }
        
        updateStatusBox(type, `🟢 Selected file: ${file.name} (${formatBytes(file.size)})`, "success");
    }
}

function clearFile(type) {
    const fileInput = document.getElementById(`${type}-file-input`);
    const fileBadge = document.getElementById(`${type}-file-badge`);
    const dropzoneText = document.querySelector(`#${type}-dropzone .dropzone-text`);
    
    event.stopPropagation(); // Avoid triggering click browse
    
    fileInput.value = "";
    state.files[type] = null;
    
    fileBadge.classList.add("hidden");
    dropzoneText.classList.remove("hidden");
    
    document.getElementById(`${type}-results`).classList.add("hidden");
    updateStatusBox(type, "Waiting for statement file ingestion...", "neutral");
}

// ==========================================
// LICENSING UTILITIES
// ==========================================
async function checkLicenseStatus(initial = false) {
    try {
        const res = await fetch("/api/status");
        const status = await res.json();
        
        state.activated = status.activated;
        state.signature = status.signature;
        state.role = status.role || "USER";
        
        const overlay = document.getElementById("license-overlay");
        const workspace = document.getElementById("app-workspace");
        const sigDisplay = document.getElementById("machine-sig-display");
        const expirySide = document.getElementById("license-expiry-side");
        const adminNavItem = document.getElementById("admin-nav-item");
        
        sigDisplay.textContent = status.signature;
        
        // Show/hide admin sidebar link
        if (status.activated && status.role === "ADMIN") {
            if (adminNavItem) adminNavItem.classList.remove("hidden");
        } else {
            if (adminNavItem) adminNavItem.classList.add("hidden");
        }
        
        if (status.activated) {
            overlay.classList.add("hidden");
            workspace.classList.remove("hidden");
            expirySide.textContent = status.expiry_date === "Lifetime" ? "Lifetime Active" : `Expires: ${status.expiry_date}`;
            
            if (initial) {
                // If activated, go to main route
                handleRouting();
            }
        } else {
            overlay.classList.remove("hidden");
            workspace.classList.add("hidden");
            document.getElementById("activation-error").textContent = status.message;
            document.getElementById("activation-error").classList.remove("hidden");
            
            // If active tab was admin-tab, switch away
            if (window.location.hash === "#admin-tab") {
                window.location.hash = "#license-tab";
            }
        }
    } catch (err) {
        console.error("License check failed:", err);
    }
}

async function submitActivation() {
    const keyInput = document.getElementById("activation-key-input");
    const errorBox = document.getElementById("activation-error");
    const key = keyInput.value.trim();
    
    if (!key) {
        showActivationError("Please enter an activation key.");
        return;
    }
    
    errorBox.classList.add("hidden");
    
    try {
        const res = await fetch("/api/activate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key })
        });
        const data = await res.json();
        
        if (data.success) {
            keyInput.value = "";
            checkLicenseStatus();
        } else {
            showActivationError(data.message);
        }
    } catch (err) {
        showActivationError("Failed to communicate with activation server.");
    }
}

function showActivationError(msg) {
    const errorBox = document.getElementById("activation-error");
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
}

async function deactivateLicense() {
    if (!confirm("Are you sure you want to deactivate and lock this computer installation?")) {
        return;
    }
    try {
        const res = await fetch("/api/deactivate", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            checkLicenseStatus();
        }
    } catch (err) {
        alert("Deactivation failed.");
    }
}

function updateLicenseTabDetails() {
    document.getElementById("lic-info-signature").textContent = state.signature;
    fetch("/api/status")
        .then(res => res.json())
        .then(status => {
            const statusVal = document.getElementById("lic-info-status");
            statusVal.textContent = status.activated ? "ACTIVE (Registered)" : "UNLICENSED";
            statusVal.className = status.activated ? "info-value text-success" : "info-value text-danger";
            
            const roleVal = document.getElementById("lic-info-role");
            if (roleVal) {
                roleVal.textContent = status.role || "USER";
            }
            
            document.getElementById("lic-info-expiry").textContent = status.expiry_date || "-";
            let daysText = "-";
            if (status.days_remaining !== undefined) {
                if (status.role === "ADMIN" || status.days_remaining === 99999) {
                    daysText = "∞";
                } else {
                    daysText = status.days_remaining;
                }
            }
            document.getElementById("lic-info-days").textContent = daysText;
        })
        .catch(err => console.error("Error updating license tab details:", err));
}

function copySignature() {
    navigator.clipboard.writeText(state.signature)
        .then(() => alert("Machine Signature ID copied to clipboard!"))
        .catch(err => console.error("Copy failed", err));
}

// ==========================================
// BANK CONVERSION OPERATIONS
// ==========================================
async function runBankConversion() {
    if (!state.files.bank) {
        updateStatusBox("bank", "⚠️ Error: Please upload a bank statement PDF first.", "danger");
        return;
    }
    
    const btn = document.getElementById("btn-convert-bank");
    const btnText = document.getElementById("bank-btn-text");
    const spinner = document.getElementById("bank-spinner");
    
    // Toggle loading UI
    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Processing Conversion Chain...";
    
    const bankType = document.getElementById("bank-type-select").value;
    const strategy = document.getElementById("strategy-select").value;
    const cutoffDate = document.getElementById("bank-cutoff-date").value;
    const debitLedger = document.getElementById("bank-debit-ledger").value.trim();
    const creditLedger = document.getElementById("bank-credit-ledger").value.trim();
    const prevBalance = document.getElementById("bank-prev-balance") ? document.getElementById("bank-prev-balance").value.trim() : "";
    
    const formData = new FormData();
    formData.append("file", state.files.bank);
    formData.append("bank_type", bankType);
    formData.append("strategy_type", strategy);
    formData.append("cutoff_date", cutoffDate);
    formData.append("debit_ledger", debitLedger);
    formData.append("credit_ledger", creditLedger);
    formData.append("prev_balance", prevBalance);
    
    updateStatusBox("bank", "⏳ Step 1: Running verification & row extraction...", "info");
    
    try {
        const res = await fetch("/api/convert_bank", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            renderBankResults(data);
            if (data.report.statement.is_reconciled) {
                updateStatusBox("bank", "✅ PDF Ingestion & Verification Chain Complete!", "success");
            } else {
                updateStatusBox("bank", `⚠️ Warning: ${data.report.statement.audit_message || "Audit pipeline validation checks failed."}`, "danger");
            }
        } else {
            updateStatusBox("bank", `❌ Error: ${data.message}`, "danger");
        }
    } catch (err) {
        updateStatusBox("bank", `❌ System Failure: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute Conversion Chain ⚡";
    }
}

async function reprocessBankLedgers() {
    const debitLedger = document.getElementById("bank-debit-ledger").value.trim();
    const creditLedger = document.getElementById("bank-credit-ledger").value.trim();
    
    // Grey out/disable the bank results card
    const resultsDiv = document.getElementById("bank-results");
    if (resultsDiv) {
        resultsDiv.style.opacity = "0.4";
        resultsDiv.style.pointerEvents = "none";
    }
    
    try {
        const res = await fetch("/api/reprocess_bank", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ debit_ledger: debitLedger, credit_ledger: creditLedger })
        });
        const data = await res.json();
        if (data.success) {
            renderBankResults(data);
            if (data.report.statement.is_reconciled) {
                updateStatusBox("bank", "✅ Custom Ledger settings applied and files re-generated successfully!", "success");
            } else {
                updateStatusBox("bank", `⚠️ Warning: ${data.report.statement.audit_message || "Audit pipeline validation checks failed."}`, "danger");
            }
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (err) {
        alert(`System error: ${err.message}`);
    } finally {
        if (resultsDiv) {
            resultsDiv.style.opacity = "1.0";
            resultsDiv.style.pointerEvents = "auto";
        }
    }
}

function renderBankResults(data) {
    const report = data.report;
    const stmt = report.statement;
    const xml = report.xml;
    
    // Set validation status badge
    const badge = document.getElementById("bank-audit-badge");
    badge.textContent = stmt.is_reconciled ? "🟢 RECONCILED" : "🔴 AUDIT ERROR";
    badge.className = `badge ${stmt.is_reconciled ? 'success' : 'danger'}`;
    
    // Set metrics
    document.getElementById("m-bank-count").textContent = formatNumber(stmt.transaction_count);
    document.getElementById("m-bank-inflow").textContent = formatCurrency(stmt.debit_total);
    document.getElementById("m-bank-outflow").textContent = formatCurrency(stmt.credit_total);
    document.getElementById("m-bank-closing").textContent = formatCurrency(stmt.closing_balance);
    
    // Build table rows
    const tbody = document.querySelector("#bank-summary-table tbody");
    tbody.innerHTML = "";
    
    if (stmt.monthly_summaries && stmt.monthly_summaries.length > 0) {
        stmt.monthly_summaries.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row.month_label}</strong></td>
                <td>${row.transaction_count}</td>
                <td>${formatCurrency(row.opening_balance)}</td>
                <td class="text-success">${formatCurrency(row.debit_total)}</td>
                <td class="text-danger">${formatCurrency(row.credit_total)}</td>
                <td><strong>${formatCurrency(row.closing_balance)}</strong></td>
                <td>${row.is_reconciled ? '🟢 PASSED' : '🔴 ERROR'}</td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    // Render dynamic SVG chart
    renderMonthlyChart("bank-chart-canvas", stmt.monthly_summaries, ["debit_total", "credit_total"], ["#10b981", "#ef4444"]);
    
    // Display results section
    document.getElementById("bank-results").classList.remove("hidden");
    
    // Inject a small re-process button next to the ledger input fields if not already done
    addReprocessButton("bank", reprocessBankLedgers);
}

// ==========================================
// ASHRAMAM LEDGER OPERATIONS
// ==========================================
async function runCashConversion() {
    if (!state.files.cash) {
        updateStatusBox("cash", "⚠️ Error: Please upload a receipts ledger sheet first.", "danger");
        return;
    }
    
    const btn = document.getElementById("btn-convert-cash");
    const btnText = document.getElementById("cash-btn-text");
    const spinner = document.getElementById("cash-spinner");
    
    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Ingesting Receipts Ledger...";
    
    const cutoffDate = document.getElementById("cash-cutoff-date").value;
    const debitLedger = document.getElementById("cash-debit-ledger").value.trim();
    const creditLedger = document.getElementById("cash-credit-ledger").value.trim();
    
    const formData = new FormData();
    formData.append("file", state.files.cash);
    formData.append("cutoff_date", cutoffDate);
    formData.append("debit_ledger", debitLedger);
    formData.append("credit_ledger", creditLedger);
    
    updateStatusBox("cash", "⏳ Ingesting workbook sheets...", "info");
    
    try {
        const res = await fetch("/api/convert_cash", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            state.cashSession.flaggedNames = data.flagged_names;
            state.cashSession.masterNames = data.master_names;
            state.cashSession.debitLedger = data.debit_ledger;
            state.cashSession.creditLedger = data.credit_ledger;
            
            renderCashResults(data);
            updateStatusBox("cash", "✅ Ingestion complete! Review spelling flags below.", "success");
        } else {
            updateStatusBox("cash", `❌ Error: ${data.message}`, "danger");
        }
    } catch (err) {
        updateStatusBox("cash", `❌ System error: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute Receipts Ingestion 🔮";
    }
}

async function reprocessCashLedgers(fromLexicon = false) {
    const debitLedger = document.getElementById("cash-debit-ledger").value.trim();
    const creditLedger = document.getElementById("cash-credit-ledger").value.trim();
    
    // Grey out/disable the cash exports card (the second card in the results panel)
    const resultsCards = document.querySelectorAll("#cash-results .glass-card");
    const exportsCard = resultsCards[1];
    if (exportsCard) {
        exportsCard.style.opacity = "0.4";
        exportsCard.style.pointerEvents = "none";
    }
    
    try {
        const res = await fetch("/api/reprocess_cash", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ debit_ledger: debitLedger, credit_ledger: creditLedger })
        });
        const data = await res.json();
        if (data.success) {
            state.cashSession.debitLedger = data.debit_ledger;
            state.cashSession.creditLedger = data.credit_ledger;
            renderCashResults(data);
            
            const msg = fromLexicon 
                ? "Lexicon updated and ledger reprocessed successfully!" 
                : "Ledger configurations applied successfully!";
            alert(msg);
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (err) {
        alert(`System error: ${err.message}`);
    } finally {
        if (exportsCard) {
            exportsCard.style.opacity = "1.0";
            exportsCard.style.pointerEvents = "auto";
        }
    }
}

function renderCashResults(data) {
    const report = data.report;
    
    // Set counts
    document.getElementById("m-cash-count").textContent = formatNumber(report.total_count);
    document.getElementById("m-cash-total").textContent = formatCurrency(report.total_debit);
    
    // Load Translation tables
    populateTranslationTables(data.flagged_names, data.master_names);
    
    // Build Monthly summary table
    const tbody = document.querySelector("#cash-summary-table tbody");
    tbody.innerHTML = "";
    
    if (report.monthly_summaries && report.monthly_summaries.length > 0) {
        report.monthly_summaries.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${row.month_label}</strong></td>
                <td>${row.transaction_count}</td>
                <td class="text-success">${formatCurrency(row.debit_total)}</td>
                <td>🟢 VERIFIED</td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    // Draw bar chart
    renderMonthlyChart("cash-chart-canvas", report.monthly_summaries, ["debit_total"], ["#10b981"]);
    
    // Show results
    document.getElementById("cash-results").classList.remove("hidden");
    addReprocessButton("cash", reprocessCashLedgers);
}

function populateTranslationTables(flaggedNames, masterNames) {
    const flagsTbody = document.querySelector("#cash-flags-table tbody");
    flagsTbody.innerHTML = "";
    
    const flaggedList = Object.keys(flaggedNames);
    document.getElementById("count-critical-flags").textContent = flaggedList.length;
    
    if (flaggedList.length === 0) {
        flagsTbody.innerHTML = `<tr><td colspan="2" class="text-success text-center">🟢 No severe Telugu name spelling flags in this workbook block!</td></tr>`;
    } else {
        flaggedList.forEach((telugu, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${telugu}</td>
                <td><input type="text" class="flag-input" data-telugu="${telugu}" data-original="${flaggedNames[telugu]}" value="${flaggedNames[telugu]}"></td>
            `;
            flagsTbody.appendChild(tr);
        });
    }
    
    const dirTbody = document.querySelector("#cash-directory-table tbody");
    dirTbody.innerHTML = "";
    
    const masterList = Object.keys(masterNames);
    document.getElementById("count-all-donors").textContent = masterList.length;
    
    if (masterList.length === 0) {
        dirTbody.innerHTML = `<tr><td colspan="2" class="text-center">No donor names parsed.</td></tr>`;
    } else {
        masterList.forEach((telugu, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${telugu}</td>
                <td><input type="text" class="dir-input" data-telugu="${telugu}" data-original="${masterNames[telugu]}" value="${masterNames[telugu]}"></td>
            `;
            dirTbody.appendChild(tr);
        });
    }
}

async function saveTranslationDesk() {
    const updates = {};
    
    // Pull updates from inputs (only if modified by the user)
    document.querySelectorAll("#cash-flags-table .flag-input").forEach(input => {
        const telugu = input.getAttribute("data-telugu");
        const val = input.value.trim();
        const original = (input.getAttribute("data-original") || "").trim();
        if (val && val !== original) {
            updates[telugu] = val;
        }
    });
    
    document.querySelectorAll("#cash-directory-table .dir-input").forEach(input => {
        const telugu = input.getAttribute("data-telugu");
        const val = input.value.trim();
        const original = (input.getAttribute("data-original") || "").trim();
        if (val && val !== original) {
            updates[telugu] = val;
        }
    });
    
    if (Object.keys(updates).length === 0) {
        alert("No translation updates recorded.");
        return;
    }
    
    try {
        const res = await fetch("/api/lexicon/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ updates })
        });
        const data = await res.json();
        
        if (data.success) {
            // Direct reprocess and alert inside reprocessCashLedgers
            await reprocessCashLedgers(true);
        } else {
            alert(`Error updating lexicon: ${data.message}`);
        }
    } catch (err) {
        alert(`System error: ${err.message}`);
    }
}

function filterDirectoryTable() {
    const q = document.getElementById("directory-search-input").value.toLowerCase();
    document.querySelectorAll("#cash-directory-table tbody tr").forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(q)) {
            row.classList.remove("hidden");
        } else {
            row.classList.add("hidden");
        }
    });
}

// ==========================================
// TRANSLITERATION LEXICON MANAGER
// ==========================================
async function loadLexiconManager() {
    try {
        const res = await fetch("/api/lexicon");
        const data = await res.json();
        state.lexicon = data;
        renderLexiconTable(data);
    } catch (err) {
        console.error("Failed to load lexicon", err);
    }
}

function renderLexiconTable(lexiconData) {
    const tbody = document.querySelector("#lexicon-manager-table tbody");
    tbody.innerHTML = "";
    
    const keys = Object.keys(lexiconData);
    if (keys.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center">No translation items stored.</td></tr>`;
        return;
    }
    
    keys.forEach(k => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${k}</strong></td>
            <td><input type="text" value="${lexiconData[k]}" onchange="updateLexiconTerm('${k}', this.value)"></td>
            <td>
                <button class="btn btn-danger" style="padding: 6px 12px; font-size: 0.8rem;" onclick="deleteLexiconTerm('${k}')">Remove</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function updateLexiconTerm(teluguKey, newEnglish) {
    const updates = {};
    updates[teluguKey] = newEnglish;
    
    try {
        const res = await fetch("/api/lexicon/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ updates })
        });
        const data = await res.json();
        if (!data.success) {
            alert(`Error: ${data.message}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function deleteLexiconTerm(teluguKey) {
    if (!confirm(`Are you sure you want to remove the translation for '${teluguKey}'?`)) {
        return;
    }
    try {
        const res = await fetch("/api/lexicon/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ deletes: [teluguKey] })
        });
        const data = await res.json();
        if (data.success) {
            loadLexiconManager();
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (err) {
        console.error(err);
    }
}

function searchLexiconTable() {
    const q = document.getElementById("lexicon-search").value.toLowerCase();
    document.querySelectorAll("#lexicon-manager-table tbody tr").forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(q)) {
            row.classList.remove("hidden");
        } else {
            row.classList.add("hidden");
        }
    });
}

// Modal actions
function openAddLexiconModal() {
    document.getElementById("add-lexicon-modal").classList.remove("hidden");
    document.getElementById("modal-error").classList.add("hidden");
}

function closeAddLexiconModal() {
    document.getElementById("add-lexicon-modal").classList.add("hidden");
    document.getElementById("new-telugu-term").value = "";
    document.getElementById("new-english-term").value = "";
}

async function submitNewLexiconEntry() {
    const telugu = document.getElementById("new-telugu-term").value.trim();
    const english = document.getElementById("new-english-term").value.trim();
    const errorBox = document.getElementById("modal-error");
    
    if (!telugu || !english) {
        errorBox.textContent = "Both fields are required.";
        errorBox.classList.remove("hidden");
        return;
    }
    
    const updates = {};
    updates[telugu] = english;
    
    try {
        const res = await fetch("/api/lexicon/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ updates })
        });
        const data = await res.json();
        if (data.success) {
            closeAddLexiconModal();
            loadLexiconManager();
        } else {
            errorBox.textContent = data.message;
            errorBox.classList.remove("hidden");
        }
    } catch (err) {
        errorBox.textContent = "System communication error.";
        errorBox.classList.remove("hidden");
    }
}

async function cleanLexiconMismatches() {
    if (!confirm("Are you sure you want to clean the translation dictionary? This will remove all English-to-English word mappings, leaving only Telugu-to-English mappings.")) {
        return;
    }
    
    try {
        const btn = document.querySelector('button[onclick="cleanLexiconMismatches()"]');
        const origText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = "🧹 Cleaning...";
        
        const res = await fetch("/api/lexicon/clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        
        btn.disabled = false;
        btn.innerHTML = origText;
        
        if (data.success) {
            alert(data.message);
            loadLexiconManager();
        } else {
            alert(`Error cleaning dictionary: ${data.message}`);
        }
    } catch (err) {
        console.error(err);
        alert("Failed to clean dictionary. Communication error.");
    }
}

// ==========================================
// DYNAMIC SVG CHART GENERATOR (NO DEPENDENCIES)
// ==========================================
function renderMonthlyChart(containerId, data, keys, colors) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    
    if (!data || data.length === 0) {
        container.innerHTML = "<p class='neutral-status'>No monthly records to chart.</p>";
        return;
    }
    
    // Find max value for scaling
    let maxVal = 0;
    data.forEach(d => {
        keys.forEach(k => {
            if (d[k] > maxVal) maxVal = d[k];
        });
    });
    if (maxVal === 0) maxVal = 100;
    
    // Set dimensions
    const width = 800;
    const height = 300;
    const paddingLeft = 60;
    const paddingRight = 20;
    const paddingTop = 20;
    const paddingBottom = 40;
    
    const plotWidth = width - paddingLeft - paddingRight;
    const plotHeight = height - paddingTop - paddingBottom;
    
    // Create SVG
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("class", "chart-svg");
    
    // Draw grid lines
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
        const y = paddingTop + (plotHeight / gridLines) * i;
        const val = maxVal - (maxVal / gridLines) * i;
        
        // Line
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", paddingLeft);
        line.setAttribute("y1", y);
        line.setAttribute("x2", width - paddingRight);
        line.setAttribute("y2", y);
        line.setAttribute("stroke", "rgba(255,255,255,0.06)");
        line.setAttribute("stroke-width", "1");
        svg.appendChild(line);
        
        // Label
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", paddingLeft - 10);
        text.setAttribute("y", y + 4);
        text.setAttribute("fill", "#6b7280");
        text.setAttribute("font-size", "10");
        text.setAttribute("text-anchor", "end");
        text.textContent = formatCompactCurrency(val);
        svg.appendChild(text);
    }
    
    // Draw columns
    const colCount = data.length;
    const colSpacing = plotWidth / colCount;
    const barWidth = Math.max(12, (colSpacing * 0.5) / keys.length);
    
    data.forEach((d, dIdx) => {
        const colX = paddingLeft + colSpacing * dIdx + colSpacing / 2;
        
        // Column label (Month)
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", colX);
        label.setAttribute("y", height - paddingBottom + 18);
        label.setAttribute("fill", "#9ca3af");
        label.setAttribute("font-size", "10");
        label.setAttribute("text-anchor", "middle");
        label.textContent = d.month_label;
        svg.appendChild(label);
        
        // Draw bars for each key
        keys.forEach((k, kIdx) => {
            const val = d[k] || 0;
            const barHeight = (val / maxVal) * plotHeight;
            const barX = colX + (kIdx - (keys.length - 1) / 2) * (barWidth + 4) - barWidth / 2;
            const barY = height - paddingBottom - barHeight;
            
            const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            rect.setAttribute("x", barX);
            rect.setAttribute("y", barY);
            rect.setAttribute("width", barWidth);
            rect.setAttribute("height", barHeight);
            rect.setAttribute("fill", colors[kIdx]);
            rect.setAttribute("rx", "3");
            
            // Subtle transition/hover
            const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
            title.textContent = `${d.month_label} (${k === 'debit_total' ? 'Inflow' : 'Outflow'}): ${formatCurrency(val)}`;
            rect.appendChild(title);
            
            svg.appendChild(rect);
        });
    });
    
    container.appendChild(svg);
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================
function updateStatusBox(type, msg, status) {
    const box = document.getElementById(`${type}-status-info`);
    let classVal = "neutral-status";
    if (status === "success") classVal = "text-success";
    if (status === "danger") classVal = "text-danger";
    if (status === "info") classVal = "text-highlight";
    
    box.innerHTML = `<p class="${classVal}">${msg}</p>`;
}

function addReprocessButton(type, reprocessCallback) {
    // Check if reprocess button already exists in controls card
    const card = document.querySelector(`#${type}-tab .glass-card`);
    let reprocessBtn = document.getElementById(`btn-reprocess-${type}`);
    
    if (!reprocessBtn) {
        const container = card.querySelector(".actions-bar");
        reprocessBtn = document.createElement("button");
        reprocessBtn.id = `btn-reprocess-${type}`;
        reprocessBtn.className = "btn btn-secondary btn-block mt-2";
        reprocessBtn.textContent = "Apply Custom Ledger Names & Re-Generate 🔄";
        reprocessBtn.onclick = reprocessCallback;
        container.appendChild(reprocessBtn);
    }
}

function toggleDateFilter(type) {
    const strat = document.getElementById("strategy-select").value;
    const filter = document.getElementById("bank-date-filter-group");
    const prevBalGroup = document.getElementById("bank-prev-balance-group");
    
    if (strat === "Incomplete statement (Continuation)") {
        if (filter) filter.classList.remove("hidden");
        if (prevBalGroup) prevBalGroup.classList.remove("hidden");
    } else {
        if (filter) filter.classList.add("hidden");
        if (prevBalGroup) prevBalGroup.classList.add("hidden");
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatNumber(num) {
    return parseInt(num).toLocaleString('en-IN');
}

function formatCurrency(num) {
    return '₹ ' + parseFloat(num).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatCompactCurrency(num) {
    if (num >= 10000000) { // 1 Crore
        return '₹' + (num / 10000000).toFixed(1) + 'Cr';
    }
    if (num >= 100000) { // 1 Lakh
        return '₹' + (num / 100000).toFixed(1) + 'L';
    }
    if (num >= 1000) {
        return '₹' + (num / 1000).toFixed(0) + 'K';
    }
    return '₹' + num.toFixed(0);
}

// Intercept clicks on download buttons and route to pywebview native save dialog or browser stream
async function triggerDownload(fileType) {
    if (window.pywebview && window.pywebview.api) {
        try {
            const res = await window.pywebview.api.download_file(fileType);
            if (res.success) {
                alert(`File successfully saved to:\n${res.path}`);
            } else if (res.message && res.message !== "Cancelled" && res.message !== "Save cancelled") {
                alert(`Save failed: ${res.message}`);
            }
        } catch (err) {
            alert(`Native download error: ${err.message}`);
        }
    } else {
        // Fallback for standard web browser
        window.open(`/api/download/${fileType}`, '_blank');
    }
}

// ==========================================
// ADMIN CONSOLE UTILITIES
// ==========================================
async function generateAdminKey() {
    const signatureInput = document.getElementById("admin-target-sig");
    const roleSelect = document.getElementById("admin-role-select");
    const durationSelect = document.getElementById("admin-duration-select");
    const resultContainer = document.getElementById("admin-key-result-container");
    const displaySpan = document.getElementById("admin-generated-key-display");
    
    const signature = signatureInput.value.trim().toUpperCase();
    const role = roleSelect.value;
    const duration = durationSelect.value;
    
    if (!signature) {
        alert("Please enter a target machine signature ID.");
        return;
    }
    
    try {
        const res = await fetch("/api/admin/generate_key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ signature, role, duration })
        });
        const data = await res.json();
        
        if (data.success) {
            displaySpan.textContent = data.key;
            resultContainer.classList.remove("hidden");
        } else {
            alert(`Key Generation Failed: ${data.message}`);
        }
    } catch (err) {
        alert(`Error communicating with server: ${err.message}`);
    }
}

function copyGeneratedAdminKey() {
    const displaySpan = document.getElementById("admin-generated-key-display");
    const key = displaySpan.textContent.trim();
    if (key && key !== "ACT-USER-XXXXX-XXXXX") {
        navigator.clipboard.writeText(key)
            .then(() => alert("Generated Activation Key copied to clipboard!"))
            .catch(err => console.error("Copy failed", err));
    }
}

function checkTargetSignatureRoleLock(sig) {
    const roleSelect = document.getElementById("admin-role-select");
    if (!roleSelect) return;
    
    const formattedSig = sig.trim().toUpperCase();
    const isOwnMachine = (state.signature && formattedSig === state.signature.toUpperCase());
    
    if (isOwnMachine && state.role === "ADMIN") {
        roleSelect.value = "ADMIN";
        roleSelect.disabled = true;
    } else {
        roleSelect.disabled = false;
    }
}
