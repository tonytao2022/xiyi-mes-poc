"""效率主线 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import efficiency

router = APIRouter()


@router.get("/duration-stats")
def duration_stats(db: Session = Depends(get_db)):
    """各工序时长类指标统计。"""
    return efficiency.duration_stats(db)


@router.get("/heat-count-by-team")
def heat_count_by_team(db: Session = Depends(get_db)):
    """班组炉数与符合率。"""
    return efficiency.heat_count_by_team(db)


@router.get("/rolling-shift-output")
def rolling_shift_output(db: Session = Depends(get_db)):
    """轧钢班次产量与温度（SWRCH22A）。"""
    return efficiency.rolling_shift_output(db)


@router.get("/heating-stats")
def heating_stats(db: Session = Depends(get_db)):
    """加热工艺统计（SWRCH22A）。"""
    return efficiency.heating_stats(db)


@router.get("/insights")
def efficiency_insights_api(db: Session = Depends(get_db)):
    """效率智能洞察：瓶颈工序/时长异常/班组差距。"""
    from app.services import insights
    return insights.efficiency_insights(db)


@router.get("/ai-analysis")
def efficiency_ai_analysis_api(db: Session = Depends(get_db)):
    """效率AI分析（聚焦效率指标：周期/班组/设备/趋势）。"""
    from app.services import efficiency_ai
    return efficiency_ai.efficiency_ai_analysis(db)


@router.get("/casting-params")
def casting_params_api(process: str = "板坯", db: Session = Depends(get_db)):
    """板坯/方坯连铸关键参数（对标 demo S2/S3）。"""
    return efficiency.casting_params(db, process)


@router.get("/equipment-output")
def equipment_output_api(db: Session = Depends(get_db)):
    """设备产量占比（对标 demo S7）。"""
    return efficiency.equipment_output(db)


@router.get("/trend-series")
def trend_series_api(indicator: str = "中包过热度", limit: int = 100, db: Session = Depends(get_db)):
    """关键参数趋势时序（对标 demo S8）。"""
    return efficiency.trend_series(db, indicator, limit)
