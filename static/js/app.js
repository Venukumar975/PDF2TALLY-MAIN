// static/js/app.js

// Global application state
const state = {
    activated: false,
    userLoggedIn: sessionStorage.getItem("userLoggedIn") === "true",
    signature: "",
    role: "USER",
    activeTab: "bank-tab",
    files: {
        bank: null,
        cash: null,
        gstr1: null,
        hsn: null
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
    setupDragAndDrop("gstr1");
    setupDragAndDrop("hsn");
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

    // Check for application updates at startup
    checkApplicationUpdate();
});

function handleRouting() {
    const hash = window.location.hash || "#bank-tab";
    const tabId = hash.substring(1);
    switchTab(tabId);
}

function switchTab(tabId) {
    if ((!state.activated || !state.userLoggedIn) && tabId !== "activate-tab") {
        window.location.hash = "#activate-tab";
        return;
    }
    
    if (state.activated && state.userLoggedIn && tabId === "activate-tab") {
        window.location.hash = "#bank-tab";
        return;
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
    
    // Toggle minimized sidebar for Review Desk tab
    const workspaceEl = document.getElementById("app-workspace");
    if (workspaceEl) {
        if (tabId === "review-tab") {
            workspaceEl.classList.add("sidebar-minimized", "review-mode-active");
        } else {
            workspaceEl.classList.remove("sidebar-minimized", "review-mode-active");
        }
    }
    
    // Specific tab loads
    if (tabId === "lexicon-tab") {
        loadLexiconManager();
    } else if (tabId === "license-tab") {
        updateLicenseTabDetails();
    } else if (tabId === "support-tab") {
        updateSupportTabDetails();
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
            if (window.location.hash === "#activate-tab") {
                window.location.hash = "#bank-tab";
            }
        } else {
            state.userLoggedIn = false;
            sessionStorage.removeItem("userLoggedIn");
            // Locked! Show appropriate state
            if (overlay) overlay.classList.remove("hidden");
            if (workspace) workspace.classList.add("hidden");
            
            if (status.error_type) {
                if (stateLoading) stateLoading.classList.add("hidden");
                if (stateError) stateError.classList.add("hidden");
                if (statePortal) statePortal.classList.remove("hidden");
                
                const statusBox = document.getElementById("login-console-status");
                const regStatusBox = document.getElementById("register-console-status");
                const keyInput = document.getElementById("lic-user-key");
                const verifyBtn = document.getElementById("lic-verify-btn");

                // Auto-restore license if missing, modified/corrupted, or if system clock rollback is detected
                if (status.error_type === "missing" || status.error_type === "modified" || status.error_type === "tampered") {
                    if (keyInput) {
                        keyInput.disabled = true;
                        keyInput.readOnly = true;
                        keyInput.value = "";
                    }
                    if (verifyBtn) {
                        verifyBtn.disabled = true;
                        verifyBtn.textContent = "Checking Server...";
                    }
                    if (statusBox) {
                        let warnMsg = "Local license cache is missing or modified. Contacting licensing server to restore your active license...";
                        if (status.error_type === "tampered") {
                            warnMsg = "System clock manipulation detected! Contacting licensing server to verify and restore your license time...";
                        }
                        statusBox.textContent = warnMsg;
                        statusBox.className = "alert alert-warning";
                        statusBox.classList.remove("hidden");
                    }

                    fetch("/api/restore-device", { method: "POST" })
                        .then(res => res.json())
                        .then(resData => {
                            if (resData.success && resData.activated) {
                                if (keyInput) {
                                    keyInput.value = resData.license_key;
                                    keyInput.disabled = false;
                                    keyInput.readOnly = false;
                                }
                                if (verifyBtn) {
                                    verifyBtn.disabled = false;
                                    verifyBtn.textContent = "Verify & Log In";
                                }
                                if (statusBox) {
                                    statusBox.textContent = "License registry verified successfully! Re-saving local cache and logging in...";
                                    statusBox.className = "alert alert-success";
                                }
                                state.userLoggedIn = true;
                                sessionStorage.setItem("userLoggedIn", "true");
                                setTimeout(() => {
                                    checkLicenseStatus();
                                }, 1500);
                            } else {
                                // No active key registered to this device
                                if (keyInput) {
                                    keyInput.disabled = false;
                                    keyInput.readOnly = false;
                                    keyInput.value = "";
                                }
                                if (verifyBtn) {
                                    verifyBtn.disabled = false;
                                    verifyBtn.textContent = "Verify & Log In";
                                }
                                if (statusBox) {
                                    let errMsg = resData.message || "No active license is registered to this computer. Please enter your license key to activate.";
                                    if (status.error_type === "tampered") {
                                        errMsg = resData.message || "Clock verification failed: no active registered license matches this device. Enter your key to activate.";
                                    }
                                    statusBox.textContent = errMsg;
                                    statusBox.className = "alert alert-danger";
                                }
                            }
                        })
                        .catch(err => {
                            console.error("Restore error:", err);
                            if (keyInput) {
                                keyInput.disabled = false;
                                keyInput.readOnly = false;
                            }
                            if (verifyBtn) {
                                verifyBtn.disabled = false;
                                verifyBtn.textContent = "Verify & Log In";
                            }
                            if (statusBox) {
                                statusBox.textContent = "Could not connect to licensing server. Please check your internet connection.";
                                statusBox.className = "alert alert-danger";
                            }
                        });
                    return;
                }

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
                    const loginStatusBox = document.getElementById("login-console-status");
                    if (status.message && status.message.toLowerCase().includes("expired")) {
                        if (loginStatusBox) {
                            const licenseKey = status.license_key || "";
                            loginStatusBox.innerHTML = `
                                ${status.message}<br>
                                <button class="btn btn-primary" onclick="triggerClientRenewal('${licenseKey}')" style="margin-top: 10px; padding: 6px 12px; font-size: 0.8rem; line-height: 1;">Request License Renewal 🔄</button>
                            `;
                            loginStatusBox.className = "alert alert-danger";
                            loginStatusBox.classList.remove("hidden");
                        }
                    }
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
            
            if (window.location.hash !== "#activate-tab") {
                window.location.hash = "#activate-tab";
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
    const verifyBtn = document.getElementById("lic-verify-btn");
    const licenseKey = keyInput ? keyInput.value.trim() : "";
    
    if (!licenseKey) {
        if (statusBox) {
            statusBox.textContent = "Please enter your License Key / ID.";
            statusBox.className = "alert alert-danger";
            statusBox.classList.remove("hidden");
        }
        return;
    }
    
    if (keyInput) keyInput.disabled = true;
    if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.textContent = "Verifying...";
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
            sessionStorage.setItem("userLoggedIn", "true");
            if (statusBox) {
                statusBox.textContent = data.message || "Login successful! Opening Workspace...";
                statusBox.className = "alert alert-success";
            }
            if (verifyBtn) verifyBtn.textContent = "Success!";
            setTimeout(async () => {
                await checkLicenseStatus();
            }, 1000);
        } else {
            if (keyInput) keyInput.disabled = false;
            if (verifyBtn) {
                verifyBtn.disabled = false;
                verifyBtn.textContent = "Verify & Log In";
            }
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
        if (keyInput) keyInput.disabled = false;
        if (verifyBtn) {
            verifyBtn.disabled = false;
            verifyBtn.textContent = "Verify & Log In";
        }
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

async function updateLicenseTabDetails() {
    const signatureVal = document.getElementById("lic-info-signature");
    if (signatureVal) signatureVal.textContent = state.signature;
    
    try {
        const res = await fetch("/api/status");
        const status = await res.json();
        
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
    } catch (err) {
        console.error("Error updating license tab details:", err);
    }
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

// ==========================================
// VOUCHER REVIEW DESK MODULE (OFFLINE-FIRST)
// ==========================================

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
    ledgerCache: {},
    openingBalance: 0.00,
    particularsIsFlex: true,
    colWidths: {
        date: 90,
        particulars: 180,
        narration: 250,
        vchType: 100,
        vchNo: 100,
        debit: 120,
        credit: 120
    }
};

// Initialize Drag & Drop and Persistent JSON Cache
document.addEventListener("DOMContentLoaded", () => {
    // Load mappings cache from backend JSON file
    loadReviewCacheFromServer();
    
    // Set up drag & drop hooks
    setupReviewDragAndDrop();
    
    // Bind Keyboard event listener for virtual viewport
    const viewport = document.getElementById("review-virtual-viewport");
    if (viewport) {
        viewport.addEventListener("keydown", onReviewTableKeydown);
    }
    
    // Global keyboard listener for shortcuts (Tally Action Keys panel)
    window.addEventListener("keydown", handleGlobalReviewShortcuts);
    
    // Autocomplete list close on click outside
    document.addEventListener("click", (e) => {
        const modalList = document.getElementById("review-modal-ledger-autocomplete-list");
        const replaceInput = document.getElementById("review-modal-new-ledger");
        if (modalList && e.target !== replaceInput && !modalList.contains(e.target)) {
            modalList.classList.add("hidden");
        }
    });
});

async function loadReviewCacheFromServer() {
    try {
        const res = await fetch("/api/review/cache");
        const data = await res.json();
        if (data.success) {
            reviewState.ledgerCache = data.cache || {};
        }
    } catch (e) {
        console.error("Failed to load persistent ledger cache from server:", e);
    }
}

function handleGlobalReviewShortcuts(e) {
    // Only intercept shortcuts when Review Desk tab is active
    if (state.activeTab !== "review-tab" || !reviewState.xmlDoc) return;
    
    // Ignore if user is actively writing inside an input or select
    if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "SELECT") {
        // Esc key closes autocomplete or modal if active
        if (e.key === "Escape") {
            const openModal = document.querySelector(".tally-modal-overlay:not(.hidden)");
            if (openModal) {
                openModal.classList.add("hidden");
                // Restore focus to virtual viewport
                const viewport = document.getElementById("review-virtual-viewport");
                if (viewport) viewport.focus();
                e.preventDefault();
            }
        }
        return;
    }
    
    let handled = false;
    
    // Check key patterns
    if (e.key === "F2") {
        openPeriodModal();
        handled = true;
    } else if (e.key === "F4") {
        openLedgerFilterModal();
        handled = true;
    } else if (e.key === "5") {
        toggleReviewNarrationFromBtn();
        handled = true;
    } else if (e.key === "6") {
        openNarrationFilterModal();
        handled = true;
    } else if (e.key === "y" || e.key === "Y") {
        openReplaceLedgerModal();
        handled = true;
    } else if (e.key === "m" || e.key === "M") {
        openMonthlyAnalysisModal();
        handled = true;
    } else if (e.key === "Escape") {
        const openModal = document.querySelector(".tally-modal-overlay:not(.hidden)");
        if (openModal) {
            openModal.classList.add("hidden");
            const viewport = document.getElementById("review-virtual-viewport");
            if (viewport) viewport.focus();
        } else {
            reviewState.selectedIds.clear();
            updateReviewStats();
            onReviewTableScroll();
        }
        handled = true;
    } else if (e.ctrlKey && (e.key === "e" || e.key === "E")) {
        exportReviewXML();
        handled = true;
    }
    
    if (handled) {
        e.preventDefault();
    }
}

function setupReviewDragAndDrop() {
    const zone = document.getElementById("review-import-zone");
    if (!zone) return;
    
    ["dragenter", "dragover"].forEach(evtName => {
        zone.addEventListener(evtName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.style.background = "#e6f2ff";
            zone.style.borderColor = "#005ea5";
        }, false);
    });
    
    ["dragleave", "drop"].forEach(evtName => {
        zone.addEventListener(evtName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.style.background = "#f8fafc";
            zone.style.borderColor = "#002d5a";
        }, false);
    });
    
    zone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0 && files[0].name.toLowerCase().endsWith(".xml")) {
            loadReviewXML(files[0]);
        } else {
            alert("Please drop a valid Tally XML file.");
        }
    }, false);
}

