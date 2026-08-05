"""价格 API。步骤6 完善 SMM 爬取与定时调度。"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.overview import ESTIMATED_ALLOY, ESTIMATED_SCRAP

router = APIRouter()


@router.get("/list")
def price_list(category: str | None = None, db: Session = Depends(get_db)):
    """查询价格表（步骤6 爬取后填充 dim_price）。"""
    sql = "SELECT * FROM dim_price"
    params: dict = {}
    if category:
        sql += " WHERE category = :cat"
        params["cat"] = category
    sql += " ORDER BY price_date DESC LIMIT 200"
    rows = db.execute(text(sql), params).all()
    return [dict(r._mapping) for r in rows]


@router.get("/estimated-prices")
def estimated_prices():
    """估算价格表（POC 占位，后续替换为 SMM 真实价）。"""
    return {
        "scrap": ESTIMATED_SCRAP,
        "alloy": ESTIMATED_ALLOY,
        "source": "estimated",
        "note": "POC 估算值，步骤6 爬取 SMM 真实价格后替换",
    }


@router.post("/crawl")
def trigger_crawl():
    """手动触发 SMM 价格爬取，写入 dim_price。"""
    from app.crawler.smm import crawl_smm

    return crawl_smm()


@router.get("/coverage")
def price_coverage():
    """价格覆盖情况：SMM 可得品种 vs 估算占位品种。"""
    from app.crawler.smm import SMM_SLUGS

    return {
        "smm_covered": [{"slug": s, "item": n[1]} for s, n in SMM_SLUGS.items()],
        "estimated_scrap": list(ESTIMATED_SCRAP.keys()),
        "estimated_alloy": list(ESTIMATED_ALLOY.keys()),
        "note": "SMM 覆盖 5 种合金，废钢及多数铁合金用估算值占位",
    }
