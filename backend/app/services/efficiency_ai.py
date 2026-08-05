"""AI智能分析服务 - 效率域（聚焦效率指标：周期/班组/设备/趋势）。

不包含效率损失成本（在综合分析的效率×成本交叉）。
只分析：冶炼周期、班组产能、设备利用率、工艺趋势。

单位约定：源数据中转炉时长类指标为秒（如总吹氩180-660s），
精炼/真空为分钟。统一换算为分钟后再做统计对比。
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

# 时长统一为分钟：转炉（除镇静）为秒÷60，其余保持分钟
DUR_CTE = """
    WITH d AS (
        SELECT process, indicator_name,
            CASE WHEN process = '转炉' AND indicator_name <> '镇静时长'
                 THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END AS dur
        FROM fact_heat_indicator
        WHERE indicator_name LIKE '%时长%'
            AND actual_value ~ '^[0-9]+\\.?[0-9]*$'
    )
"""


def _rate(hit, judged):
    return round(100 * hit / judged, 1) if judged else 0


def efficiency_overview_analysis(db: Session) -> dict:
    """效率总览AI：全局效率评价 + 瓶颈工序 + 班组差距。"""
    # 各工序时长（已统一为分钟；P99为典型上限，原始MAX用于异常发现）
    durations = db.execute(text(DUR_CTE + """
        SELECT process, indicator_name,
            ROUND((AVG(dur))::numeric, 1) AS avg_val,
            ROUND((PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY dur))::numeric, 1) AS p99_val,
            ROUND((MAX(dur))::numeric, 1) AS max_val,
            COUNT(*) AS n
        FROM d GROUP BY process, indicator_name ORDER BY avg_val DESC NULLS LAST
    """)).all()

    # 班组产能
    teams = db.execute(text("""
        SELECT team,
            COUNT(DISTINCT heat_no) AS heats,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE team IS NOT NULL
        GROUP BY team ORDER BY heats DESC
    """)).all()

    # 设备负荷（按工序×设备，避免同设备号跨工序重复计数）
    equipment = db.execute(text("""
        SELECT process, equipment,
            COUNT(DISTINCT heat_no) AS heats,
            ROUND(100.0 * COUNT(DISTINCT heat_no) / SUM(COUNT(DISTINCT heat_no)) OVER (PARTITION BY process), 1) AS pct
        FROM fact_heat_indicator WHERE equipment IS NOT NULL
        GROUP BY process, equipment ORDER BY pct DESC
    """)).all()

    total_heats = sum(t.heats for t in teams)
    total_equipment = len(set(r.equipment for r in equipment))

    # 瓶颈工序（avg最大，分钟）
    bottleneck = max(durations, key=lambda r: float(r.avg_val or 0)) if durations else None

    findings = []
    if bottleneck:
        bn_avg = float(bottleneck.avg_val or 0)
        bn_p99 = float(bottleneck.p99_val or 0)
        findings.append({"title": "瓶颈工序", "level": "警告" if bn_avg > 30 else "提示",
            "content": f"{bottleneck.process}·{bottleneck.indicator_name}均值{bn_avg}min，典型上限P99为{bn_p99}min，是节奏瓶颈。该指标直接影响冶炼周期和连铸匹配。",
            "evidence": f"均值{bn_avg}min P99={bn_p99}min"})

    # 班组差距
    if len(teams) >= 2:
        rates = [(_rate(t.hit, t.judged), t.team, t.heats) for t in teams]
        best = max(rates, key=lambda x: x[0])
        worst = min(rates, key=lambda x: x[0])
        gap = best[0] - worst[0]
        if gap > 10:
            findings.append({"title": "班组效率差距", "level": "警告",
                "content": f"班组符合率差距{gap}pp，{best[1]}班({best[0]}%)优于{worst[1]}班({worst[0]}%)。效率低意味着同样产量需要更多时间/炉次。",
                "evidence": f"差距{gap}pp"})
        # 产量差距
        max_h = max(t.heats for t in teams)
        min_h = min(t.heats for t in teams)
        if max_h > min_h * 1.5:
            findings.append({"title": "班组产量不均", "level": "提示",
                "content": f"班组产量差距大(最高{max_h}炉/最低{min_h}炉)，可能存在排产不均或效率差异。",
                "evidence": f"{max_h} vs {min_h}"})

    # 设备负荷集中度（工序内占比）
    if equipment:
        top_eq = equipment[0]
        if float(top_eq.pct or 0) > 40:
            findings.append({"title": "设备负荷集中", "level": "提示",
                "content": f"{top_eq.process}工序设备{top_eq.equipment}承担{top_eq.pct}%的炉次，负荷集中度高。建议评估同工序设备调度均衡性。",
                "evidence": f"{top_eq.pct}%"})

    # 时长异常长尾（P99为正常上限，超出视为异常/疑似脏值）
    for d in durations:
        p99 = float(d.p99_val or 0)
        mx = float(d.max_val or 0)
        if p99 > 0 and mx > p99 * 2:
            findings.append({"title": "时长异常长尾", "level": "警告",
                "content": f"{d.process}·{d.indicator_name}典型上限P99为{p99}min，但存在最高{mx}min的极端记录（约{mx/p99:.0f}倍），疑似录入异常或异常长炉次，建议核查对应熔炼号。",
                "evidence": f"MAX {mx}min vs P99 {p99}min"})
            break

    summary = f"共{total_heats}炉，{len(teams)}个班组，{total_equipment}台设备。"
    if bottleneck:
        summary += f" 瓶颈工序为{bottleneck.process}·{bottleneck.indicator_name}({float(bottleneck.avg_val or 0)}min)。"
    if len(teams) >= 2 and gap > 10:
        summary += f" 班组效率差距{gap}pp。"

    recommendations = []
    if bottleneck:
        recommendations.append(f"优先优化{bottleneck.process}的{bottleneck.indicator_name}，缩短冶炼周期")
    if len(teams) >= 2 and gap > 10:
        recommendations.append(f"组织{worst[1]}班向{best[1]}班对标操作经验")
    recommendations.append("建立异常长炉次预警机制，及时干预节奏异常")

    risk = "高" if (bottleneck and float(bottleneck.avg_val or 0) > 30) else "中" if (gap > 10 if len(teams) >= 2 else False) else "低"
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": risk}


def cycle_analysis(db: Session) -> dict:
    """冶炼周期AI：各工序时长分布 + 瓶颈识别（统一分钟）。"""
    rows = db.execute(text(DUR_CTE + """
        SELECT process, indicator_name,
            ROUND((AVG(dur))::numeric, 1) AS avg_val,
            ROUND((MIN(dur))::numeric, 1) AS min_val,
            ROUND((PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY dur))::numeric, 1) AS p99_val,
            ROUND((STDDEV(dur))::numeric, 1) AS std_val,
            COUNT(*) AS n
        FROM d GROUP BY process, indicator_name ORDER BY avg_val DESC
    """)).all()

    findings = []
    proc_map = {}
    for r in rows:
        p = proc_map.setdefault(r.process, {"items": [], "total_avg": 0, "count": 0})
        p["items"].append(r)
        p["total_avg"] += float(r.avg_val or 0)
        p["count"] += 1

    # 各工序平均时长
    for proc, data in proc_map.items():
        proc_avg = data["total_avg"] / data["count"] if data["count"] else 0
        longest = max(data["items"], key=lambda r: float(r.avg_val or 0))
        std_v = float(longest.std_val or 0)
        level = "警告" if std_v > float(longest.avg_val or 1) * 0.5 else "提示"
        findings.append({"title": f"{proc}时长分析", "level": level,
            "content": f"{proc}各时长指标均值{proc_avg:.0f}min，最长为{longest.indicator_name}({float(longest.avg_val or 0)}min)。波动(std={std_v}){'大，工艺不稳定' if level == '警告' else '正常'}。",
            "evidence": f"均值{proc_avg:.0f}min"})

    # 超时炉次（精炼·有效精炼时长，单位分钟）
    overdue = db.execute(text("""
        WITH d AS (SELECT actual_value::numeric AS dur FROM fact_heat_indicator
                   WHERE process = '精炼' AND indicator_name = '有效精炼时长'
                     AND actual_value ~ '^[0-9]+\\.?[0-9]*$'),
             p AS (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY dur) AS p95 FROM d)
        SELECT COUNT(*) AS n, SUM(dur - p.p95) AS over_min FROM d, p WHERE d.dur > p.p95
    """)).one()
    if overdue.n and overdue.n > 0:
        findings.append({"title": "精炼超时炉次", "level": "警告",
            "content": f"精炼时长超P95的炉次{overdue.n}炉，超时{float(overdue.over_min or 0):.0f}min。超时影响连铸匹配和整体节奏。建议建立超时预警。",
            "evidence": f"{overdue.n}炉超时{float(overdue.over_min or 0):.0f}min"})

    summary = f"共{len(rows)}个时长指标，{len(proc_map)}个工序。"
    if proc_map:
        worst_proc = max(proc_map.items(), key=lambda x: x[1]["total_avg"] / x[1]["count"])
        summary += f" {worst_proc[0]}平均时长最长({worst_proc[1]['total_avg']/worst_proc[1]['count']:.0f}min)。"

    recommendations = [
        "建立各工序标准时长基线，超时自动预警",
        "分析超时炉次的根因（等待/设备/操作）",
    ]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中"}


def team_analysis(db: Session) -> dict:
    """班组产能AI：班组效率/产量/符合率对标。"""
    teams = db.execute(text("""
        SELECT team,
            COUNT(DISTINCT heat_no) AS heats,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE team IS NOT NULL
        GROUP BY team ORDER BY heats DESC
    """)).all()

    findings = []
    rates = []
    for t in teams:
        r = _rate(t.hit, t.judged)
        rates.append((r, t.team, t.heats))
        findings.append({"title": f"{t.team}班", "level": "亮点" if r >= 90 else "警告" if r < 80 else "提示",
            "content": f"{t.team}班{t.heats}炉，符合率{r}%。{'效率与质量双优' if r >= 90 else '需提升' if r < 80 else '基本达标'}。",
            "evidence": f"{r}%/{t.heats}炉"})

    gap = 0
    if len(rates) >= 2:
        best = max(rates, key=lambda x: x[0])
        worst = min(rates, key=lambda x: x[0])
        gap = best[0] - worst[0]
        if gap > 10:
            findings.append({"title": "班组对标差异", "level": "警告",
                "content": f"{best[1]}班(符合率{best[0]}%)与{worst[1]}班({worst[0]}%)差距{gap}pp。建议组织{worst[1]}班向{best[1]}班学习操作经验。",
                "evidence": f"差距{gap}pp"})
        # 产量
        max_h = max(r[2] for r in rates)
        min_h = min(r[2] for r in rates)
        if max_h > min_h * 1.3:
            findings.append({"title": "班组产量不均", "level": "提示",
                "content": f"产量差距大(最高{max_h}炉/最低{min_h}炉)，建议评估排产合理性。",
                "evidence": f"{max_h}/{min_h}"})

    summary = f"共{len(teams)}个班组，总{sum(t.heats for t in teams)}炉。"
    if len(rates) >= 2 and gap > 10:
        summary += f" 班组差距{gap}pp，{best[1]}班最优。"

    recommendations = []
    if len(rates) >= 2 and gap > 10:
        recommendations.append(f"组织{worst[1]}班向{best[1]}班对标，缩小{gap}pp差距")
    recommendations.append("建立班组效率看板，日/周/月跟踪")
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中" if gap > 10 else "低"}


def equipment_analysis(db: Session) -> dict:
    """设备效率AI：按工序×设备分析产量/负荷/符合率。"""
    equipment = db.execute(text("""
        SELECT process, equipment,
            COUNT(DISTINCT heat_no) AS heats,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE equipment IS NOT NULL
        GROUP BY process, equipment ORDER BY process, heats DESC
    """)).all()

    findings = []
    # 按工序分组，做工序内对标（同工序设备才可比）
    proc_groups = {}
    for e in equipment:
        proc_groups.setdefault(e.process, []).append(e)
    for proc, items in proc_groups.items():
        if not items:
            continue
        total = sum(e.heats for e in items)
        top = max(items, key=lambda e: e.heats)
        top_pct = round(100 * top.heats / total, 1)
        rate_best = max(items, key=lambda e: _rate(e.hit, e.judged))
        rate_worst = min(items, key=lambda e: _rate(e.hit, e.judged))
        r_best, r_worst = _rate(rate_best.hit, rate_best.judged), _rate(rate_worst.hit, rate_worst.judged)
        r_gap = r_best - r_worst

        content = f"{proc}共{len(items)}台设备（{top.equipment}承担{top_pct}%），符合率最高{rate_best.equipment}({r_best}%)，最低{rate_worst.equipment}({r_worst}%)。"
        if len(items) >= 2:
            load_max, load_min = max(items, key=lambda e: e.heats), min(items, key=lambda e: e.heats)
            gap = round(100 * load_max.heats / total - 100 * load_min.heats / total, 1)
            content += f" 负荷差距{gap}pp{'，存在偏载风险' if gap > 20 else '，基本均衡'}。"
        level = "警告" if (r_gap > 15 or (len(items) >= 2 and 100 * max(items, key=lambda e: e.heats).heats / total > 40)) else "提示"
        findings.append({"title": f"{proc}设备分析", "level": level,
            "content": content,
            "evidence": f"{len(items)}台/负荷{top_pct}%"})

    summary = f"共{len(equipment)}个工序×设备组合，覆盖{len(proc_groups)}个工序。"
    if equipment:
        top = max(equipment, key=lambda e: e.heats)
        summary += f" 单设备最高负荷为{top.process}·{top.equipment}({top.heats}炉)。"

    recommendations = ["评估同工序设备负荷均衡性，避免单一设备过载"]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中"}


def trend_analysis(db: Session) -> dict:
    """工艺趋势AI：关键参数时序 + 趋势预警。"""
    # 关键参数：连铸中包过热度 / 精炼有效精炼时长 / 转炉出钢时长（转炉秒→分钟）
    indicators = db.execute(text("""
        WITH d AS (
            SELECT process, indicator_name,
                CASE WHEN process = '转炉' AND indicator_name <> '镇静时长'
                     THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END AS v
            FROM fact_heat_indicator
            WHERE ((process IN ('板坯', '方坯') AND indicator_name = '中包过热度')
                OR (process = '精炼' AND indicator_name = '有效精炼时长')
                OR (process = '转炉' AND indicator_name = '出钢时长'))
                AND actual_value ~ '^[0-9]+\\.?[0-9]*$'
        )
        SELECT process, indicator_name, COUNT(*) AS n,
            ROUND((AVG(v))::numeric, 1) AS avg_val,
            ROUND((STDDEV(v))::numeric, 1) AS std_val
        FROM d GROUP BY process, indicator_name
    """)).all()

    findings = []
    data = []
    for ind in indicators:
        avg = float(ind.avg_val or 0)
        std = float(ind.std_val or 0)
        cv = (std / avg * 100) if avg > 0 else 0
        level = "警告" if cv > 30 else "提示"
        unit = "°C" if ind.indicator_name == "中包过热度" else "min"
        data.append({"indicator": f"{ind.process}·{ind.indicator_name}", "avg": avg, "std": std, "cv": round(cv, 1), "unit": unit})
        findings.append({"title": f"{ind.indicator_name}趋势", "level": level,
            "content": f"{ind.process}·{ind.indicator_name}均值{avg}{unit}，标准差{std}{unit}，变异系数{cv:.1f}%。{'波动大，工艺稳定性不足' if cv > 30 else '波动正常，工艺稳定'}。",
            "evidence": f"CV={cv:.1f}%"})

    summary = f"分析{len(indicators)}个关键参数趋势。"
    unstable = [f for f in findings if f["level"] == "警告"]
    if unstable:
        summary += f" {len(unstable)}个参数波动较大，需关注工艺稳定性。"

    recommendations = ["建立关键参数控制图(SPC)，实时监控趋势", "对波动大的参数开展工艺优化"]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "高" if unstable else "低", "data": data}


def efficiency_ai_analysis(db: Session) -> dict:
    """效率AI分析汇总。"""
    return {
        "overview": efficiency_overview_analysis(db),
        "cycle": cycle_analysis(db),
        "team": team_analysis(db),
        "equipment": equipment_analysis(db),
        "trend": trend_analysis(db),
    }
