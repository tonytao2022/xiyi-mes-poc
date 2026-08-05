"""AI智能分析服务 - 成本域（聚焦直接成本：钢铁料/合金/能源/耐材）。

不包含质量损失/效率损失/富裕损失（这些在综合分析和综合成本模型）。
只分析：花了多少钱买材料、各科目多少、价格趋势、直接成本对标。
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from .overview import ESTIMATED_ALLOY, ESTIMATED_SCRAP


def cost_overview_analysis(db: Session) -> dict:
    """成本总览AI：直接成本综合评价 + 成本结构 + 价格风险。"""
    # 直接成本结构
    scrap_rows = db.execute(text("""
        SELECT scrap_type, SUM(weight) AS weight
        FROM fact_scrap_ratio GROUP BY scrap_type
    """)).all()
    total_scrap_weight = sum(float(r.weight or 0) for r in scrap_rows)
    scrap_cost = sum(float(r.weight or 0) * ESTIMATED_SCRAP.get(r.scrap_type, 2800) for r in scrap_rows)

    alloy_rows = db.execute(text("""
        SELECT indicator_name AS alloy,
            SUM(actual_value::numeric) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS total_amount
        FROM fact_heat_indicator WHERE process = '合金'
        GROUP BY indicator_name
    """)).all()
    alloy_cost = sum(float(r.total_amount or 0) * ESTIMATED_ALLOY.get(r.alloy, 8000) for r in alloy_rows)

    # 价格覆盖
    real_prices = db.execute(text("SELECT COUNT(*) FROM dim_price WHERE source = 'smm'")).scalar() or 0
    total_items = len(ESTIMATED_SCRAP) + len(ESTIMATED_ALLOY)
    coverage_pct = round(100 * real_prices / total_items, 1) if total_items else 0

    # 各料型成本占比
    scrap_costs = sorted([
        {"type": r.scrap_type, "weight": float(r.weight or 0),
         "cost": float(r.weight or 0) * ESTIMATED_SCRAP.get(r.scrap_type, 2800)}
        for r in scrap_rows
    ], key=lambda x: x["cost"], reverse=True)
    scrap_top3_pct = round(100 * sum(s["cost"] for s in scrap_costs[:3]) / scrap_cost, 1) if scrap_cost else 0

    # 合金成本占比
    alloy_costs = sorted([
        {"alloy": r.alloy, "amount": float(r.total_amount or 0),
         "cost": float(r.total_amount or 0) * ESTIMATED_ALLOY.get(r.alloy, 8000)}
        for r in alloy_rows
    ], key=lambda x: x["cost"], reverse=True)
    alloy_top3_pct = round(100 * sum(a["cost"] for a in alloy_costs[:3]) / alloy_cost, 1) if alloy_cost else 0

    total_direct = scrap_cost + alloy_cost
    scrap_pct = round(100 * scrap_cost / total_direct, 1) if total_direct else 0
    alloy_pct = round(100 * alloy_cost / total_direct, 1) if total_direct else 0

    findings = []
    if scrap_top3_pct > 80:
        findings.append({"title": "废钢料型高度集中", "level": "警告",
            "content": f"Top3废钢料型成本占{scrap_top3_pct}%，配料结构集中度高。低价料(渣钢+压块)占比偏低，配料成本优化空间有限，建议拓展料型采购渠道。",
            "evidence": f"Top3占比{scrap_top3_pct}%"})
    else:
        findings.append({"title": "废钢料型结构均衡", "level": "提示",
            "content": f"Top3废钢料型成本占{scrap_top3_pct}%，配料结构相对均衡。",
            "evidence": f"Top3占比{scrap_top3_pct}%"})

    if alloy_top3_pct > 60:
        findings.append({"title": "合金成本集中", "level": "警告",
            "content": f"Top3合金成本占{alloy_top3_pct}%，合金成本波动对总成本影响大。建议关注硅锰/低碳锰铁/铜板的价格趋势。",
            "evidence": f"Top3占比{alloy_top3_pct}%"})

    if coverage_pct < 30:
        findings.append({"title": "价格数据覆盖不足", "level": "警告",
            "content": f"仅{real_prices}种物料有SMM真实价格，覆盖率{coverage_pct}%。多数用估算价，成本分析准确性受限。建议扩大价格采集范围。",
            "evidence": f"覆盖{coverage_pct}%({real_prices}/{total_items})"})
    else:
        findings.append({"title": "价格覆盖良好", "level": "亮点",
            "content": f"SMM真实价格覆盖{coverage_pct}%，成本分析基础较好。",
            "evidence": f"覆盖{coverage_pct}%"})

    summary = f"直接成本合计{total_direct/1e4:.1f}万元，钢铁料占{scrap_pct}%、合金占{alloy_pct}%。"
    if scrap_top3_pct > 80:
        summary += " 废钢料型集中度高，建议优化配料结构。"
    if coverage_pct < 30:
        summary += " 价格覆盖率偏低，建议扩大SMM采集范围。"

    recommendations = [
        f"关注Top3废钢料型({', '.join(s['type'] for s in scrap_costs[:3])})的价格走势",
        f"关注Top3合金({', '.join(a['alloy'] for a in alloy_costs[:3])})的市场行情",
    ]
    if coverage_pct < 30:
        recommendations.append("扩大SMM价格采集品种，提升成本分析准确性")
    if scrap_top3_pct > 80:
        recommendations.append("评估增加低价料(渣钢/压块)配比的可行性，降低钢铁料成本")

    return {
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "risk": "中" if scrap_top3_pct > 80 or coverage_pct < 30 else "低",
        "metrics": {
            "total_direct": round(total_direct, 0), "scrap_cost": round(scrap_cost, 0),
            "alloy_cost": round(alloy_cost, 0), "scrap_pct": scrap_pct, "alloy_pct": alloy_pct,
            "coverage_pct": coverage_pct, "real_prices": real_prices,
        }
    }


def steel_material_analysis(db: Session) -> dict:
    """钢铁料成本AI：配比结构 + 钢种用量 + 成本分析。"""
    rows = db.execute(text("""
        SELECT scrap_type, SUM(weight) AS weight, SUM(heat_count) AS heats
        FROM fact_scrap_ratio GROUP BY scrap_type ORDER BY weight DESC
    """)).all()
    total_weight = sum(float(r.weight or 0) for r in rows)
    total_cost = sum(float(r.weight or 0) * ESTIMATED_SCRAP.get(r.scrap_type, 2800) for r in rows)

    # 高低价料分析
    low_end = {"渣钢", "普通压块", "冷饼"}
    low_weight = sum(float(r.weight or 0) for r in rows if r.scrap_type in low_end)
    low_pct = round(100 * low_weight / total_weight, 1) if total_weight else 0

    # 单价差异
    prices = [(r.scrap_type, ESTIMATED_SCRAP.get(r.scrap_type, 2800), float(r.weight or 0)) for r in rows]
    max_price = max(prices, key=lambda x: x[1]) if prices else ("", 0, 0)
    min_price = min(prices, key=lambda x: x[1]) if prices else ("", 0, 0)

    findings = []
    if low_pct < 10:
        findings.append({"title": "低价料占比低", "level": "提示",
            "content": f"低价料(渣钢+压块+冷饼)占比仅{low_pct}%，配料成本偏高。如质量允许，增加低价料配比可降低钢铁料成本。",
            "evidence": f"低价料{low_pct}%"})
    elif low_pct > 30:
        findings.append({"title": "低价料占比高", "level": "警告",
            "content": f"低价料占比{low_pct}%，需关注杂质元素对质量的影响。低价料杂质含量高，可能影响成分命中率（质量×成本交叉分析）。",
            "evidence": f"低价料{low_pct}%"})

    price_spread = max_price[1] - min_price[1]
    if price_spread > 1000:
        findings.append({"title": "料型价差大", "level": "提示",
            "content": f"最高价料型{max_price[0]}({max_price[1]}元/吨)与最低价{min_price[0]}({min_price[1]}元/吨)价差{price_spread}元/吨，配料结构优化空间大。",
            "evidence": f"价差{price_spread}元/吨"})

    # 钢种消耗
    grades = db.execute(text("""
        SELECT steel_grade, MAX(total_weight) AS w, MAX(heat_count) AS h
        FROM fact_scrap_ratio GROUP BY steel_grade ORDER BY w DESC LIMIT 5
    """)).all()
    if grades:
        top_grade = grades[0]
        findings.append({"title": "高消耗钢种", "level": "提示",
            "content": f"钢种{top_grade.steel_grade}废钢消耗最高({float(top_grade.w or 0):.0f}吨/{int(top_grade.h or 0)}炉)，是该钢种配料成本的主要贡献者。",
            "evidence": f"{float(top_grade.w or 0):.0f}吨"})

    summary = f"钢铁料总成本{total_cost/1e4:.1f}万元，总用量{total_weight:.0f}吨。低价料占{low_pct}%。"
    if low_pct < 10:
        summary += " 低价料占比偏低，有配料优化空间。"

    recommendations = []
    if low_pct < 15:
        recommendations.append(f"评估增加低价料配比（当前{low_pct}%），每增加1%约可节省{total_weight*0.01*200:.0f}元/吨")
    recommendations.append("关注废钢市场行情，锁定低价采购窗口")
    if price_spread > 1000:
        recommendations.append(f"分析{max_price[0]}与{min_price[0]}的替代可行性")

    return {
        "summary": summary, "findings": findings, "recommendations": recommendations,
        "risk": "中" if low_pct < 10 or low_pct > 30 else "低",
    }


def alloy_cost_analysis(db: Session) -> dict:
    """合金成本AI：使用频率 + 加入量 + 成本分析。"""
    rows = db.execute(text("""
        SELECT indicator_name AS alloy,
            SUM(actual_value::numeric) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS total_amount,
            COUNT(*) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$' AND actual_value::numeric > 0) AS used_count,
            ROUND(AVG(actual_value::numeric) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$'), 2) AS avg_amount
        FROM fact_heat_indicator WHERE process = '合金'
        GROUP BY indicator_name ORDER BY total_amount DESC NULLS LAST
    """)).all()

    alloy_data = []
    total_cost = 0
    for r in rows:
        price = ESTIMATED_ALLOY.get(r.alloy, 8000)
        amount = float(r.total_amount or 0)
        cost = amount * price
        total_cost += cost
        alloy_data.append({"alloy": r.alloy, "amount": round(amount, 1), "price": price,
                          "cost": round(cost, 0), "used": int(r.used_count or 0),
                          "avg": float(r.avg_amount or 0)})

    alloy_data.sort(key=lambda x: x["cost"], reverse=True)
    top3_cost = sum(a["cost"] for a in alloy_data[:3])
    top3_pct = round(100 * top3_cost / total_cost, 1) if total_cost else 0

    findings = []
    if top3_pct > 60:
        top3_names = "、".join(a["alloy"] for a in alloy_data[:3])
        findings.append({"title": "合金成本集中", "level": "警告",
            "content": f"Top3合金({top3_names})成本占{top3_pct}%，价格波动对总成本影响大。建议建立这3种合金的价格监控和采购策略。",
            "evidence": f"Top3占比{top3_pct}%"})

    # 高价合金
    expensive = [a for a in alloy_data if a["price"] > 100000]
    if expensive:
        names = "、".join(a["alloy"] for a in expensive[:3])
        total_exp = sum(a["cost"] for a in expensive)
        findings.append({"title": "高价合金", "level": "警告",
            "content": f"{names}等高价合金(>10万/吨)成本合计{total_exp/1e4:.1f}万元，是成本敏感品种。建议评估替代方案或窄控制加入量。",
            "evidence": f"{len(expensive)}种>{100000}元/吨"})

    # 使用率低的合金
    low_usage = [a for a in alloy_data if a["used"] > 0 and a["avg"] < 1]
    if low_usage:
        findings.append({"title": "低用量合金", "level": "提示",
            "content": f"{len(low_usage)}种合金平均加入量<1，可能存在过量配置或不必要合金，建议评估精简。",
            "evidence": f"{len(low_usage)}种低用量"})

    summary = f"合金成本合计{total_cost/1e4:.1f}万元，Top3占{top3_pct}%。"
    if expensive:
        summary += f" 高价合金(>10万/吨)成本{sum(a['cost'] for a in expensive)/1e4:.1f}万元，是成本敏感品种。"

    recommendations = [
        f"重点监控{alloy_data[0]['alloy']}(成本最高{alloy_data[0]['cost']/1e4:.1f}万)的市场行情",
    ]
    if expensive:
        recommendations.append(f"评估{names}的替代合金或窄控制方案")
    if low_usage:
        recommendations.append("评估低用量合金的必要性")

    return {
        "summary": summary, "findings": findings, "recommendations": recommendations,
        "risk": "高" if top3_pct > 70 else "中" if top3_pct > 50 else "低",
    }


def cost_benchmark_analysis(db: Session) -> dict:
    """成本对标AI：钢种/班组直接成本差异。"""
    # 钢种直接成本
    grades = db.execute(text("""
        SELECT steel_grade, MAX(total_weight) AS w, MAX(heat_count) AS h
        FROM fact_scrap_ratio GROUP BY steel_grade ORDER BY w DESC LIMIT 10
    """)).all()
    grade_costs = [{"grade": g.steel_grade, "weight": float(g.w or 0),
                    "heats": int(g.h or 0),
                    "per_heat": round(float(g.w or 0) / int(g.h or 1), 1)} for g in grades]
    grade_costs.sort(key=lambda x: x["per_heat"], reverse=True)

    findings = []
    if grade_costs:
        top = grade_costs[0]
        avg = sum(g["per_heat"] for g in grade_costs) / len(grade_costs)
        if top["per_heat"] > avg * 1.3:
            findings.append({"title": "高成本钢种", "level": "警告",
                "content": f"钢种{top['grade']}单炉废钢消耗{top['per_heat']:.1f}吨，高于平均{avg:.1f}吨的30%。建议分析其配料结构是否合理。",
                "evidence": f"{top['per_heat']:.1f} vs 均{avg:.1f}"})

    # 班组成本
    teams = db.execute(text("""
        SELECT team,
            COUNT(DISTINCT heat_no) AS heats,
            SUM(actual_value::numeric) FILTER (WHERE process='合金' AND actual_value ~ '^[0-9]+\\.?[0-9]*$') AS alloy_total
        FROM fact_heat_indicator WHERE team IS NOT NULL
        GROUP BY team ORDER BY heats DESC
    """)).all()
    team_costs = []
    for t in teams:
        alloy_cost = float(t.alloy_total or 0) * 8000
        team_costs.append({"team": t.team, "heats": int(t.heats),
                          "alloy_cost": round(alloy_cost / int(t.heats or 1), 0)})
    team_costs.sort(key=lambda x: x["alloy_cost"], reverse=True)

    if len(team_costs) >= 2:
        gap = team_costs[0]["alloy_cost"] - team_costs[-1]["alloy_cost"]
        if gap > 5000:
            findings.append({"title": "班组成本差异", "level": "警告",
                "content": f"班组间单炉合金成本差异{gap}元/炉，{team_costs[0]['team']}班高于{team_costs[-1]['team']}班。建议对标最优班组操作经验。",
                "evidence": f"差异{gap}元/炉"})

    if not findings:
        findings.append({"title": "成本分布均衡", "level": "亮点",
            "content": "各钢种/班组直接成本差异在合理范围内。", "evidence": "无显著差异"})

    summary = f"对标{len(grade_costs)}个钢种、{len(team_costs)}个班组的直接成本。"
    if findings and findings[0]["level"] in ("警告", "严重"):
        summary += f" 主要差异：{findings[0]['title']}。"

    recommendations = []
    if grade_costs and grade_costs[0]["per_heat"] > sum(g["per_heat"] for g in grade_costs) / len(grade_costs) * 1.3:
        recommendations.append(f"分析{grade_costs[0]['grade']}钢种配料结构，降低单炉消耗")
    if len(team_costs) >= 2 and team_costs[0]["alloy_cost"] > team_costs[-1]["alloy_cost"] * 1.2:
        recommendations.append(f"组织{team_costs[-1]['team']}班向{team_costs[0]['team']}班对标操作经验")

    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中" if findings else "低"}


def price_risk_analysis(db: Session) -> dict:
    """价格风险AI：SMM价格覆盖 + 价格趋势。"""
    real_count = db.execute(text("SELECT COUNT(*) FROM dim_price WHERE source = 'smm'")).scalar() or 0
    total_items = len(ESTIMATED_SCRAP) + len(ESTIMATED_ALLOY)
    coverage = round(100 * real_count / total_items, 1) if total_items else 0

    # SMM覆盖品种
    smm_items = db.execute(text("""
        SELECT DISTINCT item_name FROM dim_price WHERE source = 'smm'
    """)).all()
    smm_names = [r.item_name for r in smm_items]

    # 最近价格
    latest = db.execute(text("""
        SELECT item_name, unit_price, price_date
        FROM dim_price WHERE source = 'smm'
        ORDER BY price_date DESC LIMIT 5
    """)).all()

    findings = []
    if coverage < 30:
        findings.append({"title": "价格覆盖不足", "level": "严重",
            "content": f"SMM真实价格仅覆盖{real_count}种({coverage}%)，废钢全部用估算价。成本分析准确性受限，建议扩大采集范围（优先废钢单价）。",
            "evidence": f"{real_count}/{total_items}({coverage}%)"})
    else:
        findings.append({"title": "价格覆盖良好", "level": "亮点",
            "content": f"SMM真实价格覆盖{coverage}%，合金价格基础较好。",
            "evidence": f"{real_count}/{total_items}({coverage}%)"})

    if not smm_names:
        findings.append({"title": "无废钢价格", "level": "严重",
            "content": "SMM未覆盖任何废钢料型价格，钢铁料成本全部基于估算。建议优先采集废钢单价。",
            "evidence": "废钢覆盖0%"})
    else:
        findings.append({"title": "SMM已覆盖品种", "level": "提示",
            "content": f"SMM覆盖：{', '.join(smm_names[:5])}。这些品种有真实市场价格参考。",
            "evidence": f"{len(smm_names)}种"})

    summary = f"价格覆盖{coverage}%({real_count}/{total_items})。"
    if coverage < 30:
        summary += " 覆盖率偏低，多数成本用估算，准确性受限。"
    else:
        summary += " 覆盖较好，合金有真实价参考。"

    recommendations = [
        "优先采集废钢单价（当前全部估算）",
        f"扩大SMM采集至Top3合金({', '.join(list(ESTIMATED_ALLOY.keys())[:3])})",
    ]

    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "高" if coverage < 20 else "中"}


def cost_ai_analysis(db: Session) -> dict:
    """成本AI分析汇总（聚焦直接成本）。"""
    return {
        "overview": cost_overview_analysis(db),
        "steel_material": steel_material_analysis(db),
        "alloy": alloy_cost_analysis(db),
        "benchmark": cost_benchmark_analysis(db),
        "price_risk": price_risk_analysis(db),
    }
