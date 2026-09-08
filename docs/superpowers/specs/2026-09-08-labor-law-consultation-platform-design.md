# 法律智能咨询平台(劳动领域)改造设计 Spec

- 日期:2026-09-08
- 基线:ac01e36(保险顾问项目改造前快照)
- 背景:毕业设计。将现有「保险顾问项目 hm-insurance」整体换行业为「面向劳动/劳动争议领域的 AI 智能文书与咨询平台」。

## 1. 目标与边界

在**不改动现有多 Agent 编排骨架、LangGraph 状态图、聊天线程/鉴权/前端框架**的前提下,把领域语义从「保险」平移到「劳动法律」,并新增核心能力「结构化问答收集案情要素 → 受控模板拼装生成可下载法律文书」。

### 决策记录(已由用户确认)
1. 领域收敛:**劳动 / 劳动争议**。
2. 商城形态:**法律文书产品化**(product=文书模板),保留商品浏览 + 方案 + 下单闭环。
3. 文书生成方式:**结构化问答 → 填模板拼装**(非 AI 自由整篇起草)。docx 优先,附 HTML 预览。
4. 内容铺真度:**精选 10 份文书 + 真实法条 RAG**(约10份文书、多份真实法规)。
5. 目标用户:**个人用户自助**(保留登录、无后台管理端,与现状一致)。
6. 版本控制:已 `git init` 并建立改造前基线提交,后续改动以增量提交推进。

## 2. 概念映射

| 保险(现状) | 劳动法律(目标) |
|---|---|
| 保险产品 `products`(类别=险种) | **法律文书模板** `document_templates`(类别=纠纷类型) |
| 险种:medical/critical_illness/accident/life | 类别:`contract 合同`·`termination 解除与补偿`·`wage 工资与加班`·`injury 工伤`·`arbitration 劳动仲裁` |
| 保险方案 `insurance_plans`(需求→组合+保额预算) | **维权处理方案** `case_plans`(案情→建议文书/行动步骤/依据法条),项含理由 |
| 投保下单 → 保单 | **生成的法律文书** `generated_documents`(结构化要素 + 成文文本 + 下载记录 + 状态) |
| `insurance_advisor`(需求→推荐方案) | `law_advisor`(案情分析→出维权方案→引导生成文书) |
| `claim`(理赔) | `legal_qa`(劳动法规咨询,RAG 问答) |
| `chitchat` | 保留 `chitchat` |
| 商品字段:insurer/premium/target_group | 字段:`category`/适用场景(案情类型)/文书模板引用/`element_schema`(要素 Schema)/主文模板 |
| RAG 条款 PDF 库 | RAG **劳动法规库**(纯文本/markdown 切分) |

## 3. 文书目录(初版 11 份,分 5 类)

- `arbitration` 劳动仲裁:① 劳动仲裁申请书 ② 劳动仲裁答辩状
- `termination` 解除与补偿:③ 被迫解除劳动合同通知书 ④ 协商解除劳动合同协议书 ⑤ 经济补偿金/赔偿金主张书
- `wage` 工资与加班:⑥ 未签书面劳动合同二倍工资主张书 ⑦ 加班费主张书 ⑧ 拖欠工资(欠薪)主张书
- `injury` 工伤:⑨ 工伤认定申请书 ⑩ 工伤待遇(赔偿)主张书
- `contract` 合同:⑪ 劳动合同(范本)

每份文书含一段**要素 Schema** 定义(JSON),说明需向用户收集的字段(如当事人信息、入职时间、月工资、是否签合同、解除原因、加班记录、主张金额及计算方式、证据线索等),以及可选的受控计算逻辑(经济补偿 N、二倍工资月数、加班费倍率、工伤待遇项目)。

## 4. 系统结构

沿用现状分层,仅替换/新增领域单元:
- `app/agents/law_advisor.py`:主顾问。流程 = 案情理解 → (RAG 佐证)判断纠纷类型/适用文书 → 调用「保存维权方案」人工确认 → 逐项收集要素 → 生成文书。
- `app/agents/legal_qa.py`:面向法规条文与劳动政策的自由问答(RAG 召回 + 来源引用 + 免责声明)。
- `app/agents/orchestrator.py`:状态图节点改为 `chitchat / law_advisor / legal_qa / human_handoff / fallback`。
- `app/agents/tools.py`:
  - `query_document_templates(categories)` — 按纠纷类别查询候选文书模板。
  - `save_case_plan(...)` — 保存维权方案(带 `interrupt` 人工确认,复用现有机制)。
  - `query_legal_provision(query, ...)` — RAG 检索法条并流式返回引用来源。
  - (新增)`generate_document(product_id, elements)` — 校验要素齐全 → 填模板拼装成文 → 落库为 `generated_documents` → 返回可下载产物。
