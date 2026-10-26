import re
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.schemas import RouteResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
你是法律咨询平台智能客服的意图识别节点，请判断用户消息应该交给哪个工作流。

intent 只能从以下选项中选择：
- legal_qa：劳动法律咨询（工时、加班费、解除补偿、未签合同二倍工资、工伤、仲裁程序及时效、维权方式等），包括询问“公司拖欠工资/辞退我怎么办”这类寻求法律解答的咨询
- human_handoff：投诉、高风险问题或用户明确要求人工服务
- chitchat：与劳动法律业务无关的普通聊天
- fallback：无法判断用户意图
""".strip()


class IntentRouter:

    def __init__(self) -> None:
        model = init_chat_model(
            model=settings.llm.chat_model,
            model_provider="deepseek",
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
        )
        self.model = model.with_structured_output(RouteResult)

    async def route(self, message: str, context: str) -> RouteResult | str:
        social_intent = match_social_intent(message)
        if social_intent:
            return response_by_social_intent(social_intent)
        try:
            result = await self.model.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=f"历史对话信息：{context}\n用户本轮消息：{message}\n"),
                ]
            )
            logger.info("模型意图识别完成", route_result=result)
            return result
        except Exception:
            logger.exception("模型意图识别失败")
            return RouteResult(intent="fallback", reason="模型意图识别失败")


SocialIntent = Literal["greeting", "thanks", "goodbye"]
SOCIAL_PATTERNS = {
    "greeting": (r"(你|您)?好(呀|啊|哦)?", r"嗨", r"哈喽", r"hello", r"hi", r"在吗"),
    "thanks": (r"谢谢(你|您)?", r"多谢(你|您)?", r"感谢(你|您)?", r"辛苦了"),
    "goodbye": (r"再见", r"拜拜", r"先这样", r"没事了"),
}
SOCIAL_RESPONSES = {
    "greeting": "您好，我是劳动法律咨询助手，可以帮您检索劳动法规、解答劳动法律问题。",
    "thanks": "不客气，后续有劳动法律问题可以随时问我。",
    "goodbye": "好的，后续需要帮助时随时联系我。",
}


def normalize_message(message: str) -> str:
    return re.sub(r"[\s，。！？、,.!?~～]", "", message).lower()


def match_social_intent(message: str) -> SocialIntent | None:
    normalized = normalize_message(message)
    for intent, patterns in SOCIAL_PATTERNS.items():
        if any(re.fullmatch(pattern, normalized) for pattern in patterns):
            return intent
    return None


def response_by_social_intent(intent: SocialIntent) -> str:
    return SOCIAL_RESPONSES.get(intent, "")


intent_router = IntentRouter()