function handleReviewXMLSelect(event) {
    const file = event.target.files[0];
    if (file) {
        loadReviewXML(file);
    }
}

function loadReviewXML(file) {
    reviewState.originalFileName = file.name;
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const text = e.target.result;
        const parser = new DOMParser();
        let xmlDoc;
        try {
            xmlDoc = parser.parseFromString(text, "text/xml");
            
            // Check parsing errors
            const parserError = xmlDoc.querySelector("parsererror");
            if (parserError) {
                alert("Error parsing XML: " + parserError.textContent);
                return;
            }
        } catch (err) {
            alert("Error reading XML file: " + err.message);
            return;
        }
        
        reviewState.xmlDoc = xmlDoc;
        
        let openingBalance = 0.00;
        const ledgerNodes = xmlDoc.getElementsByTagName("LEDGER");
        for (let i = 0; i < ledgerNodes.length; i++) {
            const node = ledgerNodes[i];
            const name = node.getAttribute("NAME") || "";
            const isBank = /bank|sbi|bob|axis|cash|hdfc|icici|tmb|idbi|pnb/i.test(name);
            if (isBank) {
                const opNode = node.querySelector("OPENINGBALANCE");
                if (opNode) {
                    const val = parseFloat(opNode.textContent || "0");
                    openingBalance = -val;
                }
            }
        }
        reviewState.openingBalance = openingBalance;
        reviewState.showNarration = false;
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
        
        const voucherNodes = xmlDoc.getElementsByTagName("VOUCHER");
        reviewState.vouchers = [];
        reviewState.selectedIds.clear();
        reviewState.focusedIndex = -1;
        reviewState.lastSelectedIndex = -1;
        
        let bankName = "Unknown Bank";
        const uniqueLedgers = new Set();
        
        for (let i = 0; i < voucherNodes.length; i++) {
            const node = voucherNodes[i];
            const dateVal = (node.querySelector("DATE")?.textContent || "").trim();
            const vchType = (node.querySelector("VOUCHERTYPENAME")?.textContent || "").trim();
            const vchNo = (node.querySelector("VOUCHERNUMBER")?.textContent || "").trim();
            const narration = (node.querySelector("NARRATION")?.textContent || "").trim();
            
            // Query ledger list entries
            const entries = node.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST");
            let particulars = "Suspense";
            let amount = 0.0;
            let type = "DEBIT";
            
            let bankDeemedPos = "Yes";
            entries.forEach(ent => {
                const ledger = (ent.querySelector("LEDGERNAME")?.textContent || "").trim();
                uniqueLedgers.add(ledger);
                
                const rawAmt = parseFloat(ent.querySelector("AMOUNT")?.textContent || "0");
                
                // Particulars is the non-bank ledger.
                const isPartyNode = ent.querySelector("ISPARTYLEDGER");
                const isPartyLedger = isPartyNode ? (isPartyNode.textContent.trim() === "Yes") : !(/bank|sbi|bob|axis|cash|hdfc|icici|tmb|idbi|pnb/i.test(ledger));
                if (!isPartyLedger) {
                    bankName = ledger;
                    bankDeemedPos = ent.querySelector("ISDEEMEDPOSITIVE")?.textContent || "Yes";
                } else {
                    particulars = ledger;
                    amount = Math.abs(rawAmt);
                }
            });
            type = (bankDeemedPos === "Yes") ? "DEBIT" : "CREDIT";
            
            let displayDate = dateVal;
            if (dateVal.length === 8) {
                displayDate = `${dateVal.substring(6, 8)}-${dateVal.substring(4, 6)}-${dateVal.substring(0, 4)}`;
            }
            
            reviewState.vouchers.push({
                id: i,
                date: displayDate,
                rawDate: dateVal,
                particulars: particulars,
                vchType: vchType,
                vchNo: vchNo,
                debit: (type === "DEBIT") ? amount : 0.0,
                credit: (type === "CREDIT") ? amount : 0.0,
                narration: narration,
                originalNode: node,
                modified: false
            });
        }
        
        // Populate header details
        document.getElementById("review-imported-filename").textContent = `Imported XML: ${file.name}`;
        document.getElementById("review-bank-profile").textContent = `Bank: ${bankName}`;
        
        // Find date range
        if (reviewState.vouchers.length > 0) {
            const sortedDates = [...reviewState.vouchers]
                .map(v => v.rawDate)
                .filter(d => d.length === 8)
                .sort();
            
            if (sortedDates.length > 0) {
                const minD = sortedDates[0];
                const maxD = sortedDates[sortedDates.length - 1];
                
                const fromStr = `${minD.substring(0, 4)}-${minD.substring(4, 6)}-${minD.substring(6, 8)}`;
                const toStr = `${maxD.substring(0, 4)}-${maxD.substring(4, 6)}-${maxD.substring(6, 8)}`;
                
                document.getElementById("review-modal-from-date").value = fromStr;
                document.getElementById("review-modal-to-date").value = toStr;
                
                document.getElementById("review-current-period").textContent = `Period: ${minD.substring(6, 8)}/${minD.substring(4, 6)} to ${maxD.substring(6, 8)}/${maxD.substring(4, 6)}`;
            }
        }
        
        // Populate ledger dropdown lists
        const ledgerSelect = document.getElementById("review-modal-ledger-select");
        if (ledgerSelect) {
            ledgerSelect.innerHTML = '<option value="all">All Ledgers</option>';
            Array.from(uniqueLedgers).sort().forEach(led => {
                const opt = document.createElement("option");
                opt.value = led;
                opt.textContent = led;
                ledgerSelect.appendChild(opt);
            });
        }
        
        // Update elements visibility
        document.getElementById("review-import-zone").classList.add("hidden");
        document.getElementById("review-table-container").classList.remove("hidden");
        
        // Process default filters & render
        applyReviewFilters();
        
        // Auto focus scroll area
        setTimeout(() => {
            const viewport = document.getElementById("review-virtual-viewport");
            if (viewport) viewport.focus();
        }, 100);
    };
    
    reader.readAsText(file);
}

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
            particularsHeader.style.width = "18%";
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
    
    // Toggle button text
    const label = document.getElementById("btn-tally-narration-label");
    if (label) {
        label.textContent = reviewState.showNarration ? "Hide Narration" : "Show Narration";
    }
    
    onReviewTableScroll();
}