- `app/modules/product` → 改造为「文书模板」数据模型与增删查。
- `app/modules/insurance_plan` → 改造为「维权方案 case_plan」。
- (新增)`app/modules/document` — 生成的文书:要素快照(JSONB)+ 成文文本 + 状态(draft→generated→downloaded)+ 下载(.docx/.html)。
- `app/rag/` 与 `scripts/ingest_rag.py`:语料由保险条款 PDF 换为劳动法规文本(见 §6)。

### 模板拼装器
- 新增 `app/documents/`:
  - `element_schemas.py` — 每份文书的要素 Schema 定义与校验。
  - `builder.py` — 纯 Python 模板渲染(以受控占位符/`str.format` 或轻量模板实现,不引入不可控自由生成);负责把要素渲染进主文模板、按需计算补偿金额。
  - `render.py` — 产出成文文本、HTML 预览;`.docx` 生成(引入 `python-docx`)。
  - 每份生成文书正文末尾固定追加**免责声明**:内容仅作模板参考,不构成正式法律意见;重大/涉诉事项建议咨询执业律师。AI 客服层同步输出免责提示。

## 5. 数据流(一条主流程)

1. 用户在首页浏览文书/维权入口 → 进 `AdvisorPage` 对话。
2. 意图路由识别 `law_advisor` → 用户描述案情。
3. `law_advisor` 调用 `query_document_templates` 找出候选文书 + `query_legal_provision` 引法条 → 生成「维权方案」(建议文书/行动/依据),`save_case_plan` 抛中断给用户 **确认/拒绝**。
4. 确认后,顾问按文书要素 Schema 逐项提问收集(`工资?入职时间?有无书面合同?加班事实?…`)。
5. 要素齐 → 调 `generate_document`:校验 → 拼装 → 计算 → 落库为 `generated_documents`(draft→generated)→ 返回。
6. 前端新「文书详情/生成」页展示成文文本与法条引用,可**下载 .docx** 或 HTML 预览打印;生成记录进入「我的文书」供再次查看。

## 6. 语料与数据改造

- `agent-service/data/raw/kb/`:替换为真实法规纯文本,至少含:**《中华人民共和国劳动法》《劳动合同法》《劳动争议调解仲裁法》《劳动合同法实施条例》**、最高法**关于审理劳动争议案件适用法律问题的解释(一)**、常见地方性规范与工时/休假政策节选。来源标注于文档头。
- 各文书「范本要素」以文本/markdown 存 `agent-service/data/documents/`(文档模板源)。
- 种子数据(文书目录、类别、分类标签文案)重写进种子脚本/迁移。
- 现保险条款 PDF、费率表 PDF 从 `data/raw/` 移除或隔离(不在新库引用)。

## 7. 前端改造(insurance-web)

- `src/categoryLabels.ts`、`types.ts`、`ProductCard.tsx`:字段/文案改为文书模板与纠纷类别(移除 insurer/premium 语义,替换为 适用场景/文书类型/模板示意)。
- `HomePage.tsx`:商品浏览 →「法律文书与维权服务」浏览(按 5 类筛选)。
- `AdvisorPage.tsx`:聊天入口文案 → 劳动法律 AI 顾问(标注"专业建议仅供参考")。
- `ApplicationPage.tsx`:投保流程 → 「文书生成/下载」向导页(展示维权方案→ 要素填写 → 成文预览/下载),复用其表单+步骤交互骨架。
- 新增附加信息渲染支持法条来源引用与生成的文书产物(扩展 `additionalInfo.ts`/`MarkdownMessage` 兼容)。样式统一改品牌色/标题(前端 design 阶段落地)。

## 8. 测试与验收

- 单元:模板拼装器(要素齐全→正确成文;缺要素→报出缺失项);补偿金额计算逻辑对照样例断言。
- 意图路由:案情典型句 → 命中 `law_advisor`;纯闲聊 → `chitchat`;纯法规问答 → `legal_qa`。
- RAG:给定问题召回相关法条并返回引用来源。
- 端到端(主流程):首页→对话案情→确认方案→填要素→生成→下载 .docx。
- 安全/免责:所有 AI 与文书输出含免责声明。
- 验收跑通:**仓库有改造前基线**;前端 `npm run build` 通过;`agent-service` 可启动、RAG 可入库检索。

## 9. 非目标 / 后续可延展
- 不接真实支付、不接律协/真实律师资质、不做后台管理端(保持现状个人自助)。
- 后续可扩:更多领域、AI 起草辅助段落(加校验)、要素的 LLM 自动抽取、文书在线编辑。

## 10. 实施步骤建议(将转入 writing-plans 展开)
1. 语料与种子数据替换(法规入库 + 文书目录 + 要素 Schema)。
2. 后端领域改名:models/schemas/service/router、agents、tools、orchestrator、rag 引用。
3. 新增 document 模块与模板拼装器、`.docx` 渲染。
4. 前端文案/字段/页面改造 + 新增文书生成页与引用渲染。
5. RAG 入库脚本改造与重灌。
6. 测试 + 构建 + 端到端验收。
