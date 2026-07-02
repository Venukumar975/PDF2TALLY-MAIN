import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class License(db.Model):
    __tablename__ = 'licenses'
    
    license_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_key = db.Column(db.String(100), unique=True, nullable=False)
    machine_hash = db.Column(db.String(100), nullable=True)
    plan_name = db.Column(db.String(50), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Active, Expired, Revoked
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship to user
    users = db.relationship('User', backref='license', lazy=True)

    def to_dict(self):
        return {
            "license_id": self.license_id,
            "license_key": self.license_key,
            "machine_hash": self.machine_hash,
            "plan_name": self.plan_name,
            "duration_days": self.duration_days,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "activated_at": self.activated_at.strftime("%Y-%m-%d %H:%M:%S") if self.activated_at else None,
            "expires_at": self.expires_at.strftime("%Y-%m-%d %H:%M:%S") if self.expires_at else None
        }

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    machine_hash = db.Column(db.String(100), nullable=True)
    license_id = db.Column(db.String(50), db.ForeignKey('licenses.license_id'), nullable=True)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone_number": self.phone_number,
            "machine_hash": self.machine_hash,
            "license_id": self.license_id,
            "registered_at": self.registered_at.strftime("%Y-%m-%d %H:%M:%S") if self.registered_at else None,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None
        }

class Admin(db.Model):
    __tablename__ = 'admins'
    
    admin_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='ADMIN') # ADMIN, CO-ADMIN
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "admin_id": self.admin_id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active
        }

class RenewalRequest(db.Model):
    __tablename__ = 'renewal_requests'
    
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_id = db.Column(db.String(50), db.ForeignKey('licenses.license_id'), nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Approved, Rejected

    # Relationship back to license
    license = db.relationship('License', backref=db.backref('renewal_requests', cascade='all, delete-orphan', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "license_id": self.license_id,
            "requested_at": self.requested_at.strftime("%Y-%m-%d %H:%M:%S") if self.requested_at else None,
            "status": self.status
        }

