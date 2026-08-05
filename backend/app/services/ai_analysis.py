"""AI智能分析服务（分层质量体系 + 跨层综合研判）。

核心设计：
- L1最终产品质量(结果) / L2关键工艺参数(过程) / L3操作规范(合规) 分层独立
- L4合金投料移至成本域
- AI分析跨层关联：L2异常->L1影响、L3操作->L2工艺、综合质量研判
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def _rate(hit, judged):
    return round(100 * hit / judged, 1) if judged else 0


# === L1 最终产品质量分析 ===

def _l1_analysis(db: Session) -> dict:
    """L1产品质量：化学成分/力学性能/尺寸合格率（基于现有样本，未来全量）。"""
    # 化学成分（C/Mn/P/S 4元素同时达标 = 成分合格炉次）
    chem = db.execute(text("""
        SELECT
          COUNT(*) AS n,
          COUNT(*) FILTER (WHERE "C" BETWEEN 0.18 AND 0.22) AS c_ok,
          COUNT(*) FILTER (WHERE "Mn" BETWEEN 0.70 AND 0.85) AS mn_ok,
          COUNT(*) FILTER (WHERE "P" <= 0.025) AS p_ok,
          COUNT(*) FILTER (WHERE "S" <= 0.015) AS s_ok,
          COUNT(*) FILTER (WHERE "C" BETWEEN 0.18 AND 0.22
                           AND "Mn" BETWEEN 0.70 AND 0.85
                           AND "P" <= 0.025 AND "S" <= 0.015) AS all_ok
        FROM fact_inspect_chem
    """)).one()
    chem_rate = _rate(chem.all_ok, chem.n) if chem.n else 0

    # 力学性能
    mech = db.execute(text("""
        SELECT
          COUNT(*) AS n,
          COUNT(*) FILTER (WHERE yield_strength BETWEEN 270 AND 360
                           AND tensile_strength BETWEEN 430 AND 530
                           AND elongation >= 30) AS all_ok,
          ROUND((AVG(yield_strength))::numeric,1) ys_avg,
          ROUND((STDDEV(yield_strength))::numeric,1) ys_std,
          ROUND((AVG(tensile_strength))::numeric,1) ts_avg,
          ROUND((AVG(elongation))::numeric,1) el_avg
        FROM fact_inspect_mech
    """)).one()
    mech_rate = _rate(mech.all_ok, mech.n) if mech.n else 0

    # 尺寸
    dim = db.execute(text("""
        SELECT COUNT(*) AS n,
          COUNT(*) FILTER (WHERE dim_result = '合格') AS ok
        FROM fact_inspect_dim
    """)).one()
    dim_rate = _rate(dim.ok, dim.n) if dim.n else 0

    return {
        "metrics": {
            "chemical_rate": chem_rate, "mechanical_rate": mech_rate, "dimension_rate": dim_rate,
            "sample_n": int(chem.n or 0), "mech_n": int(mech.n or 0), "dim_n": int(dim.n or 0),
            "ys_avg": float(mech.ys_avg or 0), "ts_avg": float(mech.ts_avg or 0), "el_avg": float(mech.el_avg or 0),
        },
        "findings": _l1_findings(chem, mech, dim, chem_rate, mech_rate, dim_rate),
    }


def _l1_findings(chem, mech, dim, chem_rate, mech_rate, dim_rate):
    findings = []
    if chem_rate < 95:
        # 找最差的元素
        worst_el = min([("C", chem.c_ok, chem.n), ("Mn", chem.mn_ok, chem.n),
                        ("P", chem.p_ok, chem.n), ("S", chem.s_ok, chem.n)],
                       key=lambda x: x[1]/x[2] if x[2] else 1)
        wr = _rate(worst_el[1], worst_el[2])
        findings.append({"title": "化学成分风险", "level": "严重" if wr < 80 else "警告",
            "content": f"化学成分全元素合格率 {chem_rate}%，{worst_el[0]}元素合格率最低({wr}%)，成分控制不稳定将直接影响产品性能和下游加工。",
            "evidence": f"样本{chem.n}炉，全元素合格{chem.all_ok}炉"})
    else:
        findings.append({"title": "化学成分稳定", "level": "亮点",
            "content": f"化学成分全元素合格率 {chem_rate}%，成分控制良好。", "evidence": f"样本{chem.n}炉"})

    if mech_rate >= 100:
        findings.append({"title": "力学性能达标", "level": "亮点",
            "content": f"力学性能合格率100%，屈服{mech.ys_avg}MPa/抗拉{mech.ts_avg}MPa/伸长率{mech.el_avg}%，完全满足标准。",
            "evidence": f"样本{mech.n}件"})
    elif mech_rate < 95:
        findings.append({"title": "力学性能波动", "level": "警告",
            "content": f"力学性能合格率 {mech_rate}%，存在不合格试样，需检查轧制温度和化学成分的稳定性。",
            "evidence": f"样本{mech.n}件，合格{mech.all_ok}件"})

    if dim_rate < 95:
        findings.append({"title": "尺寸精度不足", "level": "警告",
            "content": f"尺寸合格率 {dim_rate}%，椭圆度或直径偏差超标，影响下游加工精度。",
            "evidence": f"样本{dim.n}批，合格{dim.ok}批"})
    elif dim_rate >= 100:
        findings.append({"title": "尺寸精度良好", "level": "亮点",
            "content": f"尺寸合格率100%，几何精度满足要求。", "evidence": f"样本{dim.n}批"})
    return findings


# === L2 关键工艺参数分析 ===

def _l2_analysis(db: Session) -> dict:
    """L2工艺参数：终点命中率/关键参数符合率/加权综合（排除L4合金）。"""
    # 转炉终点命中率（温度+C双命中）
    endpoint = db.execute(text("""
        SELECT
          COUNT(DISTINCT heat_no) AS heats,
          COUNT(*) FILTER (WHERE indicator_name = '终点温度' AND judge = 1) AS temp_ok,
          COUNT(*) FILTER (WHERE indicator_name = '终点温度' AND judge IS NOT NULL) AS temp_judged,
          COUNT(*) FILTER (WHERE indicator_name = '终点C' AND judge = 1) AS c_ok,
          COUNT(*) FILTER (WHERE indicator_name = '终点C' AND judge IS NOT NULL) AS c_judged
        FROM fact_heat_indicator WHERE process = '转炉'
    """)).one()
    temp_rate = _rate(endpoint.temp_ok, endpoint.temp_judged)
    c_rate = _rate(endpoint.c_ok, endpoint.c_judged)

    # 各工序符合率（排除合金）
    procs = db.execute(text("""
        SELECT process,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE process != '合金'
        GROUP BY process
    """)).all()
    proc_rates = {r.process: _rate(r.hit, r.judged) for r in procs}

    # 补吹率
    reblow = db.execute(text("""
        SELECT COUNT(DISTINCT heat_no) AS total,
          COUNT(DISTINCT heat_no) FILTER (WHERE indicator_name = '补吹出钢' AND judge = 0) AS reblow
        FROM fact_heat_indicator WHERE process = '转炉'
    """)).one()
    reblow_rate = _rate(reblow.reblow, reblow.total) if reblow.total else 0

    # 连铸关键参数
    cc_superheat = db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
               COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE process IN ('板坯','方坯') AND indicator_name = '中包过热度'
    """)).one()
    superheat_rate = _rate(cc_superheat.hit, cc_superheat.judged)

    return {
        "metrics": {
            "endpoint_temp_rate": temp_rate, "endpoint_c_rate": c_rate,
            "endpoint_hit_rate": round(min(temp_rate, c_rate), 1),  # 双命中近似
            "reblow_rate": reblow_rate,
            "superheat_rate": superheat_rate,
            "proc_rates": proc_rates,
            "weighted_rate": round(sum(proc_rates.values()) / len(proc_rates), 1) if proc_rates else 0,
        },
        "findings": _l2_findings(temp_rate, c_rate, reblow_rate, superheat_rate, proc_rates),
    }


