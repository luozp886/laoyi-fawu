from uuid import UUID, uuid4

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, CreateAtMixin, UpdateAtMixin


class ChatThread(Base, CreateAtMixin, UpdateAtMixin):
    """客服会话"""

    __tablename__ = "chat_threads"

    # UUID：全局唯一标识码，使用uuid4生成
    id: Mapped[UUID] = mapped_column(
        # as_uuid=True 要为True，否则会当成字符串，字符串的效率就低了
        # 存储到表中时，它的类型不是string，而是uuid类型
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(
        String(200),
        default="新会话",
        server_default="新会话",
    )
    # 创建时间、更新时间字段，来自父类 Mixin：CreateAtMixin, UpdateAtMixin
