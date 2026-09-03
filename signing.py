from eth_account import Account
from eth_account.messages import encode_defunct

def generate_account():
    """
    Generate a new Ethereum account (private key and address).
    Returns (private_key_hex, address).
    """
    acct = Account.create()
    return acct.key.hex(), acct.address

def sign_owner_proof(challenge_text: str, private_key: str) -> str:
    """
    Signature 1: Owner Proof (wallet creation)
    Signs a text message WITH the EIP-191 prefix.
    """
    message = encode_defunct(text=challenge_text)
    signed = Account.sign_message(message, private_key=private_key)
    return signed.signature.hex()

def sign_proposal_hash(digest_hex: str, private_key: str) -> str:
    """
    Signature 2: Proposal Sign (transfer)
    Signs a raw 32-byte hash WITHOUT the EIP-191 prefix.
    """
    # Remove '0x' prefix if present before converting to bytes
    digest_bytes = bytes.fromhex(digest_hex.replace("0x", ""))
    signed = Account.unsafe_sign_hash(digest_bytes, private_key)
    return signed.signature.hex()
