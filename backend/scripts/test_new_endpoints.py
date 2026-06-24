"""
Test new endpoints: /metrics/system and /metrics/stats
"""
import sys
import httpx

BASE = "http://127.0.0.1:8000"

# Login
r = httpx.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "AdminSecurePassword123!"})
assert r.status_code == 200, f"Login failed: {r.text}"
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[OK] Login")

# Test /metrics/system
r2 = httpx.get(f"{BASE}/api/v1/metrics/system", headers=headers)
assert r2.status_code == 200, f"System metrics failed: {r2.text}"
data = r2.json()
print(f"[OK] GET /metrics/system — CPU: {data['cpu']['usage_pct']}%, Mem: {data['memory']['used_pct']}%")
print(f"     Disk: {data['disk']['used_pct']}%, Net sent: {data['network']['bytes_sent_mb']} MB")
if data.get("top_processes"):
    print(f"     Top process: {data['top_processes'][0]['name']}")

# Test /metrics/stats
r3 = httpx.get(f"{BASE}/api/v1/metrics/stats?hours=2", headers=headers)
assert r3.status_code == 200, f"Stats failed: {r3.text}"
stats = r3.json()
print(f"[OK] GET /metrics/stats — avg_cpu: {stats['averages']['cpu_pct']}%, readings: {stats['total_readings']}")

print("\n[SUCCESS] All new endpoints work correctly!")
