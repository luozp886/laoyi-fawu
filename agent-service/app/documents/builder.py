"""文书正文拼装器：把用户收集到的要素渲染为受控的 Markdown/纯文本正文。

仅做“模板填充 + 确定性计算”，不调用模型自由起草，避免编造法条。
"""
from __future__ import annotations

from typing import Any

from app.documents.calc import (
    double_wage_delta,
    economic_compensation,
    illegal_dismissal_compensation,
    overtime_amount,
)
from app.documents.registry import TEMPLATE_REGISTRY

DISCLAIMER = (
    "\n\n---\n"
    "【温馨提示】本文书由本平台根据您填写的信息自动生成，仅作模板与参考之用，"
    "不构成正式法律意见；具体法律后果请以仲裁委/法院及执业律师意见为准。"
)


def _g(elements: dict[str, Any], key: str, default: str = "") -> str:
    v = elements.get(key)
    return default if v is None else str(v).strip()


def _ln(text: str) -> str:
    return text if text else "＿＿＿＿＿＿＿＿＿＿＿＿"


def _header(title: str) -> str:
    return f"# {title}\n"


def _applicant_block(e: dict[str, Any]) -> list[str]:
    return [
        f"申请人：{_g(e, 'applicant_name')}",
        f"身份证号：{_g(e, 'applicant_idno')}",
        f"住址：{_g(e, 'applicant_address')}",
        f"联系电话：{_g(e, 'applicant_phone')}",
    ]


def _respondent_block(e: dict[str, Any]) -> list[str]:
    lines = [
        f"被申请人：{_g(e, 'company')}",
        f"住所地：{_g(e, 'company_address')}",
    ]
    if _g(e, "respondent_legal_rep"):
        lines.append(f"法定代表人：{_g(e, 'respondent_legal_rep')}")
    return lines


# ---- 各文书正文渲染 ----
def _labor_arbitration_application(e: dict[str, Any]) -> str:
    s = ["# 劳动仲裁申请书\n"]
    s += ["## 申请人信息"]
    s += _applicant_block(e)
    s += ["", "## 被申请人信息"]
    s += _respondent_block(e)
    s += ["", "## 仲裁请求"]
    s += [f"1. 请求裁决被申请人支付申请人在职期间的劳动争议款项，具体如下："]
    s += [f"   {_ln(e.get('claim_items'))}"]
    s += ["", "## 事实与理由"]
    s += [
        f"申请人于 {_g(e, 'entry_date')} 入职，任 {_g(e, 'position')}，月工资为 {_g(e, 'monthly_wage')} 元。"
    ]
    s += [f"{_g(e, 'facts')}"]
    s += ["", "此致\n＿＿＿＿劳动人事争议仲裁委员会", "", "申请人（签名）：＿＿＿＿＿＿\n日期：＿＿＿＿＿＿"]
    return "\n".join(s)


def _labor_arbitration_reply(e: dict[str, Any]) -> str:
    s = ["# 劳动仲裁答辩状\n"]
    s += [f"答辩人（被申请人）：{_g(e, 'company')}"]
    s += [f"申请人：{_g(e, 'applicant_name')}", ""]
    s += ["## 答辩意见"]
    s += [f"{_ln(e.get('reply_position'))}", "", "## 事实与理由"]
    s += [f"{_g(e, 'facts')}", ""]
    s += ["答辩人（盖章）：＿＿＿＿＿＿\n日期：＿＿＿＿＿＿"]
    return "\n".join(s)


def _forced_resignation_notice(e: dict[str, Any]) -> str:
    s = ["# 被迫解除劳动合同通知书\n"]
    s += [f"{_g(e, 'company')}：", ""]
    s += [
        f"本人 {_g(e, 'applicant_name')}，自 {_g(e, 'entry_date')} 入职贵单位工作。",
        f"因贵单位存在以下情形：{_g(e, 'force_reason')}，根据《中华人民共和国劳动合同法》第三十八条，"
        "本人特此通知贵单位，自本通知发出之日解除双方劳动关系。",
        "请贵单位依法支付经济补偿、结清工资并办理离职手续。", "",
        "通知人（签名）：＿＿＿＿＿＿",
        f"日期：{_g(e, 'notice_date')}",
    ]
    return "\n".join(s)


