"""综合看板服务：顶层 KPI + 直接成本估算（价格用估算值，步骤6 后接 SMM 真实价）。"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import cost_factors as cf

# 估算价格（元/吨）。统一引自 cost_factors（单一源），保留旧名供 price/cost_ai 复用。
ESTIMATED_SCRAP = cf.scrap_price_map()  # 料型 -> 单价
ESTIMATED_ALLOY = cf.get("alloy_prices")  # 合金 -> 单价


def _latest_price(db: Session, item_name: str) -> float | None:
    """查询 dim_price 中该品种最新真实价格（SMM 爬取），无则返回 None。"""
    row = db.execute(text("""
        SELECT unit_price FROM dim_price
        WHERE item_name = :n AND unit_price IS NOT NULL
        ORDER BY price_date DESC LIMIT 1
    """), {"n": item_name}).first()
    return float(row[0]) if row else None


def kpi(db: Session) -> dict:
    """顶层 KPI。"""
    r = db.execute(text("""
        SELECT
            COUNT(DISTINCT heat_no) AS heats,
            COUNT(DISTINCT steel_grade) AS grades,
            MIN(tap_time) AS date_from,
            MAX(tap_time) AS date_to,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator
    """)).one()
    scrap = db.execute(text("""
        SELECT SUM(hc) AS h, SUM(tw) AS w FROM (
            SELECT steel_grade, MAX(heat_count) AS hc, MAX(total_weight) AS tw
            FROM fact_scrap_ratio GROUP BY steel_grade
        ) t
    """)).one()
    mech = db.execute(text("SELECT COUNT(*) AS n FROM fact_inspect_mech")).scalar()
    rolling = db.execute(text("SELECT COUNT(*) AS n FROM fact_rolling")).scalar()
    heating = db.execute(text("SELECT COUNT(*) AS n FROM fact_heating")).scalar()
    days = None
    if r.date_from and r.date_to:
        days = (r.date_to.date() - r.date_from.date()).days + 1
    judged = int(r.judged or 0)
    hit = int(r.hit or 0)
    return {
        "total_heats": int(r.heats or 0),
        "steel_grade_count": int(r.grades or 0),
        "coverage_days": days,
        "date_from": str(r.date_from) if r.date_from else None,
        "date_to": str(r.date_to) if r.date_to else None,
        "overall_compliance_rate": round(100 * hit / judged, 2) if judged else 0,
        "total_judged": judged,
        "total_hit": hit,
        "scrap_total_weight": float(scrap.w or 0),
        "scrap_total_heats": int(scrap.h or 0),
        "mech_samples": int(mech or 0),
        "rolling_records": int(rolling or 0),
        "heating_records": int(heating or 0),
    }


def direct_cost(db: Session) -> dict:
    """直接成本估算 = 废钢成本(钢种级) + 合金成本(炉次级)。"""
    # 废钢：各料型总量 × 估算单价
    scrap_rows = db.execute(text("""
        SELECT scrap_type, SUM(weight) AS weight
        FROM fact_scrap_ratio GROUP BY scrap_type
    """)).all()
    scrap_cost = []
    total_scrap = 0.0
    for r in scrap_rows:
        real = _latest_price(db, r.scrap_type)
        price = real if real else ESTIMATED_SCRAP.get(r.scrap_type, 0)
        cost = float(r.weight or 0) * price
        total_scrap += cost
        scrap_cost.append({
            "scrap_type": r.scrap_type, "weight": float(r.weight or 0),
            "price": price, "cost": round(cost, 0),
            "source": "smm" if real else "estimated",
        })

    # 合金：各合金总加入量 × 估算单价
    alloy_rows = db.execute(text("""
        SELECT indicator_name AS alloy,
            SUM(actual_value::numeric)
                FILTER (WHERE actual_value ~ '^-?[0-9]+\\.?[0-9]*$') AS total_amount
        FROM fact_heat_indicator
        WHERE process = '合金'
        GROUP BY indicator_name
    """)).all()
    alloy_cost = []
    total_alloy = 0.0
    for r in alloy_rows:
        real = _latest_price(db, r.alloy)
        price = real if real else ESTIMATED_ALLOY.get(r.alloy, 0)
        amount = float(r.total_amount or 0)
        cost = amount * price
        total_alloy += cost
        alloy_cost.append({
            "alloy": r.alloy, "total_amount": round(amount, 1),
            "price": price, "cost": round(cost, 0),
            "source": "smm" if real else "estimated",
        })
    alloy_cost.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "scrap_cost": sorted(scrap_cost, key=lambda x: x["cost"], reverse=True),
        "alloy_cost": alloy_cost,
        "total_scrap_cost": round(total_scrap, 0),
        "total_alloy_cost": round(total_alloy, 0),
        "total_direct_cost": round(total_scrap + total_alloy, 0),
        "price_source": "estimated（估算值，步骤6 爬取 SMM 真实价后替换）",
    }