function applyReviewFilters() {
    const statusVal = document.getElementById("review-modal-status-select").value;
    const ledgerVal = document.getElementById("review-modal-ledger-select").value;
    const searchVal = document.getElementById("review-modal-narration-keyword").value.toLowerCase().trim();
    
    const fromVal = document.getElementById("review-modal-from-date").value.replace(/-/g, "");
    const toVal = document.getElementById("review-modal-to-date").value.replace(/-/g, "");
    
    reviewState.filteredVouchers = reviewState.vouchers.filter(vch => {
        // 1. Status filter
        if (statusVal === "suspense" && !vch.particulars.toLowerCase().includes("suspense")) {
            return false;
        }
        if (statusVal === "modified" && !vch.modified) {
            return false;
        }
        
        // 2. Ledger filter
        if (ledgerVal !== "all" && vch.particulars !== ledgerVal) {
            return false;
        }
        
        // 3. Date range filter
        if (fromVal && vch.rawDate < fromVal) return false;
        if (toVal && vch.rawDate > toVal) return false;
        
        // 4. Substring Narration filter (compare case-insensitive)
        if (searchVal && !vch.narration.toLowerCase().includes(searchVal)) {
            return false;
        }
        
        return true;
    });
    
    // Reset focus index if it exceeds length
    if (reviewState.focusedIndex >= reviewState.filteredVouchers.length) {
        reviewState.focusedIndex = reviewState.filteredVouchers.length - 1;
    }
    
    updateReviewStats();
    onReviewTableScroll();
}

function updateReviewStats() {
    const total = reviewState.vouchers.length;
    const modified = reviewState.vouchers.filter(v => v.modified).length;
    const remainingSuspense = reviewState.vouchers.filter(v => !v.modified && v.particulars.toLowerCase().includes("suspense")).length;
    
    // Statistics panel
    document.getElementById("review-stat-total").textContent = total;
    document.getElementById("review-stat-modified").textContent = modified;
    document.getElementById("review-stat-suspense").textContent = remainingSuspense;
    
    // Footer status bar (safe check in case footer element is deleted)
    const fl = document.getElementById("review-footer-loaded");
    if (fl) fl.textContent = total;
    const fs = document.getElementById("review-footer-showing");
    if (fs) fs.textContent = reviewState.filteredVouchers.length;
    const fsel = document.getElementById("review-footer-selected");
    if (fsel) fsel.textContent = reviewState.selectedIds.size;
    const fm = document.getElementById("review-footer-modified");
    if (fm) fm.textContent = modified;
    const fsusp = document.getElementById("review-footer-suspense");
    if (fsusp) fsusp.textContent = remainingSuspense;
}

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
            "width: 18%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-weight: 500; box-sizing: border-box;" :
            "flex: 1; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-weight: 500; box-sizing: border-box;";
            
        const narrationCellStyles = reviewState.showNarration ?
            "flex: 1; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box; display: block;" :
            "display: none;";
            
        html += `
            <div class="review-row ${bgClass}" onclick="onReviewRowClick(event, ${i})" style="display: flex; height: ${reviewState.rowHeight}px; align-items: center; border-bottom: 1px solid #eeeeee; font-size: 0.78rem; position: absolute; top: ${i * reviewState.rowHeight}px; left: 0; right: 0; cursor: pointer; user-select: none; ${borderStyle} ${modStyle}">
                <div style="width: 10%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.date}</div>
                <div style="${particularsCellStyles}">${vch.particulars}</div>
                <div style="${narrationCellStyles}">${vch.narration}</div>
                <div style="width: 12%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.vchType}</div>
                <div style="width: 10%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-sizing: border-box;">${vch.vchNo}</div>
                <div style="width: 14%; flex-shrink: 0; padding: 6px 8px; border-right: 1px solid #eeeeee; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #10b981; box-sizing: border-box;">${debitText}</div>
                <div style="width: 14%; flex-shrink: 0; padding: 6px 8px; text-align: right; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #ef4444; box-sizing: border-box;">${creditText}</div>
            </div>
        `;
    }
    
    content.innerHTML = html;
}

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
        for (let i = start; i <= end; i++) {
            const item = reviewState.filteredVouchers[i];
            if (item) reviewState.selectedIds.add(item.id);
        }
    } else {
        // Single selection
        reviewState.selectedIds.clear();
        reviewState.selectedIds.add(vch.id);
    }
    
    reviewState.focusedIndex = index;
    reviewState.lastSelectedIndex = index;
    
    updateReviewStats();
    onReviewTableScroll();
}

function onReviewTableKeydown(e) {
    const count = reviewState.filteredVouchers.length;
    if (count === 0) return;
    
    let nextIndex = reviewState.focusedIndex;
    let handled = false;
    
    switch (e.key) {
        case "ArrowDown":
            nextIndex = Math.min(count - 1, reviewState.focusedIndex + 1);
            if (nextIndex !== reviewState.focusedIndex) {
                if (e.shiftKey) {
                    const currVch = reviewState.filteredVouchers[nextIndex];
                    if (currVch) reviewState.selectedIds.add(currVch.id);
                } else {
                    reviewState.selectedIds.clear();
                    const currVch = reviewState.filteredVouchers[nextIndex];
                    if (currVch) reviewState.selectedIds.add(currVch.id);
                }
            }
            handled = true;
            break;
            
        case "ArrowUp":
            nextIndex = Math.max(0, reviewState.focusedIndex - 1);
            if (nextIndex !== reviewState.focusedIndex) {
                if (e.shiftKey) {
                    const currVch = reviewState.filteredVouchers[nextIndex];
                    if (currVch) reviewState.selectedIds.add(currVch.id);
                } else {
                    reviewState.selectedIds.clear();
                    const currVch = reviewState.filteredVouchers[nextIndex];
                    if (currVch) reviewState.selectedIds.add(currVch.id);
                }
            }
            handled = true;
            break;
            
        case "PageDown":
            nextIndex = Math.min(count - 1, reviewState.focusedIndex + reviewState.visibleCount);
            reviewState.selectedIds.clear();
            const pdVch = reviewState.filteredVouchers[nextIndex];
            if (pdVch) reviewState.selectedIds.add(pdVch.id);
            handled = true;
            break;
            
        case "PageUp":
            nextIndex = Math.max(0, reviewState.focusedIndex - reviewState.visibleCount);
            reviewState.selectedIds.clear();
            const puVch = reviewState.filteredVouchers[nextIndex];
            if (puVch) reviewState.selectedIds.add(puVch.id);
            handled = true;
            break;
            
        case "Home":
            nextIndex = 0;
            reviewState.selectedIds.clear();
            const hVch = reviewState.filteredVouchers[nextIndex];
            if (hVch) reviewState.selectedIds.add(hVch.id);
            handled = true;
            break;
            
        case "End":
            nextIndex = count - 1;
            reviewState.selectedIds.clear();
            const eVch = reviewState.filteredVouchers[nextIndex];
            if (eVch) reviewState.selectedIds.add(eVch.id);
            handled = true;
            break;
            
        case "Escape":
            reviewState.selectedIds.clear();
            updateReviewStats();
            onReviewTableScroll();
            handled = true;
            break;
            
        case "Enter":
            openReplaceLedgerModal();
            handled = true;
            break;
    }
    
    if (handled) {
        e.preventDefault();
        reviewState.focusedIndex = nextIndex;
        if (!e.shiftKey) {
            reviewState.lastSelectedIndex = nextIndex;
        }
        
        // Scroll item into view
        const viewport = document.getElementById("review-virtual-viewport");
        if (viewport) {
            const topBoundary = viewport.scrollTop;
            const bottomBoundary = topBoundary + viewport.clientHeight;
            const itemTop = nextIndex * reviewState.rowHeight;
            const itemBottom = itemTop + reviewState.rowHeight;
            
            if (itemTop < topBoundary) {
                viewport.scrollTop = itemTop;
            } else if (itemBottom > bottomBoundary) {
                viewport.scrollTop = itemBottom - viewport.clientHeight;
            }
        }
        
        updateReviewStats();
        onReviewTableScroll();
    }
}

