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
    security_answers = relationship("UserSecurityAnswer", back_populates="user")

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

class SecurityQuestion(Base):
    __tablename__ = "security_question"

    question_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_text: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user_answers = relationship("UserSecurityAnswer", back_populates="question")


class UserSecurityAnswer(Base):
    __tablename__ = "user_security_answer"

    answer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("security_question.question_id"), nullable=False, index=True)

    answer_hash: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="security_answers")
    question = relationship("SecurityQuestion", back_populates="user_answers")