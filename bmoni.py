import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BMONI_BASE_URL = os.getenv("BMONI_BASE_URL", "https://embedded-dev.bmoni.com")

client = httpx.Client(timeout=30.0)

def get_headers():
    return {
        "x-api-key": os.getenv("BMONI_API_KEY", ""),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def create_user(name: str, email: str, phone: str):
    url = f"{BMONI_BASE_URL}/v1/users"
    parts = name.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    payload = {"firstName": first_name, "lastName": last_name, "email": email, "phoneNumber": phone}
    response = client.post(url, json=payload, headers=get_headers())
    response.raise_for_status()
    return response.json()

def submit_kyc(user_id: str, dob: str, gender: str, address: dict):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/kyc"
    payload = {
        "dob": dob,
        "gender": gender,
        "address": address
    }
    response = client.patch(url, json=payload, headers=get_headers())
    response.raise_for_status()
    return response.json()

def get_owner_proof_challenge(user_id: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/smart-wallets/owner-proof-challenges"
    response = client.post(url, json={}, headers=get_headers())
    response.raise_for_status()
    return response.json()

def create_managed_wallet(user_id: str, signature: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/smart-wallets/create-managed"
    payload = {"signature": signature}
    response = client.post(url, json=payload, headers=get_headers())
    response.raise_for_status()
    return response.json()

def start_nigeria_onboarding(user_id: str, bvn: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/onboarding/start-nigeria"
    payload = {"bvn": bvn}
    response = client.post(url, json=payload, headers=get_headers())
    response.raise_for_status()
    return response.json()

def get_onboarding_status(user_id: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/onboarding/status"
    response = client.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def create_transfer_proposal(user_id: str, smart_wallet_id: str, to_address: str, amount: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/smart-wallets/{smart_wallet_id}/proposals"
    payload = {
        "to": to_address,
        "amount": amount
    }
    response = client.post(url, json=payload, headers=get_headers())
    response.raise_for_status()
    return response.json()

def approve_transfer_proposal(user_id: str, proposal_id: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/smart-wallets/proposals/{proposal_id}/approve"
    response = client.post(url, json={}, headers=get_headers())
    response.raise_for_status()
    return response.json()

def get_proposal_sign_payload(user_id: str, proposal_id: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/smart-wallets/proposals/{proposal_id}/sign-payload"
    response = client.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def sign_transfer_proposal(user_id: str, proposal_id: str, signature: str):
    url = f"{BMONI_BASE_URL}/v1/users/{user_id}/smart-wallets/proposals/{proposal_id}/sign"
    payload = {"signature": signature}
    response = client.post(url, json=payload, headers=get_headers())
    response.raise_for_status()
    return response.json()
