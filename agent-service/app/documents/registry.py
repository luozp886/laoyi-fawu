"""文书模板注册表：定义每份文书要收集的要素（中文提问标签 + 是否必填）。

Agent 依据 required 要素向用户逐项提问；generate_document 依据它做校验；
builder 依据这些要素拼装正文。此注册表为代码侧“单一事实来源”。
"""
from __future__ import annotations

# 字段：key 存于 elements；label 用于问用户；required 用于校验
F = lambda key, label, required=True: {"key": key, "label": label, "required": required}

COMMON_APPLICANT = [
    F("applicant_name", "申请人(员工)姓名"),
    F("applicant_phone", "联系电话"),
    F("applicant_idno", "身份证号"),
    F("applicant_address", "住址"),
]
COMMON_RESPONDENT = [
    F("company", "用人单位名称"),
    F("company_address", "用人单位地址"),
    F("respondent_legal_rep", "用人单位法定代表人", required=False),
]
COMMON_EMPLOYMENT = [
    F("entry_date", "入职日期"),
    F("position", "工作岗位"),
    F("monthly_wage", "月工资(元)"),
]
COMMON_FACTS = [
    F("facts", "争议事实简述"),
]

TEMPLATE_REGISTRY: dict[str, dict] = {
    "labor_arbitration_application": {
        "title": "劳动仲裁申请书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT + COMMON_EMPLOYMENT +
            [
                F("years", "工作年限(年)"),
                F("claim_items", "请求事项(分条写)"),
                F("evidence", "主要证据线索", required=False),
            ] + COMMON_FACTS
        ),
    },
    "labor_arbitration_reply": {
        "title": "劳动仲裁答辩状",
        "fields": [
            F("applicant_name", "申请人姓名"),
            F("company", "答辩人(单位)名称"),
            F("reply_position", "答辩意见正文"),
            F("facts", "事实与理由简述"),
        ],
    },
    "forced_resignation_notice": {
        "title": "被迫解除劳动合同通知书",
        "fields": (
            [
                F("company", "用人单位名称"),
                F("applicant_name", "员工姓名"),
                F("entry_date", "入职日期"),
                F("notice_date", "发出通知日期"),
                F("force_reason", "被迫解除的具体事由(如未足额支付工资/未缴社保等)"),
            ] + COMMON_FACTS
        ),
    },
    "negotiated_termination_agreement": {
        "title": "协商解除劳动合同协议书",
        "fields": [
            F("company", "甲方(用人单位)名称"),
            F("applicant_name", "乙方(员工)姓名"),
            F("entry_date", "入职日期"),
            F("end_date", "解除日期"),
            F("monthly_wage", "月工资(元)"),
            F("years", "工作年限(年)"),
            F("termination_package", "经济补偿/款项总金额(元)", required=False),
            F("facts", "其他约定事项", required=False),
        ],
    },
    "compensation_claim": {
        "title": "经济补偿金/赔偿金主张书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT +
            [
                F("entry_date", "入职日期"),
                F("end_date", "解除/终止日期"),
                F("years", "工作年限(年)"),
                F("monthly_wage", "解除前十二个月平均工资(元)"),
                F("claim_kind", "主张类型(经济补偿金N 或 违法解除赔偿金2N)"),
                F("facts", "解除事由简述"),
            ]
        ),
    },
    "double_wage_claim": {
        "title": "未签书面劳动合同二倍工资主张书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT +
            [
                F("entry_date", "入职日期"),
                F("contract_signed_date", "实际补签/应签截止日期", required=False),
                F("months", "二倍工资差额月数(最长11)"),
                F("monthly_wage", "月工资(元)"),
                F("facts", "未签合同事实简述"),
            ]
        ),
    },
    "overtime_wage_claim": {
        "title": "加班费主张书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT +
            [
                F("monthly_wage", "月工资(元)"),
                F("weekday_hours", "延时加班小时数"),
                F("weekend_hours", "休息日加班小时数"),
                F("holiday_hours", "法定节假日加班小时数"),
                F("facts", "加班事实简述"),
            ]
        ),
    },
    "arrears_wage_claim": {
        "title": "拖欠工资(欠薪)主张书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT +
            [
                F("period", "被拖欠工资的期间"),
                F("arrears_amount", "被拖欠工资金额(元)"),
                F("monthly_wage", "月工资(元)"),
                F("facts", "欠薪事实简述"),
            ]
        ),
    },
    "injury_identification_application": {
        "title": "工伤认定申请书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT +
            [
                F("injury_date", "事故发生日期"),
                F("injury_place", "事故发生地点"),
                F("injury_desc", "事故经过及伤情描述"),
                F("facts", "劳动关系证明情况", required=False),
            ]
        ),
    },
    "injury_treatment_claim": {
        "title": "工伤待遇主张书",
        "fields": (
            COMMON_APPLICANT + COMMON_RESPONDENT +
            [
                F("level", "劳动能力鉴定伤残等级", required=False),
                F("stop_pay_monthly", "停工留薪期月工资(元)", required=False),
                F("stop_months", "停工留薪期月数", required=False),
                F("medical_amount", "医疗费等主张金额(元)", required=False),
                F("facts", "工伤待遇争议事实简述"),
            ]
        ),
    },
    "labor_contract_template": {
        "title": "劳动合同(范本)",
        "fields": [
            F("company", "甲方(用人单位)名称"),
            F("company_address", "甲方地址"),
            F("respondent_legal_rep", "法定代表人", required=False),
            F("applicant_name", "乙方(劳动者)姓名"),
            F("applicant_idno", "乙方身份证号"),
            F("position", "工作岗位"),
            F("work_place", "工作地点", required=False),
            F("monthly_wage", "试用期月工资/约定工资(元)"),
            F("entry_date", "合同开始日期"),
            F("end_date", "合同结束日期", required=False),
            F("facts", "其他约定条款", required=False),
        ],
    },
}

# 兼容 API：返回某模板 key 必填要素名列表
def get_required_fields(template_key: str) -> list[str]:
    conf = TEMPLATE_REGISTRY.get(template_key)
    if not conf:
        return []
    return [f["key"] for f in conf["fields"] if f["required"]]


def get_field_labels(template_key: str) -> dict[str, str]:
    conf = TEMPLATE_REGISTRY.get(template_key)
    if not conf:
        return {}
    return {f["key"]: f["label"] for f in conf["fields"]}
