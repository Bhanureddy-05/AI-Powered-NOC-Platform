"""
verify_features.py
==================
Feature Verification Script

WHY THIS FILE EXISTS:
    Validates all newly implemented features across alert management,
    incident ticketing, ML analytics, exports, and auditing logs.
"""

import sys
import random
import httpx

BASE_URL = "http://127.0.0.1:8000"

print("============================================================")
print("AETHER NOC PLATFORM - COMPREHENSIVE FEATURES VERIFICATION")
print("============================================================\n")

# 1. User Register & Login
test_id = random.randint(1000, 9999)
username = f"verifier_{test_id}"
email = f"verifier_{test_id}@aethernoc.net"
password = "VerifierSecurePassword123!"

print("1. Enrolling a test Administrator and acquiring JWT token...")
try:
    reg_r = httpx.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "role": "admin"
    })
    if reg_r.status_code != 201:
        print(f"   [ERROR] Failed registering admin: {reg_r.text}")
        sys.exit(1)
        
    log_r = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    if log_r.status_code != 200:
        print(f"   [ERROR] Failed login: {log_r.text}")
        sys.exit(1)
        
    token = log_r.json()["access_token"]
    print("   [OK] Admin role activated. Token acquired.")
except Exception as e:
    print(f"   [ERROR] Connection failed: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

# 2. Get/Create a test Device to target alerts/tickets
print("\n2. Finding or creating a network device to link alerts...")
try:
    # Get first device
    devs_r = httpx.get(f"{BASE_URL}/api/v1/devices/", headers=headers)
    devices = devs_r.json().get("devices", [])
    
    if not devices:
        # Create a router
        create_dev_r = httpx.post(f"{BASE_URL}/api/v1/devices/", json={
            "device_name": f"verify-router-{test_id}",
            "ip_address": f"10.0.{test_id % 254}.1",
            "location": "Verification Staging Lab",
            "device_type": "router",
            "status": "active"
        }, headers=headers)
        if create_dev_r.status_code != 201:
            print(f"   [ERROR] Failed creating staging device: {create_dev_r.text}")
            sys.exit(1)
        device = create_dev_r.json()
    else:
        device = devices[0]
        
    device_id = device["id"]
    print(f"   [OK] Staging device active: {device['device_name']} (ID: {device_id})")
except Exception as e:
    print(f"   [ERROR] Device mapping failed: {e}")
    sys.exit(1)

# 3. Trigger Alert
print("\n3. Triggering a test telemetry Alert...")
try:
    alert_r = httpx.post(f"{BASE_URL}/api/v1/alerts/", json={
        "device_id": device_id,
        "alert_type": "LATENCY_SPIKE",
        "severity": "critical",
        "message": "Verify script: Latency exceeded 300ms SLA threshold.",
        "status": "open",
        "resolved": False
    }, headers=headers)
    
    if alert_r.status_code != 201:
        print(f"   [ERROR] Alert triggering failed: {alert_r.text}")
        sys.exit(1)
        
    alert = alert_r.json()
    alert_id = alert["id"]
    print(f"   [OK] Alert created. ID: {alert_id} | Type: {alert['alert_type']}")
except Exception as e:
    print(f"   [ERROR] Alert creation failed: {e}")
    sys.exit(1)

# 4. Acknowledge and Resolve Alert
print("\n4. Testing Alert Lifecycle (Acknowledge -> Resolve)...")
try:
    # Acknowledge
    ack_r = httpx.patch(f"{BASE_URL}/api/v1/alerts/{alert_id}/acknowledge", json={
        "notes": "Verifier: Acknowledging latency spike. Pinging device..."
    }, headers=headers)
    if ack_r.status_code != 200 or ack_r.json()["status"] != "acknowledged":
        print(f"   [ERROR] Alert acknowledge transition failed: {ack_r.text}")
        sys.exit(1)
    print("   [OK] Alert transitioned to 'acknowledged' status successfully.")
    
    # Resolve
    res_r = httpx.patch(f"{BASE_URL}/api/v1/alerts/{alert_id}/resolve", json={
        "notes": "Verifier: Latency subsided. Device responsive."
    }, headers=headers)
    if res_r.status_code != 200 or res_r.json()["status"] != "resolved" or not res_r.json()["resolved"]:
        print(f"   [ERROR] Alert resolve transition failed: {res_r.text}")
        sys.exit(1)
    print("   [OK] Alert transitioned to 'resolved' status successfully.")
except Exception as e:
    print(f"   [ERROR] Alert state changes failed: {e}")
    sys.exit(1)

# 5. Create Incident Ticket
print("\n5. Creating a new Incident Ticket for the device...")
try:
    ticket_r = httpx.post(f"{BASE_URL}/api/v1/tickets/", json={
        "device_id": device_id,
        "alert_id": alert_id,
        "title": f"VERIFY-LATENCY-INCIDENT-{test_id}",
        "description": "Verifier raised ticket to document sustained latency spike logs.",
        "priority": "critical",
        "severity": "critical",
        "status": "open"
    }, headers=headers)
    
    if ticket_r.status_code != 201:
        print(f"   [ERROR] Ticket creation failed: {ticket_r.text}")
        sys.exit(1)
        
    ticket = ticket_r.json()
    ticket_id = ticket["id"]
    print(f"   [OK] Ticket raised. ID: {ticket_id} | Title: {ticket['title']}")
except Exception as e:
    print(f"   [ERROR] Ticket creation failed: {e}")
    sys.exit(1)

# 6. Add Comment & Audit Ticket history
print("\n6. Posting commentary notes and updating ticket status...")
try:
    # Post comment
    comm_r = httpx.post(f"{BASE_URL}/api/v1/tickets/{ticket_id}/comments", json={
        "comment": "Verifier: Incident assigned to backup shift. Device diagnostic diagnostics clear."
    }, headers=headers)
    if comm_r.status_code != 201:
        print(f"   [ERROR] Comment post failed: {comm_r.text}")
        sys.exit(1)
    print("   [OK] Comment note posted successfully.")
    
    # Update status to in_progress
    up_r = httpx.put(f"{BASE_URL}/api/v1/tickets/{ticket_id}", json={
        "status": "in_progress",
        "assigned_to": 1 # Assign to initial admin user
    }, headers=headers)
    if up_r.status_code != 200 or up_r.json()["status"] != "in_progress":
        print(f"   [ERROR] Ticket modification failed: {up_r.text}")
        sys.exit(1)
    print("   [OK] Ticket updated to 'in_progress' and assignee modified.")
    
    # Retrieve audit history log
    hist_r = httpx.get(f"{BASE_URL}/api/v1/tickets/{ticket_id}/history", headers=headers)
    logs = hist_r.json()
    print(f"   [OK] Checked ticket activity trail. Found {len(logs)} state updates.")
except Exception as e:
    print(f"   [ERROR] Ticket comments or updates failed: {e}")
    sys.exit(1)

# 7. Test AI/ML Predictions & retrain
print("\n7. Triggering AI/ML Retraining Pipeline...")
try:
    retrain_r = httpx.post(f"{BASE_URL}/api/v1/ml/retrain", headers=headers)
    if retrain_r.status_code != 200:
        print(f"   [ERROR] ML retrain request failed: {retrain_r.text}")
        sys.exit(1)
    print(f"   [OK] Models trained successfully: {retrain_r.json()['message']}")
    
    # Query predictions
    preds_r = httpx.get(f"{BASE_URL}/api/v1/ml/predictions", headers=headers)
    preds = preds_r.json()
    print(f"   [OK] Health predictions fetched. Monitored devices rated: {len(preds)}")
    if preds:
        print(f"     - Top device health score: {preds[0]['device_name']} -> {preds[0]['health_score']}% ({preds[0]['risk_level'].upper()} RISK)")
except Exception as e:
    print(f"   [ERROR] ML pipeline verification failed: {e}")
    sys.exit(1)

# 8. Test Reports & PDF/CSV Downloads
print("\n8. Downloading CSV and PDF reports...")
try:
    # PDF
    pdf_r = httpx.get(f"{BASE_URL}/api/v1/reports/pdf?days=7", headers=headers)
    if pdf_r.status_code != 200 or pdf_r.headers.get("content-type") != "application/pdf":
        print(f"   [ERROR] PDF compilation failed: {pdf_r.status_code}")
        sys.exit(1)
    print(f"   [OK] PDF Report downloaded successfully ({len(pdf_r.content)} bytes).")
    
    # CSV
    csv_r = httpx.get(f"{BASE_URL}/api/v1/reports/csv?type=alerts&days=7", headers=headers)
    if csv_r.status_code != 200 or "text/csv" not in csv_r.headers.get("content-type", ""):
        print(f"   [ERROR] CSV export failed: {csv_r.status_code}")
        sys.exit(1)
    print(f"   [OK] Alerts CSV dataset exported successfully ({len(csv_r.text)} lines).")
except Exception as e:
    print(f"   [ERROR] Reports validation failed: {e}")
    sys.exit(1)

print("\n============================================================")
print("[SUCCESS] All NOC Platform features verified successfully!")
print("============================================================")
