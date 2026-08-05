"""综合分析域 AI（跨域因果链是核心亮点）。

5个子分析对应5个Tab：
- overview        综合成本健康度 + 三块占比 + 全厂结论
- quality_loss    质量损失结构 + 跨域因果链(质量根因->损失->综合成本)
- efficiency_loss 效率损失结构 + 跨域因果链(瓶颈->损失)
- cross_leverage   杠杆点识别 + 敏感度排序 + 优化优先级
- optimization    多方案对比 + 最优解推荐 + 风险提示

跨域因果链复用 ai_analysis._cross_layer_analysis 的模式（双指标配对触发 + chain 数组），
但终点接到综合成本的货币化标量（quality/efficiency loss 金额）。
AnalysisCard 原生渲染 f.chain（v-if="f.chain"），前端零改动。

置信度措辞：精确口径(formula)用"显示/达"，估算(estimated)用"估算约"。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import comprehensive, comprehensive_drilldown, simulation


def _rate(hit, judged):
    return round(100 * hit / judged, 1) if judged else 0


# 时长归一（与 comprehensive/cross 一致）
_DUR_EXPR = ("CASE WHEN process = '转炉' AND indicator_name <> '镇静时长' "
             "THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END")


def _cross_metrics(db: Session) -> dict:
    """跨域关键指标（用于因果链触发与货币化量化）。"""
    # 质量域关切：补吹率 + 终点命中率（转炉）
    q = db.execute(text("""
        SELECT
          COUNT(DISTINCT heat_no) AS heats,
          COUNT(DISTINCT heat_no) FILTER (WHERE indicator_name = '补吹出钢' AND judge = 0) AS reblow_heats,
          ROUND(100.0 * COUNT(*) FILTER (WHERE indicator_name = '终点温度' AND judge = 1)
                / NULLIF(COUNT(*) FILTER (WHERE indicator_name = '终点温度' AND judge IS NOT NULL), 0), 1) AS temp_rate,
          ROUND(100.0 * COUNT(*) FILTER (WHERE indicator_name = '终点C' AND judge = 1)
                / NULLIF(COUNT(*) FILTER (WHERE indicator_name = '终点C' AND judge IS NOT NULL), 0), 1) AS c_rate
        FROM fact_heat_indicator WHERE process = '转炉'
    """)).one()
    heats = int(q.heats or 0)
    reblow_heats = int(q.reblow_heats or 0)
    reblow_rate = round(100 * reblow_heats / heats, 1) if heats else 0
    temp_rate, c_rate = float(q.temp_rate or 0), float(q.c_rate or 0)
    endpoint_hit = round(min(temp_rate, c_rate), 1)

    # 效率域关切：有效精炼时长 P95 + 超时炉数
    overdue = db.execute(text("""
        WITH d AS (SELECT heat_no, actual_value::numeric AS dur FROM fact_heat_indicator
                   WHERE indicator_name = '有效精炼时长' AND actual_value ~ '^[0-9]+\\.?[0-9]*$'),
             p AS (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY dur) AS p95 FROM d)
        SELECT COUNT(*) AS n, ROUND((MAX(p.p95))::numeric, 1) AS p95, SUM(dur - p.p95) AS over_min
        FROM d, p WHERE d.dur > p.p95
    """)).one()

    # 班组效率损失差距（来自 fact_loss_detail 效率损失）
    team_loss = db.execute(text("""
        SELECT team, ROUND(SUM(amount)) AS total
        FROM fact_loss_detail WHERE loss_category = 'efficiency'
        GROUP BY team ORDER BY total DESC
    """)).all()

    # 低端料占比 vs 合金符合率（成本×质量权衡）
    trade = comprehensive_drilldown.tradeoff_analysis(db).get("scrap_quality_tradeoff", [])
    low_end_high = any(t["low_pct"] > 30 for t in trade) if trade else False

    return {
        "heats": heats, "reblow_heats": reblow_heats, "reblow_rate": reblow_rate,
        "endpoint_hit": endpoint_hit, "temp_rate": temp_rate, "c_rate": c_rate,
        "overdue_p95": float(overdue.p95 or 0), "overdue_heats": int(overdue.n or 0),
        "overdue_min": round(float(overdue.over_min or 0), 0),
        "team_loss": [(r.team, float(r.total or 0)) for r in team_loss],
        "tradeoff": trade, "low_end_high": low_end_high,
    }


def _overview(ctx: dict) -> dict:
    """综合成本总账AI：三块占比评价 + 最大损失块 + 全厂成本健康度。"""
    s = ctx["structure"]
    xm = ctx["xm"]
    findings = []

    # 三块占比评价
    findings.append({"title": "综合成本结构", "level": "提示",
        "content": f"直接成本{s['direct_pct']}% / 质量损失{s['quality_pct']}% / 效率损失{s['efficiency_pct']}%。"
                   f"综合成本合计约{s['total']/1e4:.0f}万元（{xm['heats']}炉样本）。",
        "evidence": f"直接{s['direct_pct']}% 质量{s['quality_pct']}% 效率{s['efficiency_pct']}%"})

    # 最大损失块
    if s["quality_pct"] >= s["efficiency_pct"]:
        dom, dom_pct, dom_val = "质量损失", s["quality_pct"], s["quality"]
    else:
        dom, dom_pct, dom_val = "效率损失", s["efficiency_pct"], s["efficiency"]
    if dom_pct > 5:
        findings.append({"title": f"{dom}是主要损失块", "level": "警告",
            "content": f"{dom}占综合成本{dom_pct}%（约{dom_val/1e4:.1f}万元），高于行业标杆(<3%)，是降本主攻方向。"
                       f"{'质量损失多源于补吹/废品/合金富裕，建议从终点命中率切入' if dom=='质量损失' else '效率损失多源于超时/能耗，建议从精炼周期切入'}。",
            "evidence": f"{dom}{dom_pct}%"})

    # 补吹三重损失（跨域概览）
    if xm["reblow_rate"] > 3:
        findings.append({"title": "补吹形成三重损失链", "level": "警告",
            "content": f"补吹率{xm['reblow_rate']}%（{xm['reblow_heats']}炉，估算损失约{xm['reblow_heats']*5000/1e4:.1f}万元），"
                       f"同时推高质量损失(补吹损失)与效率损失(补吹延长周期)，是跨域优化的关键切入点，详见质量损失折算Tab。",
            "evidence": f"补吹率{xm['reblow_rate']}%"})

    # 核心瓶颈：终点命中率（三域共同根因）
    if xm["endpoint_hit"] < 80:
        findings.append({"title": "核心瓶颈: 终点命中率低", "level": "严重" if xm["endpoint_hit"] < 60 else "警告",
            "content": f"转炉终点命中率仅{xm['endpoint_hit']}%（温度{xm['temp_rate']}%/碳{xm['c_rate']}%），"
                       f"是质量(成分波动)、效率(补吹延长周期)、成本(补吹损失)三域的共同根因，提升终点命中率是综合成本优化第一杠杆。",
            "evidence": f"终点{xm['endpoint_hit']}%"})

    risk = ("高" if (xm["endpoint_hit"] < 60 or xm["reblow_rate"] > 15 or xm["overdue_heats"] > 80)
            else "中" if (xm["endpoint_hit"] < 80 or xm["reblow_rate"] > 5 or xm["overdue_heats"] > 30)
            else "低")
    summary = (f"综合成本研判（{risk}风险）：直接成本占{s['direct_pct']}%，"
               f"损失合计约{(s['quality']+s['efficiency'])/1e4:.1f}万元（{xm['heats']}炉）。")
    if xm["endpoint_hit"] < 80:
        summary += f" 核心瓶颈为终点命中率({xm['endpoint_hit']}%)，是三域共同根因。"
    if xm["reblow_rate"] > 3:
        summary += f" 补吹率{xm['reblow_rate']}%形成质量×效率跨域损失链。"
    recommendations = [
        f"聚焦{dom}（占比{dom_pct}%）做折算明细下钻，找最大损失项",
        "建立综合成本日报，跟踪三块占比趋势",
    ]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": risk,
            "metrics": s}


def _quality_loss(ctx: dict) -> dict:
    """质量损失折算AI：损失结构 + 主要损失源 + 跨域因果链（质量根因->损失->综合成本）。"""
    db = ctx["db"]
    s = ctx["structure"]
    xm = ctx["xm"]
    drill = comprehensive_drilldown.quality_loss_drilldown(db)
    by_name = {r["loss_name"]: r for r in drill["by_loss_name"]}
    total_q = drill["summary"]["total_quality_loss"]

    findings = []
    # 损失结构
    struct_parts = []
    for name in ("surplus_loss", "defect_loss", "downgrade_loss", "reblow_loss"):
        # 合并 estimated+formula
        amt = sum(r["total"] for r in drill["by_loss_name"] if r["loss_name"] == name)
        if amt > 0:
            struct_parts.append(f"{name.replace('_loss','')}{amt/1e4:.1f}万({round(100*amt/total_q) if total_q else 0}%)")
    findings.append({"title": "质量损失结构", "level": "提示",
        "content": f"质量损失合计约{total_q/1e4:.1f}万元（估算口径，defect/downgrade/reblow为系数估算，合金富裕97炉为精确口径）。"
                   f"结构：{ '；'.join(struct_parts) }。",
        "evidence": f"合计{total_q/1e4:.1f}万元"})

    # 主要损失源（按 loss_name 合并 estimated+formula，与结构口径一致）
    merged = {}
    for r in drill["by_loss_name"]:
        merged[r["loss_name"]] = merged.get(r["loss_name"], 0) + r["total"]
    if merged:
        top_name = max(merged, key=merged.get)
        top_total = merged[top_name]
        findings.append({"title": f"主要损失源: {top_name}", "level": "警告" if top_total > total_q * 0.4 else "提示",
            "content": f"{top_name}约{top_total/1e4:.1f}万元占质量损失{round(100*top_total/total_q) if total_q else 0}%，是质量降本首要抓手。",
            "evidence": f"{top_total/1e4:.1f}万"})

    # 跨域因果链1: 补吹->三重损失->综合成本（货币化）
    if xm["reblow_rate"] > 3:
        reblow_loss = sum(r["total"] for r in drill["by_loss_name"] if r["loss_name"] == "reblow_loss")
        per_heat = reblow_loss / xm["heats"] if xm["heats"] else 0
        findings.append({"title": "因果链: 补吹->三重损失->综合成本", "level": "警告" if xm["reblow_rate"] > 15 else "提示",
            "content": f"补吹率{xm['reblow_rate']}%（{xm['reblow_heats']}炉），形成跨域损失链："
                       f"质量侧补吹损失约{reblow_loss/1e4:.1f}万元（估算{per_heat:.0f}元/炉），"
                       f"效率侧补吹延长冶炼周期（见效率损失折算），根因为终点命中率{xm['endpoint_hit']}%。",
            "evidence": f"补吹率{xm['reblow_rate']}% 损失{reblow_loss/1e4:.1f}万",
            "chain": [f"质量域:补吹率{xm['reblow_rate']}%", "补吹损失+多耗合金",
                      "效率域:补吹延长周期", f"综合成本↑约{per_heat:.0f}元/炉"]})

    # 跨域因果链2: 终点命中率->成分->COQ
    if xm["endpoint_hit"] < 85:
        coq = sum(r["total"] for r in drill["by_loss_name"] if r["loss_name"] in ("defect_loss", "downgrade_loss"))
        findings.append({"title": "因果链: 终点命中率->成分波动->COQ损失", "level": "警告",
            "content": f"终点命中率{xm['endpoint_hit']}%（温度{xm['temp_rate']}%/碳{xm['c_rate']}%），"
                       f"导致碳/温度偏差->成分波动->废品+降级损失约{coq/1e4:.1f}万元。终点命中率每提升10%，预计COQ损失可降3-5%。",
            "evidence": f"终点{xm['endpoint_hit']}% COQ{coq/1e4:.1f}万",
            "chain": [f"质量域:终点命中率{xm['endpoint_hit']}%", "碳/温度偏差->成分波动",
                      "废品+降级损失", f"综合成本↑约{coq/1e4:.1f}万元"]})

    summary = f"质量损失折算（{total_q/1e4:.1f}万元）："
    if xm["reblow_rate"] > 3:
        summary += f" 补吹率{xm['reblow_rate']}%形成跨域损失链，是首要切入点。"
    if xm["endpoint_hit"] < 85:
        summary += f" 终点命中率{xm['endpoint_hit']}%为根因。"
    recommendations = []
    if xm["endpoint_hit"] < 85:
        recommendations.append(f"提升终点命中率(当前{xm['endpoint_hit']}%)至85%+，预计COQ损失降3-5%")
    if xm["reblow_rate"] > 3:
        recommendations.append(f"降低补吹率(当前{xm['reblow_rate']}%)，每降1%约省{5000*xm['heats']*0.01/1e4:.1f}万元/批次")
    recommendations.append("核查合金富裕精确明细(formula口径)，针对超上限合金优化投料")
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "高" if xm["reblow_rate"] > 20 else "中"}


def _efficiency_loss(ctx: dict) -> dict:
    """效率损失折算AI：损失结构 + 瓶颈损失 + 跨域因果链（瓶颈->损失->综合成本）。"""
    db = ctx["db"]
    s = ctx["structure"]
    xm = ctx["xm"]
    drill = comprehensive_drilldown.efficiency_loss_drilldown(db)
    total_e = drill["summary"]["total_efficiency_loss"]

    findings = []
    # 损失结构
    parts = [f"{r['loss_name'].replace('_loss','')}{r['total']/1e4:.1f}万" for r in drill["by_loss_name"]]
    findings.append({"title": "效率损失结构", "level": "提示",
        "content": f"效率损失合计约{total_e/1e4:.1f}万元（估算口径）。结构：{'；'.join(parts)}。",
        "evidence": f"合计{total_e/1e4:.1f}万元"})

    # 瓶颈工序
    proc_cost = drill["by_process_cost"]
    if proc_cost:
        bn = proc_cost[0]
        findings.append({"title": f"瓶颈工序: {bn['process']}", "level": "警告",
            "content": f"{bn['process']}工序总时长{bn['total_min']:.0f}min，折算能耗成本{bn['cost']/1e4:.1f}万元，是效率损失集中工序。",
            "evidence": f"{bn['process']} {bn['cost']/1e4:.1f}万"})

    # 跨域因果链3: 精炼超时->连铸断浇->产能闲置
    if xm["overdue_heats"] > 0:
        overdue_cost = xm["overdue_min"] * 200  # time_cost
        findings.append({"title": "因果链: 精炼超时->连铸断浇->产能闲置", "level": "警告" if xm["overdue_heats"] > 50 else "提示",
            "content": f"有效精炼时长超P95({xm['overdue_p95']}min)的炉次{xm['overdue_heats']}炉，超时{xm['overdue_min']:.0f}min，"
                       f"折算效率损失约{overdue_cost/1e4:.1f}万元。超时影响连铸节奏匹配，严重时导致断浇/产能闲置。",
            "evidence": f"超时{xm['overdue_heats']}炉 {xm['overdue_min']:.0f}min",
            "chain": [f"效率域:精炼超时{xm['overdue_heats']}炉", "连铸断浇风险",
                      "产能闲置损失", f"综合成本↑约{overdue_cost/1e4:.1f}万元"]})

    # 班组效率差距货币化
    if len(xm["team_loss"]) >= 2:
        best = min(xm["team_loss"], key=lambda x: x[1])
        worst = max(xm["team_loss"], key=lambda x: x[1])
        gap = worst[1] - best[1]
        if gap > 0:
            findings.append({"title": "班组效率差距货币化", "level": "提示",
                "content": f"{worst[0]}班效率损失{worst[1]/1e4:.1f}万元 vs {best[0]}班{best[1]/1e4:.1f}万元，差距{gap/1e4:.1f}万元。"
                           f"若{worst[0]}班向{best[0]}班对标，预计可降本{gap/1e4:.1f}万元。",
                "evidence": f"差距{gap/1e4:.1f}万元"})

    summary = f"效率损失折算（{total_e/1e4:.1f}万元）："
    if proc_cost:
        summary += f" {proc_cost[0]['process']}为瓶颈工序。"
    if xm["overdue_heats"] > 0:
        summary += f" {xm['overdue_heats']}炉精炼超时。"
    recommendations = [
        f"优化瓶颈工序{proc_cost[0]['process'] if proc_cost else ''}的时长基线，超时自动预警" if proc_cost else "建立各工序标准时长基线",
        "建立精炼超时预警，P95为超时阈值",
    ]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中" if xm["overdue_heats"] > 50 else "低"}


def _cross_leverage(ctx: dict) -> dict:
    """交叉杠杆AI：杠杆点识别 + 敏感度排序 + 优化优先级矩阵。"""
    s = ctx["structure"]
    xm = ctx["xm"]
    # 敏感度（纯函数，复用 ctx structure，无需重算 comprehensive_model）
    sens = {}
    for var in ("efficiency", "quality", "energy_price", "yield_rate"):
        try:
            sens[var] = simulation.sensitivity_analysis(s, var)
        except Exception:
            pass

    findings = []
    # 杠杆点排序（按弹性）
    elastics = sorted([(v, r.get("elasticity", 0), r.get("label", v)) for v, r in sens.items()],
                      key=lambda x: x[1], reverse=True)
    if elastics:
        top = elastics[0]
        findings.append({"title": f"最大杠杆点: {top[2]}", "level": "警告",
            "content": f"{top[2]}的弹性系数{top[1]}，即该变量波动±10%时综合成本变化最大。是优化投入产出比最高的杠杆点。",
            "evidence": f"弹性{top[1]}"})
        if len(elastics) >= 2:
            findings.append({"title": "敏感度排序", "level": "提示",
                "content": "各变量对综合成本的弹性排序：" + " > ".join(f"{e[2]}({e[1]})" for e in elastics) + "。优先优化弹性高的变量。",
                "evidence": " > ".join(str(e[1]) for e in elastics)})

    # 优化优先级矩阵（影响×难度四象限）
    levers = [
        {"name": "提升终点命中率", "impact": "高" if xm["endpoint_hit"] < 85 else "低", "difficulty": "中",
         "note": f"终点{xm['endpoint_hit']}%，同时降质量+效率损失"},
        {"name": "降低补吹率", "impact": "高" if xm["reblow_rate"] > 15 else "中", "difficulty": "低",
         "note": f"补吹率{xm['reblow_rate']}%，每降1%省约5000元/炉"},
        {"name": "精炼超时治理", "impact": "中" if xm["overdue_heats"] > 30 else "低", "difficulty": "低",
         "note": f"{xm['overdue_heats']}炉超时，建超时预警即可"},
        {"name": "合金富裕优化", "impact": "中", "difficulty": "中", "note": "精确口径97炉超上限"},
    ]
    findings.append({"title": "优化优先级矩阵（影响×难度）", "level": "提示",
        "content": "；".join(f"{l['name']}(影响{l['impact']}/难度{l['difficulty']})" for l in levers) + "。优先做'高影响+低难度'象限。",
        "evidence": f"{len(levers)}个杠杆点"})

    # 跨域因果链4: 低端料->合金符合率->COQ
    if xm["low_end_high"]:
        findings.append({"title": "因果链: 低端料->合金符合率->COQ", "level": "警告",
            "content": "部分钢种低端料占比>30%，低价料杂质波动->合金符合率下降->COQ+合金富裕损失上升。"
                       "配料优化需权衡采购成本节省与质量损失增加（见优化仿真Tab的配料LP）。",
            "evidence": "低端料>30%",
            "chain": ["成本域:低端料占比高", "杂质波动->合金符合率降",
                      "COQ+合金富裕损失", "综合成本↑"]})

    summary = f"交叉杠杆分析：识别{len(levers)}个优化杠杆点。"
    if elastics:
        summary += f" 最大杠杆为{elastics[0][2]}(弹性{elastics[0][1]})。"
    recommendations = [f"优先优化{elastics[0][2]}（弹性最高）" if elastics else "分析各变量弹性",
                       "聚焦'高影响+低难度'杠杆：降低补吹率、精炼超时治理"]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中"}


def _optimization(ctx: dict) -> dict:
    """优化仿真AI：多方案对比 + 最优解推荐 + 风险提示。"""
    s = ctx["structure"]
    try:
        scenarios = simulation.parameter_simulation(s).get("scenarios", [])
    except Exception:
        scenarios = []

    findings = []
    if scenarios:
        # 找综合成本最低方案
        best = min(scenarios, key=lambda x: x.get("total", 0))
        baseline = next((x for x in scenarios if "基准" in x.get("scenario", "")), scenarios[0])
        findings.append({"title": "最优方案推荐", "level": "亮点",
            "content": f"在{len(scenarios)}个方案中，'{best.get('scenario')}'综合成本最低"
                       f"（{best.get('total',0)/1e4:.0f}万元，较基准{best.get('delta_pct',0):.1f}%）。"
                       f"该方案{best.get('desc','')}。",
            "evidence": f"{best.get('scenario')} {best.get('delta_pct',0):.1f}%"})

        # 三块此消彼长
        if baseline:
            findings.append({"title": "三块此消彼长", "level": "提示",
                "content": f"基准方案直接{baseline.get('direct',0)/1e4:.0f}万/质量{baseline.get('quality',0)/1e4:.0f}万/效率{baseline.get('efficiency',0)/1e4:.0f}万。"
                           f"优化方案需关注三块此消彼长：如低端料增加降直接成本但升质量损失。",
                "evidence": f"基准{baseline.get('total',0)/1e4:.0f}万"})

    # 风险提示
    findings.append({"title": "降本方案副作用风险", "level": "警告",
        "content": "部分降本方案以质量/效率损失上升为代价（如增加低端料降采购成本但升COQ）。"
                   "须以'综合成本'而非'直接成本'为优化目标，避免局部最优全局恶化。这正是配料LP升级为综合成本目标的理由。",
        "evidence": "综合成本视角"})

    summary = f"优化仿真：对比{len(scenarios)}个方案。"
    if scenarios:
        best = min(scenarios, key=lambda x: x.get("total", 0))
        summary += f" '{best.get('scenario')}'综合成本最低(较基准{best.get('delta_pct',0):.1f}%)。"
    summary += " 须以综合成本为优化目标，警惕降本副作用。"
    recommendations = [
        "以综合成本(非直接成本)为优化目标，配料LP升级纳入质量/效率惩罚",
        "优先实施'高影响低难度'方案：降低补吹率、精炼超时治理",
        "建立方案回测机制，跟踪实施后三块成本变化",
    ]
    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": "中"}


def comprehensive_ai_analysis(db: Session) -> dict:
    """综合AI分析汇总（5个子分析 + 跨域因果链）。"""
    model = comprehensive.comprehensive_model(db, 100000)  # 全量样本，保证结构口径与 fact_loss_detail 一致
    xm = _cross_metrics(db)
    ctx = {"db": db, "model": model, "structure": model["structure"], "xm": xm}
    return {
        "overview": _overview(ctx),
        "quality_loss": _quality_loss(ctx),
        "efficiency_loss": _efficiency_loss(ctx),
        "cross_leverage": _cross_leverage(ctx),
        "optimization": _optimization(ctx),
    }
