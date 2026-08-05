"""综合成本模型的折算系数唯一源（single source of truth）。

集中 comprehensive / cross / simulation / overview 四处重复定义的系数，
消除散落的硬编码魔数。每项系数标注 source/confidence/note，便于：
- AI 分析按置信度区分措辞（estimated 用"估算约"，formula 用"精确口径"）
- 客户确认真实系数后批量替换（只改本文件）

source 取值约定：
- estimated  系数估算（待客户真实数据替换）
- formula    公式精确口径（如合金富裕 actual>std 超出量，非系数）
"""
from __future__ import annotations

# === 系数注册表 ===
COEFFICIENTS: dict[str, dict] = {
    # --- 产出 / 收得 ---
    "yield_rate":            {"value": 0.92, "source": "estimated", "note": "收得率(投入->产出)"},
    "est_output":            {"value": 100,  "source": "estimated", "note": "炉次产出估算(吨)"},
    # --- 单价 ---
    "alloy_avg_price":       {"value": 8000,  "source": "estimated", "note": "合金均价(元/吨)"},
    "scrap_price":           {"value": 2800,  "source": "estimated", "note": "废钢均价(元/吨)"},
    "ton_steel_cost":        {"value": 3000,  "source": "estimated", "note": "吨钢成本(元)"},
    "refractory_per_heat":   {"value": 800,   "source": "estimated", "note": "耐材(元/炉)"},
    # --- 质量损失系数 ---
    "defect_rate_map":       {"value": [(0.8, 0.02), (0.9, 0.01), (1.01, 0.003)],
                              "source": "estimated", "note": "符合率->废品率 阈值映射"},
    "downgrade_loss_per_ton":{"value": 500,   "source": "estimated", "note": "降级损失(元/吨)"},
    "residual_rate":         {"value": 0.7,   "source": "estimated", "note": "废品残值占吨钢成本"},
    "surplus_loss_factor":   {"value": 0.3,   "source": "estimated",
                              "note": "合金富裕损失占合金成本比(原 comprehensive L63 匿名魔数)"},
    "coq_loss_factor":       {"value": 0.3,   "source": "estimated",
                              "note": "COQ速算损失系数(符合率每差1%的吨钢成本损失比，cross 速算口径)"},
    "low_end_quality_penalty": {"value": 300, "source": "estimated",
                              "note": "低端料质量风险惩罚(元/吨，杂质->COQ的线性惩罚，LP用)"},
    "reblow_cost":           {"value": 5000,  "source": "estimated",
                              "note": "补吹综合损失(元/炉，含氧气+烧损+合金补偿+时间)"},
    # --- 效率损失系数 ---
    "energy_per_min":        {"value": 150,   "source": "estimated", "note": "工序能耗(元/分钟)"},
    "time_cost":             {"value": 200,   "source": "estimated",
                              "note": "时间成本(元/分钟/炉，含耐材，cross 原 EST_TIME_COST)"},
    "std_duration":          {"value": 30,    "source": "estimated", "note": "标准时长阈值(分钟，超此为超时)"},
    # --- simulation 专用（Phase C 解耦时消费，先归口） ---
    "seq_cost":              {"value": 10000, "source": "estimated", "note": "连铸每次开停浇成本(元)"},
    "base_seq":              {"value": 20,    "source": "estimated", "note": "基准连浇炉数"},
    "low_end_discount":      {"value": 0.3,   "source": "estimated", "note": "低端料便宜折扣率"},
    "alloy_sub_factor":      {"value": 0.15,  "source": "estimated", "note": "合金替代率每10%降本系数"},
    "surplus_half":          {"value": 0.5,   "source": "estimated", "note": "合金富裕损失折算系数(interactive)"},
    # --- 料型表（合并 overview.ESTIMATED_SCRAP + simulation.SCRAP_TYPES_LP，消除11项重复） ---
    "scrap_types":           {"value": [
        {"name": "一类废钢",      "price": 2800, "yield": 0.95, "low_end": False},
        {"name": "普通压块",      "price": 2400, "yield": 0.88, "low_end": True},
        {"name": "剪料",          "price": 2600, "yield": 0.92, "low_end": False},
        {"name": "热饼",          "price": 2500, "yield": 0.90, "low_end": False},
        {"name": "冷饼",          "price": 2300, "yield": 0.88, "low_end": True},
        {"name": "渣钢",          "price": 2000, "yield": 0.82, "low_end": True},
        {"name": "生铁",          "price": 3200, "yield": 0.96, "low_end": False},
        {"name": "低镍生铁",      "price": 3500, "yield": 0.96, "low_end": False},
        {"name": "铸铁块",        "price": 3300, "yield": 0.95, "low_end": False},
        {"name": "耐候系列合金",  "price": 4000, "yield": 0.93, "low_end": False},
        {"name": "含铬钼合金",    "price": 5200, "yield": 0.93, "low_end": False},
    ], "source": "estimated", "note": "废钢11料型 price/yield/low_end"},
    # --- 合金单价（合并 overview.ESTIMATED_ALLOY，24项） ---
    "alloy_prices":          {"value": {
        "硅锰合金": 6000, "硅铁": 6500, "高铝铁": 12000, "铝粒": 16000,
        "低碳锰铁": 10000, "中碳锰铁": 9000, "高碳锰铁": 8000,
        "低碳铬铁": 12000, "中碳铬铁": 11000, "高碳铬铁": 9000,
        "磷铁": 8000, "硅钙钡": 10000, "钛铁30": 15000, "钛铁70": 25000,
        "铌铁": 185000, "铌磷铁": 60000, "钒铁": 125000, "钒氮合金": 155000,
        "钼铁": 200000, "铜板": 65000, "镍板": 135000, "锑锭": 80000, "硼铁": 26000,
    }, "source": "estimated", "note": "24种合金单价(元/吨)"},
}


def get(name: str):
    """取系数值。"""
    return COEFFICIENTS[name]["value"]


def factor(name: str) -> dict:
    """取系数完整记录(含 source/note)。"""
    return COEFFICIENTS[name]


def defect_rate(compliance_rate: float) -> float:
    """符合率->废品率映射（符合率低->废品率高）。"""
    for threshold, rate in get("defect_rate_map"):
        if compliance_rate < threshold:
            return rate
    return get("defect_rate_map")[-1][1]


def scrap_price_map() -> dict[str, int]:
    """料型->单价 映射（供 overview/cross 复用）。"""
    return {s["name"]: s["price"] for s in get("scrap_types")}


def scrap_types_lp() -> list[dict]:
    """LP 配料用的料型表（price/yield/low_end）。"""
    return get("scrap_types")


def alloy_price(name: str) -> int:
    """合金单价，未知品种返回 0。"""
    return get("alloy_prices").get(name, 0)
