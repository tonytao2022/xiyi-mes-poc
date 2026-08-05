"""双维度交汇分析服务（创举性：揭示单线分析看不到的权衡与冲突）。

系数统一来自 cost_factors（单一源）。时长统一为分钟（转炉秒÷60）。
每条交汇：title + level + content + value(金额/率) + 可选 chart 数据。
"""
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import cost_factors as cf


def _std_upper(std) -> float | None:
    """解析标准区间上限，如 '1.2-2.6' -> 2.6；'-1-99'(无要求) -> None。"""
    if not std:
        return None
    m = re.match(r'^(-?[0-9.]+)-(-?[0-9.]+)$', str(std).strip())
    if m:
        upper = float(m.group(2))
        return None if upper < 0 else upper
    return None


# 时长归一：转炉(除镇静)秒->分钟，其余分钟（与 efficiency_ai/comprehensive 一致）
_DUR_EXPR = ("CASE WHEN process = '转炉' AND indicator_name <> '镇静时长' "
             "THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END")


def quality_cost_crossover(db: Session) -> dict:
    """质量×成本交汇：合金富裕损失(精确)、补吹损失、配料-合格率权衡、COQ、钢种矩阵。"""
    items = []

    # 1. 合金富裕损失（精确：actual > std上限 的超出量 × 单价）
    rows = db.execute(text("""
        SELECT indicator_name AS alloy, actual_value, std_value
        FROM fact_heat_indicator WHERE process = '合金'
        AND actual_value ~ '^[0-9]+\\.?[0-9]*$' AND std_value IS NOT NULL
    """)).all()
    total_surplus = 0.0
    amap: dict = {}
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
            a = amap.setdefault(r.alloy, {"alloy": r.alloy, "excess_amount": 0.0, "surplus_cost": 0.0, "price": price})
            a["excess_amount"] += excess
            a["surplus_cost"] += cost
    alloy_surplus = sorted(amap.values(), key=lambda x: x["surplus_cost"], reverse=True)
    items.append({
        "title": "合金富裕损失（actual 超 std 上限 × 单价，精确口径）",
        "level": "警告" if total_surplus > 1e6 else "提示",
        "content": f"合金 actual 超过 std 上限的富裕量预估损失 {total_surplus / 1e4:.1f} 万元（仅算 actual>上限 的超出部分×单价，替代旧的符合率估算）",
        "value": round(total_surplus, 0),
        "chart": {"type": "bar", "title": "各合金富裕损失 Top8", "labels": [a["alloy"] for a in alloy_surplus[:8]],
                  "values": [round(a["surplus_cost"], 0) for a in alloy_surplus[:8]]},
    })

    # 2. 补吹损失
    reblow = db.execute(text(
        "SELECT COUNT(DISTINCT heat_no) FROM fact_heat_indicator WHERE indicator_name = '补吹出钢' AND judge = 0"
    )).scalar() or 0
    reblow_cost = reblow * cf.get("reblow_cost")
    items.append({
        "title": "补吹损失（质量未命中 -> 效率+成本双损）",
        "level": "警告" if reblow > 100 else "提示",
        "content": f"补吹炉次 {reblow} 炉，预估损失 {reblow_cost / 1e4:.1f} 万元（{cf.get('reblow_cost')}元/炉）",
        "value": reblow_cost,
    })

    # 3. 配料-合格率权衡（Python 关联）
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
    trade = []
    for r in low_end:
        g = grade_q.get(r.steel_grade)
        if g and r.total_w and g.judged:
            trade.append({"steel_grade": r.steel_grade,
                          "low_pct": round(100 * float(r.low_w or 0) / float(r.total_w), 1),
                          "alloy_rate": round(100 * float(g.hit or 0) / float(g.judged), 1)})
    trade.sort(key=lambda x: x["low_pct"], reverse=True)
    items.append({
        "title": "配料-合格率权衡（低端料占比 vs 合金符合率）",
        "level": "提示",
        "content": f"分析 {len(trade)} 个钢种：低端料占比 vs 合金符合率，找成本-质量平衡点",
        "chart": {"type": "scatter", "title": "低端料占比 vs 合金符合率",
                  "points": [[t["low_pct"], t["alloy_rate"]] for t in trade[:15]],
                  "labels": [t["steel_grade"] for t in trade[:15]],
                  "xName": "低端料占比%", "yName": "合金符合率%"},
    })

    # 4. 质量损失成本 COQ（低分炉次预估废品/降级损失）
    heats = db.execute(text("""
        SELECT heat_no, steel_grade,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator GROUP BY heat_no, steel_grade
        HAVING COUNT(*) FILTER (WHERE judge IS NOT NULL) > 0
    """)).all()
    total_coq = 0.0
    grade_coq: dict = {}
    for h in heats:
        rate = (h.hit / h.judged) if h.judged else 1
        if rate < 0.95:
            loss = (1 - rate) * cf.get("coq_loss_factor") * cf.get("est_output") * cf.get("ton_steel_cost")
            total_coq += loss
            grade_coq[h.steel_grade] = grade_coq.get(h.steel_grade, 0) + loss
    grade_coq_list = sorted([{"grade": k, "loss": v} for k, v in grade_coq.items()], key=lambda x: x["loss"], reverse=True)
    items.append({
        "title": "质量损失成本 COQ（低分炉次预估废品/降级损失）",
        "level": "警告" if total_coq > 1e6 else "提示",
        "content": f"符合率<95% 的炉次预估质量损失 {total_coq / 1e4:.1f} 万元（(1-符合率)×{cf.get('coq_loss_factor')}损失系数×{cf.get('est_output')}吨×{cf.get('ton_steel_cost')}元/吨）",
        "value": round(total_coq, 0),
        "chart": {"type": "bar", "title": "钢种质量损失 Top8", "labels": [g["grade"] for g in grade_coq_list[:8]],
                  "values": [round(g["loss"], 0) for g in grade_coq_list[:8]]},
    })

    # 5. 钢种质量-成本矩阵（象限分析：高成本低质量=重点改进）
    scrap_grade = {r.steel_grade: float(r.total_w or 0) for r in db.execute(text(
        "SELECT steel_grade, MAX(total_weight) AS total_w FROM fact_scrap_ratio GROUP BY steel_grade"
    )).all()}
    matrix_points = []
    for g in grade_coq_list[:20]:
        dc = scrap_grade.get(g["grade"], 0) * cf.get("scrap_price") / 10000  # 废钢成本估算(万元)
        matrix_points.append([round(dc, 1), round(g["loss"] / 1e4, 1), g["grade"]])
    items.append({
        "title": "钢种质量-成本矩阵（象限：高成本低质量=重点改进）",
        "level": "提示",
        "content": f"钢种直接成本(废钢) vs 质量损失，4象限分析识别重点改进钢种（{len(matrix_points)}个钢种）",
        "chart": {"type": "scatter", "title": "钢种直接成本(万) vs 质量损失(万)", "points": [[p[0], p[1]] for p in matrix_points],
                  "labels": [p[2] for p in matrix_points],
                  "xName": "直接成本(万)", "yName": "质量损失(万)"},
    })

    return {"category": "质量 × 成本", "items": items}


