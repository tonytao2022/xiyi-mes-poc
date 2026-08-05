"""模型模拟能力（Phase C 解耦后：纯函数，无 db 依赖）。

- parameter_simulation/sensitivity/interactive 均为纯函数，接收 structure dict
- LP 配料优化升级为 min 综合成本(采购+质量惩罚+效率惩罚)，避免"降本副作用"
- 所有系数来自 cost_factors（单一源）
"""
import pulp

from . import cost_factors as cf


def parameter_simulation(structure: dict) -> dict:
    """参数仿真/情景对比：多方案综合成本对比（三块此消彼长）。

    纯函数：接收 comprehensive.comprehensive_model 的 structure dict。
    """
    base = structure
    scenarios = [
        {"name": "现状基准", "quality_f": 1.0, "efficiency_f": 1.0, "desc": "当前综合成本"},
        {"name": "收得率+2%(0.94)", "quality_f": 0.7, "efficiency_f": 1.0, "desc": "废品降->质量损失降30%"},
        {"name": "精炼时长-10%", "quality_f": 1.05, "efficiency_f": 0.9, "desc": "效率损失降10%，质量略升5%"},
        {"name": "补吹率降50%", "quality_f": 0.6, "efficiency_f": 0.95, "desc": "补吹降->质量损失降40%、效率降5%"},
        {"name": "能耗单价+10%", "quality_f": 1.0, "efficiency_f": 1.1, "desc": "能耗升->效率损失升10%"},
        {"name": "综合优化(全改善)", "quality_f": 0.5, "efficiency_f": 0.8, "desc": "质量损失降50%、效率损失降20%"},
    ]
    results = []
    for s in scenarios:
        new_direct = base["direct"]
        new_quality = round(base["quality"] * s["quality_f"])
        new_efficiency = round(base["efficiency"] * s["efficiency_f"])
        new_total = new_direct + new_quality + new_efficiency
        results.append({
            "scenario": s["name"], "desc": s["desc"],
            "direct": new_direct, "quality": new_quality, "efficiency": new_efficiency,
            "total": new_total, "delta": new_total - base["total"],
            "delta_pct": round(100 * (new_total - base["total"]) / base["total"], 1) if base["total"] else 0,
        })
    return {"base": base, "scenarios": results}


def sensitivity_analysis(structure: dict, variable: str = "efficiency") -> dict:
    """敏感度分析：变量波动 ±20% -> 综合成本变化，找优化杠杆点。

    纯函数：接收 structure dict。
    variable: efficiency(效率损失) / quality(质量损失) / energy_price(能耗单价) / yield_rate(收得率)
    """
    base = structure
    var_map = {
        "efficiency": ("效率损失", "efficiency"),
        "quality": ("质量损失", "quality"),
        "energy_price": ("能耗单价(影响效率损失)", "efficiency"),
        "yield_rate": ("收得率(影响质量损失)", "quality"),
    }
    label, target = var_map.get(variable, var_map["efficiency"])
    points = []
    for pct in range(-20, 21, 5):
        factor = 1 + pct / 100
        if target == "efficiency":
            new_total = base["direct"] + base["quality"] + base["efficiency"] * factor
        else:
            new_total = base["direct"] + base["quality"] * factor + base["efficiency"]
        points.append({"pct": pct, "total": round(new_total), "delta": round(new_total - base["total"])})
    # 弹性系数：±10% 的综合成本变化率
    p_minus10 = points[2]["total"]  # -10%
    p_plus10 = points[6]["total"]  # +10%
    elastic = round((p_plus10 - p_minus10) / base["total"] / 0.2 * 100, 1) if base["total"] else 0
    return {
        "variable": variable, "label": label, "base_total": base["total"],
        "points": points, "elasticity": elastic,
        "note": f"弹性系数 {elastic}%：该变量每波动1%，综合成本变化 {elastic / 20:.2f}%",
    }


