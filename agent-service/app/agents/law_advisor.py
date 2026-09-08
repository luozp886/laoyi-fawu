from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.agents.tools import (
    generate_document,
    query_document_templates,
    query_legal_provision,
    save_case_plan,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
你是“劳动法律维权顾问”，面向普通劳动者的劳动/劳动争议智能文书与咨询助手。
职责：
1. 用户描述案情后，先判断其归属的纠纷类别（仲裁/解除补偿/工资加班/工伤/合同）。
2. 调用 query_document_templates 查询适用的文书模板；涉及权利义务判断时调用 query_legal_provision 检索法条并给出依据。
3. 依据案情向用户说明维权路径，给出“维权处理方案”（推荐文书 + 理由 + 依据法条），并调用 save_case_plan 请用户确认保存。
4. 方案确认后，按所选文书的 required_fields 逐项向用户收集要素；收集齐全后调用 generate_document 生成文书。
5. 回答须基于检索到的法条，不得编造法条编号或内容；证据不足时如实说明并追问。
6. 文书与答复仅供模板参考，重大涉诉事项应提示用户咨询执业律师。回答简短、条理清楚。
"""


def init_law_advisor():
    """初始化劳动维权顾问（主 Agent）"""
    model = init_chat_model(
        model=settings.llm.chat_model,
        model_provider="deepseek",
        api_key=settings.llm.api_key,
        extra_body={"thinking": {"type": "disabled"}},
    )
    agent = create_agent(
        model=model,
        tools=[
            query_document_templates,
            query_legal_provision,
            save_case_plan,
            generate_document,
        ],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=True,
        name="law_advisor",
    )
    logger.info("劳动维权顾问子 Agent 初始化成功")
    return agent
