import os
import sys
import unittest
import json
import time
from datetime import datetime, timedelta

# Add backend directory to path at index 0 to avoid importing root app.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import app, db, User, License, Admin

class TestLicensingFlow(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            # Seed default admin if not already present
            existing = Admin.query.filter_by(username="admin").first()
            if not existing:
                db.session.add(Admin(
                    admin_id="test-admin-id",
                    username="admin",
                    password_hash="fake-hash",
                    role="ADMIN",
                    is_active=True
                ))
                db.session.commit()
            
    def tearDown(self):
        with app.app_context():
            db.session.rollback()
            db.session.remove()
            db.drop_all()

    def test_complete_licensing_lifecycle(self):
        # 1. Customer registration request
        reg_response = self.client.post('/register-request', json={
            "full_name": "Auditor Rama",
            "email": "rama@auditing.com",
            "phone_number": "9998887770",
            "machine_hash": "MAC-HASH-RAMA-1234"
        })
        self.assertEqual(reg_response.status_code, 200)
        reg_data = json.loads(reg_response.data)
        self.assertTrue(reg_data["success"])
        self.assertIn("Waiting for Administrator", reg_data["message"])

        # Verify user is in database
        with app.app_context():
            user = User.query.filter_by(email="rama@auditing.com").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.full_name, "Auditor Rama")
            self.assertIsNone(user.license_id)
            user_id = user.user_id

        # 2. Direct database license creation (simulating standalone admin approval)
        license_key = "LIC-RAMA-TEST-KEY1"
        with app.app_context():
            user = User.query.filter_by(email="rama@auditing.com").first()
            new_lic = License(
                license_id="rama-license-id",
                license_key=license_key,
                plan_name="Monthly",
                duration_days=30,
                status='Pending',
                created_at=datetime.utcnow()
            )
            db.session.add(new_lic)
            db.session.flush()
            user.license_id = new_lic.license_id
            db.session.commit()

        # Verify license is generated in database
        with app.app_context():
            lic = License.query.filter_by(license_key=license_key).first()
            self.assertIsNotNone(lic)
            self.assertEqual(lic.status, 'Pending') # Starts as pending activation
            self.assertEqual(lic.duration_days, 30)

        # 4. Client Activation
        # Client activation calls POST /activate-license
        activate_response = self.client.post('/activate-license', json={
            "license_key": license_key,
            "machine_hash": "MAC-HASH-RAMA-1234"
        })
        self.assertEqual(activate_response.status_code, 200)
        act_data = json.loads(activate_response.data)
        self.assertTrue(act_data["success"])
        self.assertTrue(act_data["activated"])
        license_id = act_data["license_id"]

        # Verify license is active in database
        with app.app_context():
            lic = License.query.filter_by(license_key=license_key).first()
            self.assertEqual(lic.status, 'Active')
            self.assertEqual(lic.machine_hash, "MAC-HASH-RAMA-1234")
            self.assertIsNotNone(lic.activated_at)
            self.assertIsNotNone(lic.expires_at)

        # 5. Client Auto-Login check
        # Client auto-login calls POST /login
        login_response = self.client.post('/login', json={
            "license_id": license_id,
            "machine_hash": "MAC-HASH-RAMA-1234"
        })
        self.assertEqual(login_response.status_code, 200)
        login_data = json.loads(login_response.data)
        self.assertTrue(login_data["authorized"])
        self.assertIn("Authentication successful", login_data["message"])

        # 6. Restore License Flow
        # If client clears local cache (.pdf2tally.lic deleted), they restore using email and machine hash
        restore_response = self.client.post('/restore-license', json={
            "email": "rama@auditing.com",
            "machine_hash": "MAC-HASH-RAMA-1234"
        })
        self.assertEqual(restore_response.status_code, 200)
        restore_data = json.loads(restore_response.data)
        self.assertTrue(restore_data["success"])
        self.assertEqual(restore_data["license_key"], license_key)
        self.assertEqual(restore_data["license_id"], license_id)

    def test_minute_based_expiry(self):
        # Register and Approve request with 1min plan
        with app.app_context():
            new_user = User(
                user_id="user-1min",
                full_name="Quick Tester",
                email="test@quick.com",
                phone_number="12345"
            )
            db.session.add(new_user)
            db.session.commit()
            user_id = new_user.user_id

        # Approve request with 1min plan in DB
        license_key = "LIC-1MIN-TEST-KEY"
        with app.app_context():
            user = User.query.get(user_id)
            new_lic = License(
                license_id="1min-license-id",
                license_key=license_key,
                plan_name="1min",
                duration_days=0,
                status='Pending',
                created_at=datetime.utcnow()
            )
            db.session.add(new_lic)
            db.session.flush()
            user.license_id = new_lic.license_id
            db.session.commit()

        # Activate
        activate_response = self.client.post('/activate-license', json={
            "license_key": license_key,
            "machine_hash": "MAC-1MIN"
        })
        self.assertEqual(activate_response.status_code, 200)
        act_data = json.loads(activate_response.data)
        self.assertTrue(act_data["activated"])
        self.assertLessEqual(act_data["seconds_remaining"], 60)
        self.assertGreater(act_data["seconds_remaining"], 50)

if __name__ == '__main__':
    unittest.main()
