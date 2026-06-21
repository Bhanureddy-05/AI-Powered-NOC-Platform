"""
verify_devices.py
=================
Live Device Management & RBAC Verification Script

WHY THIS FILE EXISTS:
    Validates the Device Management endpoints against the running server on port 8000.
    Simulates admin, operator, and viewer tokens to ensure RBAC rules are enforced,
    verifies database constraints (unique IP/names, invalid IPs), and verifies
    creation of audit logs.
"""

import sys
import random
import httpx
import sqlite3

BASE_URL = "http://127.0.0.1:8000"

print("============================================================")
print("AETHER NOC PLATFORM - DEVICE CRUD & RBAC VERIFICATION")
print("============================================================\n")

# Setup clients and users
test_id = random.randint(100, 999)
credentials = {
    "admin": {"username": f"admin_{test_id}", "email": f"admin_{test_id}@aethernoc.net", "password": "AdminSecurePassword123!", "role": "admin"},
    "operator": {"username": f"operator_{test_id}", "email": f"op_{test_id}@aethernoc.net", "password": "OperatorSecurePassword123!", "role": "operator"},
    "viewer": {"username": f"viewer_{test_id}", "email": f"view_{test_id}@aethernoc.net", "password": "ViewerSecurePassword123!", "role": "viewer"}
}

tokens = {}

# 1. Register & Login Roles
print("1. Enrolling test users and signing JWT tokens...")
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
        if log_r.status_code != 200:
            print(f"   [ERROR] Failed login for {role}: {log_r.text}")
            sys.exit(1)
        
        tokens[role] = log_r.json()["access_token"]
        print(f"   [OK] Role '{role}' active. Token acquired.")
except Exception as e:
    print(f"   [ERROR] Connection failed: {e}")
    sys.exit(1)

# Helpers for HTTP calls
headers = {r: {"Authorization": f"Bearer {tokens[r]}"} for r in tokens}

# 2. Test RBAC: Create Device
print("\n2. Testing RBAC restrictions on Device Creation...")

device_a_payload = {
    "device_name": f"cisco-switch-{test_id}-a",
    "ip_address": f"192.168.{test_id % 254}.1",
    "location": "Rack 12-A, Floor 2",
    "device_type": "switch",
    "status": "active"
}

device_b_payload = {
    "device_name": f"cisco-router-{test_id}-b",
    "ip_address": f"192.168.{test_id % 254}.2",
    "location": "Rack 14-B, Floor 3",
    "device_type": "router",
    "status": "active"
}

# Viewer Attempt -> Should Fail (403)
print("   Attempting creation using 'viewer' role...")
r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=device_a_payload, headers=headers["viewer"])
if r.status_code == 403:
    print("   [OK] Viewer creation blocked as expected (403 Forbidden).")
else:
    print(f"   [ERROR] Viewer was not blocked! Status: {r.status_code}, Body: {r.text}")
    sys.exit(1)

# Operator Attempt -> Should Succeed (201)
print("   Attempting creation using 'operator' role...")
r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=device_a_payload, headers=headers["operator"])
if r.status_code == 201:
    device_a = r.json()
    print(f"   [OK] Operator created device: {device_a['device_name']} (ID: {device_a['id']})")
else:
    print(f"   [ERROR] Operator creation failed ({r.status_code}): {r.text}")
    sys.exit(1)

# Admin Attempt -> Should Succeed (201)
print("   Attempting creation using 'admin' role...")
r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=device_b_payload, headers=headers["admin"])
if r.status_code == 201:
    device_b = r.json()
    print(f"   [OK] Admin created device: {device_b['device_name']} (ID: {device_b['id']})")
else:
    print(f"   [ERROR] Admin creation failed ({r.status_code}): {r.text}")
    sys.exit(1)


# 3. Test Validation Constraints (Unique & IP validation)
print("\n3. Testing input validations & unique constraints...")

# Duplicate Name
print("   Creating device with duplicate name using admin...")
dup_payload = device_a_payload.copy()
dup_payload["ip_address"] = f"192.168.{test_id % 254}.100" # different IP
r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=dup_payload, headers=headers["admin"])
if r.status_code == 400:
    print(f"   [OK] Duplicate name blocked (400 Bad Request: {r.json()['detail']})")
else:
    print(f"   [ERROR] Duplicate name was not blocked! Code: {r.status_code}, Body: {r.text}")
    sys.exit(1)

# Duplicate IP
print("   Creating device with duplicate IP using admin...")
dup_payload = device_b_payload.copy()
dup_payload["device_name"] = f"cisco-dup-name-{test_id}" # different name
r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=dup_payload, headers=headers["admin"])
if r.status_code == 400:
    print(f"   [OK] Duplicate IP blocked (400 Bad Request: {r.json()['detail']})")
else:
    print(f"   [ERROR] Duplicate IP was not blocked! Code: {r.status_code}, Body: {r.text}")
    sys.exit(1)