function openMonthlyAnalysisModal() {
    const modal = document.getElementById("review-modal-monthly");
    if (!modal) return;
    
    // Sort vouchers by rawDate to calculate correct cumulative closing balances
    const sortedVch = [...reviewState.vouchers].sort((a, b) => a.rawDate.localeCompare(b.rawDate));
    
    const openingBal = reviewState.openingBalance || 0.00;
    
    // Group by month key "YYYY-MM"
    const groups = {};
    
    sortedVch.forEach(v => {
        let year = "";
        let month = "";
        let monthName = "";
        
        if (v.rawDate && v.rawDate.length === 8) {
            year = v.rawDate.substring(0, 4);
            month = v.rawDate.substring(4, 6);
            
            const dateObj = new Date(parseInt(year), parseInt(month) - 1, 1);
            monthName = dateObj.toLocaleString('default', { month: 'long', year: 'numeric' });
        } else {
            // Fallback parsing from date field e.g. "02-04-2025"
            const parts = v.date.split("-");
            if (parts.length === 3) {
                year = parts[2];
                month = parts[1];
                const dateObj = new Date(parseInt(year), parseInt(month) - 1, 1);
                monthName = dateObj.toLocaleString('default', { month: 'long', year: 'numeric' });
            } else {
                monthName = "Unknown Month";
            }
        }
        
        const key = `${year}-${month}`;
        if (!groups[key]) {
            groups[key] = {
                key: key,
                name: monthName,
                count: 0,
                debit: 0.0,
                credit: 0.0
            };
        }
        
        groups[key].count++;
        groups[key].debit += parseFloat(v.debit || 0);
        groups[key].credit += parseFloat(v.credit || 0);
    });
    
    // Convert to sorted array
    const sortedGroups = Object.values(groups).sort((a, b) => a.key.localeCompare(b.key));
    
    // Calculate cumulative closing balances month by month
    let runningBalance = openingBal;
    sortedGroups.forEach(g => {
        // Bank balance increases with Debit (money received) and decreases with Credit (money spent)
        runningBalance = runningBalance + g.debit - g.credit;
        g.closingBalance = runningBalance;
    });
    
    // Populate opening balance display
    const opBalSection = document.getElementById("review-monthly-opbal-section");
    const opBalVal = document.getElementById("review-monthly-opbal-val");
    if (openingBal !== 0.0) {
        if (opBalSection) opBalSection.style.display = "block";
        if (opBalVal) opBalVal.textContent = formatCurrency(openingBal);
    } else {
        // Hide if opening balance is zero/not found
        if (opBalSection) opBalSection.style.display = "none";
    }
    
    // Populate table
    const tbody = document.getElementById("review-monthly-table-body");
    if (tbody) {
        if (sortedGroups.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="padding: 15px; text-align: center; color: #718096;">No voucher data loaded</td></tr>`;
        } else {
            let html = "";
            sortedGroups.forEach(g => {
                html += `
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="width: 28%; padding: 8px; font-weight: 500; color: #2d3748; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${g.name}</td>
                        <td style="width: 14%; padding: 8px; text-align: right; color: #4a5568;">${g.count}</td>
                        <td style="width: 19%; padding: 8px; text-align: right; color: #10b981; white-space: nowrap;">${g.debit > 0 ? formatCurrency(g.debit) : "-"}</td>
                        <td style="width: 19%; padding: 8px; text-align: right; color: #ef4444; white-space: nowrap;">${g.credit > 0 ? formatCurrency(g.credit) : "-"}</td>
                        <td style="width: 20%; padding: 8px; text-align: right; font-weight: 600; color: #002d5a; white-space: nowrap;">${formatCurrency(g.closingBalance)}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }
    }
    
    modal.classList.remove("hidden");
}

function openPeriodModal() {
    const modal = document.getElementById("review-modal-period");
    if (!modal) return;
    
    modal.classList.remove("hidden");
    
    // Prefill dates from current reviewState filters
    const fromStr = document.getElementById("review-modal-from-date");
    
    setTimeout(() => fromStr.focus(), 100);
}

function confirmPeriodFilter() {
    const fromInput = document.getElementById("review-modal-from-date").value;
    const toInput = document.getElementById("review-modal-to-date").value;
    
    const minD = fromInput.replace(/-/g, "");
    const maxD = toInput.replace(/-/g, "");
    
    if (minD && maxD) {
        document.getElementById("review-current-period").textContent = `Period: ${minD.substring(6, 8)}/${minD.substring(4, 6)} to ${maxD.substring(6, 8)}/${maxD.substring(4, 6)}`;
    }
    
    closeReviewModal("period");
    applyReviewFilters();
}

function openLedgerFilterModal() {
    const modal = document.getElementById("review-modal-ledger");
    if (!modal) return;
    
    modal.classList.remove("hidden");
    
    setTimeout(() => {
        const select = document.getElementById("review-modal-ledger-select");
        if (select) select.focus();
    }, 100);
}

function confirmLedgerFilter() {
    closeReviewModal("ledger");
    applyReviewFilters();
}

function openNarrationFilterModal() {
    const modal = document.getElementById("review-modal-narration");
    if (!modal) return;
    
    modal.classList.remove("hidden");
    const input = document.getElementById("review-modal-narration-keyword");
    if (input) {
        input.value = "";
        setTimeout(() => input.focus(), 100);
    }
}

function confirmNarrationFilter() {
    const keywordInput = document.getElementById("review-modal-narration-keyword");
    const keyword = keywordInput ? keywordInput.value.toLowerCase().trim() : "";
    
    if (keyword) {
        // Run test filter count on all currently active vouchers (ignoring the narration filter itself)
        const statusVal = document.getElementById("review-modal-status-select").value;
        const ledgerVal = document.getElementById("review-modal-ledger-select").value;
        const fromVal = document.getElementById("review-modal-from-date").value.replace(/-/g, "");
        const toVal = document.getElementById("review-modal-to-date").value.replace(/-/g, "");
        
        const matchingCount = reviewState.vouchers.filter(vch => {
            // 1. Status filter
            if (statusVal === "suspense" && !vch.particulars.toLowerCase().includes("suspense")) {
                return false;
            }
            if (statusVal === "modified" && !vch.modified) {
                return false;
            }
            
            // 2. Ledger filter
            if (ledgerVal !== "all" && vch.particulars !== ledgerVal) {
                return false;
            }
            
            // 3. Date range filter
            if (fromVal && vch.rawDate < fromVal) return false;
            if (toVal && vch.rawDate > toVal) return false;
            
            // Check keyword (convert input keyword and actual stored narration to lowercase)
            return vch.narration.toLowerCase().includes(keyword);
        }).length;
        
        if (matchingCount === 0) {
            alert("No results found");
            // Do not close the modal, let the user adjust the input
            return;
        }
    }
    
    closeReviewModal("narration");
    applyReviewFilters();
}

function openReplaceLedgerModal() {
    if (reviewState.selectedIds.size === 0) {
        alert("Please select vouchers first.");
        return;
    }
    
    const modal = document.getElementById("review-modal-replace");
    if (!modal) return;
    
    document.getElementById("review-modal-replace-count").textContent = reviewState.selectedIds.size;
    
    const newLedgerInput = document.getElementById("review-modal-new-ledger");
    if (newLedgerInput) newLedgerInput.value = "";
    
    modal.classList.remove("hidden");
    setTimeout(() => {
        if (newLedgerInput) newLedgerInput.focus();
    }, 100);
}

