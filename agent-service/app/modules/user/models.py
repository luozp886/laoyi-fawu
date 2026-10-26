from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class User(Base, CreateAtMixin, UpdateAtMixin):
    """平台用户（注册/登录）"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        server_default="active",
    )


class RefreshToken(Base, CreateAtMixin, UpdateAtMixin):
    """登录刷新令牌（双 token 机制中的 refresh token）。

    数据库只保存令牌的 SHA-256 哈希，不落明文；
    每次刷新会轮换：撤销旧令牌并签发新令牌，防止令牌泄露重放。
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[str | None] = mapped_column(String(64))
