"""双维度交汇分析 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import cross

router = APIRouter()


@router.get("/all")
def crossover_all_api(db: Session = Depends(get_db)):
    """全部双维度交汇汇总。"""
    return cross.crossover_all(db)


@router.get("/quality-cost")
def quality_cost_api(db: Session = Depends(get_db)):
    """质量×成本交汇。"""
    return cross.quality_cost_crossover(db)


@router.get("/quality-efficiency")
def quality_efficiency_api(db: Session = Depends(get_db)):
    """质量×效率交汇。"""
    return cross.quality_efficiency_crossover(db)


@router.get("/cost-efficiency")
def cost_efficiency_api(db: Session = Depends(get_db)):
    """成本×效率交汇。"""
    return cross.cost_efficiency_crossover(db)