def _l2_findings(temp_rate, c_rate, reblow_rate, superheat_rate, proc_rates):
    findings = []
    # 终点命中率
    hit_rate = round(min(temp_rate, c_rate), 1)
    if hit_rate < 70:
        findings.append({"title": "转炉终点命中率低", "level": "严重",
            "content": f"终点温度符合率{temp_rate}%、终点碳符合率{c_rate}%，双命中率约{hit_rate}%。终点命中率是转炉最核心工艺指标，命中率低直接导致成分偏差、补吹增加、效率下降。建议优化终点控制模型。",
            "evidence": f"温度{temp_rate}% 碳{c_rate}%"})
    elif hit_rate < 85:
        findings.append({"title": "终点命中率需提升", "level": "警告",
            "content": f"终点命中率约{hit_rate}%（温度{temp_rate}%/碳{c_rate}%），有较大提升空间。命中率每提升1%可减少补吹和成分波动。",
            "evidence": f"双命中{hit_rate}%"})

    # 补吹率
    if reblow_rate > 15:
        findings.append({"title": "补吹率高", "level": "严重" if reblow_rate > 30 else "警告",
            "content": f"补吹率{reblow_rate}%，{reblow_rate}%的炉次需要补吹。补吹导致：温度波动->成分偏移(L2)、时间延长(效率损失)、氧气+钢铁料烧损(成本损失)。终点命中率低是根因。",
            "evidence": f"补吹率{reblow_rate}%"})

    # 连铸过热度
    if superheat_rate < 80:
        findings.append({"title": "连铸过热度控制差", "level": "严重" if superheat_rate < 60 else "警告",
            "content": f"中包过热度符合率{superheat_rate}%，过热度不稳定直接影响表面质量(裂纹)和内部质量(偏析)，是连铸最关键参数。",
            "evidence": f"符合率{superheat_rate}%"})

    # 最差工序
    if proc_rates:
        worst_proc = min(proc_rates.items(), key=lambda x: x[1])
        if worst_proc[1] < 80:
            findings.append({"title": f"{worst_proc[0]}工序工艺薄弱", "level": "警告",
                "content": f"{worst_proc[0]}符合率{worst_proc[1]}%，是该批次工艺最薄弱环节。建议针对性分析其短板指标。",
                "evidence": f"{worst_proc[0]} {worst_proc[1]}%"})
    return findings


