from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, LargeBinary, func, Boolean


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, index=True)
    client: Mapped[str] = mapped_column(String, nullable=False, default="portal", index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    biometric_data = relationship("BiometricData", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class BiometricData(Base):
    __tablename__ = "biometric_data"

    data_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    enc_feature_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), nullable=False)
    user = relationship("User", back_populates="biometric_data")


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result: Mapped[str] = mapped_column(String, nullable=False)
    time: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    details: Mapped[str] = mapped_column(String, nullable=False, default="")

    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), nullable=False)
    user = relationship("User", back_populates="audit_logs")