def _negotiated_termination_agreement(e: dict[str, Any]) -> str:
    amount = _g(e, "termination_package")
    s = ["# 协商解除劳动合同协议书\n"]
    s += [
        f"甲方（用人单位）：{_g(e, 'company')}",
        f"乙方（劳动者）：{_g(e, 'applicant_name')}", "",
        "双方经平等协商一致，就解除劳动合同达成如下协议：",
        f"一、甲乙双方同意自 {_g(e, 'end_date')} 解除双方之间的劳动合同。",
        f"二、双方确认乙方于 {_g(e, 'entry_date')} 入职，工作年限 {_g(e, 'years')} 年。",
    ]
    if amount:
        s.append(f"三、甲方一次性支付乙方经济补偿及各项款项合计人民币 {amount} 元，乙方对此无其他异议。")
    else:
        comp, note = economic_compensation(monthly_wage=_g(e, "monthly_wage") or None, years=_g(e, "years"))
        s.append(f"三、甲方一次性支付乙方经济补偿合计人民币 {comp} 元（{note}）。乙方对此无其他异议。")
    s += ["", "甲方（盖章）：＿＿＿＿＿＿    乙方（签字）：＿＿＿＿＿＿", "日期：＿＿＿＿＿＿"]
    return "\n".join(s)


def _compensation_claim(e: dict[str, Any]) -> str:
    kind = _g(e, "claim_kind")
    is_2n = "2N" in kind or "赔偿" in kind or "违法" in kind
    if is_2n:
        amount, note = illegal_dismissal_compensation(monthly_wage=_g(e, "monthly_wage") or None, years=_g(e, "years"))
    else:
        amount, note = economic_compensation(monthly_wage=_g(e, "monthly_wage") or None, years=_g(e, "years"))
    s = ["# 经济补偿金/赔偿金主张书\n"]
    s += ["## 申请人信息"] + _applicant_block(e)
    s += ["", "## 被申请人信息"] + _respondent_block(e)
    s += ["", "## 主张事项"]
    s += [
        f"申请人于 {_g(e, 'entry_date')} 入职，至 {_g(e, 'end_date')} 解除劳动关系，工作年限 {_g(e, 'years')} 年。",
        f"主张金额：人民币 {amount} 元。",
        f"计算说明：{note}",
        "主张类型：" + ("违法解除赔偿金(2N)" if is_2n else "经济补偿金(N)"),
    ]
    s += ["", "## 事实与理由"]
    s += [f"{_g(e, 'facts')}"]
    return "\n".join(s)


def _double_wage_claim(e: dict[str, Any]) -> str:
    amount, note = double_wage_delta(monthly_wage=_g(e, "monthly_wage") or None, months=_g(e, "months"))
    s = ["# 未签书面劳动合同二倍工资主张书\n"]
    s += ["## 申请人信息"] + _applicant_block(e)
    s += ["", "## 被申请人信息"] + _respondent_block(e)
    s += ["", "## 主张事项"]
    s += [
        f"申请人于 {_g(e, 'entry_date')} 入职，用人单位自用工之日起超过一个月未与申请人订立书面劳动合同。",
        f"主张二倍工资差额：人民币 {amount} 元。",
        f"计算说明：{note}",
    ]
    s += ["", "## 事实与理由"]
    s += [f"{_g(e, 'facts')}"]
    return "\n".join(s)


def _overtime_wage_claim(e: dict[str, Any]) -> str:
    amount, note = overtime_amount(
        monthly_wage=_g(e, "monthly_wage") or None,
        weekday_hours=_g(e, "weekday_hours") or 0,
        weekend_hours=_g(e, "weekend_hours") or 0,
        holiday_hours=_g(e, "holiday_hours") or 0,
    )
    s = ["# 加班费主张书\n"]
    s += ["## 申请人信息"] + _applicant_block(e)
    s += ["", "## 被申请人信息"] + _respondent_block(e)
    s += ["", "## 主张事项"]
    s += [f"主张加班费合计：人民币 {amount} 元。"]
    s += [f"计算说明：{note}"]
    s += ["", "## 事实与理由"]
    s += [f"{_g(e, 'facts')}"]
    return "\n".join(s)


def _arrears_wage_claim(e: dict[str, Any]) -> str:
    s = ["# 拖欠工资(欠薪)主张书\n"]
    s += ["## 申请人信息"] + _applicant_block(e)
    s += ["", "## 被申请人信息"] + _respondent_block(e)
    s += ["", "## 主张事项"]
    s += [
        f"被申请人拖欠申请人 {_g(e, 'period')} 的劳动报酬，合计人民币 {_g(e, 'arrears_amount')} 元。",
        "请求被申请人立即足额支付上述欠薪，并依法支付加付赔偿金。",
    ]
    s += ["", "## 事实与理由"]
    s += [f"{_g(e, 'facts')}"]
    return "\n".join(s)


