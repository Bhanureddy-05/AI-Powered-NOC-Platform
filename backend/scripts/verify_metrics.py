"""
verify_metrics.py
=================
Live Telemetry Metrics Ingestion & RBAC Verification Script

WHY THIS FILE EXISTS:
    Validates Phase 4 HTTP endpoints (/api/v1/metrics/) against the running server.
    Ensures input ranges are validated, RBAC authorization blocks unauthorized writes,
    and history search returns the correct data.
"""

import sys
import random
import httpx

BASE_URL = "http://127.0.0.1:8000"

print("============================================================")
print("AETHER NOC PLATFORM - TELEMETRY INGESTION VERIFICATION")
print("============================================================\n")

# Setup users
test_id = random.randint(100, 999)
credentials = {
    "admin": {"username": f"admin_metrics_{test_id}", "email": f"adm_m_{test_id}@aethernoc.net", "password": "AdminSecurePassword123!", "role": "admin"},
    "operator": {"username": f"operator_metrics_{test_id}", "email": f"op_m_{test_id}@aethernoc.net", "password": "OperatorSecurePassword123!", "role": "operator"},
    "viewer": {"username": f"viewer_metrics_{test_id}", "email": f"view_m_{test_id}@aethernoc.net", "password": "ViewerSecurePassword123!", "role": "viewer"}
}

tokens = {}

# 1. Login/Register Roles
print("1. Enrolling test roles and acquiring session tokens...")
try:
    for role, payload in credentials.items():
        # Register
        reg_r = httpx.post(f"{BASE_URL}/api/v1/auth/register", json=payload)
        if reg_r.status_code != 201:
            print(f"   [ERROR] Failed registering {role}: {reg_r.text}")
            sys.exit(1)
        
        # Login
        log_r = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": payload["username"],
            "password": payload["password"]
        })
        tokens[role] = log_r.json()["access_token"]
    print("   [OK] Admin, Operator, and Viewer sessions established.")
except Exception as e:
    print(f"   [ERROR] Setup failed: {e}")
    sys.exit(1)

headers = {r: {"Authorization": f"Bearer {tokens[r]}"} for r in tokens}

# 2. Register a Test Device to attach metrics
print("\n2. Registering a test device for telemetry attachment...")
device_payload = {
    "device_name": f"cisco-edge-switch-{test_id}",
    "ip_address": f"10.10.{test_id % 254}.254",
    "location": "NOC Test Bench, HQ",
    "device_type": "switch",
    "status": "active"
}

try:
    r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=device_payload, headers=headers["admin"])
    if r.status_code == 201:
        device = r.json()
        device_id = device["id"]
        print(f"   [OK] Test device registered. ID: {device_id}")
    else:
        print(f"   [ERROR] Device registration failed: {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] Device setup failed: {e}")
    sys.exit(1)


# 3. Test Ingestion RBAC & Validation
print("\n3. Testing Ingestion RBAC permissions & Range constraints...")

valid_metric = {
    "device_id": device_id,
    "cpu_usage": 45.2,
    "memory_usage": 60.1,
    "latency": 12.4,
    "packet_loss": 0.0,
    "bandwidth_usage": 150.5
}

# Ingest - Viewer -> Should fail (403)
print("   Attempting metric post using 'viewer' token...")
r = httpx.post(f"{BASE_URL}/api/v1/metrics/", json=valid_metric, headers=headers["viewer"])
if r.status_code == 403:
    print("   [OK] Viewer write blocked successfully (403 Forbidden).")
else:
    print(f"   [ERROR] Viewer was not blocked! Code: {r.status_code}, Body: {r.text}")
    sys.exit(1)

# Ingest - Operator -> Should succeed (201)
print("   Attempting metric post using 'operator' token...")
r = httpx.post(f"{BASE_URL}/api/v1/metrics/", json=valid_metric, headers=headers["operator"])
if r.status_code == 201:
    print(f"   [OK] Operator metric ingestion succeeded. Response: {r.json()}")
else:
    print(f"   [ERROR] Operator ingestion failed! Code: {r.status_code}, Body: {r.text}")
    sys.exit(1)

# Ingest - Invalid range (CPU > 100%) -> Should fail (422)
print("   Attempting invalid metric post (CPU = 120%)...")
invalid_metric = valid_metric.copy()
invalid_metric["cpu_usage"] = 120.0
r = httpx.post(f"{BASE_URL}/api/v1/metrics/", json=invalid_metric, headers=headers["operator"])
if r.status_code == 422:
    print("   [OK] Out-of-bounds percentage value blocked by Pydantic.")
else:
    print(f"   [ERROR] Invalid range was not blocked! Code: {r.status_code}")
    sys.exit(1)

# Ingest - Negative Latency -> Should fail (422)
print("   Attempting invalid metric post (Latency = -5.0ms)...")
invalid_metric = valid_metric.copy()
invalid_metric["latency"] = -5.0
r = httpx.post(f"{BASE_URL}/api/v1/metrics/", json=invalid_metric, headers=headers["operator"])
if r.status_code == 422:
    print("   [OK] Negative latency blocked by Pydantic.")
else:
    print(f"   [ERROR] Negative latency was not blocked! Code: {r.status_code}")
    sys.exit(1)


# 4. Test Historical Metrics Queries
print("\n4. Testing telemetry retrieval & filtering...")

# Fetch history (Viewer)
r = httpx.get(f"{BASE_URL}/api/v1/metrics/{device_id}", headers=headers["viewer"])
if r.status_code == 200:
    history = r.json()
    print(f"   [OK] Viewer successfully fetched telemetry list. Length: {len(history)}")
    print(f"        First element: {history[0]}")
else:
    print(f"   [ERROR] History query failed: {r.text}")
    sys.exit(1)

print("\n============================================================")
print("[SUCCESS] API Ingestion and Query verification passed!")
print("============================================================")