async function confirmReplaceLedger() {
    const targetLedger = document.getElementById("review-modal-target-ledger").value.trim();
    const newLedger = document.getElementById("review-modal-new-ledger").value.trim();
    
    if (!targetLedger || !newLedger) {
        alert("Please specify both target and replacement ledger accounts.");
        return;
    }
    
    let replacedCount = 0;
    
    // Run replacement in memory
    reviewState.selectedIds.forEach(id => {
        const vch = reviewState.vouchers[id];
        if (vch) {
            // Only replace if matching target ledger (or target ledger is '*')
            if (targetLedger === "*" || vch.particulars.toLowerCase() === targetLedger.toLowerCase()) {
                vch.particulars = newLedger;
                vch.modified = true;
                
                // Replace in XML tree node
                const entries = vch.originalNode.querySelectorAll("ALLLEDGERENTRIES\\.LIST, LEDGERENTRIES\\.LIST");
                entries.forEach(ent => {
                    const ledgerNode = ent.querySelector("LEDGERNAME");
                    if (ledgerNode && ledgerNode.textContent.toLowerCase() === targetLedger.toLowerCase()) {
                        ledgerNode.textContent = newLedger;
                    }
                });
                
                // Persist new mapping keyword to backend JSON file
                if (vch.narration) {
                    const cleanWord = vch.narration.toUpperCase().replace(/[^A-Z0-9\s]/g, "").trim().split(/\s+/).slice(0, 3).join(" ");
                    if (cleanWord && cleanWord.length > 2) {
                        reviewState.ledgerCache[cleanWord] = newLedger;
                        saveReviewMappingToBackend(cleanWord, newLedger);
                    }
                }
                
                replacedCount++;
            }
        }
    });
    
    alert(`Successfully replaced ledger in ${replacedCount} vouchers.`);
    
    closeReviewModal("replace");
    reviewState.selectedIds.clear();
    
    // Re-populate ledger filters
    const ledgerSelect = document.getElementById("review-modal-ledger-select");
    if (ledgerSelect) {
        const uniqueLedgers = new Set();
        reviewState.vouchers.forEach(v => uniqueLedgers.add(v.particulars));
        
        ledgerSelect.innerHTML = '<option value="all">All Ledgers</option>';
        Array.from(uniqueLedgers).sort().forEach(led => {
            const opt = document.createElement("option");
            opt.value = led;
            opt.textContent = led;
            ledgerSelect.appendChild(opt);
        });
    }
    
    applyReviewFilters();
}

async function saveReviewMappingToBackend(keyword, ledger) {
    try {
        await fetch("/api/review/cache/update", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({keyword, ledger})
        });
    } catch (e) {
        console.error("Failed to persist ledger mapping to server:", e);
    }
}

function closeReviewModal(type) {
    const modal = document.getElementById(`review-modal-${type}`);
    if (modal) modal.classList.add("hidden");
    
    // Restore focus back to virtual viewport
    const viewport = document.getElementById("review-virtual-viewport");
    if (viewport) viewport.focus();
}

// Autocomplete suggestions inside Replace modal
function showLedgerAutocompleteModal() {
    const list = document.getElementById("review-modal-ledger-autocomplete-list");
    if (!list) return;
    
    const options = new Set(["Suspense", "Cash", "Sales", "Expenses", "Food Expenses", "Office Expenses", "Purchases"]);
    
    reviewState.vouchers.forEach(v => {
        if (v.particulars) options.add(v.particulars);
    });
    
    Object.values(reviewState.ledgerCache).forEach(led => {
        options.add(led);
    });
    
    const sorted = Array.from(options).sort();
    
    let html = "";
    sorted.forEach(opt => {
        html += `<div class="ledger-autocomplete-item" onclick="selectLedgerAutocompleteModal('${opt}')">${opt}</div>`;
    });
    
    list.innerHTML = html;
    list.classList.remove("hidden");
}

function filterLedgerAutocompleteModal() {
    const inputVal = document.getElementById("review-modal-new-ledger").value.toLowerCase().trim();
    const list = document.getElementById("review-modal-ledger-autocomplete-list");
    if (!list) return;
    
    const items = list.querySelectorAll(".ledger-autocomplete-item");
    let matchCount = 0;
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(inputVal)) {
            item.style.display = "block";
            matchCount++;
        } else {
            item.style.display = "none";
        }
    });
    
    if (matchCount > 0) {
        list.classList.remove("hidden");
    } else {
        list.classList.add("hidden");
    }
}

function selectLedgerAutocompleteModal(val) {
    const input = document.getElementById("review-modal-new-ledger");
    if (input) input.value = val;
    
    const list = document.getElementById("review-modal-ledger-autocomplete-list");
    if (list) list.classList.add("hidden");
}