def _injury_identification_application(e: dict[str, Any]) -> str:
    s = ["# 工伤认定申请书\n"]
    s += ["## 申请人信息"] + _applicant_block(e)
    s += ["", "## 用人单位信息"] + _respondent_block(e)
    s += ["", "## 事故情况"]
    s += [
        f"事故发生时间：{_g(e, 'injury_date')}",
        f"事故发生地点：{_g(e, 'injury_place')}",
        f"事故经过及伤情：{_g(e, 'injury_desc')}",
    ]
    s += ["", "现依法申请对上述事故造成的伤害认定为工伤。", "", "此致\n＿＿＿＿人力资源社会保障局", "", "申请人（签名）：＿＿＿＿＿＿\n日期：＿＿＿＿＿＿"]
    return "\n".join(s)


def _injury_treatment_claim(e: dict[str, Any]) -> str:
    s = ["# 工伤待遇主张书\n"]
    s += ["## 申请人信息"] + _applicant_block(e)
    s += ["", "## 被申请人信息"] + _respondent_block(e)
    s += ["", "## 主张事项"]
    items = []
    if _g(e, "level"):
        items.append(f"按劳动能力鉴定伤残等级 {_g(e, 'level')} 主张一次性伤残补助等待遇。")
    if _g(e, "stop_pay_monthly") and _g(e, "stop_months"):
        items.append(f"主张停工留薪期工资 {_g(e, 'stop_pay_monthly')} 元 × {_g(e, 'stop_months')} 个月。")
    if _g(e, "medical_amount"):
        items.append(f"主张医疗费等待遇合计人民币 {_g(e, 'medical_amount')} 元。")
    s += items or ["（请补充具体主张项目）"]
    s += ["", "## 事实与理由"]
    s += [f"{_g(e, 'facts')}"]
    return "\n".join(s)


def _labor_contract_template(e: dict[str, Any]) -> str:
    s = ["# 劳动合同(范本)\n"]
    s += [
        f"甲方(用人单位)：{_g(e, 'company')}",
        f"住所：{_g(e, 'company_address')}",
    ]
    if _g(e, "respondent_legal_rep"):
        s.append(f"法定代表人：{_g(e, 'respondent_legal_rep')}")
    s += [
        f"乙方(劳动者)：{_g(e, 'applicant_name')}",
        f"身份证号：{_g(e, 'applicant_idno')}", "",
        "根据《中华人民共和国劳动法》《中华人民共和国劳动合同法》，双方就建立劳动关系订立本合同：",
        f"第一条 乙方担任 {_g(e, 'position')} 岗位，工作地点为 {_g(e, 'work_place')}。",
        f"第二条 合同期限自 {_g(e, 'entry_date')} 起" +
        (f"至 {_g(e, 'end_date')} 止" if _g(e, "end_date") else "") + "。",
        f"第三条 劳动报酬为人民币 {_g(e, 'monthly_wage')} 元/月，甲方应依法按时足额支付。",
    ]
    if _g(e, "facts"):
        s.append(f"第四条 其他约定：{_g(e, 'facts')}")
    s += ["", "甲方（盖章）：＿＿＿＿＿＿    乙方（签字）：＿＿＿＿＿＿", "签订日期：＿＿＿＿＿＿"]
    return "\n".join(s)


_BUILDERS = {
    "labor_arbitration_application": _labor_arbitration_application,
    "labor_arbitration_reply": _labor_arbitration_reply,
    "forced_resignation_notice": _forced_resignation_notice,
    "negotiated_termination_agreement": _negotiated_termination_agreement,
    "compensation_claim": _compensation_claim,
    "double_wage_claim": _double_wage_claim,
    "overtime_wage_claim": _overtime_wage_claim,
    "arrears_wage_claim": _arrears_wage_claim,
    "injury_identification_application": _injury_identification_application,
    "injury_treatment_claim": _injury_treatment_claim,
    "labor_contract_template": _labor_contract_template,
}


def get_title(template_key: str) -> str:
    conf = TEMPLATE_REGISTRY.get(template_key, {})
    return conf.get("title", template_key)


def build_body(template_key: str, elements: dict[str, Any]) -> str:
    builder = _BUILDERS.get(template_key)
    if builder is None:
        # 未实现的模板：给出要素清单骨架，绝不自由生成正文
        raise ValueError(f"未实现文书模板: {template_key}")
    return builder(elements) + DISCLAIMER


def build_document(
    template_key: str,
    elements: dict[str, Any],
) -> tuple[str, str]:
    """返回 (title, body_text)。"""
    return get_title(template_key), build_body(template_key, elements)
