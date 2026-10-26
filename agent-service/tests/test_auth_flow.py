"""端到端鉴权冒烟测试：注册 → 刷新令牌续期 → 受保护接口鉴权。

使用内存伪会话替换 get_session，不依赖真实数据库/Milvus：
验证双 token 签发、/auth/refresh 轮换、以及受保护路由
（白名单放行 / 缺 token 401 / 无效 token 401 / 有效 token 放行）的完整链路。
"""
from fastapi.testclient import TestClient

from app.infra.database import get_session
from app.main import app
from app.modules.user.models import RefreshToken, User


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class MemoryDB:
    def __init__(self):
        self.login_user: User | None = None
        self.refresh_tokens: list[RefreshToken] = []
        self.next_user_id = 1
        self.users: dict[int, User] = {}
        self.added: list = []


db = MemoryDB()


class FakeSession:
    def __init__(self, memory: MemoryDB):
        self.memory = memory

    @staticmethod
    def _hash_from_where(stmt) -> str | None:
        where = stmt.whereclause
        if where is None or not hasattr(where, "right"):
            return None
        right = where.right
        return getattr(right, "value", None) or getattr(right, "effective_value", None)

    async def scalar(self, stmt):
        entity = stmt.column_descriptions[0]["entity"] if stmt.column_descriptions else None
        if entity is User:
            return self.memory.login_user
        if entity is RefreshToken:
            hashed = self._hash_from_where(stmt)
            for token in self.memory.refresh_tokens:
                if hashed is None or token.token_hash == hashed:
                    return token
            return None
        return None

    async def scalars(self, stmt):
        return FakeScalarResult([])

    async def get(self, model, pk):
        if model is User:
            return self.memory.users.get(pk)
        return None

    def add(self, obj):
        if isinstance(obj, User):
            obj.id = self.memory.next_user_id
            self.memory.next_user_id += 1
            self.memory.users[obj.id] = obj
        elif isinstance(obj, RefreshToken):
            self.memory.refresh_tokens.append(obj)
        self.memory.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


def override_get_session():
    yield FakeSession(db)


app.dependency_overrides[get_session] = override_get_session
# TestClient 不触发 lifespan，此处给 app.state.agent 一个占位对象，
# 避免 chat-threads 路由构造 ChatThreadService 时访问不到 app.state.agent。
app.state.agent = object()
client = TestClient(app)


def test_full_auth_flow():
    # 1. 注册：返回双 token
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "测试用户", "email": "test@example.com", "password": "123456"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "测试用户"
    access_token = data["token"]
    refresh_token = data["refresh_token"]

    # 2. 受保护接口：无 token → 401
    assert client.get("/api/v1/chat-threads").status_code == 401
    # 3. 受保护接口：无效 token → 401
    assert (
        client.get("/api/v1/chat-threads", headers={"Authorization": "Bearer bad.token.here"}).status_code
        == 401
    )
    # 4. 受保护接口：有效 access token → 200
    threads = client.get(
        "/api/v1/chat-threads", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert threads.status_code == 200

    # 5. 刷新令牌续期：返回新的 access + refresh
    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refreshed.status_code == 200, refreshed.text
    refreshed_data = refreshed.json()
    assert refreshed_data["token"]
    assert refreshed_data["refresh_token"]
    assert refreshed_data["refresh_token"] != refresh_token  # 轮换

    # 6. 旧刷新令牌复用 → 401（已轮换撤销）
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}).status_code
        == 401
    )

    # 7. 白名单路径不需要鉴权
    assert client.get("/health").status_code == 200
    assert client.post("/api/v1/auth/login", json={}).status_code == 422  # 缺 body 是参数错误，而非 401

