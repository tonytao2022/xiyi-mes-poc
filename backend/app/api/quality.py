"""质量主线 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import quality

router = APIRouter()


@router.get("/compliance-overview")
def compliance_overview(db: Session = Depends(get_db)):
    """各工序工艺符合率总览（含合计）。"""
    return quality.compliance_overview(db)


@router.get("/compliance-by-dimension")
def compliance_by_dimension(
    dim: str = "steel_grade",
    process: str | None = None,
    db: Session = Depends(get_db),
):
    """按维度(steel_grade/team/equipment/process_route)下钻符合率。"""
    return quality.compliance_by_dimension(db, dim, process)


@router.get("/indicator-ranking")
def indicator_ranking(
    process: str | None = None,
    order: str = "asc",
    db: Session = Depends(get_db),
):
    """指标合格率排序：asc 短板，desc 优秀。"""
    return quality.indicator_ranking(db, process, order)


@router.get("/mechanical-stats")
def mechanical_stats(db: Session = Depends(get_db)):
    """力学性能统计（SWRCH22A）。"""
    return quality.mechanical_stats(db)


@router.get("/mechanical-distribution")
def mechanical_distribution(db: Session = Depends(get_db)):
    """力学性能 Min/Mean/Max 分布（对应 demo S1）。"""
    return quality.mechanical_distribution(db)


@router.get("/chemical-radar")
def chemical_radar(db: Session = Depends(get_db)):
    """化学成分均值雷达（对应 demo S2）。"""
    return quality.chemical_radar(db)


@router.get("/single-deviation")
def single_deviation(sample_lot_no: str | None = None, db: Session = Depends(get_db)):
    """单件物料 z-score 偏差（对应 PDF 单块物料分析报告）。"""
    return quality.single_deviation(db, sample_lot_no)


@router.get("/heat-score")
def heat_score(limit: int = 20, db: Session = Depends(get_db)):
    """炉次质量评分（借鉴兴澄：符合率作为得分）。"""
    return quality.heat_score(db, limit)


@router.get("/history-best")
def history_best(limit: int = 10, db: Session = Depends(get_db)):
    """按钢种查历史最高分炉次（借鉴兴澄历史最优指导）。"""
    return quality.history_best(db, limit)


@router.get("/heat-trace")
def heat_trace(heat_no: str | None = None, db: Session = Depends(get_db)):
    """熔炼号全流程追溯一张图（借鉴兴澄⑧）。"""
    return quality.heat_trace(db, heat_no)


@router.get("/heating-temperature")
def heating_temperature(db: Session = Depends(get_db)):
    """加热工艺各段温度 Min/Mean/Max（对标 demo S3）。"""
    return quality.heating_temperature(db)


@router.get("/rolling-temperature-series")
def rolling_temperature_series(limit: int = 60, db: Session = Depends(get_db)):
    """轧制温度时序（对标 demo S4）。"""
    return quality.rolling_temperature_series(db, limit)


@router.get("/hit-rate-distribution")
def hit_rate_distribution(db: Session = Depends(get_db)):
    """A/B/C 命中率分布（对标 demo S7）。"""
    return quality.hit_rate_distribution(db)


@router.get("/insights")
def quality_insights_api(db: Session = Depends(get_db)):
    """质量智能洞察：自动识别短板指标/合金超标准/低分炉次/力学离群。"""
    from app.services import insights
    return insights.quality_insights(db)


@router.get("/indicator-detail")
def indicator_detail_api(process: str, indicator: str, limit: int = 50, db: Session = Depends(get_db)):
    """指标根因下钻：符合率+异常炉次明细+实绩分布+趋势（场景D）。"""
    return quality.indicator_detail(db, process, indicator, limit)


@router.get("/correlation")
def correlation_api(db: Session = Depends(get_db)):
    """成分-性能相关系数（对标 demo S5）。"""
    return quality.correlation(db)


@router.get("/scatter")
def scatter_api(x: str = "C", y: str = "yield_strength", db: Session = Depends(get_db)):
    """成分-性能散点（对标 demo S6）。"""
    return quality.scatter(db, x, y)


@router.get("/dimension-stats")
def dimension_stats_api(db: Session = Depends(get_db)):
    """尺寸检验统计（对标 demo S9）。"""
    return quality.dimension_stats(db)


@router.get("/mechanical-histogram")
def mechanical_histogram_api(db: Session = Depends(get_db)):
    """力学性能分布直方图（对标 demo S1）。"""
    return quality.mechanical_histogram(db)


@router.get("/chemical-stats")
def chemical_stats_api(db: Session = Depends(get_db)):
    """化学成分统计卡（均值/标准差/范围，对标 demo S2）。"""
    return quality.chemical_stats(db)


@router.get("/ai-analysis")
def ai_analysis_api(db: Session = Depends(get_db)):
    """AI智能分析：对质量数据自动分析输出结论。"""
    from app.services import ai_analysis
    return ai_analysis.quality_ai_analysis(db)


@router.get("/compliance-by-grade")
def compliance_by_grade_api(process: str = "板坯", limit: int = 8, db: Session = Depends(get_db)):
    """钢种×指标合格率矩阵（对标 demo S6）。"""
    return quality.compliance_by_grade(db, process, limit)


@router.get("/ai-trace")
def ai_trace_api(heat_no: str | None = None, db: Session = Depends(get_db)):
    """追溯AI分析。"""
    from app.services import ai_analysis
    return ai_analysis.trace_analysis(db, heat_no)