def recipe_optimization(total_weight: float = 100, low_end_limit: float = 20,
                        metal_requirement: float = 0.90) -> dict:
    """配料优化（线性规划）：min 综合成本 = 采购成本 + 质量惩罚 + 效率惩罚。

    升级要点：低端料降采购成本但升质量风险(杂质->COQ)、低收得率料升效率损失(产出少)，
    二者作为线性惩罚进目标函数，避免"只看采购成本的局部最优"（降本副作用）。

    min  Σ [ price_i·x_i + q_penalty_i·x_i + e_penalty_i·x_i ]
    s.t. Σ x_i = W                    (总投料量)
         Σ yield_i · x_i ≥ W · req    (金属量需求)
         Σ low_end_i · x_i ≤ W · lim  (低端料上限，质量约束)
         x_i ≥ 0
    其中 q_penalty_i = low_end ? low_end_quality_penalty : 0
         e_penalty_i = (1 - yield_i) · ton_steel_cost   (收得率损失的产出机会成本)
    """
    types = cf.scrap_types_lp()
    q_pen = cf.get("low_end_quality_penalty")
    tsc = cf.get("ton_steel_cost")

    prob = pulp.LpProblem("recipe_opt", pulp.LpMinimize)
    x = {s["name"]: pulp.LpVariable(f"x_{i}", lowBound=0) for i, s in enumerate(types)}
    # 综合成本目标 = 采购 + 质量惩罚(低端料) + 效率惩罚(收得率损失)
    prob += pulp.lpSum(
        (s["price"] + (q_pen if s["low_end"] else 0) + (1 - s["yield"]) * tsc) * x[s["name"]]
        for s in types
    )
    prob += pulp.lpSum(x[s["name"]] for s in types) == total_weight
    prob += pulp.lpSum(s["yield"] * x[s["name"]] for s in types) >= total_weight * metal_requirement
    prob += pulp.lpSum(x[s["name"]] for s in types if s["low_end"]) <= total_weight * low_end_limit / 100
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    recipe = []
    purchase_cost = quality_penalty = efficiency_penalty = 0.0
    for s in types:
        amt = x[s["name"]].value()
        if amt and amt > 0.01:
            buy = amt * s["price"]
            qp = amt * (q_pen if s["low_end"] else 0)
            ep = amt * (1 - s["yield"]) * tsc
            purchase_cost += buy
            quality_penalty += qp
            efficiency_penalty += ep
            recipe.append({"name": s["name"], "amount": round(amt, 1), "price": s["price"],
                           "cost": round(buy, 0), "quality_penalty": round(qp, 0),
                           "efficiency_penalty": round(ep, 0),
                           "comprehensive": round(buy + qp + ep, 0),
                           "pct": round(100 * amt / total_weight, 1),
                           "low_end": s["low_end"], "yield": s["yield"]})
    recipe.sort(key=lambda r: r["comprehensive"], reverse=True)
    comp_cost = purchase_cost + quality_penalty + efficiency_penalty

    # 基准：全一类废钢（高收得率、非低端），对比综合成本
    base_yield = next(s["yield"] for s in types if s["name"] == "一类废钢")
    base_price = next(s["price"] for s in types if s["name"] == "一类废钢")
    baseline_purchase = total_weight * base_price
    baseline_quality = 0  # 非低端料
    baseline_efficiency = total_weight * (1 - base_yield) * tsc
    baseline_comp = baseline_purchase + baseline_quality + baseline_efficiency

    return {
        "recipe": recipe,
        "cost_breakdown": {
            "purchase": round(purchase_cost, 0),
            "quality_penalty": round(quality_penalty, 0),
            "efficiency_penalty": round(efficiency_penalty, 0),
            "comprehensive": round(comp_cost, 0),
        },
        "baseline": {
            "purchase": round(baseline_purchase, 0), "quality_penalty": 0,
            "efficiency_penalty": round(baseline_efficiency, 0),
            "comprehensive": round(baseline_comp, 0),
        },
        "total_weight": total_weight, "low_end_limit": low_end_limit, "metal_requirement": metal_requirement,
        "saving": round(baseline_comp - comp_cost, 0),
        "saving_pct": round(100 * (baseline_comp - comp_cost) / baseline_comp, 1) if baseline_comp else 0,
        "status": pulp.LpStatus[prob.status],
        "note": "目标=min(采购+质量惩罚+效率惩罚)；质量惩罚=低端料×low_end_quality_penalty；效率惩罚=(1-收得率)×吨钢成本",
    }


