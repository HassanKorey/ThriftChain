import os
import bmoni
import signing

def run_test():
    print("Testing BMONI API Sandbox...")
    if not os.getenv("BMONI_API_KEY") or "your_sandbox" in os.getenv("BMONI_API_KEY"):
        print("Please set your real BMONI_API_KEY in .env before testing.")
        return

    import random
    rand_suffix = random.randint(1000, 9999)
    persona = {
        "name": "Bunch Dillon",
        "email": f"bunch.dillon{rand_suffix}@example.com",
        "phone": f"+23480000{rand_suffix}",
        "dob": "1990-01-15",
        "gender": "male",
        "address": {
            "street": "15 Admiralty Way",
            "city": "Lagos",
            "state": "Lagos",
            "country": "NGA"
        },
        "bvn": "95888168924"
    }

    try:
        print("\n--- 1. Create User ---")
        user_res = bmoni.create_user(persona["name"], persona["email"], persona["phone"])
        print(user_res)
        
        # Determine ID based on typical JSON shapes
        user_id = user_res.get("id") or user_res.get("userId") or (user_res.get("data", {}).get("id"))
        if not user_id:
            print("Could not auto-extract user ID. Please inspect the response manually.")
            return
            
        print(f"\n--- 2. Submit KYC for user {user_id} ---")
        kyc_res = bmoni.submit_kyc(user_id, persona["dob"], persona["gender"], persona["address"])
        print(kyc_res)
        
        print(f"\n--- 3. Get Owner Proof Challenge ---")
        challenge_res = bmoni.get_owner_proof_challenge(user_id)
        print(challenge_res)
        
        challenge_text = challenge_res.get("challenge") or challenge_res.get("data", {}).get("challenge")
        if not challenge_text:
            print("Could not extract challenge text from response.")
            return

        print(f"\n--- 4. Sign Challenge ---")
        priv_key, address = signing.generate_account()
        signature = signing.sign_owner_proof(challenge_text, priv_key)
        print(f"Generated Signature: {signature}")

        print(f"\n--- 5. Create Managed Wallet ---")
        wallet_res = bmoni.create_managed_wallet(user_id, signature)
        print(wallet_res)

        print(f"\n--- 6. Start Nigeria Onboarding ---")
        onboard_res = bmoni.start_nigeria_onboarding(user_id, persona["bvn"])
        print(onboard_res)

        print(f"\n--- 7. Get Onboarding Status ---")
        status_res = bmoni.get_onboarding_status(user_id)
        print(status_res)
        
        print("\nAll Setup Steps Passed Successfully!")
        
    except Exception as e:
        print(f"\n[!] Error occurred: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Body: {e.response.text}")

if __name__ == "__main__":
    run_test()
