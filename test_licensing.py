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
        assert verify_data.get("pending_approval") is False, "New signature should not be pending."
        print("[PASS] Verification endpoint checked. Unregistered signature successfully blocked.")
        
        # 2. Test Admin Login
        print("[TEST] Logging in as Master Admin...")
        login_resp = requests.post(f"{base_url}/api/cloud/admin/login", json={
            "email": "pichikavenui5@gmail.com",
            "admin_key": "ADM-7F9X-23QK-91ZT",
            "password": "p@55w0rD!_Xy9#LkT"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        login_data = login_resp.json()
        assert login_data["success"] is True
        token = login_data["token"]
        print("[PASS] Master Admin authenticated. Token retrieved.")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2.1 Test Registration Request (Keyless Queue Flow)
        print("[TEST] Sending registration request for TEST-REQ-1...")
        req_resp = requests.post(f"{base_url}/api/cloud/register_request", json={"machine_signature": "TEST-REQ-1"})
        assert req_resp.status_code == 200
        assert req_resp.json()["success"] is True
        assert "Waiting for" in req_resp.json()["message"]
        print("[PASS] Registration request successfully created.")
        
        # 2.2 Verify status of TEST-REQ-1 shows pending
        verify_req_resp = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-REQ-1"})
        assert verify_req_resp.status_code == 200
        verify_req_data = verify_req_resp.json()
        assert verify_req_data["activated"] is False
        assert verify_req_data.get("pending_approval") is True
        print("[PASS] Verification of pending signature TEST-REQ-1 returns pending_approval=True.")
        
        # 2.3 Fetch pending requests list
        list_reqs = requests.get(f"{base_url}/api/cloud/admin/requests", headers=headers)
        assert list_reqs.status_code == 200
        pending_list = list_reqs.json()["requests"]
        assert any(r["machine_signature"] == "TEST-REQ-1" for r in pending_list)
        print("[PASS] Pending requests list fetched and contains TEST-REQ-1.")
        
        # 2.4 Test Rejection Flow
        print("[TEST] Creating and rejecting registration request for TEST-REQ-2...")
        requests.post(f"{base_url}/api/cloud/register_request", json={"machine_signature": "TEST-REQ-2"})
        reject_resp = requests.post(f"{base_url}/api/cloud/admin/reject_request", json={"machine_signature": "TEST-REQ-2"}, headers=headers)
        assert reject_resp.status_code == 200
        
        # Verify requests list no longer contains TEST-REQ-2
        list_reqs_2 = requests.get(f"{base_url}/api/cloud/admin/requests", headers=headers)
        assert not any(r["machine_signature"] == "TEST-REQ-2" for r in list_reqs_2.json()["requests"])
        print("[PASS] Rejection flow completed and verified.")
        
        # 2.5 Approve TEST-REQ-1
        print("[TEST] Approving/registering TEST-REQ-1...")
        approve_resp = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-REQ-1",
            "role": "USER",
            "duration": "1month"
        }, headers=headers)
        assert approve_resp.status_code == 200
        
        # Verify requests list no longer contains TEST-REQ-1 (removed automatically on registration)
        list_reqs_3 = requests.get(f"{base_url}/api/cloud/admin/requests", headers=headers)
        assert not any(r["machine_signature"] == "TEST-REQ-1" for r in list_reqs_3.json()["requests"])
        print("[PASS] TEST-REQ-1 successfully registered and removed from pending requests.")
        
        # Verify TEST-REQ-1 is active
        verify_req_active = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-REQ-1"})
        assert verify_req_active.status_code == 200
        assert verify_req_active.json()["activated"] is True
        print("[PASS] TEST-REQ-1 verified active.")
        
        # 3. Test Register New User License
        print("[TEST] Registering new USER signature (TEST-USER-1)...")
        reg_resp = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-USER-1",
            "role": "USER",
            "duration": "1hour" if "1hour" == "" else "1month" # 1month duration
        }, headers=headers)
        assert reg_resp.status_code == 200, f"Failed to register signature: {reg_resp.text}"
        print("[PASS] Signature TEST-USER-1 registered as USER.")
        
        # 4. Test Signature Uniqueness Check (Reactivation / Overwrite)
        print("[TEST] Attempting duplicate signature registration (overwriting/reactivating)...")
        dup_resp = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-USER-1",
            "role": "USER",
            "duration": "1month"
        }, headers=headers)
        assert dup_resp.status_code == 200, f"Duplicate registration / reactivation failed: {dup_resp.status_code}"
        print("[PASS] Duplicate registration reactivated successfully (HTTP 200).")
        
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
        assert "deactivated" in verify_data_2["message"].lower()
        print("[PASS] Deactivated machine signature blocked from verification.")
        
        # 9. Test Deletion of License Registration
        print("[TEST] Deleting license registration (TEST-USER-1)...")
        delete_resp = requests.post(f"{base_url}/api/cloud/admin/delete", json={
            "machine_signature": "TEST-USER-1"
        }, headers=headers)
        assert delete_resp.status_code == 200, f"Failed to delete license: {delete_resp.text}"
        print("[PASS] USER license registration deleted completely.")
        
        # Verify deleted signature is completely unregistered
        verify_resp_3 = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-USER-1"})
        assert verify_resp_3.status_code == 200
        verify_data_3 = verify_resp_3.json()
        assert verify_data_3["activated"] is False
        assert "not registered" in verify_data_3["message"].lower()
        print("[PASS] Deleted signature successfully verified as unregistered.")
        
        # 10. Test Deactivated & Expired status
        print("[TEST] Registering and deactivating/expiring a license...")
        reg_temp = requests.post(f"{base_url}/api/cloud/admin/licenses", json={
            "machine_signature": "TEST-TEMP-EXPIRE",
            "role": "USER",
            "duration": "1month"
        }, headers=headers)
        assert reg_temp.status_code == 200
        
        deact_temp = requests.post(f"{base_url}/api/cloud/admin/deactivate", json={
            "machine_signature": "TEST-TEMP-EXPIRE"
        }, headers=headers)
        assert deact_temp.status_code == 200
        
        verify_temp_1 = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-TEMP-EXPIRE"})
        assert verify_temp_1.status_code == 200
        assert verify_temp_1.json()["message"] == "Device is Deactivated."
        print("[PASS] Non-expired deactivated license returns 'Device is Deactivated.'")
        
        # Manually alter database.json to backdate the expiry_time
        import json
        with open(db_file, "r", encoding="utf-8") as f:
            db_data = json.load(f)
        for lic in db_data["licenses"]:
            if lic["machine_signature"] == "TEST-TEMP-EXPIRE":
                lic["expiry_time"] = "2020-01-01 00:00:00"
                lic["is_active"] = False
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=4)
            
        verify_temp_2 = requests.post(f"{base_url}/api/cloud/verify", json={"machine_signature": "TEST-TEMP-EXPIRE"})
        assert verify_temp_2.status_code == 200
        assert verify_temp_2.json()["message"] == "Subscription expired and Device deactivated."
        print("[PASS] Expired and deactivated license returns 'Subscription expired and Device deactivated.'")
        
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
