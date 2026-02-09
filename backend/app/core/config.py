from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Multi-Modal Biometric Auth"
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # Feature encryption (store only encrypted processed features)
    FEATURE_ENC_KEY_B64: str = ""  # base64 key for Fernet (set in .env)

    # Thresholds (tune later)
    FACE_LIVENESS_THRESHOLD: float = 0.60
    VOICE_LIVENESS_THRESHOLD: float = 0.60
    FUSION_PASS_THRESHOLD: float = 0.65  # weighted fusion score

settings = Settings()
