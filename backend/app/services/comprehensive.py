"""三维度综合炉次成本模型（创举核心）。

综合炉次成本 = 直接成本 + 质量损失成本 + 效率损失成本
- 系数统一来自 cost_factors（单一源，待客户真实数据替换）
- 货币化统一：质量、效率都折算为成本，形成标量优化目标
- calc_heat_cost 为纯函数（无 db 依赖），供 simulation/AI/ETL 复用，确保口径一致
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import cost_factors as cf


def _percentile(values: list[float], p: float) -> float:
    """简单百分位（p in 0..1）。空列表返回 0。"""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def _std_upper(std) -> float | None:
    """解析标准区间上限，如 '1.2-2.6' -> 2.6；'-1-99'(无要求) -> None。"""
    if not std:
        return None
    m = re.match(r'^(-?[0-9.]+)-(-?[0-9.]+)$', str(std).strip())
    if m:
        upper = float(m.group(2))
        return None if upper < 0 else upper
    return None


def alloy_surplus_by_heat(db: Session) -> dict:
    """精确口径：每炉合金 actual 超 std 上限 的超出量 × 单价（吸收自 cross）。

    返回 {heat_no: surplus_cost}。source=formula（精确，非系数估算）。
    """
    rows = db.execute(text("""
        SELECT heat_no, indicator_name AS alloy, actual_value, std_value
        FROM fact_heat_indicator WHERE process = '合金'
        AND actual_value ~ '^[0-9]+\\.?[0-9]*$' AND std_value IS NOT NULL
    """)).all()
    surplus: dict = {}
    for r in rows:
        upper = _std_upper(r.std_value)
        if upper is None:
            continue
        actual = float(r.actual_value)
        if actual > upper:
            excess = actual - upper
            surplus[r.heat_no] = surplus.get(r.heat_no, 0.0) + excess * cf.alloy_price(r.alloy)
    return surplus


def calc_heat_cost(row, overdue_threshold: float | None = None, alloy_surplus: float | None = None) -> dict:
    """纯函数：单炉三块成本计算（无 db 依赖）。

    row: 聚合查询行，需含 heat_no/steel_grade/team/equipment/alloy_total/judged/hit/reblow/avg_dur。
    overdue_threshold: 超时阈值(分钟)，None 则用 cost_factors.std_duration。
    alloy_surplus: 精确合金富裕损失(元)，None 则用估算口径 alloy_cost*(1-rate)*factor。
    返回含 direct/quality_loss/efficiency_loss/total 及 loss_breakdown 明细。
    """
    rate = (row.hit / row.judged) if row.judged else 1
    alloy_cost = float(row.alloy_total or 0) * cf.get("alloy_avg_price")
    std_dur = cf.get("std_duration")
    threshold = overdue_threshold if overdue_threshold is not None else std_dur

    # 1. 直接成本
    scrap_cost = cf.get("est_output") * cf.get("scrap_price")
    direct = alloy_cost + scrap_cost + cf.get("refractory_per_heat")

    # 2. 质量损失成本（COQ）
    output = cf.get("est_output") * cf.get("yield_rate")
    defect_rate = cf.defect_rate(rate)
    defect_loss = output * defect_rate * cf.get("ton_steel_cost") * (1 - cf.get("residual_rate"))
    downgrade_loss = output * defect_rate * cf.get("downgrade_loss_per_ton")
    # 合金富裕：优先用精确口径(actual>std 超出量×单价)，无则估算
    if alloy_surplus is not None:
        surplus_loss = alloy_surplus
        surplus_source = "formula"
    else:
        surplus_loss = alloy_cost * (1 - rate) * cf.get("surplus_loss_factor")
        surplus_source = "estimated"
    reblow_loss = int(row.reblow or 0) * cf.get("reblow_cost")
    quality_loss = defect_loss + downgrade_loss + surplus_loss + reblow_loss

    # 3. 效率损失成本（超时阈值动态 P95，统一 cross 口径）
    dur = float(row.avg_dur or 0)
    energy_loss = dur * cf.get("energy_per_min")
    overdue_loss = max(0, dur - threshold) * cf.get("energy_per_min")
    efficiency_loss = energy_loss + overdue_loss

    total = direct + quality_loss + efficiency_loss
    return {
        "heat_no": row.heat_no, "steel_grade": row.steel_grade, "team": row.team,
        "equipment": row.equipment, "compliance_rate": round(rate * 100, 1),
        "direct": round(direct, 0), "quality_loss": round(quality_loss, 0),
        "efficiency_loss": round(efficiency_loss, 0), "total": round(total, 0),
        "loss_breakdown": {
            "defect_loss": round(defect_loss, 0), "downgrade_loss": round(downgrade_loss, 0),
            "surplus_loss": round(surplus_loss, 0), "reblow_loss": round(reblow_loss, 0),
            "energy_loss": round(energy_loss, 0), "overdue_loss": round(overdue_loss, 0),
            "surplus_source": surplus_source,
        },
        "_raw": {"rate": rate, "alloy_cost": alloy_cost, "dur": dur, "output": output,
                 "defect_rate": defect_rate, "overdue_threshold": threshold,
                 "defect_rate_val": defect_rate},
    }


def build_structure(heats: list[dict]) -> dict:
    """三块汇总与占比 + per-heat 均值（供 simulation 直接用，无需反推）。"""
    td = sum(h["direct"] for h in heats)
    tq = sum(h["quality_loss"] for h in heats)
    te = sum(h["efficiency_loss"] for h in heats)
    tot = td + tq + te
    n = len(heats) or 1
    avg_alloy = sum(h["_raw"]["alloy_cost"] for h in heats) / n
    return {
        "direct": round(td, 0), "quality": round(tq, 0), "efficiency": round(te, 0),
        "total": round(tot, 0),
        "direct_pct": round(100 * td / tot, 1) if tot else 0,
        "quality_pct": round(100 * tq / tot, 1) if tot else 0,
        "efficiency_pct": round(100 * te / tot, 1) if tot else 0,
        "heats_count": len(heats),
        "avg_direct": round(td / n, 0), "avg_quality": round(tq / n, 0),
        "avg_efficiency": round(te / n, 0), "avg_alloy": round(avg_alloy, 0),
    }


def build_grade_benchmark(heats: list[dict]) -> list[dict]:
    """钢种对标 Top10（按综合成本降序）。"""
    gmap: dict = {}
    for h in heats:
        g = gmap.setdefault(h["steel_grade"], {"n": 0, "total": 0, "direct": 0, "quality": 0, "efficiency": 0})
        g["n"] += 1
        g["total"] += h["total"]
        g["direct"] += h["direct"]
        g["quality"] += h["quality_loss"]
        g["efficiency"] += h["efficiency_loss"]
    return sorted([
        {"steel_grade": k, "n": v["n"], "avg_total": round(v["total"] / v["n"], 0),
         "avg_direct": round(v["direct"] / v["n"], 0), "avg_quality": round(v["quality"] / v["n"], 0),
         "avg_efficiency": round(v["efficiency"] / v["n"], 0)}
        for k, v in gmap.items()
    ], key=lambda x: x["avg_total"], reverse=True)[:10]


def build_team_benchmark(heats: list[dict]) -> list[dict]:
    """班组对标（按综合成本升序）。"""
    tmap: dict = {}
    for h in heats:
        t = tmap.setdefault(h["team"], {"n": 0, "total": 0})
        t["n"] += 1
        t["total"] += h["total"]
    return sorted([
        {"team": k, "n": v["n"], "avg_total": round(v["total"] / v["n"], 0)}
        for k, v in tmap.items()
    ], key=lambda x: x["avg_total"])


# 聚合查询：每炉合金总量/判定/命中/补吹/平均时长（转炉秒统一÷60归一为分钟）
_HEAT_SQL = """
    SELECT heat_no, steel_grade, team, equipment,
      SUM(actual_value::numeric) FILTER (WHERE process = '合金' AND actual_value ~ '^[0-9]+\\.?[0-9]*$') AS alloy_total,
      COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
      COUNT(*) FILTER (WHERE judge = 1) AS hit,
      COUNT(*) FILTER (WHERE indicator_name = '补吹出钢' AND judge = 0) AS reblow,
      AVG(CASE WHEN process = '转炉' AND indicator_name <> '镇静时长'
               THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END)
          FILTER (WHERE indicator_name LIKE '%时长%' AND actual_value ~ '^[0-9]+\\.?[0-9]*$') AS avg_dur
    FROM fact_heat_indicator
    GROUP BY heat_no, steel_grade, team, equipment
    HAVING COUNT(*) FILTER (WHERE process = '合金') > 0
    LIMIT :limit
