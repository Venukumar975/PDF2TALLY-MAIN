// static/js/app.js

// Global application state
const state = {
    activated: false,
    userLoggedIn: false,
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
    loadSavedLayouts();
    
    // Auto-update debit ledger name when bank selection changes
    const bankTypeSelect = document.getElementById("bank-type-select");
    const debitLedgerInput = document.getElementById("bank-debit-ledger");
    if (bankTypeSelect && debitLedgerInput) {
        const updateLedgerDefault = () => {
            const val = bankTypeSelect.value;
            if (val.includes("BOB")) {
                debitLedgerInput.value = "BANK OF BARODA";
                debitLedgerInput.placeholder = "e.g. BANK OF BARODA";
            } else if (val.includes("Axis")) {
                debitLedgerInput.value = "AXIS BANK";
                debitLedgerInput.placeholder = "e.g. AXIS BANK";
            } else if (val.includes("Hybrid")) {
                debitLedgerInput.value = "Generic Bank";
                debitLedgerInput.placeholder = "e.g. Generic Bank";
            } else {
                debitLedgerInput.value = "STATE BANK OF INDIA";
                debitLedgerInput.placeholder = "e.g. STATE BANK OF INDIA";
            }
        };
        bankTypeSelect.addEventListener("change", updateLedgerDefault);
        updateLedgerDefault(); // Sync on initial load
    }
    
    // Admin sig input listener removed

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
    
    // Admin tab guard removed
    
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
    // Admin tab load logic removed
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
        
        if (type === "bank") {
            triggerOpeningBalanceDetection();
        }
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
// Global countdown timer intervals
let localLicenseCountdownInterval = null;
let adminTableCountdownInterval = null;
let activeRegistrationsList = []; // Cache of fetched active registrations for ticking
let registeredSignatures = new Set();

function padZero(num) {
    return num.toString().padStart(2, "0");
}

function formatCountdown(seconds) {
    if (seconds === -1) return "Lifetime";
    if (seconds <= 0) return "00:00:00:00:00 (Expired)";
    
    let months = Math.floor(seconds / (30 * 86400));
    let rem = seconds % (30 * 86400);
    
    let days = Math.floor(rem / 86400);
    rem %= 86400;
    
    let hours = Math.floor(rem / 3600);
    rem %= 3600;
    
    let minutes = Math.floor(rem / 60);
    let secs = rem % 60;
    
    return `${padZero(months)}:${padZero(days)}:${padZero(hours)}:${padZero(minutes)}:${padZero(secs)}`;
}

async function checkLicenseStatus(initial = false) {
    const overlay = document.getElementById("license-overlay");
    const workspace = document.getElementById("app-workspace");
    const sigDisplay = document.getElementById("machine-sig-display");
    const expirySide = document.getElementById("license-expiry-side");
    const adminNavItem = document.getElementById("admin-nav-item");
    const adminCurrentRole = document.getElementById("admin-current-role");
    
    const stateLoading = document.getElementById("lic-state-loading");
    const stateError = document.getElementById("lic-state-error");
    const statePortal = document.getElementById("lic-state-portal");
    
    // Default show loading state first if it's the initial call
    if (initial) {
        if (overlay) overlay.classList.remove("hidden");
        if (workspace) workspace.classList.add("hidden");
        if (stateLoading) stateLoading.classList.remove("hidden");
        if (stateError) stateError.classList.add("hidden");
        if (statePortal) statePortal.classList.add("hidden");
        
        // Start connection timer display
        let start = Date.now();
        let connTimer = setInterval(() => {
            let elapsed = Math.round((Date.now() - start) / 1000);
            let timerEl = document.getElementById("lic-loading-timer");
            if (timerEl) {
                timerEl.textContent = `Attempting connection: ${elapsed}s / 60s`;
            }
            if (elapsed >= 60 || !stateLoading || stateLoading.classList.contains("hidden")) {
                clearInterval(connTimer);
            }
        }, 1000);
    }
    
    try {
        const res = await fetch("/api/status");
        const status = await res.json();
        
        state.activated = status.activated;
        state.signature = status.signature;
        state.role = status.role || "USER";
        
        if (sigDisplay) sigDisplay.textContent = status.signature || "UNKNOWN";
        
        // Auto-prefill saved license key if present and input is empty
        const keyInput = document.getElementById("lic-user-key");
        if (keyInput && status.license_key && !keyInput.value) {
            keyInput.value = status.license_key;
        }

        if (status.activated && state.userLoggedIn) {
            // Success! Hide overlays, show workspace
            if (overlay) overlay.classList.add("hidden");
            if (workspace) workspace.classList.remove("hidden");
            
            // Show/hide admin console link
            if (state.role === "ADMIN" || state.role === "CO-ADMIN") {
                if (adminNavItem) adminNavItem.classList.remove("hidden");
                if (adminCurrentRole) adminCurrentRole.textContent = state.role;
                
                // Show/hide Co-Admin register option
                const coAdminOpt = document.getElementById("admin-role-coadmin-opt");
                if (coAdminOpt) {
                    if (state.role === "CO-ADMIN") {
                        coAdminOpt.disabled = true;
                        coAdminOpt.style.display = "none";
                    } else {
                        coAdminOpt.disabled = false;
                        coAdminOpt.style.display = "block";
                    }
                }
            } else {
                if (adminNavItem) adminNavItem.classList.add("hidden");
            }
            
            // Start local countdown for the sidebar and status tab
            startLocalLicenseCountdown(status.seconds_remaining, status.expiry_date);
            
            if (initial) {
                handleRouting();
            }
        } else {
            // Locked! Show appropriate state
            if (overlay) overlay.classList.remove("hidden");
            if (workspace) workspace.classList.add("hidden");
            
            if (status.error_type) {
                // Connection or server-side issue - stay on the login/register console and show a status message
                if (stateLoading) stateLoading.classList.add("hidden");
                if (stateError) stateError.classList.add("hidden");
                if (statePortal) statePortal.classList.remove("hidden");
                
                const statusBox = document.getElementById("login-console-status");
                const regStatusBox = document.getElementById("register-console-status");
                
                let errText = "";
                if (status.error_type === "internet") {
                    errText = "Internet Connection Issue: unable to contact the cloud licensing server.";
                } else {
                    errText = status.message || "Licensing server returned an error.";
                }
                
                // Show the error text in both status boxes
                if (statusBox) {
                    statusBox.textContent = errText;
                    statusBox.className = "alert alert-danger";
                    statusBox.classList.remove("hidden");
                }
                if (regStatusBox) {
                    regStatusBox.textContent = errText;
                    regStatusBox.className = "alert alert-danger";
                    regStatusBox.classList.remove("hidden");
                }
            } else {
                // Device signature not registered or pending, OR just not logged in yet
                if (stateLoading) stateLoading.classList.add("hidden");
                if (stateError) stateError.classList.add("hidden");
                if (statePortal) statePortal.classList.remove("hidden");
                
                const statusBox = document.getElementById("register-console-status");
                const reqBtn = document.getElementById("btn-request-register");
                
                if (status.pending_approval) {
                    if (statusBox) {
                        statusBox.textContent = "Waiting for Administrator's Authorization.";
                        statusBox.className = "alert alert-warning";
                        statusBox.classList.remove("hidden");
                    }
                    if (reqBtn) {
                        reqBtn.disabled = true;
                        reqBtn.textContent = "Pending Approval...";
                    }
                    if (initial) {
                        switchLandingTab("landing-register");
                    }
                } else if (!status.activated) {
                    if (statusBox) {
                        statusBox.textContent = status.message || "Device signature is not registered. Please contact your administrator.";
                        statusBox.className = "alert alert-danger";
                        statusBox.classList.remove("hidden");
                    }
                    if (reqBtn) {
                        reqBtn.disabled = false;
                        reqBtn.textContent = "Request Registration ";
                    }
                    if (initial) {
                        switchLandingTab("landing-login");
                    }
                } else {
                    // Activated but not logged in (userLoggedIn is false)
                    if (initial) {
                        switchLandingTab("landing-login");
                    }
                }
            }
            
            if (window.location.hash === "#admin-tab" || window.location.hash === "#bank-tab") {
                window.location.hash = "#license-tab";
            }
        }
    } catch (err) {
        console.error("Local client status fetch failed:", err);
        if (stateLoading) stateLoading.classList.add("hidden");
        if (statePortal) statePortal.classList.add("hidden");
        if (stateError) stateError.classList.remove("hidden");
        
        const errTitle = document.getElementById("lic-error-title");
        const errMessage = document.getElementById("lic-error-message");
        if (errTitle) errTitle.textContent = "Local Server Issue";
        if (errMessage) errMessage.textContent = "The client application failed to receive licensing status from local engine.";
    }
}

function startLocalLicenseCountdown(secondsRemaining, expiryDateString) {
    if (localLicenseCountdownInterval) clearInterval(localLicenseCountdownInterval);
    
    const expirySide = document.getElementById("license-expiry-side");
    const expiryTab = document.getElementById("lic-info-expiry");
    const daysTab = document.getElementById("lic-info-days");
    
    if (expiryTab) expiryTab.textContent = expiryDateString || "Lifetime";
    
    if (state.role === "ADMIN" || secondsRemaining === -1) {
        if (expirySide) expirySide.textContent = "Lifetime Active";
        if (daysTab) daysTab.textContent = "∞";
        return;
    }
    
    let currentRemaining = secondsRemaining;
    
    function tick() {
        if (currentRemaining <= 0) {
            if (expirySide) expirySide.textContent = "License Expired";
            if (daysTab) daysTab.textContent = "Expired";
            checkLicenseStatus(); // Locks app instantly
            clearInterval(localLicenseCountdownInterval);
            return;
        }
        
        const countdownStr = formatCountdown(currentRemaining);
        if (expirySide) expirySide.textContent = `Time left: ${countdownStr}`;
        if (daysTab) daysTab.textContent = countdownStr;
        
        currentRemaining--;
    }
    
    tick();
    localLicenseCountdownInterval = setInterval(tick, 1000);
}

async function retryLicenseConnection() {
    checkLicenseStatus(true);
}

function switchLandingTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll(".landing-tab-content").forEach(el => {
        el.classList.add("hidden");
    });
    // Show selected content
    const activeContent = document.getElementById(tabId);
    if (activeContent) activeContent.classList.remove("hidden");
    
    // Update tab buttons active classes & styling
    document.querySelectorAll(".portal-tab-btn").forEach(btn => {
        btn.classList.remove("active");
        btn.style.color = "var(--text-muted)";
        btn.style.background = "none";
    });
    
    let activeBtnId = "";
    if (tabId === "landing-login") activeBtnId = "btn-tab-login";
    else if (tabId === "landing-register") activeBtnId = "btn-tab-register";
    else if (tabId === "landing-admin") activeBtnId = "btn-tab-admin";
    
    const activeBtn = document.getElementById(activeBtnId);
    if (activeBtn) {
        activeBtn.classList.add("active");
        activeBtn.style.color = "#ffffff";
        activeBtn.style.background = "rgba(255, 255, 255, 0.08)";
    }
}

