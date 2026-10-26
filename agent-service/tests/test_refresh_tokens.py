"""刷新令牌轮换逻辑测试（双 token 机制）：轮换、过期、已撤销场景。

使用伪 Session 隔离数据库，验证 rotate/revoke 的核心业务规则。
"""
import asyncio
from datetime import datetime, timedelta, timezone

from app.modules.user.models import RefreshToken
from app.modules.user.service import revoke_refresh_token, rotate_refresh_token


class FakeSession:
    """最小伪会话：scalar 返回预设行，add 记录新增对象。"""

    def __init__(self, row):
        self.row = row
        self.added = []

    async def scalar(self, stmt):
        return self.row

    def add(self, obj):
        self.added.append(obj)


def _token(expires_in: timedelta, *, revoked: bool = False) -> RefreshToken:
    return RefreshToken(
        user_id=3,
        token_hash="fake-hash",
        expires_at=datetime.now(timezone.utc) + expires_in,
        revoked_at=datetime.now(timezone.utc) if revoked else None,
    )


def test_rotate_refresh_token_success():
    """有效刷新令牌：撤销旧令牌并签发新令牌。"""
    old = _token(timedelta(days=7))
    session = FakeSession(old)
    result = asyncio.run(rotate_refresh_token(session, "refresh-token-abc"))
    assert result is not None
    user_id, new_token = result
    assert user_id == 3
    assert new_token
    assert old.revoked_at is not None
    assert len(session.added) == 1


def test_rotate_refresh_token_rejects_expired():
    """过期刷新令牌：返回 None（拒绝续期）。"""
    session = FakeSession(_token(timedelta(days=-1)))
    result = asyncio.run(rotate_refresh_token(session, "refresh-token-abc"))
    assert result is None


def test_rotate_refresh_token_rejects_revoked():
    """已撤销刷新令牌：返回 None（拒绝续期）。"""
    session = FakeSession(_token(timedelta(days=7), revoked=True))
    result = asyncio.run(rotate_refresh_token(session, "refresh-token-abc"))
    assert result is None


def test_revoke_refresh_token():
    """退出登录：撤销刷新令牌。"""
    token = _token(timedelta(days=7))
    session = FakeSession(token)
    asyncio.run(revoke_refresh_token(session, "refresh-token-abc"))
    assert token.revoked_at is not None
