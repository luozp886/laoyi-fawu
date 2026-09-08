from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.chitchat import init_chitchat_agent
from app.agents.intent_router import intent_router
from app.agents.law_advisor import init_law_advisor
from app.agents.legal_qa import init_legal_qa
from app.agents.schemas import Intent, LegalAgentContext, LegalAgentState

# 意图常量：chitchat / law_advisor / legal_qa / human_handoff / fallback


async def route_node(state: LegalAgentState) -> Command[Intent]:
    """意图识别节点"""
    previous_workflow = state.get("active_workflow", "")
    previous_ai_message = find_previous_ai_message(state["messages"])
    context = f"上轮对话工作流:{previous_workflow}\n上轮对话AI回复:{previous_ai_message}"
    result = await intent_router.route(state["messages"][-1].content, context)

    if isinstance(result, str):
        return Command(
            update={
                "messages": [AIMessage(content=result)],
                "previous_workflow": previous_workflow,
                "active_workflow": "chitchat",
            },
            goto=END,
        )

    return Command(
        update={
            "previous_workflow": previous_workflow,
            "active_workflow": result.intent,
        },
        goto=result.intent,
    )


def find_previous_ai_message(messages: list[BaseMessage]) -> str:
    """查找本轮用户消息之前最近一条可展示的 AI 回复"""
    for message in reversed(messages[:-1]):
        if not isinstance(message, AIMessage):
            continue
        if message.tool_calls:
            continue
        if message.text:
            return message.text
    return ""


def human_handoff_node(state: LegalAgentState) -> dict:
    return {"messages": [AIMessage("已记录转人工请求，后续可接入人工客服系统。")]}


def fallback_node(state: LegalAgentState) -> dict:
    return {
        "messages": [
            AIMessage("我还不能确定您的需求。请说明是想咨询劳动法律问题，还是想根据案情生成维权文书。")
        ]
    }


def init_legal_orchestrator(checkpointer: AsyncPostgresSaver):
    """初始化法律顾问主 Graph"""
    builder = StateGraph(
        LegalAgentState,
        context_schema=LegalAgentContext,
    )
    builder.add_node("route", route_node)
    builder.add_node("chitchat", init_chitchat_agent())
    builder.add_node("law_advisor", init_law_advisor())
    builder.add_node("legal_qa", init_legal_qa())
    builder.add_node("human_handoff", human_handoff_node)
    builder.add_node("fallback", fallback_node)

    builder.add_edge(START, "route")
    builder.add_edge("chitchat", END)
    builder.add_edge("law_advisor", END)
    builder.add_edge("legal_qa", END)
    builder.add_edge("human_handoff", END)
    builder.add_edge("fallback", END)

    return builder.compile(checkpointer=checkpointer)