def interactive_simulation(
    structure: dict,
    reblow_count: int = 0,
    # 质量维度（工艺可优化）
    yield_rate: float = 0.92,
    defect_rate: float = 0.01,
    alloy_surplus_pct: float = 0.05,
    # 成本维度（采购/配料可优化）
    low_end_ratio: float = 0.15,
    scrap_price: float = 2800,
    alloy_substitution_rate: float = 0.10,
    # 效率维度（生产组织可优化）
    refining_duration: float = 30,
    converter_duration: float = 25,
    waiting_time: float = 10,
    sequence_length: int = 20,
) -> dict:
    """交互式模拟：11个真实可优化业务要素，实时算综合成本变化。

    纯函数：接收 structure dict（含 avg_alloy/heats_count）+ reblow_count。
    所有系数来自 cost_factors。base_alloy 直接取 structure["avg_alloy"]，无需反推。
    """
    base = structure
    HC = base.get("heats_count", 50) or 1
    OUT = cf.get("est_output")
    REF = cf.get("refractory_per_heat")

    # --- 直接成本：废钢(低端料折扣) + 合金(替代率) + 耐材 ---
    base_alloy = base.get("avg_alloy", 0)  # per-heat 合金成本，直接取（无反推）
    new_scrap = OUT * scrap_price * (1 - low_end_ratio * cf.get("low_end_discount"))
    new_alloy = base_alloy * (1 - alloy_substitution_rate * cf.get("alloy_sub_factor"))
    new_direct = (new_scrap + new_alloy + REF) * HC

    # --- 质量损失：废品 + 补吹 + 富裕 ---
    output = OUT * yield_rate
    defect_loss = output * defect_rate * cf.get("ton_steel_cost") * (1 - cf.get("residual_rate"))
    reblow_loss = reblow_count * cf.get("reblow_cost") / HC
    surplus_loss = new_alloy * alloy_surplus_pct * cf.get("surplus_half")
    new_quality = (defect_loss + reblow_loss + surplus_loss) * HC

    # --- 效率损失：时长能耗 + 连浇开停 ---
    base_total_min = 30 + 25 + 10  # 基准精炼30+转炉25+等待10
    energy_per_min = base["efficiency"] / (base_total_min * HC) if (base_total_min * HC) else 0
    new_total_min = refining_duration + converter_duration + waiting_time
    energy_loss = energy_per_min * new_total_min * HC
    sequence_loss = (HC / sequence_length - HC / cf.get("base_seq")) * cf.get("seq_cost")
    new_efficiency = energy_loss + sequence_loss

    new_total = new_direct + new_quality + new_efficiency

    def pct(n, o):
        return round(100 * (n - o) / o, 1) if o else 0

    return {
        "base": base,
        "adjusted": {"direct": round(new_direct), "quality": round(new_quality),
                      "efficiency": round(new_efficiency), "total": round(new_total)},
        "delta": {"direct": round(new_direct - base["direct"]), "quality": round(new_quality - base["quality"]),
                  "efficiency": round(new_efficiency - base["efficiency"]), "total": round(new_total - base["total"])},
        "delta_pct": {"direct": pct(new_direct, base["direct"]), "quality": pct(new_quality, base["quality"]),
                      "efficiency": pct(new_efficiency, base["efficiency"]), "total": pct(new_total, base["total"])},
        "params": {"yield_rate": yield_rate, "defect_rate": defect_rate, "reblow_count": reblow_count,
                   "alloy_surplus_pct": alloy_surplus_pct, "low_end_ratio": low_end_ratio,
                   "scrap_price": scrap_price, "alloy_substitution_rate": alloy_substitution_rate,
                   "refining_duration": refining_duration, "converter_duration": converter_duration,
                   "waiting_time": waiting_time, "sequence_length": sequence_length},
    }
