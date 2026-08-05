"""效率分析服务。时长/节奏/产能维度。"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import FactHeat, FactHeating, FactRolling


def duration_stats(db: Session) -> list[dict]:
    """各工序时长类指标统计（统一换算为分钟：转炉秒→分钟）。"""
    sql = text("""
        WITH d AS (
            SELECT process, indicator_name,
                CASE WHEN process = '转炉' AND indicator_name <> '镇静时长'
                     THEN actual_value::numeric / 60.0 ELSE actual_value::numeric END AS dur
            FROM fact_heat_indicator
            WHERE indicator_name LIKE '%时长%'
                AND actual_value ~ '^[0-9]+\\.?[0-9]*$'
        )
        SELECT process, indicator_name,
            COUNT(*) AS n,
            ROUND((AVG(dur))::numeric, 1) AS avg_val,
            ROUND((MIN(dur))::numeric, 1) AS min_val,
            ROUND((PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY dur))::numeric, 1) AS p99_val,
            ROUND((STDDEV(dur))::numeric, 1) AS std_val
        FROM d GROUP BY process, indicator_name
        ORDER BY process, avg_val DESC
    """)
    rows = db.execute(sql).all()
    out = []
    for r in rows:
        out.append({
            "process": r.process,
            "indicator": r.indicator_name,
            "n": int(r.n),
            "avg": float(r.avg_val),
            "min": float(r.min_val),
            "p99": float(r.p99_val),
            "std": float(r.std_val),
            "unit": "min",
        })
    return out


def heat_count_by_team(db: Session) -> list[dict]:
    """炼钢班组炉数与符合率（按班组下钻）。"""
    sql = text("""
        SELECT team,
            COUNT(DISTINCT heat_no) AS heats,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator
        WHERE team IS NOT NULL
        GROUP BY team ORDER BY heats DESC
    """)
    rows = db.execute(sql).all()
    return [
        {
            "team": r.team,
            "heats": int(r.heats),
            "judged": int(r.judged),
            "hit": int(r.hit),
            "rate": round(100 * r.hit / r.judged, 2) if r.judged else 0,
        }
        for r in rows
    ]


def rolling_shift_output(db: Session) -> list[dict]:
    """轧钢班次产量与温度（SWRCH22A）。"""
    sql = text("""
        SELECT shift,
            COUNT(*) AS records,
            COUNT(DISTINCT heat_no) AS heats,
            SUM(roll_weight) AS total_weight,
            ROUND((AVG(start_roll_temp))::numeric, 1) AS avg_start_temp,
            ROUND((AVG(finish_temp))::numeric, 1) AS avg_finish_temp,
            ROUND((AVG(laying_temp))::numeric, 1) AS avg_laying_temp,
            ROUND((AVG(hit_rate_a))::numeric, 2) AS avg_hit_a,
            ROUND((AVG(hit_rate_c))::numeric, 2) AS avg_hit_c
        FROM fact_rolling
        WHERE shift IS NOT NULL
        GROUP BY shift ORDER BY shift
    """)
    rows = db.execute(sql).all()
    return [
        {
            "shift": r.shift,
            "records": int(r.records),
            "heats": int(r.heats),
            "total_weight": float(r.total_weight) if r.total_weight else 0,
            "avg_start_temp": float(r.avg_start_temp) if r.avg_start_temp else 0,
            "avg_finish_temp": float(r.avg_finish_temp) if r.avg_finish_temp else 0,
            "avg_laying_temp": float(r.avg_laying_temp) if r.avg_laying_temp else 0,
            "avg_hit_a": float(r.avg_hit_a) if r.avg_hit_a else 0,
            "avg_hit_c": float(r.avg_hit_c) if r.avg_hit_c else 0,
        }
        for r in rows
    ]


def heating_stats(db: Session) -> dict:
    """加热工艺统计（SWRCH22A）。"""
    r = db.execute(text("""
        SELECT COUNT(*) AS n,
            ROUND((AVG(total_heat_time))::numeric, 1) AS avg_time,
            MIN(total_heat_time) AS min_time,
            MAX(total_heat_time) AS max_time,
            ROUND((AVG(preheat_temp))::numeric, 1) AS avg_preheat,
            ROUND((AVG(heat_section_temp))::numeric, 1) AS avg_heat,
            ROUND((AVG(soak_temp))::numeric, 1) AS avg_soak,
            ROUND((AVG(out_temp))::numeric, 1) AS avg_out
        FROM fact_heating WHERE out_temp IS NOT NULL
    """)).one()
    return {
        "record_count": int(r.n),
        "total_heat_time": {"avg": float(r.avg_time), "min": float(r.min_time), "max": float(r.max_time)},
        "preheat_temp": {"avg": float(r.avg_preheat)},
        "heat_section_temp": {"avg": float(r.avg_heat)},
        "soak_temp": {"avg": float(r.avg_soak)},
        "out_temp": {"avg": float(r.avg_out)},
    }


def casting_params(db: Session, process: str = "板坯") -> list[dict]:
    """板坯/方坯关键工艺参数：符合率 + 数值型 Min/Mean/Max（对标 demo S2/S3）。"""
    rows = db.execute(text("""
        SELECT indicator_name,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit,
          ROUND((AVG(actual_value::numeric) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$'))::numeric, 2) AS avg_v,
          MIN(actual_value::numeric) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS min_v,
          MAX(actual_value::numeric) FILTER (WHERE actual_value ~ '^[0-9]+\\.?[0-9]*$') AS max_v
        FROM fact_heat_indicator WHERE process = :p
        GROUP BY indicator_name
        ORDER BY avg_v DESC NULLS LAST
    """), {"p": process}).all()
    out = []
    for r in rows:
        judged = int(r.judged or 0)
        out.append({
            "indicator": r.indicator_name,
            "judged": judged,
            "hit": int(r.hit or 0),
            "rate": round(100 * (r.hit or 0) / judged, 1) if judged else 0,
            "avg": float(r.avg_v) if r.avg_v is not None else None,
            "min": float(r.min_v) if r.min_v is not None else None,
            "max": float(r.max_v) if r.max_v is not None else None,
        })
    return out


def equipment_output(db: Session) -> list[dict]:
    """设备产量占比（按工序×设备，避免同设备号跨工序重复计数）。"""
    rows = db.execute(text("""
        SELECT process, equipment,
          COUNT(DISTINCT heat_no) AS heats,
          COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
          COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE equipment IS NOT NULL
        GROUP BY process, equipment ORDER BY heats DESC
    """)).all()
    return [
        {"process": r.process, "equipment": r.equipment, "heats": int(r.heats),
         "rate": round(100 * (r.hit or 0) / (r.judged or 1), 1)}
        for r in rows
    ]


def trend_series(db: Session, indicator: str = "中包过热度", limit: int = 100) -> dict:
    """关键参数趋势时序（对标 demo S8）。"""
    rows = db.execute(text("""
        SELECT tap_time, actual_value::numeric AS v
        FROM fact_heat_indicator
        WHERE indicator_name = :n AND actual_value ~ '^[0-9]+\\.?[0-9]*$' AND tap_time IS NOT NULL
        ORDER BY tap_time LIMIT :limit
    """), {"n": indicator, "limit": limit}).all()
    return {
        "indicator": indicator,
        "times": [str(r.tap_time)[5:16] if r.tap_time else "" for r in rows],
        "values": [float(r.v) for r in rows],
    }
