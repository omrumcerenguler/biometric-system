from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Multi-Modal Biometric Auth"
    DATABASE_URL: str = Field(...)

    # Feature encryption (store only encrypted processed features)
    FEATURE_ENC_KEY_B64: str = ""  # base64 key for Fernet (set in .env)

    # Thresholds (tune later)
    FACE_IDENTIFICATION_THRESHOLD: float = 0.70
    FACE_LIVENESS_IDENTITY_THRESHOLD: float = 0.80
    FACE_POSE_IDENTITY_THRESHOLD: float = 0.70
    FACE_POSE_MIN_DELTA: float = 0.12
    # Additional absolute guards to prevent tiny movements from passing as full side turns.
    FACE_POSE_RIGHT_MIN_NOSE_X: float = 0.62
    FACE_POSE_LEFT_MAX_NOSE_X: float = 0.38
    VOICE_IDENTIFICATION_THRESHOLD: float = 0.70
    VOICE_TEMPLATE_UPDATE_THRESHOLD: float = 0.70
    FACE_LIVENESS_THRESHOLD: float = 0.80
    VOICE_LIVENESS_THRESHOLD: float = 0.70
    FUSION_PASS_THRESHOLD: float = 0.70

    # JWT Settings
    SECRET_KEY: str = "dev-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
