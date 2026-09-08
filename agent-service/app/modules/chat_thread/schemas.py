import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from uuid import UUID

class ChatThreadCreate(BaseModel):
    """创建会话请求参数"""
    # 会话标题
    # Field做校验：最小1，最大200字符，默认值"新会话"
    title: str = Field(default="新会话", min_length=1, max_length=200)

    # mode="before"：在类型转换、Field校验之前先执行清洗函数
    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip()  # 去掉字符串前后空格


class ChatThreadResponse(BaseModel):
    """会话功能响应数据类型"""
    id: UUID
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ChatMessageResponse(BaseModel):
    """历史消息"""

    role: Literal["user", "assistant"]
    content: str
    additional_info: Any | None = Field(default=None, description="该条AI消息使用的条款引用来源")


class ChatHistoryResponse(BaseModel):
    """会话历史响应"""

    thread_id: UUID
    messages: list[ChatMessageResponse]
    interrupt: Any | None = Field(default=None, description="尚未处理完成的中断（如保险方案待确认）")