# === L3 操作规范分析 ===

def _l3_analysis(db: Session) -> dict:
    """L3操作规范：补吹/二次出钢/操作执行率。"""
    ops = db.execute(text("""
        SELECT indicator_name,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator
        WHERE indicator_name IN ('补吹出钢','二次出钢','底吹模式','合金加入顺序')
        GROUP BY indicator_name
    """)).all()
    metrics = {r.indicator_name: _rate(r.hit, r.judged) for r in ops}
    findings = []
    for name, rate in metrics.items():
        if rate < 85:
            findings.append({"title": f"{name}执行率低", "level": "警告",
                "content": f"{name}执行率{rate}%，操作规范执行不到位，影响工艺稳定性和可追溯性。",
                "evidence": f"执行率{rate}%"})
    if not findings:
        findings.append({"title": "操作规范执行良好", "level": "亮点",
            "content": "各项操作规范执行率均≥85%，操作合规性良好。", "evidence": f"{len(metrics)}项指标"})
    return {"metrics": metrics, "findings": findings}


# === 跨层综合研判 ===

def _cross_layer_analysis(l1: dict, l2: dict, l3: dict) -> dict:
    """跨层关联分析：L2工艺异常->L1产品质量影响、L3操作->L2工艺。"""
    findings = []
    l1m, l2m, l3m = l1["metrics"], l2["metrics"], l3["metrics"]

    # 因果链1: 终点命中率低 -> 化学成分风险
    endpoint_hit = l2m.get("endpoint_hit_rate", 100)
    chem_rate = l1m.get("chemical_rate", 100)
    if endpoint_hit < 80 and chem_rate < 95:
        findings.append({
            "title": "因果链: 终点命中率低->成分波动",
            "level": "严重",
            "content": f"L2终点命中率仅{endpoint_hit}%，L1化学成分合格率{chem_rate}%。终点控制不稳定导致碳/温度偏差，直接影响成分命中率。终点命中率每提升10%，预计成分合格率可提升3-5%。",
            "evidence": f"L2终点{endpoint_hit}% -> L1成分{chem_rate}%",
            "chain": ["L2终点命中率低", "温度/碳偏差", "L1化学成分波动", "质量风险"]
        })

    # 因果链2: 补吹率高 -> 效率+质量+成本三重损失
    reblow = l2m.get("reblow_rate", 0)
    if reblow > 15:
        findings.append({
            "title": "因果链: 补吹率高->三重损失",
            "level": "严重" if reblow > 30 else "警告",
            "content": f"补吹率{reblow}%，形成'质量-成本-效率'三重损失链：补吹->温度波动(L2)->成分偏差(L1质量风险)；补吹->时间延长(效率损失)；补吹->氧气+钢铁料烧损(成本损失)。根因是终点命中率低。",
            "evidence": f"补吹率{reblow}%",
            "chain": ["终点命中率低", "补吹", "温度/成分波动", "质量+成本+效率三重损失"]
        })

    # 因果链3: 连铸过热度不稳定 -> 表面质量风险
    superheat = l2m.get("superheat_rate", 100)
    if superheat < 80:
        findings.append({
            "title": "因果链: 过热度不稳定->表面质量风险",
            "level": "警告",
            "content": f"连铸中包过热度符合率{superheat}%，过热度偏高导致表面裂纹、偏低导致冻结/水口堵塞。建议控制在目标值±5℃以内。",
            "evidence": f"过热度符合率{superheat}%",
            "chain": ["L2过热度偏离", "连铸坯表面缺陷", "L1产品质量风险"]
        })

    # 因果链4: L3操作->L2工艺
    for op_name, op_rate in l3m.items():
        if op_rate < 85 and "补吹" in op_name:
            findings.append({
                "title": "因果链: 操作执行率低->工艺不稳定",
                "level": "警告",
                "content": f"{op_name}执行率{op_rate}%，操作不规范加剧了L2工艺波动。建议加强操作培训和规程执行。",
                "evidence": f"L3 {op_name} {op_rate}%",
                "chain": ["L3操作不规范", "L2工艺波动", "L1质量风险"]
            })

    # 综合质量研判
    l1_avg = (l1m.get("chemical_rate", 0) + l1m.get("mechanical_rate", 0) + l1m.get("dimension_rate", 0)) / 3
    l2_avg = l2m.get("weighted_rate", 0)
    overall_risk = "高" if (endpoint_hit < 70 or reblow > 30 or l1_avg < 85) else "中" if (endpoint_hit < 85 or reblow > 15 or l1_avg < 95) else "低"

    summary = f"综合质量研判（{overall_risk}风险）：L1产品质量合格率约{l1_avg:.0f}%，L2工艺符合率{l2_avg}%。"
    if endpoint_hit < 85:
        summary += f" 核心瓶颈为转炉终点命中率({endpoint_hit}%)，通过提升终点命中率可同时改善质量(成分稳定性)、成本(减少补吹损失)、效率(缩短冶炼周期)。"
    if reblow > 15:
        summary += f" 补吹率{reblow}%形成三重损失链，是跨层优化的关键切入点。"

    recommendations = []
    if endpoint_hit < 85:
        recommendations.append(f"优先提升终点命中率(当前{endpoint_hit}%)：优化终点控制模型，目标提升至85%+")
    if reblow > 15:
        recommendations.append(f"降低补吹率(当前{reblow}%)：终点命中率提升后补吹率将自然下降，预计每降1%补吹率可节省约5000元/炉")
    if superheat < 80:
        recommendations.append(f"稳定连铸过热度(当前{superheat}%)：加强中包温度自动控制，目标符合率85%+")
    if not recommendations:
        recommendations.append("各层指标基本达标，建议持续监控趋势变化，防止质量波动")

    return {
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "risk": overall_risk,
        "layer_summary": {
            "L1_product_quality": round(l1_avg, 1),
            "L2_process_quality": l2_avg,
            "L3_operational": round(sum(l3m.values())/len(l3m), 1) if l3m else 0,
        }
    }