async function verifyDeviceLogin() {
    const statusBox = document.getElementById("login-console-status");
    const keyInput = document.getElementById("lic-user-key");
    const licenseKey = keyInput ? keyInput.value.trim() : "";
    
    if (!licenseKey) {
        if (statusBox) {
            statusBox.textContent = "Please enter your License Key / ID.";
            statusBox.className = "alert alert-danger";
            statusBox.classList.remove("hidden");
        }
        return;
    }
    
    if (statusBox) {
        statusBox.textContent = "Connecting to licensing backend...";
        statusBox.className = "alert alert-info";
        statusBox.classList.remove("hidden");
    }
    
    try {
        const res = await fetch("/api/activate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ license_key: licenseKey })
        });
        const data = await res.json();
        
        if (data.success && data.activated) {
            state.userLoggedIn = true;
            if (statusBox) {
                statusBox.textContent = data.message || "Login successful! Opening Workspace...";
                statusBox.className = "alert alert-success";
            }
            setTimeout(async () => {
                await checkLicenseStatus();
            }, 1000);
        } else {
            if (statusBox) {
                let msg = data.message || "Verification failed. Invalid license key or device mismatch.";
                statusBox.textContent = msg;
                statusBox.className = "alert alert-danger";
                
                if (msg.toLowerCase().includes("expired")) {
                    statusBox.innerHTML = `
                        ${msg}<br>
                        <button class="btn btn-primary" onclick="triggerClientRenewal('${licenseKey}')" style="margin-top: 10px; padding: 6px 12px; font-size: 0.8rem; line-height: 1;">Request License Renewal 🔄</button>
                    `;
                }
            }
        }
    } catch (err) {
        if (statusBox) {
            statusBox.textContent = "Connection failed. Please verify your internet settings.";
            statusBox.className = "alert alert-danger";
        }
    }
}

