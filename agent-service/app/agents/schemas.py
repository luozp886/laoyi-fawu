from dataclasses import dataclass
from typing import Annotated, Any, Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class LegalAgentContext:
    """法律顾问 Agent 运行时上下文"""

    user_id: int


# 意图常量：主图分支
Intent = Literal[
    "chitchat",      # 与法律业务无关的闲聊
    "legal_qa",      # 劳动法规咨询（RAG）
    "human_handoff", # 转人工
    "fallback",      # 无法判断
]


class RouteResult(BaseModel):
    """意图识别结果"""

    intent: Intent = Field(description="本轮消息应该进入的工作流")
    reason: str = Field(description="判断该意图的理由")


AdditionalInfo = dict[str, Any]


def merge_additional_info(
    left: dict[str, AdditionalInfo] | None,
    right: dict[str, AdditionalInfo] | None,
) -> dict[str, AdditionalInfo]:
    """合并 additional_info 状态（LangGraph 通道 reducer）。

    注意：不能调用 dict.update() 后返回其返回值——update() 原地修改但返回 None，
    会导致通道值被写成 None，进而引发历史查询 500 与子图合并崩溃。
    这里两侧都做空值兜底，并返回一份新字典（不原地修改）。
    """
    left = left or {}
    right = right or {}
    return {**left, **right}


class LegalAgentState(MessagesState):
    """法律顾问主 Graph 状态"""

    active_workflow: Intent
    previous_workflow: Intent
    additional_info: Annotated[
        dict[str, AdditionalInfo],
        merge_additional_info,
    ]
