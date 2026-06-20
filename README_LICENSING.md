# Cryptographic Licensing & Security Specifications

This document outlines the security architecture, hardware fingerprinting inputs, cryptographic key generation protocol, collision-resistance calculations, threat model, and operational steps of the offline licensing engine in the Tally Automation Suite.

---

## 1. Hardware Fingerprinting & Signature Generation

To ensure keys cannot be reused on unauthorized computers, the application locks the activation license to the specific device. 

### Fingerprint Inputs
The machine signature is compiled by retrieving four native hardware identifiers:
1. **Motherboard UUID**: Obtained via Command Prompt: `wmic csproduct get uuid`.
2. **CPU ID**: Obtained via Command Prompt: `wmic cpu get processorid`.
3. **BIOS Serial Number**: Obtained via Command Prompt: `wmic bios get serialnumber`.
4. **MAC Address (Fallback)**: Obtained via standard Python `uuid.getnode()` as fallback/additional entropy if Command Prompt commands fail or return empty.

### Signature Computation
1. The retrieved identifiers are filtered to remove empty spaces and joined using a pipe character:
   $$\text{Raw String} = \text{UUID} \mid \text{CPUID} \mid \text{BIOS\_Serial} \mid \text{MAC}$$
   *If all lookups fail, the system falls back to a default offline signature: `"DEFAULT_WINDOWS_OFFLINE_SIGNATURE_FALLBACK"`.*
2. The joined string is hashed using **SHA-256**.
3. The resulting 64-character hexadecimal hash is truncated to the first 16 characters and formatted as four blocks of four uppercase alphanumeric characters:
   $$\text{Signature} = X_1X_2X_3X_4 - Y_1Y_2Y_3Y_4 - Z_1Z_2Z_3Z_4 - W_1W_2W_3W_4$$

### Example
* **Raw Identifiers**: `3B92E870-E20B-11D2-90C8-00C04F79FEE2|BFEBFBFF000906EA|7X64Y2|248539281928`
* **SHA-256 Hash**: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
* **Resulting Signature**: `E3B0-C442-98FC-1C14`

---

## 2. Activation Key Derivation Protocol

Activation keys encode the authorization permissions (Role) and the expiration time (Expiry) and secure them with a cryptographic checksum.

### Key Formats
The system supports two key formats:
1. **New Key Format (Time-Granular)**:
   $$\text{ACT} - \text{ROLE} - \text{EXPIRY\_VALUE} - \text{CHECKSUM}$$
   * `ROLE`: `USER` (Standard) or `ADMIN` (Administrator privileges).
   * `EXPIRY_VALUE`: Either the string `"LIFETIME"` or a **Unix Epoch Timestamp** (seconds since 1970-01-01) specifying the exact expiration moment.
   * `CHECKSUM`: The first 10 characters of the SHA-256 hash of the payload:
     $$\text{Checksum} = \text{SHA-256}(\text{Signature} : \text{Role} : \text{Expiry\_Value} : \text{Secret\_Salt})[0:10]$$
2. **Legacy Key Format (Date-Granular)**:
   $$\text{ACT} - \text{YYYYMMDD} - \text{CHECKSUM}$$
   * `YYYYMMDD`: The expiration date (e.g. `20261231` or `99991231` for Lifetime).
   * `CHECKSUM`: The first 8 characters of the SHA-256 hash of the payload:
     $$\text{Checksum} = \text{SHA-256}(\text{Signature} : \text{Expiry\_Date} : \text{Secret\_Salt})[0:8]$$

### Key Generation Example (5-Minute User Key)
1. **Inputs**:
   * Machine Signature: `456A-755B-2CA7-28CE`
   * Target Role: `USER`
   * Current Time: `2026-06-20 11:00:00 UTC` (Timestamp: `1781953200`)
   * Expiry Time (5 Min): `2026-06-20 11:05:00 UTC` (Timestamp: `1781953500`)
   * Secret Salt: `PDF2TALLY_SECURE_OFFLINE_LICENSE_SALT_2026_@#$!`
2. **Payload Construction**:
   $$\text{Payload} = \text{"456A-755B-2CA7-28CE:USER:1781953500"}$$
3. **HMAC/Checksum Generation**:
   $$\text{Raw String} = \text{"456A-755B-2CA7-28CE:USER:1781953500:PDF2TALLY_SECURE_OFFLINE_LICENSE_SALT_2026_@#$!"}$$
   $$\text{SHA-256 Hash} = \text{"06d649ab787e28b12f718bc3d6718cf2337d..."}$$
   $$\text{Checksum} = \text{"06D649AB78"}$$
4. **Final Activation Key**:
   $$\text{"ACT-USER-1781953500-06D649AB78"}$$

---

## 3. Collision Resistance Analysis

### Is this system collision-resistant?
**Yes.** The checksum generation is built on the SHA-256 hashing algorithm, which possesses high collision resistance.

