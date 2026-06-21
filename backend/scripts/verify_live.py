"""
verify_live.py
==============
Live TCP API Integration Verification Script

WHY THIS FILE EXISTS:
    Unlike verify_backend.py (which tests the FastAPI code using a mock TestClient
    in-process), this script tests the actual running network server listening
    on port 8000. It checks actual network ports, HTML documentation payloads,
    and DB synchronization over TCP/IP loops.
"""

import sys
import random
import httpx

BASE_URL = "http://127.0.0.1:8000"

print("============================================================")
print("AETHER NOC PLATFORM - LIVE VERIFICATION TESTS")
print("============================================================\n")

# 1. Verify /health
print("1. Verifying /health endpoint...")
try:
    r = httpx.get(f"{BASE_URL}/health")
    if r.status_code == 200:
        print(f"   [OK] /health works: {r.json()}")
    else:
        print(f"   [ERROR] /health returned code {r.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] /health unreachable: {e}")
    sys.exit(1)

# 2. Verify /docs
print("\n2. Verifying /docs (Swagger UI) HTML accessibility...")
try:
    r = httpx.get(f"{BASE_URL}/docs")
    if r.status_code == 200 and "swagger" in r.text.lower():
        print("   [OK] /docs opens successfully (Swagger UI HTML detected).")
    else:
        print(f"   [ERROR] /docs access failed or did not return Swagger UI.")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] /docs unreachable: {e}")
    sys.exit(1)

# Generate distinct test data
test_num = random.randint(1000, 9999)
username = f"live_engineer_{test_num}"
email = f"live_{test_num}@aethernoc.net"
password = "SuperSecurePassword123"

# 3. Verify Registration
print(f"\n3. Verifying User Registration (Creating operator: {username})...")
try:
    r = httpx.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "role": "operator"
    })
    if r.status_code == 201:
        print(f"   [OK] Operator registered successfully: {r.json()}")
    else:
        print(f"   [ERROR] Registration failed ({r.status_code}): {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] Registration exception: {e}")
    sys.exit(1)

# 4. Verify Login
print("\n4. Verifying User Login (Obtaining JWT Bearer token)...")
try:
    r = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    if r.status_code == 200:
        token_data = r.json()
        token = token_data.get("access_token")
        print(f"   [OK] Login successful: {token_data}")
    else:
        print(f"   [ERROR] Login failed ({r.status_code}): {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] Login exception: {e}")
    sys.exit(1)

# 5. Verify JWT Auth
print("\n5. Verifying JWT Protected route (/auth/me)...")
try:
    headers = {"Authorization": f"Bearer {token}"}
    r = httpx.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    if r.status_code == 200:
        print(f"   [OK] JWT authentication validated: {r.json()}")
    else:
        print(f"   [ERROR] /auth/me verification failed ({r.status_code}): {r.text}")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] JWT verification exception: {e}")
    sys.exit(1)

print("\n============================================================")
print("[SUCCESS] All live API verification tasks completed successfully!")
print("============================================================")
