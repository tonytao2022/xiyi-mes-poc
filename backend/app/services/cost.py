"""成本分析服务。废钢配料(钢种级) + 合金投入(炉次级)。"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def scrap_overview(db: Session) -> dict:
    """废钢配料总览：各料型总量、占比、炉数。"""
    r = db.execute(text("""
        SELECT COUNT(*) AS grades,
            SUM(hc) AS heats,
            SUM(tw) AS total_weight
        FROM (
            SELECT steel_grade, MAX(heat_count) AS hc, MAX(total_weight) AS tw
            FROM fact_scrap_ratio GROUP BY steel_grade
        ) t
    """)).one()
    types = db.execute(text("""
        SELECT scrap_type,
            SUM(weight) AS weight,
            ROUND((100.0 * SUM(weight) / NULLIF(SUM(SUM(weight)) OVER (), 0))::numeric, 2) AS pct,
            COUNT(*) FILTER (WHERE weight > 0) AS used_grades,
            ROUND((AVG(weight) FILTER (WHERE weight > 0))::numeric, 1) AS avg_per_grade
        FROM fact_scrap_ratio
        GROUP BY scrap_type ORDER BY weight DESC
    """)).all()
    return {
        "steel_grade_count": int(r.grades),
        "total_heats": int(r.heats or 0),
        "total_weight": float(r.total_weight or 0),
        "types": [
            {"scrap_type": t.scrap_type, "weight": float(t.weight or 0), "pct": float(t.pct or 0),
             "used_grades": int(t.used_grades or 0), "avg_per_grade": float(t.avg_per_grade or 0)}
            for t in types
        ],
    }


def scrap_by_grade(db: Session, limit: int = 10) -> list[dict]:
    """按钢种废钢用量 Top。"""
    rows = db.execute(text(f"""
        SELECT steel_grade,
            MAX(heat_count) AS heats,
            MAX(total_weight) AS total_weight
        FROM fact_scrap_ratio
        WHERE steel_grade <> '合计'
        GROUP BY steel_grade
        ORDER BY total_weight DESC
        LIMIT {limit}
    """)).all()
    return [{"steel_grade": r.steel_grade, "heats": int(r.heats or 0),
             "total_weight": float(r.total_weight or 0)} for r in rows]


def scrap_matrix(db: Session, limit: int = 8) -> dict:
    """Top 钢种 × 料型 配比矩阵（ratio 百分比）。"""
    top = db.execute(text(f"""
        SELECT steel_grade FROM (
            SELECT steel_grade, MAX(total_weight) AS w
            FROM fact_scrap_ratio WHERE steel_grade <> '合计'
            GROUP BY steel_grade ORDER BY w DESC LIMIT {limit}
        ) t
    """)).all()
    grades = [r.steel_grade for r in top]
    if not grades:
        return {"grades": [], "types": [], "matrix": []}
    rows = db.execute(text("""
        SELECT steel_grade, scrap_type, ROUND((100.0 * AVG(ratio))::numeric, 2) AS avg_ratio
        FROM fact_scrap_ratio
        WHERE steel_grade = ANY(:grades) AND ratio IS NOT NULL
        GROUP BY steel_grade, scrap_type
    """), {"grades": grades}).all()
    types = sorted({r.scrap_type for r in rows})
    matrix = {g: {t: 0.0 for t in types} for g in grades}
    for r in rows:
        matrix[r.steel_grade][r.scrap_type] = float(r.avg_ratio or 0)
    return {"grades": grades, "types": types, "matrix": matrix}


def alloy_overview(db: Session) -> list[dict]:
    """合金投入总览：使用率、均值、符合率。"""
    sql = text("""
        SELECT indicator_name AS alloy,
            COUNT(*) AS records,
            COUNT(*) FILTER (WHERE actual_value ~ '^-?[0-9]+\\.?[0-9]*$'
                             AND actual_value::numeric > 0) AS used_count,
            ROUND(AVG(actual_value::numeric)
                  FILTER (WHERE actual_value ~ '^-?[0-9]+\\.?[0-9]*$'), 2) AS avg_amount,
            ROUND(MIN(actual_value::numeric)
                  FILTER (WHERE actual_value ~ '^-?[0-9]+\\.?[0-9]*$'), 2) AS min_amount,
            ROUND(MAX(actual_value::numeric)
                  FILTER (WHERE actual_value ~ '^-?[0-9]+\\.?[0-9]*$'), 2) AS max_amount,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator
        WHERE process = '合金'
        GROUP BY indicator_name
        ORDER BY avg_amount DESC NULLS LAST
    """)
    rows = db.execute(sql).all()
    total_heats = db.execute(text(
        "SELECT COUNT(DISTINCT heat_no) FROM fact_heat_indicator WHERE process='合金'"
    )).scalar() or 1
    return [
        {
            "alloy": r.alloy,
            "used_count": int(r.used_count or 0),
            "usage_rate": round(100 * (r.used_count or 0) / total_heats, 1),
            "avg_amount": float(r.avg_amount) if r.avg_amount is not None else 0,
            "min_amount": float(r.min_amount) if r.min_amount is not None else 0,
            "max_amount": float(r.max_amount) if r.max_amount is not None else 0,
            "judged": int(r.judged or 0),
            "hit": int(r.hit or 0),
            "rate": round(100 * (r.hit or 0) / (r.judged or 1), 2),
        }
        for r in rows
    ]