async function triggerClientRenewal(licenseKey) {
    const statusBox = document.getElementById("login-console-status");
    if (statusBox) {
        statusBox.textContent = "Submitting renewal request to server...";
        statusBox.className = "alert alert-info";
    }
    
    try {
        const res = await fetch("/api/request-renewal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ license_key: licenseKey })
        });
        const data = await res.json();
        if (data.success) {
            if (statusBox) {
                statusBox.textContent = data.message || "Renewal request successfully submitted! Waiting for approval.";
                statusBox.className = "alert alert-success";
            }
        } else {
            if (statusBox) {
                statusBox.textContent = data.message || "Failed to request renewal.";
                statusBox.className = "alert alert-danger";
            }
        }
    } catch (err) {
        if (statusBox) {
            statusBox.textContent = "Network error. Failed to submit renewal request.";
            statusBox.className = "alert alert-danger";
        }
    }
}

function updateLicenseTabDetails() {
    const signatureVal = document.getElementById("lic-info-signature");
    if (signatureVal) signatureVal.textContent = state.signature;
    
    fetch("/api/status")
        .then(res => res.json())
        .then(status => {
            const statusVal = document.getElementById("lic-info-status");
            if (statusVal) {
                statusVal.textContent = status.activated ? "ACTIVE (Registered)" : "UNLICENSED";
                statusVal.className = status.activated ? "info-value text-success" : "info-value text-danger";
            }
            
            const roleVal = document.getElementById("lic-info-role");
            if (roleVal) {
                roleVal.textContent = status.role || "USER";
            }
            
            const expiryVal = document.getElementById("lic-info-expiry");
            if (expiryVal) {
                expiryVal.textContent = status.expiry_date || "-";
            }
            

            startLocalLicenseCountdown(status.seconds_remaining, status.expiry_date);
        })
        .catch(err => console.error("Error updating license tab details:", err));
}

