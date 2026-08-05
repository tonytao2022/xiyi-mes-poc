"""AI 智体 API：LLM 根因分析 + 报告生成/管理 + 健康探测。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.ai_report import AiReport
from app.services.llm_client import LLMClient
from app.services.llm_analyzer import analyze_root_causes, full_lm_analysis
from app.services.report_engine import generate_report

router = APIRouter()

_VALID_DOMAINS = {"comprehensive", "quality", "cost", "efficiency"}


def _check_domain(domain: str):
    if domain not in _VALID_DOMAINS:
        raise HTTPException(status_code=400, detail=f"domain 需为 {sorted(_VALID_DOMAINS)} 之一")


@router.post("/reason")
def ai_reason(domain: str = Query("comprehensive"), db: Session = Depends(get_db)):
    """LLM 根因分析（domain: comprehensive/quality/cost/efficiency）。"""
    _check_domain(domain)
    return analyze_root_causes(db, domain)


@router.post("/report/generate")
def ai_report_generate(domain: str = Query("comprehensive"), include_llm: bool = True,
                       db: Session = Depends(get_db)):
    """生成完整 7 段式报告并入库。"""
    _check_domain(domain)
    try:
        return generate_report(db, domain, include_llm)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"报告生成失败: {e}") from e


@router.get("/report/list")
def ai_report_list(page: int = 1, page_size: int = 20, domain: str | None = None,
                   db: Session = Depends(get_db)):
    """报告历史列表（created_at 倒序分页）。"""
    q = db.query(AiReport)
    if domain and domain in _VALID_DOMAINS:
        q = q.filter(AiReport.domain == domain)
    total = q.count()
    rows = (q.order_by(AiReport.created_at.desc(), AiReport.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    items = [{
        "id": r.id, "domain": r.domain, "title": r.title, "period": r.period,
        "llm_used": r.llm_used, "model_used": r.model_used, "created_at": r.created_at,
    } for r in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/report/{report_id}")
def ai_report_detail(report_id: int, mode: str = "json", db: Session = Depends(get_db)):
    """报告详情（HTML / JSON 双模式）。"""
    r = db.query(AiReport).filter(AiReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="报告不存在")
    if mode == "html":
        return {"id": r.id, "html": r.html, "llm_used": r.llm_used}
    return {
        "id": r.id, "domain": r.domain, "title": r.title, "period": r.period,
        "meta": r.meta_json, "llm": r.llm_json, "llm_used": r.llm_used,
        "model_used": r.model_used, "created_at": r.created_at,
    }


@router.get("/health")
def ai_health():
    """LLM 配置与可用性探测（不实际调用 LLM）。"""
    client = LLMClient()
    return {
        "enabled": client.enabled,
        "base_url": settings.LLM_BASE_URL,
        "model": settings.LLM_MODEL,
        "note": "enabled=true 表示已配置 key 并启用 LLM 链路；false 为纯规则降级模式",
    }
