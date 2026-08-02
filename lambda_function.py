import json
import uuid
from datetime import datetime, timezone, timedelta
import string
import random
import os
import pymysql

# Database connection URL config (fallback to your credentials)
DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    DB_URL = "mysql+pymysql://admin:Venukumar975@pdf2tally3-database-1.cvyqa0y8gjdn.eu-north-1.rds.amazonaws.com:3306/pdf2tally"

def parse_db_url(url):
    clean_url = url.replace("mysql+pymysql://", "").replace("mysql://", "")
    auth, host_db = clean_url.split("@")
    user, password = auth.split(":")
    if "/" in host_db:
        host_port, database = host_db.split("/")
    else:
        host_port = host_db
        database = "pdf2tally"
        
    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host = host_port
        port = 3306
    return host, user, password, database, port

HOST, USER, PASSWORD, DATABASE, PORT = parse_db_url(DB_URL)

def get_connection():
    return pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        port=PORT,
        ssl={"ssl_mode": "REQUIRED"}
    )

def lambda_handler(event, context):
    # CORS headers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }
    
    # Handle preflight options request
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }
        
    raw_path = event.get("rawPath", "")
    if not raw_path:
        raw_path = event.get("path", "")
        
    body_str = event.get("body", "")
    if event.get("isBase64Encoded", False):
        import base64
        body_str = base64.b64decode(body_str).decode("utf-8")
        
    data = {}
    if body_str:
        try:
            data = json.loads(body_str)
        except Exception:
            pass
            
    conn = None
    try:
        conn = get_connection()
        if raw_path == "/register-request" or raw_path.endswith("/register-request"):
            return handle_register(conn, data, headers)
        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({"success": False, "message": f"Route not found: {raw_path}"})
            }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"success": False, "message": f"Server error: {str(e)}"})
        }
    finally:
        if conn and conn.open:
            conn.close()

def handle_register(conn, data, headers):
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone_number = data.get("phone_number", "").strip()
    machine_hash = data.get("machine_hash", "").strip().upper()
    
    if not full_name or not email or not phone_number or not machine_hash:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({"success": False, "message": "All fields are required."})
        }
        
    with conn.cursor() as cursor:
        # Check if machine already has any active or expired license
        cursor.execute("SELECT status, license_key FROM licenses WHERE machine_hash=%s", (machine_hash,))
        row = cursor.fetchone()
        if row:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "success": False, 
                    "message": f"This machine is already associated with a license key (Status: {row[0]})."
                })
            }
            
        # Generate TRIAL key
        chars = string.ascii_uppercase + string.digits
        block1 = ''.join(random.choices(chars, k=4))
        block2 = ''.join(random.choices(chars, k=4))
        block3 = ''.join(random.choices(chars, k=4))
        license_key = f"TRIAL-{block1}-{block2}-{block3}"
        
        license_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_at = now + timedelta(days=7)
        
        # 1. Insert License record with plan_name='trial'
        cursor.execute(
            """INSERT INTO licenses 
               (license_id, license_key, machine_hash, plan_name, duration_days, status, created_at, activated_at, expires_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (license_id, license_key, machine_hash, 'trial', 7, 'Active', now, now, expires_at)
        )
        
        # 2. Insert User record linked to the license
        user_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO users 
               (user_id, full_name, email, phone_number, machine_hash, license_id, registered_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, full_name, email, phone_number, machine_hash, license_id, now)
        )
        
        conn.commit()
        
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "success": True,
                "message": f"Free 7-Day Trial activated!\n\nYour Trial License Key: {license_key}\n\nCopy this key, switch to the 'Login Console' tab, paste it, and log in."
            })
        }