function copySignature() {
    const textToCopy = state.signature || document.getElementById("machine-sig-display").textContent;
    navigator.clipboard.writeText(textToCopy)
        .then(() => alert("Machine Signature ID copied to clipboard!"))
        .catch(err => console.error("Copy failed", err));
}

// -------------------------------------------------------------
// ADMIN CONSOLE ACTIONS (CLOUD)
// -------------------------------------------------------------
async function requestRegistration() {
    const statusBox = document.getElementById("register-console-status");
    const reqBtn = document.getElementById("btn-request-register");
    
    const nameInput = document.getElementById("reg-user-name");
    const emailInput = document.getElementById("reg-user-email");
    const phoneInput = document.getElementById("reg-user-phone");
    
    const fullName = nameInput ? nameInput.value.trim() : "";
    const email = emailInput ? emailInput.value.trim() : "";
    const phone = phoneInput ? phoneInput.value.trim() : "";
    
    if (!fullName || !email || !phone) {
        if (statusBox) {
            statusBox.textContent = "All fields are required.";
            statusBox.className = "alert alert-danger";
            statusBox.classList.remove("hidden");
        }
        return;
    }
    
    // Validate Name: purely alphabetic and spaces
    const nameRegex = /^[A-Za-z\s]+$/;
    if (!nameRegex.test(fullName)) {
        if (statusBox) {
            statusBox.textContent = "Full Name must contain only letters and spaces.";
            statusBox.className = "alert alert-danger";
            statusBox.classList.remove("hidden");
        }
        return;
    }
    
    // Validate Email: must contain '@' and '.'
    if (!email.includes("@") || !email.includes(".")) {
        if (statusBox) {
            statusBox.textContent = "Email must be a valid address containing '@' and '.'";
            statusBox.className = "alert alert-danger";
            statusBox.classList.remove("hidden");
        }
        return;
    }
    
    // Validate Phone: exactly 10 digits
    const cleanPhone = phone.replace(/\D/g, "");
    if (cleanPhone.length !== 10) {
        if (statusBox) {
            statusBox.textContent = "Phone Number must be exactly 10 digits.";
            statusBox.className = "alert alert-danger";
            statusBox.classList.remove("hidden");
        }
        return;
    }
    
    if (statusBox) {
        statusBox.textContent = "Sending registration request to cloud backend...";
        statusBox.className = "alert alert-info";
        statusBox.classList.remove("hidden");
    }
    if (reqBtn) reqBtn.disabled = true;
    
    try {
        const res = await fetch("/api/register_request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ full_name: fullName, email: email, phone_number: phone })
        });
        const data = await res.json();
        
        if (data.success) {
            if (statusBox) {
                statusBox.textContent = data.message || "Waiting for Administrator's Authorization.";
                statusBox.className = "alert alert-warning";
            }
            if (reqBtn) {
                reqBtn.textContent = "Pending Approval...";
            }
            // Clear inputs
            if (nameInput) nameInput.value = "";
            if (emailInput) emailInput.value = "";
            if (phoneInput) phoneInput.value = "";
        } else {
            if (statusBox) {
                statusBox.textContent = data.message || "Failed to request registration.";
                statusBox.className = "alert alert-danger";
            }
            if (reqBtn) reqBtn.disabled = false;
        }
    } catch (err) {
        if (statusBox) {
            statusBox.textContent = "Connection failed. Verify internet settings.";
            statusBox.className = "alert alert-danger";
        }
        if (reqBtn) reqBtn.disabled = false;
    }
}


