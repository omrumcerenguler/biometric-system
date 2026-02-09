import base64
from cryptography.fernet import Fernet

def _load_fernet(key_b64: str) -> Fernet:
    if not key_b64:
        # Dev mode fallback: generate ephemeral key (DON'T use in production)
        key = Fernet.generate_key()
        return Fernet(key)

    key = key_b64.encode("utf-8")
    # accept raw base64 string (urlsafe)
    try:
        base64.urlsafe_b64decode(key)
    except Exception as e:
        raise ValueError("FEATURE_ENC_KEY_B64 is not valid urlsafe base64") from e
    return Fernet(key)

def encrypt_bytes(data: bytes, key_b64: str) -> bytes:
    f = _load_fernet(key_b64)
    return f.encrypt(data)

def decrypt_bytes(token: bytes, key_b64: str) -> bytes:
    f = _load_fernet(key_b64)
    return f.decrypt(token)
