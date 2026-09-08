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
    "law_advisor",   # 劳动维权顾问：案情→维权方案→生成文书
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
    left: dict[str, AdditionalInfo],
    right: dict[str, AdditionalInfo],
) -> dict[str, AdditionalInfo]:
    if not left:
        return right
    return left.update(right)


class LegalAgentState(MessagesState):
    """法律顾问主 Graph 状态"""

    active_workflow: Intent
    previous_workflow: Intent
    additional_info: Annotated[
        dict[str, AdditionalInfo],
        merge_additional_info,
    ]
