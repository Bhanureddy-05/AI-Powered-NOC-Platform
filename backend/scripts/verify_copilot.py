"""
verify_copilot.py
=================
Verifies AI Copilot API endpoints, sessions, history, and streaming chat.
"""

import sys
import httpx
import json

# Force UTF-8 output to prevent Windows charmap encoding errors for emoji/Unicode
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    # Python < 3.7 fallback: re-open stdout in UTF-8 mode
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def safe_print(text):
    """Safely print text with Unicode, replacing unprintable chars if needed."""
    try:
        print(text, end="", flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), end="", flush=True)

BASE_URL = "http://127.0.0.1:8000"

print("============================================================")
print("AETHER NOC PLATFORM - AI COPILOT ENDPOINTS VERIFICATION")
print("============================================================\n")

# 1. Login to obtain access token
print("1. Authenticating as admin...")
try:
    login_r = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "admin",
        "password": "AdminSecurePassword123!"
    })
    if login_r.status_code != 200:
        print(f"   [ERROR] Login failed: {login_r.text}")
        sys.exit(1)
        
    token = login_r.json()["access_token"]
    print("   [OK] Authenticated. Token acquired.")
except Exception as e:
    print(f"   [ERROR] Connection failed: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

# 2. Create Chat Session
print("\n2. Initializing new chat session...")
try:
    sess_r = httpx.post(
        f"{BASE_URL}/api/v1/copilot/sessions", 
        json={"title": "Verification Chat Session"}, 
        headers=headers
    )
    if sess_r.status_code != 201:
        print(f"   [ERROR] Session creation failed: {sess_r.text}")
        sys.exit(1)
        
    session = sess_r.json()
    session_id = session["id"]
    print(f"   [OK] Session created successfully. ID: {session_id} | Title: {session['title']}")
except Exception as e:
    print(f"   [ERROR] Session creation request failed: {e}")
    sys.exit(1)

# 3. Chat with Agent (Read SSE stream)
print("\n3. Querying AI Copilot Agent ('how to mitigate high CPU on core-router-01')...")
try:
    # We do a streaming POST request
    with httpx.stream(
        "POST", 
        f"{BASE_URL}/api/v1/copilot/sessions/{session_id}/chat",
        json={"query": "how to mitigate high CPU on core-router-01"},
        headers=headers,
        timeout=30.0
    ) as r:
        if r.status_code != 200:
            print(f"   [ERROR] Chat request failed: {r.status_code}")
            sys.exit(1)
            
        print("   [STREAMING RESPONSE CHUNKS]:")
        full_text = ""
        for line in r.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                    if "content" in data:
                        chunk = data["content"]
                        full_text += chunk
                        safe_print(chunk)
                except Exception as e:
                    print(f"\n   [ERROR parsing chunk]: {e}")
        print("\n\n   [OK] Streaming completion received successfully.")
except Exception as e:
    print(f"   [ERROR] Streaming request failed: {e}")
    sys.exit(1)

# 4. Get History
print("\n4. Retrieving chat history for session...")
try:
    hist_r = httpx.get(f"{BASE_URL}/api/v1/copilot/sessions/{session_id}/history", headers=headers)
    if hist_r.status_code != 200:
        print(f"   [ERROR] History query failed: {hist_r.text}")
        sys.exit(1)
        
    messages = hist_r.json()
    print(f"   [OK] History returned. Total messages in thread: {len(messages)}")
    for msg in messages:
        try:
            print(f"     - [{msg['role'].upper()}]: {msg['content'][:60]}...")
        except UnicodeEncodeError:
            safe_content = msg['content'][:60].encode('ascii', errors='replace').decode('ascii')
            print(f"     - [{msg['role'].upper()}]: {safe_content}...")
except Exception as e:
    print(f"   [ERROR] History loading failed: {e}")
    sys.exit(1)

# 5. List Sessions
print("\n5. Listing all active sessions...")
try:
    list_r = httpx.get(f"{BASE_URL}/api/v1/copilot/sessions", headers=headers)
    if list_r.status_code != 200:
        print(f"   [ERROR] List sessions failed: {list_r.text}")
        sys.exit(1)
        
    sessions = list_r.json()
    print(f"   [OK] Active sessions listed: {len(sessions)}")
    assert any(s["id"] == session_id for s in sessions)
except Exception as e:
    print(f"   [ERROR] Session listing failed: {e}")
    sys.exit(1)

# 6. Delete Session
print("\n6. Cleaning up session...")
try:
    del_r = httpx.delete(f"{BASE_URL}/api/v1/copilot/sessions/{session_id}", headers=headers)
    if del_r.status_code != 204:
        print(f"   [ERROR] Deletion failed: {del_r.status_code}")
        sys.exit(1)
        
    print("   [OK] Session deleted successfully.")
except Exception as e:
    print(f"   [ERROR] Session cleanup failed: {e}")
    sys.exit(1)

print("\n============================================================")
print("[SUCCESS] All AI Copilot endpoints verified successfully!")
print("============================================================")
