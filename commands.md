# Tally Automation Suite: Workflow & Build Reference Guide

This document outlines the workflows for administrators, standard users, and development operations (building and cleaning).

---

## 🔑 Administrator Workflow: Generating Activation Keys

Follow these steps to generate activation keys for users or other administrators:

1. **Obtain Client Signature**:
   * Ask the user to copy their unique **Machine Signature ID** (visible on their lock screen overlay or the "License & Status" tab) and send it to you.

2. **Access the Admin Console**:
   * Launch the application on the Master Admin laptop (this machine: `6232-5DFF-EA95-C2F3`). The **Admin Console** tab is automatically visible.
   * *Note: If accessing from another machine, activate that machine with an Admin-role key first.*

3. **Enter Licensing Parameters**:
   * **Target Signature ID**: Paste the client's copied machine signature.
   * **Role Permission**: Select **Standard User** (access to conversions and lexicon) or **Administrator** (access to conversion tools plus the Admin Console).
   * **Duration**: Select the desired validity period:
     * `1 Minute` (temporary test key)
     * `5 Minutes` (temporary test key)
     * `1 Day`
     * `1 Week`
     * `1 Month`
     * `4 Months`
     * `1 Year`
     * `Lifetime` (unlimited offline access)

4. **Generate the Key**:
   * Click the **Generate Activation Key** button.
   * The app will output a cryptographic key format: `ACT-{ROLE}-{EXPIRY_TIMESTAMP_OR_LIFETIME}-{CHECKSUM}`.

5. **Deliver the Key**:
   * Click **Copy Key** and send the key code to the user.

---

## 💻 Standard User Workflow: Operating the Application

Follow these steps to activate and use the conversion pipelines:

1. **Activate the Software**:
   * Paste the activation key into the input field on the lock screen.
   * Click **Activate Software** to unlock the workspace.

2. **Ingest and Convert Bank Statements**:
   * Navigate to the **Bank Statement** tab.
   * Select the **Bank Profile** (State Bank of India or Bank of Baroda).
   * Select the **Ingestion Strategy**:
     * **Whole Document**: Processes the entire document.
     * **First Chunk**: Processes the first segment.
     * **Continuation Chunk**: Allows timeline slicing (processes items on/after a specific boundary date).
   * Drag and drop the statement PDF into the ingestion dropzone.
   * Customize the Tally ledger naming fields (e.g., target debit and credit accounts).
   * Click **Execute Conversion Chain**.

3. **Ingest and Transliterate Cash Receipts**:
   * Navigate to the **Ashramam Ledger** tab.
   * Choose a boundary cut-off date and enter Tally ledger names.
   * Upload the receipts Excel sheet (`.xlsx`/`.csv`).
   * Click **Execute Receipts Ingestion**.
   * Under the **Translation & Lexicon Review Desk**, look at **Critical System Flags** or **Complete Directory Review** to see Telugu-to-English name transliterations.
   * Edit spelling corrections directly inside the input boxes.
   * Click **Commit Lexicon Alterations & Reprocess Inflow** to update the dictionary and re-parse.

---

## 🛠️ Development Operations: Build and Clean Commands

Use these terminal commands in the project root directory on Windows:

### 1. Run the Development Server
To run the app in debug/development mode without packaging:
* **Command Prompt / PowerShell**:
  ```powershell
  .\venv\Scripts\python app_flask.py
  ```

### 2. Clean Previous Build Artifacts
Before creating a new build, clean the cache and old compilation directories to avoid packaging obsolete code:
* **PowerShell**:
  ```powershell
  # Remove build, dist, and spec file
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist
  Remove-Item -Force -ErrorAction SilentlyContinue pdf2tallyXML.spec
  ```
* **Command Prompt (cmd)**:
  ```cmd
  :: Remove directories and files
  rmdir /s /q build 2>nul
  rmdir /s /q dist 2>nul
  del /f /q pdf2tallyXML.spec 2>nul
  ```

### 3. Build/Package the Standalone Executable
Build the app into a single executable located inside the `dist` directory:
* **Command Prompt / PowerShell**:
  ```powershell
  .\venv\Scripts\python build_app.py
  ```
  *The compiled executable will be placed in `dist/pdf2tallyXML/pdf2tallyXML.exe`.*
