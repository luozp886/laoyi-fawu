import json

from langchain.tools import ToolRuntime, tool
from fastapi.encoders import jsonable_encoder
from langgraph.config import get_stream_writer
from langgraph.types import interrupt

from app.agents.schemas import LegalAgentContext
from app.documents.builder import build_document
from app.documents.registry import get_field_labels, get_required_fields
from app.infra.database import AsyncSessionFactory
from app.modules.document.repository import DocumentTemplateRepository
from app.modules.document.schemas import CasePlanCreate
from app.modules.document.service import (
    CasePlanService,
    DocumentTemplateService,
    GeneratedDocumentService,
)


@tool
async def query_document_templates(
    categories: list[str] | None = None,
    limit_per_category: int = 5,
) -> list[dict]:
    """按纠纷类别查询可用于推荐的候选法律文书模板。

    Args:
        categories: 纠纷类别列表，可选值 arbitration/termination/wage/injury/contract；为空则查全部。
        limit_per_category: 每类最多返回数量，默认 5。
    """
    cats = categories or ["arbitration", "termination", "wage", "injury", "contract"]
    result: list[dict] = []
    async with AsyncSessionFactory() as session:
        service = DocumentTemplateService(session)
        for cat in dict.fromkeys(cats):
            rows = await service.list_templates(cat)
            for row in rows[:limit_per_category]:
                labels = get_field_labels(row.template_key)
                result.append({
                    "template_id": row.id,
                    "name": row.name,
                    "category": row.category,
                    "doc_type": row.doc_type,
                    "target_scenario": row.target_scenario,
                    "template_key": row.template_key,
                    # 该文书需向用户收集的要素（供 Agent 提问）
                    "required_fields": [
                        {"key": k, "label": labels.get(k, k)}
                        for k in get_required_fields(row.template_key)
                    ],
                })
    return result


@tool
async def query_legal_provision(query: str) -> str:
    """从劳动法规知识库检索相关法条。回答法律问题时先调用本工具，再依据检索结果作答。"""
    from app.rag import retriever

    chunks = await retriever.retrieve(query, 5)
    if not chunks:
        return "没有检索到相关法条。"

    sources = {
        f"ref-{i:03d}": {
            "doc_id": chunk.doc_id,
            "doc_title": chunk.doc_title,
            "section_path": chunk.section_path,
            "content": chunk.content,
        }
        for i, chunk in enumerate(chunks, start=1)
    }
    writer = get_stream_writer()
    writer({"type": "additional_info", "data": sources})
    return json.dumps(sources, ensure_ascii=False)


@tool
async def save_case_plan(
    plan: CasePlanCreate,
    runtime: ToolRuntime[LegalAgentContext],
) -> dict[str, str]:
    """请用户确认后，保存针对当前案情的维权处理方案（推荐文书 + 理由 + 依据法条）。"""
    decision = interrupt(
        {
            "plan": plan.model_dump(mode="json"),
            "confirm_info": "是否确认保存这份维权处理方案？",
            "action": ["approve", "reject"],
        }
    )
    if decision.get("action") != "approve":
        return {"message": f"用户取消了保存维权方案，原因：{decision.get('reject_reason')}"}

    items = [
        {
            "template_id": it.template_id,
            "recommendation_reason": it.recommendation_reason,
            "law_basis": it.law_basis,
        }
        for it in plan.items
    ]
    async with AsyncSessionFactory() as session:
        service = CasePlanService(session)
        plan_id = await service.create_plan(
            user_id=runtime.context.user_id,
            plan_name=plan.plan_name,
            summary=plan.summary,
            case_profile=plan.case_profile,
            items=items,
        )
    return {"plan_id": str(plan_id), "message": "维权处理方案已保存"}


@tool
async def generate_document(
    template_id: int,
    elements: dict[str, str],
    runtime: ToolRuntime[LegalAgentContext],
) -> dict[str, str]:
    """校验要素齐全后，把用户已填要素拼装成法律文书并保存、返回正文。

    只有当某文书的 required_fields 都齐备时才可调用；缺要素时返回缺失项，由顾问继续提问。
    """
    async with AsyncSessionFactory() as session:
        repo = DocumentTemplateRepository(session)
        template = await repo.find_by_id(template_id)
    if template is None:
        return {"message": f"文书模板不存在：{template_id}"}

    required = get_required_fields(template.template_key)
    labels = get_field_labels(template.template_key)
    missing = [labels.get(k, k) for k in required if not str(elements.get(k, "")).strip()]
    if missing:
        return {"message": f"还缺少以下要素：{'、'.join(missing)}。请补充后再生成。"}

    title, body = build_document(template.template_key, dict(elements))

    decision = interrupt(
        {
            "confirm_info": "是否确认生成《" + title + "》？",
            "action": ["approve", "reject"],
            "preview": body,
        }
    )
    if decision.get("action") != "approve":
        return {"message": f"用户取消生成文书，原因：{decision.get('reject_reason')}"}

    async with AsyncSessionFactory() as session:
        service = GeneratedDocumentService(session)
        doc_id = await service.save_generated(
            user_id=runtime.context.user_id,
            plan_id=None,
            template_id=template.id,
            title=title,
            elements=dict(elements),
            law_citations=[],
            body_text=body,
            html=None,
        )
    return {
        "doc_id": str(doc_id),
        "title": title,
        "body": body,
        "message": "文书生成成功",
    }
