-- 劳动法律智能咨询平台 —— 业务库 schema 与演示数据
-- 面向「劳动 / 劳动争议」领域的法律文书与咨询平台。
-- 表结构由 SQLAlchemy 模型（agent-service/app/modules/*）与之对齐，二者需保持一致。

CREATE TABLE IF NOT EXISTS app_metadata (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO app_metadata(key, value)
VALUES ('schema', 'labor-law-platform-baseline')
ON CONFLICT (key) DO NOTHING;

-- ==== 用户账户 ====
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==== 登录刷新令牌（双 token 机制：refresh token 只存 SHA-256 哈希） ====
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    replaced_by VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- ==== 劳务文档维护（上传后父子块入库 RAG 知识库） ====
CREATE TABLE IF NOT EXISTS law_documents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'other',
    file_name VARCHAR(255),
    source VARCHAR(300),
    content TEXT NOT NULL,
    rag_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    rag_error TEXT,
    uploaded_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_law_documents_rag_status CHECK (rag_status IN ('pending', 'ingested', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_law_documents_updated ON law_documents(updated_at DESC);

-- 文档自增 id 从 100 开始，避开内置法规知识库占用的 doc_id 1~6，防止上传文档覆盖内置法规索引
SELECT setval(pg_get_serial_sequence('law_documents', 'id'), 100, true);

-- ==== 法律文书模板（原 insurance products，作为商城“商品”） ====
-- category 取值：arbitration / termination / wage / injury / contract
CREATE TABLE IF NOT EXISTS document_templates (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    doc_type VARCHAR(80),                 -- 文书具体种类，如 仲裁申请书 / 解除通知 / 协议
    source_note VARCHAR(300),             -- 依据/来源提示（如“依据劳动争议调解仲裁法”）
    image_url TEXT,
    description TEXT,
    target_scenario VARCHAR(500),         -- 适用案情场景说明
    template_key VARCHAR(120) NOT NULL UNIQUE,  -- 对应代码端模板实现标识
    element_schema JSONB NOT NULL DEFAULT '{}'::jsonb, -- 该文书需向用户收集的要素定义
    highlights TEXT[],
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_document_templates_category CHECK (
        category IN ('arbitration', 'termination', 'wage', 'injury', 'contract')
    ),
    CONSTRAINT chk_document_templates_status CHECK (
        status IN ('active', 'inactive')
    )
);

CREATE INDEX IF NOT EXISTS idx_document_templates_category ON document_templates(category, status);
CREATE INDEX IF NOT EXISTS idx_document_templates_status   ON document_templates(status);

-- ==== 维权处理方案（原 insurance_plans，顾问根据案情生成的行动/文书建议组合） ====
CREATE TABLE IF NOT EXISTS case_plans (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    plan_name VARCHAR(120) NOT NULL,
    summary TEXT,
    case_profile JSONB NOT NULL DEFAULT '{}'::jsonb,   -- 案情画像/要素
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_case_plans_status CHECK (status IN ('draft', 'active', 'closed'))
);

CREATE TABLE IF NOT EXISTS case_plan_items (
    id UUID PRIMARY KEY,
    plan_id UUID NOT NULL REFERENCES case_plans(id) ON DELETE CASCADE,
    template_id BIGINT NOT NULL REFERENCES document_templates(id),
    priority INT NOT NULL DEFAULT 1 CHECK (priority >= 1),
    recommendation_reason TEXT,
    law_basis TEXT,                        -- 依据法条说明
    status VARCHAR(30) NOT NULL DEFAULT 'recommended',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_case_plan_items_status CHECK (status IN ('recommended', 'generated')),
    CONSTRAINT uk_case_plan_items_plan_template UNIQUE (plan_id, template_id)
);

CREATE INDEX IF NOT EXISTS idx_case_plans_user       ON case_plans(user_id, status);
CREATE INDEX IF NOT EXISTS idx_case_plan_items_plan  ON case_plan_items(plan_id, status);

-- ==== 生成的法律文书（用户填要素拼装出的成品） ====
CREATE TABLE IF NOT EXISTS generated_documents (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    plan_id UUID REFERENCES case_plans(id),
    template_id BIGINT NOT NULL REFERENCES document_templates(id),
    title VARCHAR(200) NOT NULL,
    elements JSONB NOT NULL DEFAULT '{}'::jsonb,      -- 用户填写的要素快照
    law_citations JSONB NOT NULL DEFAULT '[]'::jsonb, -- 引用法条来源列表
    body_text TEXT,                                   -- 成文正文
    html TEXT,                                        -- HTML 预览
    status VARCHAR(30) NOT NULL DEFAULT 'generated',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_generated_documents_status CHECK (
        status IN ('draft', 'generated', 'downloaded')
    )
);

CREATE INDEX IF NOT EXISTS idx_generated_documents_user ON generated_documents(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_documents_plan ON generated_documents(plan_id);

-- ==== 演示用户（与前端登录一致，密码为占位） ====
INSERT INTO users (id, username, email, password_hash, display_name, status)
VALUES (1, '骆智鹏', 'luozhipeng@example.com', '$argon2id$v=19$m=65536,t=3,p=4$QW0Z6QIrQ3+D3Mv9t/U6kA$O7omR3mER68od2LXCQvqP9PKmd/m1wAShI9FnnhSY00', '骆智鹏', 'active');

-- ==== 演示文书模板种子（约 11 份 / 5 类） ====
-- element_schema 字段由 Agent 逐项向用户收集，见切片2 文档引擎实现。
INSERT INTO document_templates (id, name, category, doc_type, source_note, target_scenario, template_key, highlights)
VALUES
-- arbitration 劳动仲裁
(1,  '劳动仲裁申请书',     'arbitration', '仲裁申请书', '依据《劳动争议调解仲裁法》', '工资、解除、赔偿等争议需要提起劳动仲裁时', 'labor_arbitration_application', ARRAY['劳动仲裁','法定受案范围','被申请人答辩']),
(2,  '劳动仲裁答辩状',     'arbitration', '答辩状', '依据《劳动争议调解仲裁法》', '用人单位作为被申请人收到申请书后应诉答辩', 'labor_arbitration_reply', ARRAY['答辩意见','时效抗辩']),
-- termination 解除与补偿
(3,  '被迫解除劳动合同通知书', 'termination', '解除通知', '依据《劳动合同法》第三十八条', '用人单位拖欠工资/未缴社保等，员工依法被迫解除劳动关系', 'forced_resignation_notice', ARRAY['被迫解除','经济补偿']),
(4,  '协商解除劳动合同协议书', 'termination', '解除协议', '依据《劳动合同法》第三十六条', '双方协商一致解除劳动关系并结清补偿', 'negotiated_termination_agreement', ARRAY['协商解除','一次性补偿','保密条款']),
(5,  '经济补偿金/赔偿金主张书', 'termination', '主张书', '依据《劳动合同法》第四十六、四十七、八十七条', '主张经济补偿金 N 或违法解除赔偿金 2N', 'compensation_claim', ARRAY['经济补偿N','赔偿金2N','计算说明']),
-- wage 工资与加班
(6,  '未签书面劳动合同二倍工资主张书', 'wage', '主张书', '依据《劳动合同法》第八十二条', '入职满一月未签书面合同，主张二倍工资差额', 'double_wage_claim', ARRAY['二倍工资','最长11个月']),
(7,  '加班费主张书',       'wage', '主张书', '依据《劳动合同法》第三十一、四十四条', '主张延时/休息日/法定节假日加班费', 'overtime_wage_claim', ARRAY['延时加班1.5倍','休息日2倍','节假日3倍']),
(8,  '拖欠工资(欠薪)主张书', 'wage', '主张书', '依据《劳动合同法》第三十、五十条', '用人单位拖欠、克扣劳动报酬', 'arrears_wage_claim', ARRAY['欠薪催讨','加付赔偿金']),
-- injury 工伤
(9,  '工伤认定申请书',     'injury', '认定申请', '依据《工伤保险条例》第十七条', '职工发生事故伤害或职业病后申请工伤认定', 'injury_identification_application', ARRAY['工伤认定','30日内申请','劳动关系证明']),
(10, '工伤待遇主张书',     'injury', '主张书', '依据《工伤保险条例》相关规定', '主张停工留薪期工资、医疗费、伤残补助等工伤待遇', 'injury_treatment_claim', ARRAY['停工留薪期','伤残补助','医疗待遇']),
-- contract 劳动合同
(11, '劳动合同(范本)',     'contract', '合同范本', '依据《劳动合同法》第十七条', '建立劳动关系时订立书面劳动合同', 'labor_contract_template', ARRAY['必备条款','试用期','工作内容'])
ON CONFLICT (id) DO NOTHING;
SELECT setval(pg_get_serial_sequence('document_templates', 'id'), 11, true);

-- ==== 表注释 ====
COMMENT ON TABLE document_templates IS '法律文书模板(咨询平台可售文书)；对应前端“文书浏览”的商品维度';
COMMENT ON TABLE case_plans IS 'AI 顾问根据案情生成的维权处理方案';
COMMENT ON TABLE generated_documents IS '用户经结构化问答填要素后拼装生成的法律文书成品';