function exportReviewXML() {
    if (!reviewState.xmlDoc) {
        alert("No XML document loaded.");
        return;
    }
    
    const serializer = new XMLSerializer();
    const xmlText = serializer.serializeToString(reviewState.xmlDoc);
    
    const blob = new Blob([xmlText], {type: "text/xml"});
    const link = document.createElement("a");
    const nameStr = reviewState.originalFileName.replace(/\.xml$/i, "") + "_updated.xml";
    
    link.href = URL.createObjectURL(blob);
    link.download = nameStr;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function clearReviewDesk() {
    reviewState.xmlDoc = null;
    reviewState.originalFileName = "";
    reviewState.vouchers = [];
    reviewState.filteredVouchers = [];
    reviewState.selectedIds.clear();
    reviewState.focusedIndex = -1;
    reviewState.lastSelectedIndex = -1;
    
    document.getElementById("review-imported-filename").textContent = "Imported XML: None";
    document.getElementById("review-bank-profile").textContent = "Bank: Unspecified";
    document.getElementById("review-current-period").textContent = "Period: Full Range";
    
    // Clear inputs in modals
    document.getElementById("review-modal-from-date").value = "";
    document.getElementById("review-modal-to-date").value = "";
    document.getElementById("review-modal-narration-keyword").value = "";
    document.getElementById("review-modal-new-ledger").value = "";
    
    reviewState.showNarration = false;
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
    
    document.getElementById("review-import-zone").classList.remove("hidden");
    document.getElementById("review-table-container").classList.add("hidden");
    
    updateReviewStats();
}

// ==========================================
// GSTR-1 OFFLINE CONVERTER FRONTEND CONTROLLER
// ==========================================
async function runGstr1Conversion() {
    const file = state.files.gstr1;
    const gstin = document.getElementById("gstr1-supplier-gstin").value.trim().toUpperCase();
    const fp = document.getElementById("gstr1-fp").value.trim();

    if (!file) {
        alert("Please select or drag a sales register Excel/CSV file first.");
        updateStatusBox("gstr1", "❌ No file selected.", "error");
        return;
    }
    if (!gstin || gstin.length !== 15) {
        alert("Please enter a valid 15-character Supplier GSTIN.");
        return;
    }
    if (!fp || fp.length !== 6 || isNaN(fp)) {
        alert("Please enter a valid Financial Period in MMYYYY format (e.g. 082025).");
        return;
    }

    const spinner = document.getElementById("gstr1-spinner");
    const btnText = document.getElementById("gstr1-btn-text");
    const resultsContainer = document.getElementById("gstr1-results");

    // Show loading state
    spinner.classList.remove("hidden");
    btnText.textContent = "Processing Conversion...";
    resultsContainer.classList.add("hidden");
    updateStatusBox("gstr1", "⏳ Reading and converting sales entries...", "neutral");

    const headerRow = document.getElementById("gstr1-header-row") ? document.getElementById("gstr1-header-row").value.trim() : "4";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("supplier_gstin", gstin);
    formData.append("fp", fp);
    formData.append("header_row", headerRow || "4");

    try {
        const response = await fetch("/api/convert_gstr1", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (data.success) {
            updateStatusBox("gstr1", "🟢 GSTR-1 JSON Generated Successfully!", "success");

            // Populate Metrics
            document.getElementById("m-gstr1-recipients").textContent = data.summary.recipient_count;
            document.getElementById("m-gstr1-invoices").textContent = data.summary.invoice_count;
            document.getElementById("m-gstr1-taxable").textContent = formatCurrency(data.summary.total_taxable);
            
            const totalTax = data.summary.total_cgst + data.summary.total_sgst + data.summary.total_igst;
            document.getElementById("m-gstr1-tax").textContent = formatCurrency(totalTax);
            document.getElementById("m-gstr1-total").textContent = formatCurrency(data.summary.total_invoice_val);

            // Populate Live Preview Table
            const tbody = document.querySelector("#gstr1-preview-table tbody");
            tbody.innerHTML = "";

            let grandTxval = 0;
            let grandCgst = 0;
            let grandSgst = 0;
            let grandIgst = 0;
            let grandVal = 0;

            data.invoices.forEach(inv => {
                grandTxval += inv.txval || 0;
                grandCgst += inv.cgst || 0;
                grandSgst += inv.sgst || 0;
                grandIgst += inv.igst || 0;
                grandVal += inv.val || 0;

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td style="font-family: monospace; font-weight: 500;">${inv.ctin}</td>
                    <td style="font-weight: 500; color: #a78bfa;">${inv.inum}</td>
                    <td>${inv.idt}</td>
                    <td style="text-align: center;">${inv.pos}</td>
                    <td style="text-align: right; font-weight: 500;">${formatCurrency(inv.txval)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.7);">${formatCurrency(inv.cgst)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.7);">${formatCurrency(inv.sgst)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.7);">${formatCurrency(inv.igst)}</td>
                    <td style="text-align: right; font-weight: bold; color: #34d399;">${formatCurrency(inv.val)}</td>
                    <td style="text-align: center;"><span class="badge ${inv.rchrg === 'Y' ? 'warning' : 'neutral'}" style="padding: 2px 6px; font-size: 0.7rem;">${inv.rchrg}</span></td>
                `;
                tbody.appendChild(tr);
            });

            // Append Grand Total Row
            const totalTr = document.createElement("tr");
            totalTr.style.fontWeight = "bold";
            totalTr.style.background = "rgba(255, 255, 255, 0.05)";
            totalTr.style.borderTop = "2px solid rgba(255, 255, 255, 0.15)";
            totalTr.innerHTML = `
                <td colspan="4" style="text-align: left; font-weight: bold; letter-spacing: 0.5px;">TOTAL</td>
                <td style="text-align: right; font-weight: bold;">${formatCurrency(grandTxval)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.9);">${formatCurrency(grandCgst)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.9);">${formatCurrency(grandSgst)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.9);">${formatCurrency(grandIgst)}</td>
                <td style="text-align: right; font-weight: bold; color: #34d399;">${formatCurrency(grandVal)}</td>
                <td></td>
            `;
            tbody.appendChild(totalTr);

            // Reveal results
            resultsContainer.classList.remove("hidden");
        } else {
            alert(data.message || "Failed to process GSTR-1 conversion.");
            updateStatusBox("gstr1", "❌ Conversion failed: " + (data.message || "Unknown error"), "error");
        }
    } catch (err) {
        console.error("GSTR-1 Error:", err);
        alert("Failed to connect to backend server.");
        updateStatusBox("gstr1", "❌ Network error connecting to backend.", "error");
    } finally {
        spinner.classList.add("hidden");
        btnText.textContent = "Convert to GSTR-1 JSON";
    }
}

// ==========================================
// GSTR-1 & HSN SUB-TAB SWITCHER
// ==========================================
function switchGstr1SubTab(subTabId) {
    document.querySelectorAll("#gstr1-tab .btn-subtab").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById("btn-subtab-gstr1-" + subTabId.replace("gstr1-", ""));
    if (activeBtn) activeBtn.classList.add("active");
    
    document.querySelectorAll(".gstr1-subtab-pane").forEach(pane => pane.classList.add("hidden"));
    const activePane = document.getElementById("pane-gstr1-" + subTabId.replace("gstr1-", ""));
    if (activePane) activePane.classList.remove("hidden");
}

// ==========================================
// HSN OFFLINE CONVERTER FRONTEND CONTROLLER
// ==========================================
async function runHsnConversion() {
    const file = state.files.hsn;
    const gstin = document.getElementById("hsn-supplier-gstin").value.trim().toUpperCase();
    const fp = document.getElementById("hsn-fp").value.trim();

    if (!file) {
        alert("Please select or drag a sales register Excel/CSV file first.");
        updateStatusBox("hsn", "❌ No file selected.", "error");
        return;
    }
    if (!gstin || gstin.length !== 15) {
        alert("Please enter a valid 15-character Supplier GSTIN.");
        return;
    }
    if (!fp || fp.length !== 6 || isNaN(fp)) {
        alert("Please enter a valid Financial Period in MMYYYY format (e.g. 082025).");
        return;
    }

    const spinner = document.getElementById("hsn-spinner");
    const btnText = document.getElementById("hsn-btn-text");
    const resultsContainer = document.getElementById("hsn-results");

    // Show loading state
    spinner.classList.remove("hidden");
    btnText.textContent = "Processing Conversion...";
    resultsContainer.classList.add("hidden");
    updateStatusBox("hsn", "⏳ Reading and converting HSN summary...", "neutral");

    const headerRow = document.getElementById("hsn-header-row") ? document.getElementById("hsn-header-row").value.trim() : "4";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("supplier_gstin", gstin);
    formData.append("fp", fp);
    formData.append("header_row", headerRow || "4");

    try {
        const response = await fetch("/api/convert_hsn", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (data.success) {
            updateStatusBox("hsn", "🟢 HSN Summary Generated Successfully!", "success");

            // Populate Metrics
            document.getElementById("m-hsn-count").textContent = data.summary.hsn_count;
            document.getElementById("m-hsn-qty").textContent = data.summary.total_qty.toFixed(2);
            document.getElementById("m-hsn-taxable").textContent = formatCurrency(data.summary.total_taxable);
            document.getElementById("m-hsn-tax").textContent = formatCurrency(data.summary.total_taxes);
            document.getElementById("m-hsn-total").textContent = formatCurrency(data.summary.total_val);

            // Populate Live HSN Table
            const tbody = document.querySelector("#hsn-preview-table tbody");
            tbody.innerHTML = "";

            let grandQty = 0;
            let grandTxval = 0;
            let grandCamt = 0;
            let grandSamt = 0;
            let grandIamt = 0;
            let grandVal = 0;
            let grandCsamt = 0;

            data.hsn_data.forEach(h => {
                grandQty += h.qty || 0;
                grandTxval += h.txval || 0;
                grandCamt += h.camt || 0;
                grandSamt += h.samt || 0;
                grandIamt += h.iamt || 0;
                grandVal += h.val || 0;
                grandCsamt += h.csamt || 0;

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td style="font-family: monospace; font-weight: 500;">${h.hsn_sc}</td>
                    <td style="text-align: center;"><span class="badge ${h.sply_ty === 'B2B' ? 'info' : 'warning'}" style="padding: 2px 6px; font-size: 0.75rem;">${h.sply_ty}</span></td>
                    <td>${h.desc}</td>
                    <td style="text-align: center;"><span class="badge neutral" style="padding: 2px 6px; font-size: 0.75rem;">${h.uqc}</span></td>
                    <td style="text-align: right;">${h.qty.toFixed(2)}</td>
                    <td style="text-align: right; font-weight: 500;">${formatCurrency(h.txval)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.7);">${formatCurrency(h.camt)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.7);">${formatCurrency(h.samt)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.7);">${formatCurrency(h.iamt)}</td>
                    <td style="text-align: right; font-weight: bold; color: #34d399;">${formatCurrency(h.val)}</td>
                    <td style="text-align: right; color: rgba(255,255,255,0.5);">${formatCurrency(h.csamt)}</td>
                `;
                tbody.appendChild(tr);
            });

            // Append Grand Total Row
            const totalTr = document.createElement("tr");
            totalTr.style.fontWeight = "bold";
            totalTr.style.background = "rgba(255, 255, 255, 0.05)";
            totalTr.style.borderTop = "2px solid rgba(255, 255, 255, 0.15)";
            totalTr.innerHTML = `
                <td colspan="4" style="text-align: left; font-weight: bold; letter-spacing: 0.5px;">TOTAL</td>
                <td style="text-align: right;">${grandQty.toFixed(2)}</td>
                <td style="text-align: right; font-weight: bold;">${formatCurrency(grandTxval)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.9);">${formatCurrency(grandCamt)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.9);">${formatCurrency(grandSamt)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.9);">${formatCurrency(grandIamt)}</td>
                <td style="text-align: right; font-weight: bold; color: #34d399;">${formatCurrency(grandVal)}</td>
                <td style="text-align: right; font-weight: bold; color: rgba(255,255,255,0.7);">${formatCurrency(grandCsamt)}</td>
            `;
            tbody.appendChild(totalTr);

            // Reveal results
            resultsContainer.classList.remove("hidden");
        } else {
            alert(data.message || "Failed to process HSN conversion.");
            updateStatusBox("hsn", "❌ Conversion failed: " + (data.message || "Unknown error"), "error");
        }
    } catch (err) {
        console.error("HSN Error:", err);
        alert("Failed to connect to backend server.");
        updateStatusBox("hsn", "❌ Network error connecting to backend.", "error");
    } finally {
        spinner.classList.add("hidden");
        btnText.textContent = "Convert HSN Summary";
    }
}



// ==========================================
// PDF REDACTION FRONTEND CONTROLLER
// ==========================================
let redactState = {
    page: 0,
    totalPages: 0,
    scale: 1.5,
    isSelecting: false,
    startX: 0,
    startY: 0,
    currentRect: null,
    toolActive: false,
    isFileLoaded: false,
    widthPts: 0,
    heightPts: 0,
    widthPx: 0,
    heightPx: 0
};

function openRedactModal() {
    document.getElementById("redact-modal").classList.remove("hidden");
    
    // Reset state
    redactState = {
        page: 0,
        totalPages: 0,
        scale: 1.5,
        isSelecting: false,
        startX: 0,
        startY: 0,
        currentRect: null,
        toolActive: false,
        isFileLoaded: false,
        widthPts: 0,
        heightPts: 0,
        widthPx: 0,
        heightPx: 0
    };
    
    updateRedactUIState();
    
    // Auto-load if bank file exists
    if (state && state.files && state.files.bank) {
        uploadPdfToRedact(state.files.bank);
    } else {
        document.getElementById("redact-empty-msg").classList.remove("hidden");
        document.getElementById("redact-canvas-container").style.display = "none";
    }
}

function closeRedactModal() {
    document.getElementById("redact-modal").classList.add("hidden");
    
    const canvas = document.getElementById("redact-overlay-canvas");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    fetch("/api/redact/cleanup", { method: "POST" })
        .then(res => res.json())
        .then(data => console.log("Section Remover session cleaned up on server."))
        .catch(err => console.error("Error cleaning up section remover: ", err));
}

function triggerRedactUpload() {
    document.getElementById("redact-file-input").click();
}

function handleRedactFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        uploadPdfToRedact(file);
    }
}

