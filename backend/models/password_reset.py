from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from models.user import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False,)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True,)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False,)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,)