// ==========================================
// BANK CONVERSION OPERATIONS
// ==========================================
async function runBankConversion() {
    if (!state.files.bank) {
        updateStatusBox("bank", "Error: Please upload a bank statement PDF first.", "danger");
        return;
    }
    
    const bankType = document.getElementById("bank-type-select").value;
    
    // Route to Hybrid Generic wizard mapping chain
    if (bankType === "Hybrid Generic") {
        const btn = document.getElementById("btn-convert-bank");
        const btnText = document.getElementById("bank-btn-text");
        const spinner = document.getElementById("bank-spinner");
        
        btn.disabled = true;
        spinner.classList.remove("hidden");
        btnText.textContent = "Analyzing PDF Layout...";
        
        await runHybridValidationAndExtract();
        return;
    }
    
    const btn = document.getElementById("btn-convert-bank");
    const btnText = document.getElementById("bank-btn-text");
    const spinner = document.getElementById("bank-spinner");
    
    // Toggle loading UI
    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Processing Conversion Chain...";
    
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
    
    updateStatusBox("bank", "Step 1: Running verification & row extraction...", "info");
    
    try {
        const res = await fetch("/api/convert_bank", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            renderBankResults(data);
            if (data.report.statement.is_reconciled) {
                updateStatusBox("bank", "PDF Ingestion & Verification Chain Complete!", "success");
            } else {
                updateStatusBox("bank", `Warning: ${data.report.statement.audit_message || "Audit pipeline validation checks failed."}`, "danger");
            }
        } else {
            updateStatusBox("bank", `Error: ${data.message}`, "danger");
        }
    } catch (err) {
        updateStatusBox("bank", `System Failure: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute Conversion Chain";
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
                updateStatusBox("bank", `Warning: ${data.report.statement.audit_message || "Audit pipeline validation checks failed."}`, "danger");
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
    badge.textContent = stmt.is_reconciled ? "RECONCILED" : "AUDIT ERROR";
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
                <td>${row.is_reconciled ? 'PASSED' : 'ERROR'}</td>
            `;
            tbody.appendChild(tr);
        });
    }
    
    // Store response globally for dynamic monthly analysis computations
    state.lastResponseData = data;
    
    // Build Tally Prime Voucher Preview rows
    const tallyTbody = document.querySelector("#bank-tally-preview-table tbody");
    if (tallyTbody) {
        tallyTbody.innerHTML = "";
        const txns = data.transactions || [];
        
        if (txns.length === 0) {
            tallyTbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No vouchers available for preview.</td></tr>`;
        } else {
            txns.forEach((txn, idx) => {
                const tr = document.createElement("tr");
                const vchType = txn.type === "DEBIT" ? "Receipt" : "Payment";
                const particulars = data.credit_ledger || "Suspense";
                
                const debitVal = txn.type === "DEBIT" ? formatCurrency(txn.amount) : "-";
                const creditVal = txn.type === "CREDIT" ? formatCurrency(txn.amount) : "-";
                
                tr.innerHTML = `
                    <td>${txn.gl_date}</td>
                    <td>${particulars}</td>
                    <td><span class="badge ${txn.type === 'DEBIT' ? 'success' : 'danger'}">${vchType}</span></td>
                    <td>${idx + 1}</td>
                    <td class="${txn.type === 'DEBIT' ? 'text-success' : ''}">${debitVal}</td>
                    <td class="${txn.type === 'CREDIT' ? 'text-danger' : ''}">${creditVal}</td>
                `;
                tallyTbody.appendChild(tr);
            });
        }
    }
    
    // Default to the vouchers tab view
    switchTallyPreviewTab('vouchers');
    
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
        updateStatusBox("cash", "Error: Please upload a receipts ledger sheet first.", "danger");
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
    
    updateStatusBox("cash", "Ingesting workbook sheets...", "info");
    
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
            updateStatusBox("cash", "Ingestion complete! Review spelling flags below.", "success");
        } else {
            updateStatusBox("cash", `Error: ${data.message}`, "danger");
        }
    } catch (err) {
        updateStatusBox("cash", `System error: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute Receipts Ingestion";
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
                <td>VERIFIED</td>
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
        btn.innerHTML = "Cleaning...";
        
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
        reprocessBtn.textContent = "Apply Custom Ledger Names & Re-Generate";
        reprocessBtn.onclick = reprocessCallback;
        container.appendChild(reprocessBtn);
    }
}

