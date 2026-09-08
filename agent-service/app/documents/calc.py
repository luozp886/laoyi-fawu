"""劳动法常用金额/天数的受控计算。

仅做确定性的模板化计算，供文书正文引用；不对法条作扩张解释。
输入均为字符串或数值，输出保留两位小数的金额字符串与计算说明。
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def _money(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def economic_compensation(
    *,
    monthly_wage: object,
    years: object,
) -> tuple[str, str]:
    """经济补偿金 N：月工资 × 工作年限。

    年限规则：满一年付一个月；六个月以上不满一年按一年计；不满六个月付半个月。
    """
    wage = _money(monthly_wage)
    if wage is None or wage <= 0:
        return "—", "缺少可用的月工资，未计算。"
    try:
        y = float(years)
    except Exception:
        return "—", "缺少可用的工作年限，未计算。"
    if y < 0.5:
        months_factor = "0.5"
    elif y < 1:
        months_factor = "1"
    else:
        whole = int(y)
        frac = y - whole
        months_factor = str(whole + (1 if frac >= 0.5 else 0))
    amount = wage * Decimal(months_factor)
    return (
        f"{amount:.2f}",
        f"按解除前十二个月平均工资 {wage:.2f} 元 × {months_factor} 个月 = {amount:.2f} 元",
    )


def illegal_dismissal_compensation(*, monthly_wage: object, years: object) -> tuple[str, str]:
    """违法解除赔偿金 2N。"""
    n_amount, n_note = economic_compensation(monthly_wage=monthly_wage, years=years)
    try:
        amount = (Decimal(n_amount) * 2) if n_amount != "—" else None
    except Exception:
        amount = None
    if amount is None:
        return "—", n_note
    return f"{amount:.2f}", f"经济补偿金 N 为 {n_amount} 元，违法解除按二倍计：{amount:.2f} 元。"


def double_wage_delta(*, monthly_wage: object, months: object) -> tuple[str, str]:
    """未签书面合同二倍工资差额：月工资 ×（二倍月数，最长 11 个月）。"""
    wage = _money(monthly_wage)
    if wage is None or wage <= 0:
        return "—", "缺少可用的月工资，未计算。"
    try:
        m = max(0, min(int(float(months)), 11))
    except Exception:
        return "—", "缺少可用的二倍工资月份，未计算。"
    if m == 0:
        return "0.00", "未超过一个月宽限期，无二倍工资差额。"
    amount = wage * m
    return (
        f"{amount:.2f}",
        f"月工资 {wage:.2f} 元 × 二倍工资差额对应 {m} 个月 = {amount:.2f} 元",
    )


def overtime_amount(
    *,
    monthly_wage: object,
    weekday_hours: object,
    weekend_hours: object,
    holiday_hours: object,
) -> tuple[str, str]:
    """加班费合计。

    时薪 = 月工资 ÷ 21.75 ÷ 8；延时 1.5 倍、休息日 2 倍、法定节假日 3 倍。
    """
    wage = _money(monthly_wage)
    if wage is None or wage <= 0:
        return "—", "缺少可用的月工资，未计算。"

    def h(v: object) -> Decimal:
        try:
            return Decimal(str(float(v or 0)))
        except Exception:
            return Decimal("0")

    hourly = (wage / Decimal("21.75") / Decimal("8")).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    wh, weh, hoh = h(weekday_hours), h(weekend_hours), h(holiday_hours)
    parts = []
    total = Decimal("0")
    if wh > 0:
        v = hourly * wh * Decimal("1.5")
        total += v
        parts.append(f"延时加班 {wh:g} 小时 × 时薪 {hourly:.2f} × 1.5 = {v:.2f}")
    if weh > 0:
        v = hourly * weh * Decimal("2")
        total += v
        parts.append(f"休息日加班 {weh:g} 小时 × 时薪 {hourly:.2f} × 2 = {v:.2f}")
    if hoh > 0:
        v = hourly * hoh * Decimal("3")
        total += v
        parts.append(f"法定节假日加班 {hoh:g} 小时 × 时薪 {hourly:.2f} × 3 = {v:.2f}")
    if not parts:
        return "0.00", "未录入加班时长。"
    return f"{total:.2f}", "；".join(parts) + f"。合计 {total:.2f} 元。"
