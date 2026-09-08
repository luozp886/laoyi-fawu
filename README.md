# 劳翼AI法务 —— 劳动法律智能文书与咨询平台（毕设）

把原「保险顾问项目 hm-insurance」整体换行业为 **劳动/劳动争议领域** 的
「文书商城 + AI 顾问 + 法规 RAG」平台。架构复用原 React + FastAPI + LangGraph + Milvus 骨架。

> 框架源自 hm-insurance；业务语义、schema、语料、Agent 均改为劳动法律领域。

## 核心能力
- **文书模板商城**：11 份劳动维权文书 / 5 类纠纷，可浏览、筛选。
- **劳动法律 AI 顾问**：用户描述案情 → 顾问分析纠纷类型 → 检索法条 → 给出「维权处理方案」（推荐文书+依据）→ 收集要素 → **结构化问答拼装生成文书**。
- **劳动法规 RAG**：父子块按「法规文档」粒度入库、检索并回引来源。
- 生成文书为受控模板填充 + 确定性计算（经济补偿 N / 违法解除 2N / 二倍工资 / 加班倍率），**不做模型自由起草**，规避编造法条。

## 目录结构
```
agent-service/            FastAPI + LangGraph 后端
  app/agents/             law_advisor / legal_qa / chitchat + 意图路由 + orchestrator
  app/agents/tools.py     query_document_templates / query_legal_provision / save_case_plan / generate_document
  app/documents/          calc.py 计算 · registry.py 要素 · builder.py 拼装正文
  app/modules/document/   模板目录 / 维权方案 / 生成文书 模块（含 REST）
  app/rag/                KnowledgeChunk 父子块 RAG（吃 markdown，非 PDF）
  data/legal/             4 部劳动法规文本（入库语料）
  scripts/ingest_rag.py   法规入库脚本
insurance-web/            React + AntD 前端（切片3 改造中）
deploy/                   postgres 初始化 SQL、milvus、docker-compose（基础设施）
docs/superpowers/specs/   设计 spec
```

## 数据库表（由 deploy/postgres/init 建）
- `document_templates`（文书模板，原 products）
- `case_plans` / `case_plan_items`（维权方案，原 insurance_plans）
- `generated_documents`（生成的文书，新增）
- `knowledge_chunks`（RAG 父块，原 parent_chunks，改为 doc_id 粒度）
- `users`、`chat_threads` 沿用。

## 运行 / 验证（基础设施在你那台 VM / docker）
1. 基础设施（postgres + milvus）起来后，在 postgres 建库并应用
   `deploy/postgres/init/01-…sql`、`02-…sql`（docker 会自动初始化）。
2. 复制 `agent-service/.env.example` 为 `.env`，改成你 VM 的 DB/MILVUS 与密钥。
3. 后端：
   ```bash
   cd agent-service && uv sync && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```
   自检：`GET /health` 应返回 ok。
4. 灌法规 RAG（需 milvus 可连、已建库）：
   ```bash
   cd agent-service && uv run python scripts/ingest_rag.py
   ```
5. 前端（本机可先行静态自验）：
   ```bash
   cd insurance-web && npm install && npm run build
   ```
   单网址访问由 nginx 网关兜住（前端静态页 + 代理后端 /api）。

## 说明
- 本机无 Docker/远程库时，只能做 `python -m compileall`、`npm run build` 等编译级自验；
  端到端运行时验证需在 VM/库就绪后进行。
- 法规与文书正文含**免责提示**：模板仅供参考，重大涉诉事项请咨询执业律师。