function toggleDateFilter(type) {
    const strat = document.getElementById("strategy-select").value;
    const filter = document.getElementById("bank-date-filter-group");
    
    if (strat === "Incomplete statement (Continuation)") {
        if (filter) filter.classList.remove("hidden");
    } else {
        if (filter) filter.classList.add("hidden");
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


// =============================================================
// HYBRID GENERIC PARSER WIZARD SYSTEM
// =============================================================
const hybridWizardState = {
    tempFileId: "",
    headers: [],
    previewRows: [],
    autoMapping: {},
    currentMapping: {},
    currentStep: 1,
    inferredOpeningBalance: 0.0,
    layouts: []
};

async function loadSavedLayouts() {
    try {
        const res = await fetch("/api/hybrid/layouts");
        const data = await res.json();
        if (data.success) {
            hybridWizardState.layouts = data.layouts;
            const select = document.getElementById("hybrid-layout-select");
            if (select) {
                select.innerHTML = '<option value="">-- No Layout (Auto-Detect) --</option>';
                data.layouts.forEach(layout => {
                    const opt = document.createElement("option");
                    opt.value = layout.layout_name;
                    opt.textContent = `${layout.layout_name} (${layout.col_count} columns)`;
                    select.appendChild(opt);
                });
            }
        }
    } catch (err) {
        console.error("Failed to load layout templates:", err);
    }
}

function handleBankTypeChange() {
    const bankType = document.getElementById("bank-type-select").value;
    const hybridGroup = document.getElementById("hybrid-layout-group");
    const debitLedgerInput = document.getElementById("bank-debit-ledger");
    
    if (bankType === "Hybrid Generic") {
        if (hybridGroup) hybridGroup.classList.remove("hidden");
        if (debitLedgerInput && (debitLedgerInput.value === "STATE BANK OF INDIA" || debitLedgerInput.value === "BANK OF BARODA" || debitLedgerInput.value === "AXIS BANK")) {
            debitLedgerInput.value = "Generic Bank";
        }
    } else {
        if (hybridGroup) hybridGroup.classList.add("hidden");
        if (debitLedgerInput) {
            if (bankType.includes("SBI")) {
                debitLedgerInput.value = "STATE BANK OF INDIA";
            } else if (bankType.includes("BOB")) {
                debitLedgerInput.value = "BANK OF BARODA";
            } else if (bankType.includes("Axis")) {
                debitLedgerInput.value = "AXIS BANK";
            }
        }
    }
    triggerOpeningBalanceDetection();
}

function applySavedLayout() {
    const selectedName = document.getElementById("hybrid-layout-select").value;
    if (!selectedName) {
        hybridWizardState.currentMapping = {};
        return;
    }
    const layout = hybridWizardState.layouts.find(l => l.layout_name === selectedName);
    if (layout) {
        hybridWizardState.currentMapping = { ...layout.mapping };
    }
}

async function runHybridValidationAndExtract() {
    const btn = document.getElementById("btn-convert-bank");
    const btnText = document.getElementById("bank-btn-text");
    const spinner = document.getElementById("bank-spinner");
    
    const formData = new FormData();
    formData.append("file", state.files.bank);
    
    updateStatusBox("bank", "Validating PDF structure & extracting grid...", "info");
    
    try {
        const res = await fetch("/api/hybrid/validate-and-extract", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            updateStatusBox("bank", "PDF structure validated. Opening mapping wizard...", "success");
            
            // Populate wizard state
            hybridWizardState.tempFileId = data.temp_file_id;
            hybridWizardState.headers = data.headers;
            hybridWizardState.previewRows = data.preview_rows;
            hybridWizardState.autoMapping = data.auto_mapping;
            hybridWizardState.inferredOpeningBalance = data.inferred_opening_balance;
            
            // If user has a selected template, use that mapping, else use inferred
            if (Object.keys(hybridWizardState.currentMapping).length === 0) {
                hybridWizardState.currentMapping = { ...data.auto_mapping };
            }
            
            showHybridWizard();
        } else {
            updateStatusBox("bank", `Validation Error: ${data.message}`, "danger");
        }
    } catch (err) {
        updateStatusBox("bank", `System Failure: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Convert PDF to Tally XML";
    }
}

function showHybridWizard() {
    const modal = document.getElementById("hybrid-wizard-modal");
    if (modal) modal.classList.remove("hidden");
    
    // Reset wizard view to step 1
    navigateWizardDirect(1);
}

function closeHybridWizard() {
    const modal = document.getElementById("hybrid-wizard-modal");
    if (modal) modal.classList.add("hidden");
}

function toggleWizardLayoutName() {
    const chk = document.getElementById("wizard-save-layout-chk");
    const group = document.getElementById("wizard-layout-name-group");
    if (chk && group) {
        if (chk.checked) {
            group.classList.remove("hidden");
        } else {
            group.classList.add("hidden");
        }
    }
}

function navigateWizard(offset) {
    const nextStep = hybridWizardState.currentStep + offset;
    navigateWizardDirect(nextStep);
}

function navigateWizardDirect(step) {
    if (step === 3) {
        // Collect mapping and validate Date & Narration are mapped before proceeding
        const colCount = hybridWizardState.headers.length;
        const tempMap = { date: -1, narration: -1, debit: -1, credit: -1, balance: -1 };
        
        for (let i = 0; i < colCount; i++) {
            const selectEl = document.getElementById(`mapping-col-${i}`);
            if (selectEl) {
                const val = selectEl.value;
                if (val !== "ignore") {
                    tempMap[val] = i;
                }
            }
        }
        
        if (tempMap.date === -1 || tempMap.narration === -1) {
            alert("Please map at least Date and Narration columns before proceeding.");
            return;
        }
        
        hybridWizardState.currentMapping = tempMap;
    }
    
    // Hide all step sections
    document.getElementById("wizard-step-1").classList.add("hidden");
    document.getElementById("wizard-step-2").classList.add("hidden");
    document.getElementById("wizard-step-3").classList.add("hidden");
    
    // Show correct section
    document.getElementById(`wizard-step-${step}`).classList.remove("hidden");
    
    // Update step indicator classes
    document.getElementById("badge-step-1").className = `step-badge ${step === 1 ? 'active' : (step > 1 ? 'completed' : '')}`;
    document.getElementById("badge-step-2").className = `step-badge ${step === 2 ? 'active' : (step > 2 ? 'completed' : '')}`;
    document.getElementById("badge-step-3").className = `step-badge ${step === 3 ? 'active' : ''}`;
    
    // Update footer buttons visibility
    if (step === 1) {
        document.getElementById("btn-wizard-back").classList.add("hidden");
        document.getElementById("btn-wizard-cancel").classList.remove("hidden");
        document.getElementById("btn-wizard-next").classList.remove("hidden");
        document.getElementById("btn-wizard-submit").classList.add("hidden");
        document.getElementById("btn-wizard-next").textContent = "Proceed to Mapping ➔";
        
        buildWizardStep1Preview();
    } else if (step === 2) {
        document.getElementById("btn-wizard-back").classList.remove("hidden");
        document.getElementById("btn-wizard-cancel").classList.add("hidden");
        document.getElementById("btn-wizard-next").classList.remove("hidden");
        document.getElementById("btn-wizard-submit").classList.add("hidden");
        document.getElementById("btn-wizard-next").textContent = "Review & Save Layout ➔";
        
        buildWizardStep2Mapping();
    } else if (step === 3) {
        document.getElementById("btn-wizard-back").classList.remove("hidden");
        document.getElementById("btn-wizard-cancel").classList.add("hidden");
        document.getElementById("btn-wizard-next").classList.add("hidden");
        document.getElementById("btn-wizard-submit").classList.remove("hidden");
        
        // Populate opening balance field
        document.getElementById("wizard-opening-balance").value = hybridWizardState.inferredOpeningBalance.toFixed(2);
        
        // Build summary list
        const summaryUl = document.getElementById("wizard-summary-list");
        summaryUl.innerHTML = "";
        
        const map = hybridWizardState.currentMapping;
        const labels = { date: "Date", narration: "Narration", debit: "Debit (Withdrawal)", credit: "Credit (Deposit)", balance: "Balance" };
        
        Object.keys(labels).forEach(key => {
            const colIdx = map[key];
            const li = document.createElement("li");
            if (colIdx !== undefined && colIdx !== -1) {
                li.innerHTML = `<strong>${labels[key]}:</strong> mapped to Column ${colIdx + 1} (<em>"${hybridWizardState.headers[colIdx]}"</em>)`;
            } else {
                li.innerHTML = `<strong>${labels[key]}:</strong> <span style="color:#ef4444;">Not Mapped (Optional)</span>`;
            }
            summaryUl.appendChild(li);
        });
    }
    
    hybridWizardState.currentStep = step;
}

function buildWizardStep1Preview() {
    const table = document.getElementById("wizard-preview-table");
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");
    
    thead.innerHTML = "";
    tbody.innerHTML = "";
    
    // Headers
    const trHead = document.createElement("tr");
    hybridWizardState.headers.forEach((h, i) => {
        const th = document.createElement("th");
        th.textContent = h || `Column ${i + 1}`;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    
    // Rows
    hybridWizardState.previewRows.forEach(row => {
        const tr = document.createElement("tr");
        row.forEach(cell => {
            const td = document.createElement("td");
            td.textContent = cell;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    
    // Show/hide low confidence warning
    const warning = document.getElementById("wizard-step-1-warning");
    if (warning) {
        if (hybridWizardState.autoMapping.date === -1 || hybridWizardState.autoMapping.narration === -1) {
            warning.classList.remove("hidden");
        } else {
            warning.classList.add("hidden");
        }
    }
}

function buildWizardStep2Mapping() {
    const container = document.getElementById("wizard-mapping-form-container");
    container.innerHTML = "";
    
    hybridWizardState.headers.forEach((header, index) => {
        const div = document.createElement("div");
        div.className = "mapping-row";
        
        const label = document.createElement("div");
        label.className = "mapping-label";
        label.innerHTML = `Column ${index + 1}: <strong>"${header || '(Empty Header)'}"</strong>`;
        
        const select = document.createElement("select");
        select.className = "mapping-select";
        select.id = `mapping-col-${index}`;
        
        const options = [
            { val: "ignore", label: "Ignore / Skip Column" },
            { val: "date", label: "Date" },
            { val: "narration", label: "Narration / Description" },
            { val: "debit", label: "Debit (Withdrawals)" },
            { val: "credit", label: "Credit (Deposits)" },
            { val: "balance", label: "Running Balance" }
        ];
        
        options.forEach(opt => {
            const option = document.createElement("option");
            option.value = opt.val;
            option.textContent = opt.label;
            
            // Auto pre-select matching values from wizard state currentMapping
            const map = hybridWizardState.currentMapping;
            if (map[opt.val] === index) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        div.appendChild(label);
        div.appendChild(select);
        container.appendChild(div);
    });
}

async function submitHybridParse() {
    const btn = document.getElementById("btn-wizard-submit");
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Processing PDF...";
    
    const bankLedger = document.getElementById("bank-debit-ledger").value.trim();
    const suspenseLedger = document.getElementById("bank-credit-ledger").value.trim();
    const strategy = document.getElementById("strategy-select").value;
    const cutoffDate = document.getElementById("bank-cutoff-date").value;
    
    const openingBalanceVal = parseFloat(document.getElementById("wizard-opening-balance").value) || 0.0;
    const saveLayout = document.getElementById("wizard-save-layout-chk").checked;
    const layoutName = document.getElementById("wizard-layout-name-input").value.trim();
    
    if (saveLayout && !layoutName) {
        alert("Please enter a name for the layout template.");
        btn.disabled = false;
        btn.textContent = originalText;
        return;
    }
    
    const payload = {
        temp_file_id: hybridWizardState.tempFileId,
        mapping: hybridWizardState.currentMapping,
        bank_ledger: bankLedger,
        suspense_ledger: suspenseLedger,
        opening_balance: openingBalanceVal,
        save_layout: saveLayout,
        layout_name: layoutName,
        strategy_type: strategy,
        cutoff_date: cutoffDate
    };
    
    updateStatusBox("bank", "Running full statement parsing & XML generation...", "info");
    
    try {
        const res = await fetch("/api/hybrid/parse", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            closeHybridWizard();
            renderBankResults(data);
            updateStatusBox("bank", "PDF Ingestion & Verification Chain Complete!", "success");
            loadSavedLayouts(); // reload layouts dropdown
        } else {
            alert(`Error: ${data.message}`);
            updateStatusBox("bank", `Parsing Error: ${data.message}`, "danger");
        }
    } catch (err) {
        alert(`System error: ${err.message}`);
        updateStatusBox("bank", `System Failure: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function triggerOpeningBalanceDetection() {
    if (!state.files.bank) return;
    
    const bankType = document.getElementById("bank-type-select").value;
    const balanceInput = document.getElementById("bank-prev-balance");
    if (!balanceInput) return;
    
    balanceInput.value = "Detecting...";
    balanceInput.disabled = true;
    
    const formData = new FormData();
    formData.append("file", state.files.bank);
    formData.append("bank_type", bankType);
    
    try {
        const res = await fetch("/api/detect-opening-balance", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            balanceInput.value = parseFloat(data.opening_balance).toFixed(2);
        } else {
            balanceInput.value = "0.00";
        }
    } catch (err) {
        console.error("Failed to detect opening balance:", err);
        balanceInput.value = "0.00";
    } finally {
        balanceInput.disabled = false;
    }
}

function switchTallyPreviewTab(tabType) {
    const btnVouchers = document.getElementById("btn-tally-view-vouchers");
    const btnMonthly = document.getElementById("btn-tally-view-monthly");
    const containerVouchers = document.getElementById("tally-tab-vouchers-container");
    const containerMonthly = document.getElementById("tally-tab-monthly-container");
    
    if (tabType === 'vouchers') {
        if (btnVouchers) btnVouchers.classList.add("active");
        if (btnMonthly) btnMonthly.classList.remove("active");
        if (containerVouchers) containerVouchers.classList.remove("hidden");
        if (containerMonthly) containerMonthly.classList.add("hidden");
    } else {
        if (btnVouchers) btnVouchers.classList.remove("active");
        if (btnMonthly) btnMonthly.classList.add("active");
        if (containerVouchers) containerVouchers.classList.add("hidden");
        if (containerMonthly) containerMonthly.classList.remove("hidden");
        
        buildDynamicMonthlySummary();
    }
}

function buildDynamicMonthlySummary() {
    const data = state.lastResponseData;
    const tbody = document.querySelector("#bank-dynamic-monthly-table tbody");
    if (!tbody || !data) return;
    
    tbody.innerHTML = "";
    
    const txns = data.transactions || [];
    const openingBal = parseFloat(data.report.statement.opening_balance) || 0.0;
    
    const monthGroups = {};
    const monthOrder = [];
    
    txns.forEach(txn => {
        const parts = txn.gl_date.split("-");
        if (parts.length === 3) {
            const day = parseInt(parts[0]);
            const monthNum = parts[1];
            const year = parts[2];
            
            const monthKey = `${year}-${monthNum}`;
            const dateObj = new Date(year, parseInt(monthNum) - 1, 1);
            const monthLabel = dateObj.toLocaleString('en-US', { month: 'short', year: 'numeric' });
            
            if (!monthGroups[monthKey]) {
                monthGroups[monthKey] = {
                    key: monthKey,
                    label: monthLabel,
                    debit: 0.0,
                    credit: 0.0,
                    txns: []
                };
                monthOrder.push(monthKey);
            }
            
            monthGroups[monthKey].txns.push({
                day: day,
                amount: txn.amount,
                type: txn.type
            });
        }
    });
    
    monthOrder.sort();
    
    let runningBalance = openingBal;
    
    if (monthOrder.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No monthly data computed.</td></tr>`;
        return;
    }
    
    monthOrder.forEach(key => {
        const group = monthGroups[key];
        group.txns.sort((a, b) => a.day - b.day);
        
        group.txns.forEach(t => {
            if (t.type === "DEBIT") {
                group.debit += t.amount;
                runningBalance += t.amount;
            } else if (t.type === "CREDIT") {
                group.credit += t.amount;
                runningBalance -= t.amount;
            }
        });
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${group.label}</strong></td>
            <td class="text-success">${formatCurrency(group.debit)}</td>
            <td class="text-danger">${formatCurrency(group.credit)}</td>
            <td><strong>${formatCurrency(runningBalance)}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}
