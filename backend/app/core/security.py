import base64
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings
import bcrypt
import re

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

# =========================
# BIOMETRIC FEATURE HELPERS
# =========================

def _require_feature_encryption_key() -> str:
    if not settings.FEATURE_ENC_KEY_B64:
        raise ValueError("FEATURE_ENC_KEY_B64 is required for biometric encryption")
    return settings.FEATURE_ENC_KEY_B64


def is_encrypted_feature_blob(blob: bytes) -> bool:
    if not blob:
        return False

    key_b64 = _require_feature_encryption_key()

    try:
        decrypt_bytes(blob, key_b64)
        return True
    except InvalidToken:
        return False


def encrypt_feature_blob(raw_blob: bytes) -> bytes:
    if not raw_blob:
        raise ValueError("Biometric feature blob cannot be empty")

    key_b64 = _require_feature_encryption_key()

    if is_encrypted_feature_blob(raw_blob):
        return raw_blob

    return encrypt_bytes(raw_blob, key_b64)


def decrypt_feature_blob(stored_blob: bytes) -> bytes:
    if not stored_blob:
        raise ValueError("Biometric feature blob cannot be empty")

    key_b64 = _require_feature_encryption_key()

    try:
        return decrypt_bytes(stored_blob, key_b64)
    except InvalidToken:
        # Backward compatibility:
        # Old DB records may still contain raw float32 feature bytes.
        return stored_blob

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

#JWT decode (token verification)
def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise ValueError("INVALID_TOKEN") from e



# =========================
# SECURITY QUESTION HELPERS
# =========================

import unicodedata

import unicodedata

def normalize_security_answer(text: str) -> str:
    if not text:
        return ""

    text = text.strip().lower()

    # Unicode normalize (çok kritik)
    text = unicodedata.normalize("NFKD", text)

    # combining karakterleri temizle (noktalı i vs)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Türkçe özel fix
    text = text.replace("ı", "i")

    return text


def hash_security_answer(answer: str) -> str:
    normalized = normalize_security_answer(answer)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(normalized.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_security_answer(input_answer: str, stored_hash: str) -> bool:
    normalized = normalize_security_answer(input_answer)
    return bcrypt.checkpw(
        normalized.encode("utf-8"),
        stored_hash.encode("utf-8")
    )

BCRYPT_PASSWORD_RE = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


def is_password_hash(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return bool(BCRYPT_PASSWORD_RE.match(value))


def hash_password(password: str) -> str:
    if password is None:
        raise ValueError("Password cannot be None")

    password_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False

    if not is_password_hash(stored_hash):
        return False

    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
    
    