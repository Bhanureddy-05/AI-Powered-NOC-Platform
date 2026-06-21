"""
verify_backend.py
=================
Automated Backend Integration & Health Verification Script

WHY THIS FILE EXISTS:
    To verify that our monolithic backend is working perfectly, this script
    simulates client requests. It tests API routing, DB writes, and JWT auth
    flows in-process.
"""

import sys
import os
import asyncio
from fastapi.testclient import TestClient

# Adjust python path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Test Imports
print("Testing backend imports...")
try:
    from main import app
    from app.db.session import get_db, engine
    from app.models import User, AuditLog
    from app.schemas.user import UserCreate, UserLogin
    print("[OK] All imports succeeded!")
except Exception as e:
    print(f"[ERROR] Import failure: {e}")
    sys.exit(1)

client = TestClient(app)

# 2. Test /health Endpoint
print("\nTesting /health endpoint...")
try:
    response = client.get("/health")
    if response.status_code == 200:
        print(f"[OK] Health Check OK! Response: {response.json()}")
    else:
        print(f"[ERROR] Health Check failed with code {response.status_code}: {response.text}")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Health Check exception: {e}")
    sys.exit(1)

# 3. Test JWT Registration & Authentication Flow
print("\nTesting JWT registration and login flow...")
try:
    # Use unique usernames to allow running the test multiple times
    import random
    test_num = random.randint(1000, 9999)
    username = f"noc_engineer_{test_num}"
    email = f"engineer_{test_num}@aethernoc.net"
    password = "SuperSecurePassword123"

    # Step A: Register
    print(f"  Registering test user: {username} ({email})...")
    reg_response = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "role": "admin"
    })
    
    if reg_response.status_code == 201:
        print(f"  [OK] User registered successfully! ID: {reg_response.json().get('id')}")
    else:
        print(f"  [ERROR] Registration failed ({reg_response.status_code}): {reg_response.text}")
        sys.exit(1)

    # Step B: Login
    print("  Logging in to obtain JWT access token...")
    login_response = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    
    if login_response.status_code == 200:
        token_data = login_response.json()
        token = token_data.get("access_token")
        token_type = token_data.get("token_type")
        print(f"  [OK] Login successful! Token type: {token_type}")
        print(f"    Token: {token[:20]}...[truncated]...{token[-20:]}")
    else:
        print(f"  [ERROR] Login failed ({login_response.status_code}): {login_response.text}")
        sys.exit(1)

    # Step C: Retrieve protected profile using JWT token
    print("  Retrieving profile using JWT in Authorization header...")
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    
    if me_response.status_code == 200:
        user_profile = me_response.json()
        print(f"  [OK] Protected access validated! Profile data:")
        print(f"    - Username: {user_profile.get('username')}")
        print(f"    - Email: {user_profile.get('email')}")
        print(f"    - Role: {user_profile.get('role')}")
        print(f"    - Enrolled: {user_profile.get('created_at')}")
    else:
        print(f"  [ERROR] Protected endpoint access failed ({me_response.status_code}): {me_response.text}")
        sys.exit(1)

    print("\n[OK] JWT Authentication and database integration tests passed successfully!")

except Exception as e:
    print(f"[ERROR] Exception in auth flow verification: {e}")
    sys.exit(1)