def quality_efficiency_crossover(db: Session) -> dict:
    """质量×效率交汇：一次成功率、时长-质量关系。"""
    items = []

    # 1. 一次成功率
    total = db.execute(text(
        "SELECT COUNT(DISTINCT heat_no) FROM fact_heat_indicator WHERE indicator_name IN ('补吹出钢','二次出钢')"
    )).scalar() or 1
    bad = db.execute(text(
        "SELECT COUNT(DISTINCT heat_no) FROM fact_heat_indicator WHERE indicator_name IN ('补吹出钢','二次出钢') AND judge = 0"
    )).scalar() or 0
    success_rate = round(100 * (1 - bad / total), 1) if total else 0
    items.append({
        "title": "一次成功率（效率×质量双损）",
        "level": "警告" if success_rate < 80 else "提示",
        "content": f"一次拉成率 {success_rate}%（补吹/二次出钢 {bad}/{total} 炉），一次成功省时且质量好",
        "value": success_rate,
    })

    # 2. 时长-质量关系（精炼时长分箱符合率，Python 分箱）
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
            bins.append({"rng": f"{bl:.0f}-{bh:.0f}", "n": len(grp),
                         "rate": round(sum(grp) / len(grp), 1) if grp else 0})
    items.append({
        "title": "精炼时长-质量关系（找质量不降的最短时长）",
        "level": "提示",
        "content": f"按时长分箱看符合率，{len(bins)} 个区间，识别时长拐点（再长不提质）",
        "chart": {"type": "bar", "title": "精炼时长区间 vs 符合率",
                  "labels": [b["rng"] for b in bins], "values": [b["rate"] for b in bins]},
    })

    # 3. 超长炉次质量对比（P95 超时 vs 正常炉次符合率）
    overdue_set = {r.heat_no for r in db.execute(text("""
        WITH d AS (SELECT heat_no, actual_value::numeric AS dur FROM fact_heat_indicator
                   WHERE indicator_name = '有效精炼时长' AND actual_value ~ '^[0-9]+\\.?[0-9]*$'),
             p AS (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY dur) AS p95 FROM d)
        SELECT d.heat_no FROM d, p WHERE d.dur > p.p95
    """)).all()}
    all_rates = db.execute(text("""
        SELECT heat_no, 100.0 * COUNT(*) FILTER (WHERE judge = 1) / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL), 0) AS rate
        FROM fact_heat_indicator GROUP BY heat_no
    """)).all()
    over_rates = [float(r.rate or 0) for r in all_rates if r.heat_no in overdue_set]
    norm_rates = [float(r.rate or 0) for r in all_rates if r.heat_no not in overdue_set and r.rate is not None]
    over_avg = round(sum(over_rates) / len(over_rates), 1) if over_rates else 0
    norm_avg = round(sum(norm_rates) / len(norm_rates), 1) if norm_rates else 0
    items.append({
        "title": "超长炉次质量对比（P95超时 vs 正常炉次符合率）",
        "level": "警告" if over_avg < norm_avg - 5 else "提示",
        "content": f"精炼时长超P95的炉次 {len(over_rates)} 炉平均符合率 {over_avg}%，正常炉次 {len(norm_rates)} 炉平均 {norm_avg}%，差 {round(norm_avg - over_avg, 1)}pp",
        "chart": {"type": "bar", "title": "超时 vs 正常炉次符合率", "labels": ["超时炉次", "正常炉次"], "values": [over_avg, norm_avg]},
    })

    return {"category": "质量 × 效率", "items": items}


