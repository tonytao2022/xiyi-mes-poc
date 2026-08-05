"""三维度综合炉次成本模型 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import comprehensive, comprehensive_drilldown, simulation

router = APIRouter()


@router.get("/model")
def model_api(limit: int = 50, db: Session = Depends(get_db)):
    """综合炉次成本模型：直接+质量损失+效率损失，损失结构，钢种/班组对标。"""
    return comprehensive.comprehensive_model(db, limit)


@router.get("/ai-analysis")
def ai_analysis_api(db: Session = Depends(get_db)):
    """综合AI分析：5个子分析(总账/质量损失/效率损失/交叉杠杆/优化仿真) + 跨域因果链。"""
    from app.services import comprehensive_ai
    return comprehensive_ai.comprehensive_ai_analysis(db)


@router.get("/quality-loss-detail")
def quality_loss_detail_api(db: Session = Depends(get_db)):
    """质量损失折算明细下钻：按损失项/钢种聚合 + 合金富裕精确明细 + source 标注。"""
    return comprehensive_drilldown.quality_loss_drilldown(db)


@router.get("/efficiency-loss-detail")
def efficiency_loss_detail_api(db: Session = Depends(get_db)):
    """效率损失折算明细下钻：按损失项/班组聚合 + P95超时 + 工序成本 + source 标注。"""
    return comprehensive_drilldown.efficiency_loss_drilldown(db)


@router.get("/tradeoff")
def tradeoff_api(db: Session = Depends(get_db)):
    """权衡分析：配料-合格率 scatter + 钢种质量-成本矩阵 + 时长-质量分箱。"""
    return comprehensive_drilldown.tradeoff_analysis(db)


@router.get("/loss-source")
def loss_source_api(db: Session = Depends(get_db)):
    """损失数据来源汇总：source 分布 + 系数置信度（供 AI 按置信度措辞）。"""
    return comprehensive_drilldown.loss_source_summary(db)


@router.get("/simulation")
def simulation_api(limit: int = 50, db: Session = Depends(get_db)):
    """参数仿真/情景对比：多方案综合成本对比（三块此消彼长）。"""
    structure = comprehensive.comprehensive_model(db, limit)["structure"]
    return simulation.parameter_simulation(structure)


@router.get("/sensitivity")
def sensitivity_api(variable: str = "efficiency", limit: int = 50, db: Session = Depends(get_db)):
    """敏感度分析：变量波动 -> 综合成本变化，找优化杠杆点。"""
    structure = comprehensive.comprehensive_model(db, limit)["structure"]
    return simulation.sensitivity_analysis(structure, variable)


@router.get("/recipe")
def recipe_api(total_weight: float = 100, low_end_limit: float = 20, metal_requirement: float = 0.90):
    """配料优化（线性规划）：min 综合成本（采购+质量惩罚+效率惩罚）配料方案。"""
    return simulation.recipe_optimization(total_weight, low_end_limit, metal_requirement)


@router.get("/interactive")
def interactive_api(
    yield_rate: float = 0.92, defect_rate: float = 0.01, reblow_count: int = None,
    alloy_surplus_pct: float = 0.05, low_end_ratio: float = 0.15, scrap_price: float = 2800,
    alloy_substitution_rate: float = 0.10, refining_duration: float = 30,
    converter_duration: float = 25, waiting_time: float = 10, sequence_length: int = 20,
    limit: int = 50, db: Session = Depends(get_db),
):
    """交互式模拟：11个真实可优化业务要素。"""
    model = comprehensive.comprehensive_model(db, limit)
    structure = model["structure"]
    if reblow_count is None:
        heat_nos = [h["heat_no"] for h in model["heats"]]
        reblow_count = comprehensive.count_reblows(db, heat_nos)
    return simulation.interactive_simulation(
        structure, reblow_count, yield_rate, defect_rate, alloy_surplus_pct, low_end_ratio,
        scrap_price, alloy_substitution_rate, refining_duration, converter_duration,
        waiting_time, sequence_length
    )