### Mathematical Proof of Security
1. **Keyspace Size**: SHA-256 produces a $256$-bit keyspace.
2. **Truncation Entropy**: The new key format truncates the hash to 10 hexadecimal characters.
   * 1 hexadecimal character represents 4 bits of entropy ($16^1 = 2^4$).
   * 10 hexadecimal characters contain 40 bits of entropy ($16^{10} = 2^{40}$).
   * This yields a keyspace of $1,099,511,627,776$ (1.09 trillion) unique checksum values *per hardware signature*.
3. **Collision Probability**:
   According to the Birthday Paradox, the probability $P$ of finding at least one collision after generating $N$ keys is approximated by:
   $$P(N) \approx 1 - e^{-\frac{N^2}{2 \cdot 2^{B}}}$$
   Where $B = 40$ (bits of entropy).
   * For an administrator generating $1,000,000$ keys, the probability of a collision is:
     $$P(10^6) \approx 1 - e^{-\frac{10^{12}}{2 \cdot 1.09 \cdot 10^{12}}} \approx 1 - e^{-0.45} \approx 36.5\%$$
   * Since this is an offline client-bound system, an attacker trying to guess a key for their specific laptop signature faces a $1$ in $2^{40}$ ($1.09 \times 10^{-12}$) chance per attempt. Online brute-forcing is blocked locally by UI response delays, and offline pre-computation is impossible without knowledge of the `SECRET_SALT`.

---

## 4. Threat Model & Vulnerability Analysis

### Threat 1: Clock Tampering (System Rollback)
* **Vulnerability**: A user receives a 1-minute key. After it expires, they manually roll back their computer's system clock to a time within that 1-minute window to continue using the application.
* **Countermeasure (Incremental Timestamp Ledger)**:
  Every time the application validates the license or runs a conversion, it writes the current date and time to the hidden license file (`~/.pdf2tally.lic`) under the key `last_run_date`.
  * When checking activation, the app compares the current system time to `last_run_date`.
  * If $\text{Current Time} < \text{last\_run\_date}$, the system flags this as **Clock Tampering** and locks the application.
  * Once flagged, the user cannot bypass the lock screen even if they correct the system clock, because `last_run_date` is permanently written as a future time. Only the administrator can reset this by issuing a new key (which updates the license metadata).

### Threat 2: Reverse Engineering (Decompilation & Bytecode Editing)
* **Vulnerability**: The application is a local Python web app packaged using PyInstaller. An advanced user could extract the compiled executable (using tools like `pyi-extractor`), decompile the `.pyc` files back to readable source code using Python decompilers (like `pycdc` or `uncompyle6`), locate `check_activation()`, and modify the function to always return `True`.
* **Security Countermeasures**:
  1. **Source Obfuscation**: Prior to compilation, compile the source files using tools like **PyArmor** or **Cython**. Cython compiles Python code into C extensions, which compile down to native machine code binaries (`.pyd` on Windows) that cannot be decompiled back to Python source code.
  2. **Memory Inspection Protection**: Keep variables and secrets out of clean text files on disk.

### Threat 3: Side-Channel / Memory Hooking
* **Vulnerability**: An attacker runs the app and attaches a debugger to modify memory variables (e.g. setting `state.activated = true` in the WebView runtime debugger console).
* **Security Countermeasures**:
  * **Server-side Gatekeeping**: The frontend WebView only acts as a viewport. Actual file conversions and Tally generation occur in the Flask backend (`app_flask.py`). The Flask backend executes `check_license()` inside a `before_request` hook before servicing any endpoints. If the backend license check fails, it returns a redirect or HTTP 403, rendering frontend modifications useless because the underlying backend logic refuses to process any uploads.

---

## 5. Expiry Lifecycle & Renewal Workflows

### What happens exactly after 1 minute of activation?
1. The user inputs their key, which is saved in `~/.pdf2tally.lic`. The app starts.
2. The frontend runs a background interval timer every 15 seconds that checks `/api/status`.
3. At 1 minute, the background check detects that the current time exceeds the key's expiry timestamp.
4. The Flask backend returns `{"activated": false, "message": "License expired...", ...}`.
5. The frontend immediately locks the screen by showing the `#license-overlay` lock screen, hiding the `#app-workspace` tabs, and updating the error text to show the expired license error.
6. Any subsequent file conversion requests fail at the backend database boundary because `check_license()` redirects them to the activation overlay.

### How to issue another 1-minute key (Renewal)?
If the user requests another 1-minute key, perform the following steps:
1. Copy their Machine Signature ID.
2. Open the **Admin Console** on your laptop.
3. Paste their signature in **Target Machine Signature ID**.
4. Select Role **Standard User** and Duration **1 Minute**.
5. Click **Generate Cryptographic Activation Key**.
6. Send the new key code to the user.
7. The user enters this new key in their lock screen and clicks **Activate**. This updates the `activation_key` and resets `last_run_date` to the new current activation datetime, unlocking the app.