function uploadPdfToRedact(file) {
    showRedactLoading(true);
    document.getElementById("redact-empty-msg").classList.add("hidden");
    
    const formData = new FormData();
    formData.append("file", file);
    
    fetch("/api/redact/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            redactState.totalPages = data.page_count;
            redactState.page = 0;
            redactState.isFileLoaded = true;
            redactState.filename = file.name;
            
            // Sync to main app upload zone
            if (state && state.files) {
                if (!state.files.bank || state.files.bank.name !== file.name) {
                    state.files.bank = file;
                    const label = document.getElementById("bank-file-label");
                    if (label) {
                        label.innerText = file.name;
                    }
                }
            }
            
            loadRedactPage();
        } else {
            showRedactLoading(false);
            alert("Error loading PDF: " + data.message);
        }
    })
    .catch(err => {
        showRedactLoading(false);
        console.error(err);
        alert("Server connection failed.");
    });
}

function loadRedactPage() {
    if (!redactState.isFileLoaded) return;
    
    showRedactLoading(true);
    const url = `/api/redact/page?page=${redactState.page}&scale=${redactState.scale}&_=${new Date().getTime()}`;
    
    fetch(url)
    .then(res => res.json())
    .then(data => {
        showRedactLoading(false);
        if (data.success) {
            const img = document.getElementById("redact-page-img");
            img.src = data.image;
            
            redactState.widthPts = data.width_pts;
            redactState.heightPts = data.height_pts;
            redactState.widthPx = data.width_px;
            redactState.heightPx = data.height_px;
            
            img.onload = function() {
                const container = document.getElementById("redact-canvas-container");
                container.style.display = "inline-block";
                
                const canvas = document.getElementById("redact-overlay-canvas");
                canvas.width = img.clientWidth;
                canvas.height = img.clientHeight;
                
                redactState.currentRect = null;
                const ctx = canvas.getContext("2d");
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                updateRedactUIState();
            };
        } else {
            alert("Failed to render page: " + data.message);
        }
    })
    .catch(err => {
        showRedactLoading(false);
        console.error(err);
    });
}

function changeRedactPage(direction) {
    const newPage = redactState.page + direction;
    if (newPage >= 0 && newPage < redactState.totalPages) {
        redactState.page = newPage;
        loadRedactPage();
    }
}

function toggleRedactTool() {
    redactState.toolActive = !redactState.toolActive;
    const btn = document.getElementById("btn-redact-tool");
    const canvas = document.getElementById("redact-overlay-canvas");
    
    if (redactState.toolActive) {
        btn.style.backgroundColor = "#10b981";
        btn.style.color = "white";
        canvas.style.cursor = "crosshair";
    } else {
        btn.style.backgroundColor = "#374151";
        btn.style.color = "#d1d5db";
        canvas.style.cursor = "default";
        
        redactState.currentRect = null;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        updateRedactUIState();
    }
}

function removeRedactSelection() {
    if (!redactState.currentRect) return;
    
    showRedactLoading(true);
    
    const body = {
        page: redactState.page,
        scale: redactState.scale,
        x0: redactState.currentRect.x,
        y0: redactState.currentRect.y,
        x1: redactState.currentRect.x + redactState.currentRect.width,
        y1: redactState.currentRect.y + redactState.currentRect.height
    };
    
    fetch("/api/redact/remove", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    })
    .then(res => res.json())
    .then(data => {
        showRedactLoading(false);
        if (data.success) {
            const img = document.getElementById("redact-page-img");
            img.src = data.image;
            
            redactState.currentRect = null;
            const canvas = document.getElementById("redact-overlay-canvas");
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            document.getElementById("btn-redact-undo").disabled = !data.can_undo;
            updateRedactUIState();
        } else {
            alert("Redaction failed: " + data.message);
        }
    })
    .catch(err => {
        showRedactLoading(false);
        console.error(err);
    });
}

function undoRedact() {
    showRedactLoading(true);
    
    const body = {
        page: redactState.page,
        scale: redactState.scale
    };
    
    fetch("/api/redact/undo", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    })
    .then(res => res.json())
    .then(data => {
        showRedactLoading(false);
        if (data.success) {
            const img = document.getElementById("redact-page-img");
            img.src = data.image;
            
            redactState.currentRect = null;
            const canvas = document.getElementById("redact-overlay-canvas");
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            document.getElementById("btn-redact-undo").disabled = !data.can_undo;
            updateRedactUIState();
        } else {
            alert("Undo failed: " + data.message);
        }
    })
    .catch(err => {
        showRedactLoading(false);
        console.error(err);
    });
}

function useCleanedPdf() {
    if (!redactState.isFileLoaded) return;
    
    showRedactLoading(true);
    
    fetch("/api/redact/use", { method: "POST" })
    .then(res => res.json())
    .then(data => {
        showRedactLoading(false);
        if (data.success) {
            const label = document.getElementById("bank-file-label");
            if (label) {
                label.innerHTML = `<span style="color: #10b981; font-weight: bold;">[Cleaned]</span> ${data.filename}`;
            }
            alert("PDF cleaned and registered for parsing! You can now close this editor and click Convert.");
            closeRedactModal();
        } else {
            alert("Failed to lock cleaned PDF: " + data.message);
        }
    })
    .catch(err => {
        showRedactLoading(false);
        console.error(err);
    });
}

function downloadCleanedPdf() {
    if (window.pywebview && window.pywebview.api) {
        showRedactLoading(true);
        window.pywebview.api.download_file("last_cleaned_pdf")
        .then(res => {
            showRedactLoading(false);
            if (res.success) {
                alert(`File successfully saved to:\n${res.path}`);
            } else if (res.message && res.message !== "Cancelled" && res.message !== "Save cancelled") {
                alert(`Save failed: ${res.message}`);
            }
        })
        .catch(err => {
            showRedactLoading(false);
            alert(`Native download error: ${err.message}`);
        });
    } else {
        showRedactLoading(true);
        fetch("/api/redact/download")
        .then(res => {
            showRedactLoading(false);
            if (!res.ok) {
                return res.text().then(text => { alert("Error downloading: " + text); });
            }
            return res.blob().then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.style.display = "none";
                a.href = url;
                a.download = redactState.filename ? redactState.filename.replace(".pdf", "_cleaned.pdf") : "cleaned.pdf";
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            });
        })
        .catch(err => {
            showRedactLoading(false);
            console.error("Download error:", err);
            alert("Failed to download PDF.");
        });
    }
}

function showRedactLoading(show) {
    const loader = document.getElementById("redact-loading");
    if (show) {
        loader.classList.remove("hidden");
    } else {
        loader.classList.add("hidden");
    }
}

function updateRedactUIState() {
    const current = redactState.page + 1;
    const total = redactState.totalPages;
    
    document.getElementById("redact-page-label").innerText = `Page ${total > 0 ? current : 0} / ${total}`;
    
    document.getElementById("btn-redact-prev").disabled = !redactState.isFileLoaded || current <= 1;
    document.getElementById("btn-redact-next").disabled = !redactState.isFileLoaded || current >= total;
    
    document.getElementById("btn-redact-tool").disabled = !redactState.isFileLoaded;
    document.getElementById("btn-redact-remove").disabled = !redactState.currentRect;
    const btnUse = document.getElementById("btn-redact-use");
    if (btnUse) btnUse.disabled = !redactState.isFileLoaded;
    document.getElementById("btn-redact-download").disabled = !redactState.isFileLoaded;
}

