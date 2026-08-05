"""智能洞察服务：自动识别各主线问题（短板/异常/风险/规律）。

借鉴原 demo 的智能洞察 section + 兴澄的异常识别，做"问题识别"能力。
每条洞察：title + level(严重/警告/提示/亮点) + content + 可选 data。
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from .cost import scrap_overview
from .efficiency import duration_stats, heat_count_by_team
from .overview import direct_cost
from .quality import heat_score, indicator_ranking


def quality_insights(db: Session) -> dict:
    """质量洞察：短板指标、合金超标准、低分炉次、力学异常。"""
    items = []

    # 1. 最差指标 Top3（符合率最低）
    worst = indicator_ranking(db, None, "asc")[:3]
    for w in worst:
        level = "严重" if w["rate"] < 60 else ("警告" if w["rate"] < 80 else "提示")
        items.append({
            "title": "短板指标",
            "level": level,
            "content": f"{w['name']}（{w['process']}）符合率仅 {w['rate']}%，命中 {w['hit']}/{w['judged']}",
        })

    # 2. 合金超标准比例
    row = db.execute(text("""
        SELECT
          COUNT(*) FILTER (WHERE judge = 0) AS bad,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS total
        FROM fact_heat_indicator WHERE process = '合金'
    """)).one()
    if row.total:
        pct = round(100 * row.bad / row.total, 1)
        items.append({
            "title": "合金加入超标准",
            "level": "警告" if pct > 30 else "提示",
            "content": f"合金 judge=0 共 {row.bad} 项，占 {pct}%，存在加入量超标准（成本浪费风险）",
        })

    # 3. 低分炉次（符合率 < 80%）
    scores = heat_score(db, 200)
    low = [s for s in scores if s["score"] < 80]
    if low:
        items.append({
            "title": "低质量炉次",
            "level": "严重",
            "content": f"符合率<80% 的炉次 {len(low)} 炉，最低 {low[-1]['score']}%（{low[-1]['heat_no']} / {low[-1]['steel_grade']}）",
        })
    else:
        items.append({"title": "质量稳定性", "level": "亮点", "content": "Top200 炉次符合率均≥80%，整体质量稳定"})

    # 4. 力学性能异常（屈服/抗拉超出 3σ）
    mech = db.execute(text("""
        SELECT
          COUNT(*) FILTER (WHERE yield_strength < (SELECT AVG(yield_strength)-3*STDDEV(yield_strength) FROM fact_inspect_mech)
                             OR yield_strength > (SELECT AVG(yield_strength)+3*STDDEV(yield_strength) FROM fact_inspect_mech)) AS ys_out,
          COUNT(*) AS n
        FROM fact_inspect_mech WHERE yield_strength IS NOT NULL
    """)).one()
    if mech.n and mech.ys_out:
        items.append({
            "title": "力学性能离群",
            "level": "警告",
            "content": f"屈服强度超 3σ 的样本 {mech.ys_out} 个（共 {mech.n}），需关注离群炉次",
        })

    return {"category": "质量", "items": items}


def cost_insights(db: Session) -> dict:
    """成本洞察：料型集中度、高价合金、合金超标准损失、零用料型。"""
    items = []

    # 1. 废钢料型集中度
    s = scrap_overview(db)
    top3 = (s.get("types") or [])[:3]
    if top3:
        pct = round(sum(t["pct"] for t in top3), 1)
        names = "、".join(t["scrap_type"] for t in top3)
        items.append({
            "title": "废钢料型集中度",
            "level": "提示",
            "content": f"Top3 料型（{names}）占 {pct}%，配料结构{'高度集中' if pct > 80 else '相对均衡'}",
        })

    # 2. 高价合金集中
    dc = direct_cost(db)
    top_alloy = (dc.get("alloy_cost") or [])[:3]
    if top_alloy and dc["total_alloy_cost"]:
        pct = round(100 * sum(a["cost"] for a in top_alloy) / dc["total_alloy_cost"], 1)
        names = "、".join(a["alloy"] for a in top_alloy)
        items.append({
            "title": "高价合金集中",
            "level": "警告" if pct > 60 else "提示",
            "content": f"Top3 合金（{names}）占合金成本 {pct}%，价格波动影响大",
        })

    # 3. 合金符合率低（超标准 / 富裕）
    row = db.execute(text("""
        SELECT indicator_name,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE process = '合金'
        GROUP BY indicator_name
        ORDER BY COUNT(*) FILTER (WHERE judge = 1)::float / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL),0) ASC
        LIMIT 3
    """)).all()
    for r in row:
        rate = round(100 * r.hit / r.judged, 1) if r.judged else 0
        items.append({
            "title": "合金富裕/超标准",
            "level": "警告" if rate < 60 else "提示",
            "content": f"{r.indicator_name} 符合率 {rate}%，存在加入量超标准（富裕浪费）",
        })

    # 4. 零用料型
    zero = [t["scrap_type"] for t in (s.get("types") or []) if (t.get("used_grades") or 0) == 0]
    if zero:
        items.append({
            "title": "零用料型",
            "level": "提示",
            "content": f"{len(zero)} 种料型零使用：{'、'.join(zero)}，可考虑配料优化",
        })

    # 5. 价格来源
    real = sum(1 for a in (dc.get("alloy_cost") or []) if a.get("source") == "smm")
    items.append({
        "title": "价格覆盖",
        "level": "提示",
        "content": f"合金中 {real} 种用 SMM 真实价，其余估算，价格准确性待提升",
    })

    return {"category": "成本", "items": items}


def efficiency_insights(db: Session) -> dict:
    """效率洞察：瓶颈工序、班组差距、超时炉次。"""
    items = []

    # 1. 瓶颈工序（时长均值最大）
    dur = duration_stats(db)
    if dur:
        longest = max(dur, key=lambda x: x["avg"])
        items.append({
            "title": "瓶颈工序",
            "level": "警告",
            "content": f"{longest['process']}·{longest['indicator']} 均值 {longest['avg']}min（P99 {longest['p99']}min），是节奏瓶颈",
        })
        # 超时（max 远大于 avg）
        for d in dur:
            if d["p99"] > d["avg"] * 3 and d["avg"] > 0:
                items.append({
                    "title": "时长异常波动",
                    "level": "警告",
                    "content": f"{d['process']}·{d['indicator']} P99 {d['p99']}min 是均值 {d['avg']}min 的 {round(d['p99']/d['avg'],1)} 倍，存在异常长炉次",
                })

    # 2. 班组符合率差距
    team = heat_count_by_team(db)
    if len(team) >= 2:
        rates = [t["rate"] for t in team]
        gap = round(max(rates) - min(rates), 1)
        best = max(team, key=lambda x: x["rate"])
        worst_t = min(team, key=lambda x: x["rate"])
        items.append({
            "title": "班组质量差距",
            "level": "警告" if gap > 10 else "提示",
            "content": f"符合率最高 {best['team']}班 {best['rate']}%，最低 {worst_t['team']}班 {worst_t['rate']}%，差距 {gap}pp",
        })
        # 班组产量差距
        heats = [t["heats"] for t in team]
        items.append({
            "title": "班组产能差距",
            "level": "提示",
            "content": f"产量最高 {max(heats)} 炉，最低 {min(heats)} 炉",
        })

    return {"category": "效率", "items": items}


def overview_insights(db: Session) -> dict:
    """综合洞察：三主线汇总 + 优化优先级。"""
    q = quality_insights(db)
    c = cost_insights(db)
    e = efficiency_insights(db)

    all_items = q["items"] + c["items"] + e["items"]
    severe = [i for i in all_items if i["level"] == "严重"]
    warn = [i for i in all_items if i["level"] == "警告"]

    # 优化优先级：严重>警告，按主线
    priority = []
    if severe:
        priority.append(f"立即处理 {len(severe)} 项严重问题（质量/效率短板）")
    if warn:
        priority.append(f"重点关注 {len(warn)} 项警告（成本浪费/班组差距）")
    priority.append("补齐产出侧数据后启动综合成本模型（第二阶段）")

    return {
        "quality": q,
        "cost": c,
        "efficiency": e,
        "summary": {
            "total": len(all_items),
            "severe": len(severe),
            "warning": len(warn),
        },
        "priority": priority,
    }
