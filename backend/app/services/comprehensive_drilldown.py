"""综合成本模型·折算明细下钻（Phase A 数据底座的一部分）。

读 fact_loss_detail（物化的损失明细，带 source 标注）做净下钻；
权衡分析(scatter)走实时查询（与 cross 同源，已统一系数/单位）。
供 /api/comprehensive/quality-loss-detail 等新端点消费，Phase D 前端对接。
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import cost_factors as cf

# 时长归一（与 cross/comprehensive 一致）
_DUR_EXPR = ("CASE WHEN process = '转炉' AND indicator_name <> '镇静时长' "
             "THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END")


def _std_upper(std) -> float | None:
    if not std:
        return None
    m = re.match(r'^(-?[0-9.]+)-(-?[0-9.]+)$', str(std).strip())
    if m:
        upper = float(m.group(2))
        return None if upper < 0 else upper
    return None


def quality_loss_drilldown(db: Session) -> dict:
    """质量损失折算明细下钻：按损失项/钢种聚合 + 合金富裕精确明细 + source 标注。"""
    # 按损失项聚合（来自 fact_loss_detail，物化口径与综合成本模型一致）
    by_name = db.execute(text("""
        SELECT loss_name, source, COUNT(*) AS n, ROUND(SUM(amount)) AS total
        FROM fact_loss_detail WHERE loss_category = 'quality'
        GROUP BY loss_name, source ORDER BY total DESC
    """)).all()
    # 按钢种聚合
    by_grade = db.execute(text("""
        SELECT steel_grade, COUNT(DISTINCT heat_no) AS heats, ROUND(SUM(amount)) AS total
        FROM fact_loss_detail WHERE loss_category = 'quality'
        GROUP BY steel_grade ORDER BY total DESC LIMIT 15
    """)).all()
    # 合金富裕精确明细（按合金品种，实时查询）
    rows = db.execute(text("""
        SELECT indicator_name AS alloy, actual_value, std_value
        FROM fact_heat_indicator WHERE process = '合金'
        AND actual_value ~ '^[0-9]+\\.?[0-9]*$' AND std_value IS NOT NULL
    """)).all()
    amap: dict = {}
    total_surplus = 0.0
    for r in rows:
        upper = _std_upper(r.std_value)
        if upper is None:
            continue
        actual = float(r.actual_value)
        if actual > upper:
            excess = actual - upper
            price = cf.alloy_price(r.alloy)
            cost = excess * price
            total_surplus += cost
            a = amap.setdefault(r.alloy, {"alloy": r.alloy, "excess": 0.0, "cost": 0.0, "price": price})
            a["excess"] += excess
            a["cost"] += cost
    alloy_surplus = sorted(amap.values(), key=lambda x: x["cost"], reverse=True)[:10]

    total = sum(float(r.total or 0) for r in by_name)
    return {
        "summary": {"total_quality_loss": round(total, 0),
                    "total_alloy_surplus": round(total_surplus, 0),
                    "source_note": "defect/downgrade/reblow 为系数估算(estimated)；合金富裕为精确口径(formula)"},
        "by_loss_name": [{"loss_name": r.loss_name, "source": r.source, "n": int(r.n),
                          "total": float(r.total or 0)} for r in by_name],
        "by_steel_grade": [{"steel_grade": r.steel_grade, "heats": int(r.heats),
                            "total": float(r.total or 0)} for r in by_grade],
        "alloy_surplus_detail": [{"alloy": a["alloy"], "excess": round(a["excess"], 1),
                                  "price": a["price"], "cost": round(a["cost"], 0),
                                  "source": "formula"} for a in alloy_surplus],
    }


def efficiency_loss_drilldown(db: Session) -> dict:
    """效率损失折算明细下钻：按损失项/班组聚合 + P95超时明细 + source 标注。"""
    by_name = db.execute(text("""
        SELECT loss_name, source, COUNT(*) AS n, ROUND(SUM(amount)) AS total
        FROM fact_loss_detail WHERE loss_category = 'efficiency'
        GROUP BY loss_name, source ORDER BY total DESC
    """)).all()
    by_team = db.execute(text("""
        SELECT team, COUNT(DISTINCT heat_no) AS heats, ROUND(SUM(amount)) AS total
        FROM fact_loss_detail WHERE loss_category = 'efficiency'
        GROUP BY team ORDER BY total DESC
    """)).all()
    # P95 超时明细（有效精炼时长，实时）
    overdue = db.execute(text("""
        WITH d AS (SELECT heat_no, actual_value::numeric AS dur FROM fact_heat_indicator
                   WHERE indicator_name = '有效精炼时长' AND actual_value ~ '^[0-9]+\\.?[0-9]*$'),
             p AS (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY dur) AS p95 FROM d)
        SELECT COUNT(*) AS n, ROUND((MAX(p.p95))::numeric, 1) AS p95, SUM(dur - p.p95) AS over_min
        FROM d, p WHERE d.dur > p.p95
    """)).one()
    # 各工序时长-成本（实时，DUR 归一）
    proc_dur = db.execute(text(f"""
        SELECT process, SUM({_DUR_EXPR}) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS total_min
        FROM fact_heat_indicator WHERE indicator_name LIKE '%时长%'
        GROUP BY process ORDER BY total_min DESC
    """)).all()
    epm = cf.get("energy_per_min")

    total = sum(float(r.total or 0) for r in by_name)
    return {
        "summary": {"total_efficiency_loss": round(total, 0),
                    "overdue_p95": float(overdue.p95 or 0),
                    "overdue_heats": int(overdue.n or 0),
                    "overdue_total_min": round(float(overdue.over_min or 0), 0),
                    "overdue_cost": round(float(overdue.over_min or 0) * cf.get("time_cost"), 0),
                    "source_note": "energy/overdue 为系数估算(estimated)"},
        "by_loss_name": [{"loss_name": r.loss_name, "source": r.source, "n": int(r.n),
                          "total": float(r.total or 0)} for r in by_name],
        "by_team": [{"team": r.team, "heats": int(r.heats), "total": float(r.total or 0)} for r in by_team],
        "by_process_cost": [{"process": r.process, "total_min": round(float(r.total_min or 0), 0),
                             "cost": round(float(r.total_min or 0) * epm, 0)} for r in proc_dur],
    }


def tradeoff_analysis(db: Session) -> dict:
    """权衡分析：配料-合格率 scatter + 钢种质量-成本矩阵 + 时长-质量分箱。"""
    # 1. 配料-合格率权衡
    low_end = db.execute(text("""
        SELECT steel_grade, COALESCE(SUM(weight) FILTER (WHERE scrap_type IN ('渣钢','普通压块')), 0) AS low_w,
          SUM(weight) AS total_w
        FROM fact_scrap_ratio GROUP BY steel_grade
    """)).all()
    grade_q = {r.steel_grade: r for r in db.execute(text("""
        SELECT steel_grade, COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE process = '合金' GROUP BY steel_grade
    """)).all()}
    scrap_quality = []
    for r in low_end:
        g = grade_q.get(r.steel_grade)
        if g and r.total_w and g.judged:
            scrap_quality.append({"steel_grade": r.steel_grade,
                                  "low_pct": round(100 * float(r.low_w or 0) / float(r.total_w), 1),
                                  "alloy_rate": round(100 * float(g.hit or 0) / float(g.judged), 1)})
    scrap_quality.sort(key=lambda x: x["low_pct"], reverse=True)

    # 2. 钢种质量-成本矩阵（来自 fact_loss_detail 质量损失 × 废钢成本）
    grade_loss = {r.steel_grade: float(r.total or 0) for r in db.execute(text("""
        SELECT steel_grade, SUM(amount) AS total FROM fact_loss_detail
        WHERE loss_category = 'quality' GROUP BY steel_grade
    """)).all()}
    scrap_grade = {r.steel_grade: float(r.total_w or 0) for r in db.execute(text(
        "SELECT steel_grade, MAX(total_weight) AS total_w FROM fact_scrap_ratio GROUP BY steel_grade"
    )).all()}
    matrix = []
    for g, loss in sorted(grade_loss.items(), key=lambda x: x[1], reverse=True)[:20]:
        dc = scrap_grade.get(g, 0) * cf.get("scrap_price") / 10000
        matrix.append({"steel_grade": g, "direct_cost_wan": round(dc, 1),
                       "quality_loss_wan": round(loss / 1e4, 1)})

    # 3. 精炼时长-质量分箱（找质量不降的最短时长）
    durs = {r.heat_no: float(r.dur) for r in db.execute(text("""
        SELECT heat_no, actual_value::numeric AS dur FROM fact_heat_indicator
        WHERE indicator_name = '有效精炼时长' AND actual_value ~ '^[0-9]+\\.?[0-9]*$'
    """)).all()}
    rates = {r.heat_no: float(r.rate or 0) for r in db.execute(text("""
        SELECT heat_no, 100.0 * COUNT(*) FILTER (WHERE judge = 1) / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL), 0) AS rate
        FROM fact_heat_indicator GROUP BY heat_no
    """)).all()}
    pairs = [(durs[h], rates[h]) for h in durs if h in rates]
    bins = []
    if pairs:
        ds = [p[0] for p in pairs]
        lo, hi = min(ds), max(ds)
        step = (hi - lo) / 5 if hi > lo else 1
        for i in range(5):
            bl, bh = lo + i * step, lo + (i + 1) * step
            grp = [p[1] for p in pairs if bl <= p[0] < (bh if i < 4 else hi + 0.001)]
            bins.append({"range": f"{bl:.0f}-{bh:.0f}", "n": len(grp),
                         "rate": round(sum(grp) / len(grp), 1) if grp else 0})

    return {
        "scrap_quality_tradeoff": scrap_quality[:15],
        "grade_matrix": matrix,
        "duration_quality_bins": bins,
    }


def loss_source_summary(db: Session) -> dict:
    """损失数据来源汇总：source 分布 + 系数置信度（供 AI 按置信度措辞）。"""
    src = db.execute(text("""
        SELECT loss_category, source, COUNT(*) AS n, ROUND(SUM(amount)) AS total
        FROM fact_loss_detail GROUP BY loss_category, source ORDER BY 1, 2
    """)).all()
    # 系数来源（来自 cost_factors 注册表）
    coefficients = [{"name": k, "value": v["value"], "source": v["source"], "note": v.get("note", "")}
                    for k, v in cf.COEFFICIENTS.items()]
    return {
        "loss_source": [{"loss_category": r.loss_category, "source": r.source, "n": int(r.n),
                         "total": float(r.total or 0)} for r in src],
        "coefficients": coefficients,
        "confidence_note": "estimated=系数估算(待客户真实数据替换)；formula=精确公式口径(actual>std 超出量)",
    }