# Invalid IP Format
print("   Creating device with invalid IP address using admin...")
inv_payload = device_a_payload.copy()
inv_payload["device_name"] = f"cisco-inv-ip-{test_id}"
inv_payload["ip_address"] = "999.999.999.999" # invalid IP
r = httpx.post(f"{BASE_URL}/api/v1/devices/", json=inv_payload, headers=headers["admin"])
if r.status_code == 422:
    print(f"   [OK] Invalid IP format blocked by Pydantic validation (422 Unprocessable Entity)")
else:
    print(f"   [ERROR] Invalid IP format was not blocked! Code: {r.status_code}, Body: {r.text}")
    sys.exit(1)


# 4. Test Search, Filtering, and Pagination
print("\n4. Testing Device Queries (Search, Filter, Pagination)...")

# List devices (Viewer)
r = httpx.get(f"{BASE_URL}/api/v1/devices/", headers=headers["viewer"])
print(f"   List total devices (Viewer): {r.json()['total']}")

# Filter by type "switch"
r = httpx.get(f"{BASE_URL}/api/v1/devices/?device_type=switch", headers=headers["viewer"])
print(f"   Filtered by type 'switch' count: {len(r.json()['devices'])}")

# Search by host name substring
r = httpx.get(f"{BASE_URL}/api/v1/devices/?q=router", headers=headers["viewer"])
print(f"   Searched by query 'router' count: {len(r.json()['devices'])}")

# Pagination size=1
r = httpx.get(f"{BASE_URL}/api/v1/devices/?page=1&size=1", headers=headers["viewer"])
res = r.json()
print(f"   Pagination test: page={res['page']}, size={res['size']}, pages={res['pages']}, devices returned={len(res['devices'])}")


# 5. Test Update / Patch
print("\n5. Testing RBAC updates on Device configs...")

update_payload = {"status": "maintenance", "location": "Rack 99, Vault"}

# Viewer update -> Should Fail
r = httpx.put(f"{BASE_URL}/api/v1/devices/{device_a['id']}", json=update_payload, headers=headers["viewer"])
if r.status_code == 403:
    print("   [OK] Viewer blocked from editing config.")
else:
    print(f"   [ERROR] Viewer succeeded in editing! Code: {r.status_code}")
    sys.exit(1)

# Operator update -> Should Succeed
r = httpx.put(f"{BASE_URL}/api/v1/devices/{device_a['id']}", json=update_payload, headers=headers["operator"])
if r.status_code == 200:
    device_a_updated = r.json()
    print(f"   [OK] Operator modified device config. Status: {device_a_updated['status']}, Location: {device_a_updated['location']}")
else:
    print(f"   [ERROR] Operator update failed ({r.status_code}): {r.text}")
    sys.exit(1)


# 6. Test Delete
print("\n6. Testing RBAC restrictions on Device Deletion...")

# Operator delete -> Should Fail (403)
r = httpx.delete(f"{BASE_URL}/api/v1/devices/{device_a['id']}", headers=headers["operator"])
if r.status_code == 403:
    print("   [OK] Operator delete request blocked.")
else:
    print(f"   [ERROR] Operator deletion was not blocked! Code: {r.status_code}")
    sys.exit(1)

# Admin delete -> Should Succeed (204)
r = httpx.delete(f"{BASE_URL}/api/v1/devices/{device_a['id']}", headers=headers["admin"])
if r.status_code == 204:
    print(f"   [OK] Admin deleted device {device_a['device_name']} successfully.")
else:
    print(f"   [ERROR] Admin deletion failed ({r.status_code}): {r.text}")
    sys.exit(1)


# 7. Verify Audit Logs Database Output
print("\n7. Querying SQLite Database for generated Audit Logs...")
try:
    conn = sqlite3.connect("noc_platform.db")
    cursor = conn.cursor()
    
    # Query logs generated by our test users
    cursor.execute("""
        SELECT action, details, timestamp 
        FROM audit_logs 
        WHERE action LIKE 'device_%' 
        ORDER BY timestamp ASC
    """)
    logs = cursor.fetchall()
    
    print(f"   Found {len(logs)} Device operations log entries:")
    for action, details, timestamp in logs:
        print(f"   - [{timestamp}] ACTION: {action} | DETAILS: {details}")
    
    # Assert logs are generated for creation, update and delete
    actions = [log[0] for log in logs]
    assert "device_created" in actions, "No device_created audit log found."
    assert "device_updated" in actions, "No device_updated audit log found."
    assert "device_deleted" in actions, "No device_deleted audit log found."
    print("   [OK] All CRUD audit logs present and verified in SQL engine.")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"   [ERROR] Audit log database check failed: {e}")
    sys.exit(1)

print("\n============================================================")
print("[SUCCESS] All Phase 3 Device Management tests passed successfully!")
print("============================================================")
