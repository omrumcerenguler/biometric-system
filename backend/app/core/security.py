import base64
from cryptography.fernet import Fernet
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings

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

#JWT
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt
