# 劳动法律咨询平台 —— 测试报告

> 生成日期：2026-09-16（更新：补齐 JWT 鉴权拦截 / 双 token 刷新；精简为「法规检索 + AI 咨询」，移除劳务文档维护）
> 范围：agent-service 后端核心逻辑（认证鉴权 / 法规检索 / 问答链路）+ 前端构建

## 1. 测试环境

| 项 | 值 |
| --- | --- |
| 后端 | Python 3.14.4（.venv），FastAPI，uv 管理依赖 |
| 测试框架 | pytest 9.1.1（含 fastapi TestClient 冒烟测试） |
| 前端 | Vite 6.4.3 + TypeScript 5.6.3 + React 18（antd 5） |
| 运行方式 | `uv run pytest`（后端）/ `npm run build`（前端） |

## 2. 单元 / 集成测试（pytest，11 项全部通过）

### 2.1 密码与令牌 `tests/test_auth.py`（6 项）

| 用例 | 断言要点 |
| --- | --- |
| 密码哈希往返 | argon2 哈希可校验、错误密码被拒绝（pwdlib） |
| 访问令牌签发 | JWT 能解析出用户 id 且 `type=access`（pyjwt, HS256） |
| 无效令牌拒绝 | 伪造/错误类型令牌 → 401 |
| 刷新令牌 | 随机不透明串，SHA-256 哈希与原文不同、长度 64 |
| 白名单 | `/health`、`/api/v1/auth/login` 等放行；`/chat`、`/chat-threads` 需鉴权 |
| 鉴权依赖三步校验 | 缺 token → 401；非 Bearer → 401；无效 token → 401；有效 token → 放行返回用户 id |

### 2.2 双 token 刷新 `tests/test_refresh_tokens.py`（4 项）

| 用例 | 断言要点 |
| --- | --- |
| 刷新轮换 | 有效 refresh token → 撤销旧令牌并签发新令牌 |
| 过期拒绝 | 过期 refresh token → 返回 None（拒绝续期） |
| 已撤销拒绝 | 已撤销 refresh token → 返回 None（拒绝续期） |
| 登出撤销 | revoke 后令牌标记 revoked_at |

### 2.3 端到端鉴权冒烟 `tests/test_auth_flow.py`（1 项）

内存伪会话替换 `get_session`，验证完整链路：注册返回双 token → 无 token 访问受保护接口 401 →
无效 token 401 → 有效 access token 放行 → `/auth/refresh` 轮换出新 token →
旧 refresh token 复用 401 → 白名单路径无需鉴权。

## 3. 静态与构建验证

| 项 | 命令 | 结果 |
| --- | --- | --- |
| 后端语法编译 | `python -m compileall app scripts tests` | 通过（0 error） |
| 后端测试套件 | `uv run pytest -q` | 11 passed |
| 接口注册 | FastAPI OpenAPI schema 生成 | 全部注册；受保护接口标注 HTTPBearer |
| 前端类型检查与构建 | `npm run build` | 通过（tsc + vite build 成功） |

## 4. 知识库与对话链路验证（实测）

- **知识库**：6 部劳动法规按**条文级**分块入库（Milvus 集合 legal_collection + PostgreSQL knowledge_chunks），
  `uv run python scripts/ingest_rag.py` 重导完成。
- **对话链路**：意图路由 → legal_qa（法规问答 Agent）→ `query_legal_provision` 工具检索 → 回答流式返回并推送
  `clause_sources`（条文名 / 条文号 / 章节路径 / 法条原文）。实测样例：
  - “公司违法辞退我，能拿赔偿金吗？” → 检索命中《劳动合同法》第八十七条（2N 赔偿）、实施条例第二十五条、解释（一）等，回答引用 [ref-xxx] 标记，前端可点击查看法条原文。
  - “公司拖欠我三个月工资，我能要回吗？” → 命中《劳动法》第五十条、《劳动合同法》第八十五条（加付赔偿金）、《劳动争议调解仲裁法》第九条，回答含维权途径。
- **前端**：首页定位“劳动法规检索 · AI 法律咨询”，登录后进入咨询对话页（会话列表 + 多轮对话 + 法条引用卡片）。

## 5. 覆盖说明与遗留

- 单测未覆盖 RAG 检索链路（依赖 Milvus 与语料导入）与 Agent 对话流（依赖大模型 API），以第 4 节端到端实测作为补充验证。
- 鉴权：注册/登录/刷新/登出接口（argon2 密码哈希 + JWT 双 token），受保护接口统一拦截，
  演示账号「骆智鹏 / 123456」（id=1）；access token 默认 120 分钟，refresh token 默认 7 天。
- 数据库：虚拟机 PostgreSQL 使用实际可用凭据（insurance / insurance123，库名 legal）；
  已预置演示账号与条文级知识库；升级旧库需执行 `deploy/postgres/init/03-auth-docs-upgrade.sql`（补充 refresh_tokens 表）。
- 本项目由保险咨询 demo（hm-insurance）改造而来，README 与设计文档中保留的「原 insurance ××」字样为转型记录，非残留代码。

## 6. 健壮性加固记录（2026-10-21）

针对“打开历史会话 500”等运行时问题做了一轮全面排查与防御性加固，修改后 `compileall` 通过、pytest 仍为 **11 passed**：

| 位置 | 问题 | 修复 |
| --- | --- | --- |
| `app/modules/chat_thread/service.py` | 会话在 Checkpointer 无状态（如旧库遗留会话）时 `snapshot.values` 为 None，查历史报 500 | `state_values = snapshot.values or {}` 防御取值；删除已废弃的 interrupt 残留逻辑（schemas 已无该字段） |
| `app/modules/chat/service.py` | ① 消息为空且无 decision 时构造 `HumanMessage(None)` 崩溃；② Agent 流式调用中途异常（如模型 API 故障）直接断流 | ① 空消息抛业务异常（400 友好提示）；② 整个流式循环 try/except，异常时向客户端输出友好提示并记录日志，流以 `[DONE]` 正常结束 |
| `app/agents/schemas.py` | **根因**：`merge_additional_info` 返回 `left.update(right)`，而 `dict.update()` 返回 None，多轮对话第二次合并引用信息时把状态通道写坏，导致历史查询 500、子图合并崩溃 | 两侧空值兜底，返回新字典 `{**left, **right}`；`chat_thread/service.py` 读取时再加 `or {}` 防御存量坏数据 |
| `app/rag/retriever.py` | 子块元数据缺 `parent_id` 时 `metadata["parent_id"]` 抛 KeyError | 改为 `.get("parent_id")` 并过滤空值 |
| `app/agents/chitchat.py` | 残留“生成法律文书”引导文案（文书功能已移除） | 改为引导咨询劳动法律问题 |
| `app/main.py` | 非业务异常无兜底，默认返回 HTML 堆栈页 | 新增全局 `Exception` 兜底处理器：完整堆栈写日志，统一返回 JSON 500（`INTERNAL_ERROR`） |
| 前端 `api.ts` / `AdvisorPage.tsx`（核查确认） | — | SSE 401 自动续期重试、非 2xx 解析后端提示、流中断显示错误并清理空消息，无需改动 |

修复验证：`python -m compileall app` 0 error；`pytest -q` 11 passed；对话/历史/引用卡片链路按第 4 节实测。
