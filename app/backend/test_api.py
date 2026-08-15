import requests

BASE_URL = "http://127.0.0.1:8000/api"

# Login as patient
r = requests.post(f"{BASE_URL}/auth/token", data={"username": "patient1", "password": "password123"})
if r.status_code == 200:
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get contacts
    r2 = requests.get(f"{BASE_URL}/messages/contacts", headers=headers)
    print("Contacts:", r2.status_code, r2.text)
else:
    print("Login failed:", r.status_code, r.text)
