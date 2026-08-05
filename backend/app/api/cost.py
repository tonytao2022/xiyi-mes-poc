"""成本主线 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import cost

router = APIRouter()


@router.get("/scrap-overview")
def scrap_overview(db: Session = Depends(get_db)):
    """废钢配料总览：各料型总量、占比、炉数。"""
    return cost.scrap_overview(db)


@router.get("/scrap-by-grade")
def scrap_by_grade(limit: int = 10, db: Session = Depends(get_db)):
    """按钢种废钢用量 Top。"""
    return cost.scrap_by_grade(db, limit)


@router.get("/scrap-matrix")
def scrap_matrix(limit: int = 8, db: Session = Depends(get_db)):
    """Top 钢种 × 料型 配比矩阵。"""
    return cost.scrap_matrix(db, limit)


@router.get("/alloy-overview")
def alloy_overview(db: Session = Depends(get_db)):
    """合金投入总览：使用率、均值、符合率。"""
    return cost.alloy_overview(db)


@router.get("/insights")
def cost_insights_api(db: Session = Depends(get_db)):
    """成本智能洞察：料型集中度/高价合金/富裕损失/零用料型。"""
    from app.services import insights
    return insights.cost_insights(db)


@router.get("/ai-analysis")
def cost_ai_analysis_api(db: Session = Depends(get_db)):
    """成本AI分析（聚焦直接成本：钢铁料/合金/对标/价格风险）。"""
    from app.services import cost_ai
    return cost_ai.cost_ai_analysis(db)
