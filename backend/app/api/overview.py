"""综合看板 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import overview

router = APIRouter()


@router.get("/kpi")
def kpi(db: Session = Depends(get_db)):
    """顶层 KPI。"""
    return overview.kpi(db)


@router.get("/direct-cost")
def direct_cost(db: Session = Depends(get_db)):
    """直接成本估算（废钢 + 合金 × 估算价格）。"""
    return overview.direct_cost(db)


@router.get("/insights")
def overview_insights_api(db: Session = Depends(get_db)):
    """综合智能洞察：三主线汇总 + 优化优先级。"""
    from app.services import insights
    return insights.overview_insights(db)