document.addEventListener("DOMContentLoaded", function() {
    const canvas = document.getElementById("redact-overlay-canvas");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    
    canvas.addEventListener("mousedown", function(e) {
        if (!redactState.toolActive || !redactState.isFileLoaded) return;
        
        const rect = canvas.getBoundingClientRect();
        redactState.startX = e.clientX - rect.left;
        redactState.startY = e.clientY - rect.top;
        redactState.isSelecting = true;
        
        redactState.currentRect = {
            x: redactState.startX,
            y: redactState.startY,
            width: 0,
            height: 0
        };
    });
    
    canvas.addEventListener("mousemove", function(e) {
        if (!redactState.isSelecting) return;
        
        const rect = canvas.getBoundingClientRect();
        const curX = e.clientX - rect.left;
        const curY = e.clientY - rect.top;
        
        const x = Math.min(redactState.startX, curX);
        const y = Math.min(redactState.startY, curY);
        const width = Math.abs(redactState.startX - curX);
        const height = Math.abs(redactState.startY - curY);
        
        redactState.currentRect = { x, y, width, height };
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = "rgba(239, 68, 68, 0.15)";
        ctx.fillRect(x, y, width, height);
        
        ctx.strokeStyle = "rgb(239, 68, 68)";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(x, y, width, height);
    });
    
    canvas.addEventListener("mouseup", function(e) {
        if (!redactState.isSelecting) return;
        redactState.isSelecting = false;
        
        if (redactState.currentRect && redactState.currentRect.width > 2 && redactState.currentRect.height > 2) {
            updateRedactUIState();
        } else {
            redactState.currentRect = null;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            updateRedactUIState();
        }
    });
});

// =============================================================
// APPLICATION VERSION MANAGEMENT & UPDATE CHECKER
// =============================================================
const CURRENT_VERSION = "1.0.0";
let updateDownloadUrl = "";

async function checkApplicationUpdate() {
    try {
        const res = await fetch("/api/check-version");
        if (res.ok) {
            const data = await res.json();
            const latest = data.latest_version;
            const mandatory = data.mandatory;
            updateDownloadUrl = data.download_url || "https://pdf2tally-backend.onrender.com/download";
            const notes = data.release_notes || "No release notes available.";
            
            if (latest && isNewerVersion(CURRENT_VERSION, latest)) {
                // Update text elements in the modal
                const verSpan = document.getElementById("new-version-number");
                if (verSpan) verSpan.textContent = latest;
                
                const notesDiv = document.getElementById("release-notes-content");
                if (notesDiv) notesDiv.textContent = notes;
                
                // Show modal
                const modal = document.getElementById("update-modal");
                if (modal) {
                    modal.classList.remove("hidden");
                }
                
                // If it is a mandatory update, hide the "Later" button so they are forced to update
                const laterBtn = document.getElementById("btn-update-later");
                if (laterBtn) {
                    if (mandatory) {
                        laterBtn.style.display = "none";
                    } else {
                        laterBtn.style.display = "block";
                    }
                }
            }
        }
    } catch (e) {
        console.error("Update check failed:", e);
    }
}

function isNewerVersion(current, latest) {
    const cParts = current.split('.').map(Number);
    const lParts = latest.split('.').map(Number);
    for (let i = 0; i < Math.max(cParts.length, lParts.length); i++) {
        const cVal = cParts[i] || 0;
        const lVal = lParts[i] || 0;
        if (lVal > cVal) return true;
        if (cVal > lVal) return false;
    }
    return false;
}

function downloadUpdate() {
    if (updateDownloadUrl) {
        window.open(updateDownloadUrl, "_blank");
    } else {
        window.open("https://pdf2tally-backend.onrender.com/", "_blank");
    }
}

function closeUpdateModal() {
    const modal = document.getElementById("update-modal");
    if (modal) {
        modal.classList.add("hidden");
    }
}

// ==========================================
// HELP & SUPPORT DESK FRONTEND CONTROLLER
// ==========================================
let supportSelectedFiles = [];

function switchSupportSubTab(subTabId) {
    document.querySelectorAll("#support-tab .btn-subtab").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById("btn-subtab-support-" + subTabId);
    if (activeBtn) activeBtn.classList.add("active");
    
    document.querySelectorAll(".support-subtab-pane").forEach(pane => pane.classList.add("hidden"));
    const activePane = document.getElementById("pane-support-" + subTabId);
    if (activePane) activePane.classList.remove("hidden");
}

function updateSupportTabDetails() {
    const signatureBadge = document.getElementById("support-machine-sig");
    if (signatureBadge) {
        signatureBadge.textContent = state.signature || "UNKNOWN";
    }
}

function handleSupportFilesSelect(event) {
    const files = Array.from(event.target.files);
    
    // Add newly selected files to our global supportSelectedFiles array (preventing duplicates by file name + size)
    files.forEach(newFile => {
        const isDuplicate = supportSelectedFiles.some(existing => existing.name === newFile.name && existing.size === newFile.size);
        if (!isDuplicate) {
            supportSelectedFiles.push(newFile);
        }
    });
    
    // Reset file input value so the same files can be re-selected if removed
    event.target.value = "";
    
    updateAttachmentsList();
}

function updateAttachmentsList() {
    const label = document.getElementById("support-files-label");
    const container = document.getElementById("support-files-list");
    if (!container) return;
    
    container.innerHTML = "";
    
    if (supportSelectedFiles.length > 0) {
        label.textContent = `${supportSelectedFiles.length} file(s) selected:`;
        
        supportSelectedFiles.forEach((file, index) => {
            const pill = document.createElement("div");
            pill.style.cssText = "display: flex; align-items: center; gap: 6px; background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.2); padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; color: #fff; max-width: 250px;";
            
            const nameSpan = document.createElement("span");
            nameSpan.textContent = file.name;
            nameSpan.style.cssText = "text-overflow: ellipsis; overflow: hidden; white-space: nowrap;";
            
            const sizeSpan = document.createElement("span");
            sizeSpan.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
            sizeSpan.style.cssText = "color: var(--text-muted); font-size: 0.7rem; flex-shrink: 0;";
            
            const removeBtn = document.createElement("span");
            removeBtn.innerHTML = "&times;";
            removeBtn.style.cssText = "cursor: pointer; font-size: 1rem; color: #ef4444; font-weight: bold; padding-left: 2px; line-height: 1;";
            removeBtn.onclick = () => {
                supportSelectedFiles.splice(index, 1);
                updateAttachmentsList();
            };
            
            pill.appendChild(nameSpan);
            pill.appendChild(sizeSpan);
            pill.appendChild(removeBtn);
            container.appendChild(pill);
        });
    } else {
        label.textContent = "No files selected";
    }
}

async function submitSupportRequest(event) {
    event.preventDefault();
    
    const email = document.getElementById("support-email").value.trim();
    const phone = document.getElementById("support-phone").value.trim();
    const subjectType = document.getElementById("support-subject-type").value;
    const message = document.getElementById("support-message").value.trim();
    
    const btnSubmit = document.getElementById("btn-submit-support");
    const btnText = document.getElementById("support-btn-text");
    const spinner = document.getElementById("support-spinner");
    const statusMsg = document.getElementById("support-status-message");
    
    if (!email || !phone || !subjectType || !message) {
        alert("Please fill all required fields.");
        return;
    }
    
    // UI Loading State
    btnSubmit.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Sending Request...";
    statusMsg.classList.add("hidden");
    
    try {
        // Read selected files into Base64 format
        const attachments = [];
        let totalSize = 0;
        
        for (const file of supportSelectedFiles) {
            totalSize += file.size;
            if (totalSize > 5 * 1024 * 1024) { // 5MB total size limit
                throw new Error("Total attachment size exceeds the 5MB limit. Please select smaller files.");
            }
            
            const base64Content = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result.split(",")[1]);
                reader.onerror = (e) => reject(e);
            });
            
            attachments.push({
                filename: file.name,
                content: base64Content
            });
        }
        
        // POST to local Flask proxy
        const response = await fetch("/api/submit-support", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: "Customer", // Manual input details
                email: email,
                phone: phone,
                subject_type: subjectType,
                message: message,
                signature: state.signature,
                attachments: attachments
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            statusMsg.textContent = "✅ Support request submitted successfully! We will contact you soon.";
            statusMsg.className = "alert alert-success";
            statusMsg.classList.remove("hidden");
            
            // Clear form
            document.getElementById("support-request-form").reset();
            supportSelectedFiles = [];
            updateAttachmentsList();
        } else {
            statusMsg.textContent = "❌ Error: " + (data.message || "Failed to submit support request.");
            statusMsg.className = "alert alert-danger";
            statusMsg.classList.remove("hidden");
        }
    } catch (err) {
        console.error("Support submission failed:", err);
        statusMsg.textContent = "❌ Submission failed: " + err.message;
        statusMsg.className = "alert alert-danger";
        statusMsg.classList.remove("hidden");
    } finally {
        btnSubmit.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Submit Support Request";
    }
}

