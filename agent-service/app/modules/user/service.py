from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.modules.user.models import RefreshToken, User
from app.security import create_refresh_token, hash_refresh_token

# argon2 密码哈希器（pwdlib 默认推荐算法）
password_hash = PasswordHash.recommended()


async def register_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    email: str,
    display_name: str | None = None,
) -> User:
    """注册新用户：查重 → 哈希密码 → 落库。"""
    username = username.strip()
    email = email.strip().lower()
    exists = await session.scalar(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if exists is not None:
        raise ApplicationError("用户名或邮箱已被注册，请直接登录")
    user = User(
        username=username,
        email=email,
        password_hash=password_hash.hash(password),
        display_name=display_name.strip() if display_name else username,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def login_user(session: AsyncSession, *, username: str, password: str) -> User:
    """账号登录：校验用户名与密码。"""
    user = await session.scalar(select(User).where(User.username == username.strip()))
    if user is None or not password_hash.verify(password, user.password_hash):
        raise ApplicationError("用户名或密码错误")
    return user


async def issue_refresh_token(session: AsyncSession, user_id: int) -> str:
    """签发刷新令牌并落库（数据库只保存 SHA-256 哈希）。"""
    token = create_refresh_token()
    session.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.app.jwt_refresh_expire_days),
        )
    )
    return token


async def rotate_refresh_token(
    session: AsyncSession,
    refresh_token: str,
) -> tuple[int, str] | None:
    """刷新令牌轮换：校验 → 撤销旧令牌 → 签发新令牌。

    返回 (user_id, 新刷新令牌)；令牌无效/过期/已撤销时返回 None。
    """
    hashed = hash_refresh_token(refresh_token)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hashed)
    )
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        return None

    # 轮换：撤销旧令牌，签发新令牌
    new_token = create_refresh_token()
    new_hashed = hash_refresh_token(new_token)
    row.revoked_at = now
    row.replaced_by = new_hashed
    session.add(
        RefreshToken(
            user_id=row.user_id,
            token_hash=new_hashed,
            expires_at=now + timedelta(days=settings.app.jwt_refresh_expire_days),
        )
    )
    return row.user_id, new_token


async def revoke_refresh_token(session: AsyncSession, refresh_token: str) -> None:
    """退出登录：撤销指定刷新令牌。"""
    hashed = hash_refresh_token(refresh_token)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hashed)
    )
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
