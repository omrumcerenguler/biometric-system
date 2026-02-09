from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, LargeBinary, func

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)

    biometric_data = relationship("BiometricData", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class BiometricData(Base):
    __tablename__ = "biometric_data"

    data_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "face_feature" | "voice_feature"
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # store encrypted processed features (NOT raw image/audio)
    enc_feature_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), nullable=False)
    user = relationship("User", back_populates="biometric_data")

class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result: Mapped[str] = mapped_column(String, nullable=False)  # "GRANTED" | "DENIED"
    time: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    details: Mapped[str] = mapped_column(String, nullable=False, default="")  # short reason

    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), nullable=False)
    user = relationship("User", back_populates="audit_logs")