"""


def count_reblows(db: Session, heat_nos: list[str]) -> int:
    """指定炉次集合中的补吹次数（供 simulation 解耦复用）。"""
    if not heat_nos:
        return 0
    from sqlalchemy import bindparam
    stmt = text("""
        SELECT COUNT(*) FROM fact_heat_indicator
        WHERE indicator_name = '补吹出钢' AND judge = 0 AND heat_no IN :heats
    """).bindparams(bindparam("heats", expanding=True))
    return int(db.execute(stmt, {"heats": heat_nos}).scalar() or 0)


def comprehensive_model(db: Session, limit: int = 50) -> dict:
    """综合炉次成本模型：每炉 直接+质量损失+效率损失，损失结构，钢种/班组对标。

    编排器：查库 -> 算P95超时阈值 -> 精确合金富裕 -> 逐炉 calc_heat_cost -> 聚合对标。签名不变（零破坏 simulation）。
    """
    heats = db.execute(text(_HEAT_SQL), {"limit": limit}).all()

    # 超时阈值：用全样本 avg_dur 的 P95（动态，统一 cross 口径），无数据回退 std_duration
    durs = [float(h.avg_dur or 0) for h in heats if h.avg_dur is not None]
    overdue_threshold = _percentile(durs, 0.95) if durs else cf.get("std_duration")

    # 精确合金富裕口径（actual>std 超出量×单价，source=formula）
    surplus_map = alloy_surplus_by_heat(db)

    results = [calc_heat_cost(h, overdue_threshold, surplus_map.get(h.heat_no)) for h in heats]
    results.sort(key=lambda x: x["total"], reverse=True)

    return {
        "heats": results,
        "structure": build_structure(results),
        "grade_benchmark": build_grade_benchmark(results),
        "team_benchmark": build_team_benchmark(results),
        "overdue_threshold": round(overdue_threshold, 1),
        "note": "系数来自 cost_factors（估算值，待客户真实数据替换）；超时阈值用 P95 动态口径；合金富裕用精确口径",
    }