def cost_efficiency_crossover(db: Session) -> dict:
    """成本×效率交汇：时长-能耗、超时损失、工序/班组成本对标（时长统一为分钟）。"""
    items = []
    epm = cf.get("energy_per_min")

    # 1. 时长-能耗估算（总时长 × 单位时间能耗；转炉秒÷60归一）
    rows = db.execute(text(f"""
        SELECT process, indicator_name,
          SUM({_DUR_EXPR}) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS total_min,
          COUNT(*) AS n
        FROM fact_heat_indicator WHERE indicator_name LIKE '%时长%'
        GROUP BY process, indicator_name
    """)).all()
    total_min = sum(float(r.total_min or 0) for r in rows)
    energy_cost = total_min * epm
    items.append({
        "title": "时长-能耗成本（时间=能耗）",
        "level": "提示",
        "content": f"全工序总时长 {total_min:.0f} 分钟，估算能耗成本 {energy_cost / 1e4:.1f} 万元（{epm}元/分钟）",
        "value": round(energy_cost, 0),
    })

    # 2. 超时损失（有效精炼时长> P95 的炉次 × 超时量 × 时间成本，含耐材）
    overdue = db.execute(text("""
        WITH d AS (
          SELECT heat_no, actual_value::numeric AS dur
          FROM fact_heat_indicator
          WHERE indicator_name = '有效精炼时长' AND actual_value ~ '^[0-9]+\\.?[0-9]*$'
        ), p AS (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY dur) AS p95 FROM d)
        SELECT COUNT(*) AS n, SUM(dur - p.p95) AS over_min
        FROM d, p WHERE d.dur > p.p95
    """)).one()
    overdue_cost = float(overdue.over_min or 0) * cf.get("time_cost")
    items.append({
        "title": "超时损失（效率低->成本高）",
        "level": "警告" if overdue_cost > 1e6 else "提示",
        "content": f"精炼时长超 P95 的炉次 {overdue.n} 炉，超时 {float(overdue.over_min or 0):.0f} 分钟，预估损失 {overdue_cost / 1e4:.1f} 万元（{cf.get('time_cost')}元/分钟，含耐材）",
        "value": round(overdue_cost, 0),
    })

    # 3. 各工序时长-成本（各工序总时长 × 能耗单价）
    proc_dur = db.execute(text(f"""
        SELECT process, SUM({_DUR_EXPR}) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS total_min
        FROM fact_heat_indicator WHERE indicator_name LIKE '%时长%'
        GROUP BY process ORDER BY total_min DESC
    """)).all()
    items.append({
        "title": "各工序时长-成本（时间=成本）",
        "level": "提示",
        "content": f"各工序总时长换算能耗成本（{epm}元/分钟），识别成本集中工序",
        "chart": {"type": "bar", "title": "各工序时长-成本(万元)", "labels": [r.process for r in proc_dur],
                  "values": [round(float(r.total_min or 0) * epm / 1e4, 1) for r in proc_dur]},
    })

    # 4. 班组效率-成本对标（班组平均时长 × 能耗单价）
    team_dur = db.execute(text(f"""
        SELECT team, AVG({_DUR_EXPR}) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS avg_min
        FROM fact_heat_indicator WHERE indicator_name LIKE '%时长%' AND team IS NOT NULL
        GROUP BY team ORDER BY avg_min DESC
    """)).all()
    items.append({
        "title": "班组效率-成本对标（平均时长 × 成本）",
        "level": "提示",
        "content": f"各班组平均工序时长换算成本，识别效率差距与最优班组",
        "chart": {"type": "bar", "title": "班组平均时长-成本(元/炉)", "labels": [r.team + '班' for r in team_dur],
                  "values": [round(float(r.avg_min or 0) * epm, 0) for r in team_dur]},
    })

    return {"category": "成本 × 效率", "items": items}


def crossover_all(db: Session) -> dict:
    """全部双维度交汇汇总。"""
    return {
        "quality_cost": quality_cost_crossover(db),
        "quality_efficiency": quality_efficiency_crossover(db),
        "cost_efficiency": cost_efficiency_crossover(db),
    }
