import bmoni
import json
import uuid

try:
    uid = str(uuid.uuid4())[:8]
    user = bmoni.create_user(f"Test User {uid}", f"test{uid}@example.com", f"+23480000{uid[:4]}")
    user_id = user.get("id") or user.get("userId") or user.get("data", {}).get("id")
    print("User ID:", user_id)
    
    # Try fetching wallet details
    url = f"{bmoni.BMONI_BASE_URL}/v1/users/{user_id}/wallet"
    res = bmoni.client.get(url, headers=bmoni.get_headers())
    print("Wallet Details:", res.status_code, res.text)
except Exception as e:
    print(e)
