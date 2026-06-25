import sys
import os
import time
import subprocess
import requests
import threading

def run_test_suite():
    # 1. Start the cloud backend locally on a test port (e.g. 8000)
    # We will run backend/app.py as a subprocess.
    print("[TEST] Starting local instance of cloud licensing backend...")
    
    # Ensure any existing database.json in backend directory is cleared to start fresh
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    db_file = os.path.join(backend_dir, "database.json")
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("[TEST] Cleaned database.json for a clean test run.")
        except Exception as e:
            print(f"[TEST] Warning: Could not remove database.json: {e}")

    # Start the backend app as a subprocess
    backend_process = subprocess.Popen(
        [sys.executable, os.path.join(backend_dir, "app.py")],
        env={**os.environ, "FLASK_SECRET_KEY": "TEST_SECRET_2026"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give the backend server a moment to start up
    time.sleep(3)
    
    base_url = "http://127.0.0.1:8000"
    
    try:
        # Check if backend responds
        print("[TEST] Pinging verification endpoint...")
        resp = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-SIG-1234"})
        assert resp.status_code == 200, "Verify endpoint failed to start."
        verify_data = resp.json()
        assert verify_data["activated"] is False, "New signature should not be activated."
        print("[PASS] Verification endpoint checked. Unregistered signature successfully blocked.")
        
        # 2. Test Admin Login
        print("[TEST] Logging in as Master Admin...")
        login_resp = requests.post(f"{base_url}/api/cloud/admin/login", json={
            "email": "admin@pdf2tally.com",
            "admin_key": "ADM-SUPER-SECURE-2026",
            "password": "AdminPassword2026!"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        login_data = login_resp.json()
        assert login_data["success"] is True
        token = login_data["token"]
        print("[PASS] Master Admin authenticated. Token retrieved.")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Test Register New User License
        print("[TEST] Registering new USER signature (TEST-USER-1)...")
        reg_resp = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-USER-1",
            "role": "USER",
            "duration": "1hour" if "1hour" == "" else "1month" # 1month duration
        }, headers=headers)
        assert reg_resp.status_code == 200, f"Failed to register signature: {reg_resp.text}"
        print("[PASS] Signature TEST-USER-1 registered as USER.")
        
        # 4. Test Signature Uniqueness Check
        print("[TEST] Attempting duplicate signature registration...")
        dup_resp = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-USER-1",
            "role": "USER",
            "duration": "1month"
        }, headers=headers)
        assert dup_resp.status_code == 409, f"Uniqueness verification failed: {dup_resp.status_code}"
        print("[PASS] Duplicate registration rejected successfully (HTTP 409).")
        
        # 5. Verify the license is active
        print("[TEST] Verifying registered license...")
        verify_resp = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-USER-1"})
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["activated"] is True
        assert verify_data["role"] == "USER"
        print("[PASS] Client machine verification succeeded. Access granted.")
        
        # 6. Test Register a Co-Admin
        print("[TEST] Registering a CO-ADMIN (TEST-COADMIN-1)...")
        coadmin_reg = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-COADMIN-1",
            "role": "CO-ADMIN",
            "duration": "lifetime"
        }, headers=headers)
        assert coadmin_reg.status_code == 200, f"Failed to register co-admin: {coadmin_reg.text}"
        print("[PASS] Co-Admin device signature registered.")
        
        # 7. Test Co-Admin authentication and Co-Admin creation restrictions
        coadmin_headers = {"X-Machine-Signature": "TEST-COADMIN-1"}
        
        # Co-Admin registering a standard User (Should PASS)
        print("[TEST] Co-Admin registering a USER (TEST-USER-2)...")
        coadmin_user_reg = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-USER-2",
            "role": "USER",
            "duration": "1week"
        }, headers=coadmin_headers)
        assert coadmin_user_reg.status_code == 200, f"Co-Admin failed to register user: {coadmin_user_reg.text}"
        print("[PASS] Co-Admin successfully registered standard user.")
        
        # Co-Admin attempting to register another Co-Admin (Should FAIL)
        print("[TEST] Co-Admin attempting to register another Co-Admin (TEST-COADMIN-2)...")
        coadmin_coadmin_reg = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-COADMIN-2",
            "role": "CO-ADMIN",
            "duration": "lifetime"
        }, headers=coadmin_headers)
        assert coadmin_coadmin_reg.status_code == 403, f"Co-Admin registered co-admin! HTTP {coadmin_coadmin_reg.status_code}"
        print("[PASS] Co-Admin creation restriction enforced successfully (HTTP 403).")
        
        # 8. Test License Deactivation
        print("[TEST] Deactivating USER license (TEST-USER-1)...")
        deact_resp = requests.post(f"{base_url}/api/cloud/admin/deactivate", json={
            "machine_signature": "TEST-USER-1"
        }, headers=headers)
        assert deact_resp.status_code == 200
        print("[PASS] USER license deactivated.")
        
        # Verify deactivated license fails verify check
        print("[TEST] Verifying deactivated signature...")
        verify_resp_2 = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-USER-1"})
        verify_data_2 = verify_resp_2.json()
        assert verify_data_2["activated"] is False
        print("[PASS] Deactivated machine signature blocked from verification.")
        
        print("\n[SUCCESS] ALL LICENSING LOGIC CHECKS PASSED SUCCESSFULLY!")
        
    except AssertionError as err:
        print(f"\n❌ TEST SUITE FAILURE: {err}")
    finally:
        print("[TEST] Cleaning up backend subprocess...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        print("[TEST] Subprocess terminated.")

if __name__ == "__main__":
    run_test_suite()