# === 对外接口 ===

def quality_ai_analysis(db: Session) -> dict:
    """质量AI综合分析：L1+L2+L3分层 + 跨层综合研判。"""
    l1 = _l1_analysis(db)
    l2 = _l2_analysis(db)
    l3 = _l3_analysis(db)
    cross = _cross_layer_analysis(l1, l2, l3)

    return {
        "overview": {
            "summary": cross["summary"],
            "findings": cross["findings"],
            "recommendations": cross["recommendations"],
            "risk": cross["risk"],
            "layer_summary": cross["layer_summary"],
        },
        "l1_product": l1,
        "l2_process": l2,
        "l3_operation": l3,
        "cross_layer": cross,
    }


def trace_analysis(db: Session, heat_no: str | None = None) -> dict:
    """追溯AI分析：单炉跨层质量评价。"""
    if not heat_no:
        heat_no = db.execute(text(
            "SELECT heat_no FROM fact_heat_indicator GROUP BY heat_no ORDER BY COUNT(*) DESC LIMIT 1"
        )).scalar()
    if not heat_no:
        return {"summary": "无数据", "findings": [], "recommendations": [], "risk": "-"}

    # L2: 该炉各工序符合率
    procs = db.execute(text("""
        SELECT process,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE heat_no = :h GROUP BY process
    """), {"h": heat_no}).all()
    abnormal = db.execute(text("""
        SELECT process, indicator_name, std_value, actual_value
        FROM fact_heat_indicator WHERE heat_no = :h AND judge = 0
        ORDER BY process
    """), {"h": heat_no}).all()

    findings = []
    for p in procs:
        r = _rate(p.hit, p.judged)
        if r < 80:
            findings.append({"title": f"L2异常: {p.process}", "level": "严重" if r < 50 else "警告",
                "content": f"{p.process}符合率{r}%，工艺参数控制不佳，可能影响产品质量。",
                "evidence": f"符合率{r}%"})

    for a in abnormal[:5]:
        # 跨层标注：L2异常如何影响L1
        l1_impact = _infer_l1_impact(a.indicator_name)
        findings.append({"title": f"不合格: {a.indicator_name}", "level": "严重",
            "content": f"{a.process}·{a.indicator_name} 标准{a.std_value}实绩{a.actual_value}。{l1_impact}",
            "evidence": f"标准{a.std_value} 实绩{a.actual_value}"})

    total_rate = _rate(sum(p.hit for p in procs), sum(p.judged for p in procs))
    risk = "高" if total_rate < 70 else "中" if total_rate < 90 else "低"

    summary = f"炉次{heat_no}跨层质量评价（{risk}风险）：L2工艺符合率{total_rate}%，{len(abnormal)}项不合格。"
    if abnormal:
        procs_issue = set(a.process for a in abnormal)
        summary += f" 异常集中在{'、'.join(procs_issue)}工序，建议追溯L3操作记录并对比历史最优炉次。"

    recommendations = []
    if abnormal:
        recommendations.append(f"重点检查{'、'.join(set(a.process for a in abnormal))}工序的工艺参数和操作记录")
    recommendations.append("对比历史最优炉次，查找工艺差异并制定改善措施")

    return {"summary": summary, "findings": findings, "recommendations": recommendations, "risk": risk}


def _infer_l1_impact(indicator_name: str) -> str:
    """推断L2参数异常对L1产品质量的影响（跨层关联）。"""
    impact_map = {
        "终点温度": "温度偏差影响脱碳反应和钢水成分(C命中率)，可能导致L1化学成分偏差。",
        "终点C": "碳含量偏差直接影响L1化学成分合格率，过高/过低均导致降级。",
        "中包过热度": "过热度异常影响连铸坯表面质量(L1表面合格率)和内部偏析。",
        "终轧温度": "终轧温度偏离直接影响屈服强度和伸长率(L1力学性能)。",
        "吐丝温度": "影响线材组织和力学性能(L1力学性能)。",
        "补吹出钢": "补吹导致温度/成分波动，间接影响L1产品质量一致性。",
        "精炼时长": "精炼时长不足影响成分均匀性和夹杂物去除，影响L1力学性能。",
    }
    return impact_map.get(indicator_name, "该参数异常可能影响产品质量，需进一步分析。")
