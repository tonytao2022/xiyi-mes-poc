"""质量分析服务。

符合率口径：judge IS NOT NULL 视为判定，judge = 1 视为命中。
（板坯/方坯与客户汇总完全吻合；转炉等工序因汇总按试样级展开，口径待客户确认）
"""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import FactHeatIndicator, FactInspectMech

_DIM_MAP = {
    "steel_grade": FactHeatIndicator.steel_grade,
    "team": FactHeatIndicator.team,
    "equipment": FactHeatIndicator.equipment,
    "process_route": FactHeatIndicator.process_route,
}


def compliance_overview(db: Session) -> list[dict]:
    """各工序符合率总览（含合计）。"""
    rows = db.execute(
        select(
            FactHeatIndicator.process.label("process"),
            func.count().filter(FactHeatIndicator.judge.isnot(None)).label("judged"),
            func.count().filter(FactHeatIndicator.judge == 1).label("hit"),
            func.count(func.distinct(FactHeatIndicator.heat_no)).label("heats"),
            func.count(func.distinct(FactHeatIndicator.indicator_name)).label("indicators"),
        ).group_by(FactHeatIndicator.process)
    ).all()
    out = []
    for r in rows:
        judged = int(r.judged or 0)
        hit = int(r.hit or 0)
        out.append({
            "process": r.process,
            "judged": judged,
            "hit": hit,
            "rate": round(100 * hit / judged, 2) if judged else 0,
            "heats": int(r.heats or 0),
            "indicators": int(r.indicators or 0),
        })
    tj = sum(x["judged"] for x in out)
    th = sum(x["hit"] for x in out)
    out.append({"process": "合计", "judged": tj, "hit": th,
                "rate": round(100 * th / tj, 2) if tj else 0, "heats": "", "indicators": ""})
    return out


def compliance_by_dimension(db: Session, dim: str, process: str | None = None) -> list[dict]:
    """按维度(steel_grade/team/equipment/process_route)下钻符合率。"""
    col = _DIM_MAP[dim]
    judged_cnt = func.count().filter(FactHeatIndicator.judge.isnot(None)).label("judged")
    hit_cnt = func.count().filter(FactHeatIndicator.judge == 1).label("hit")
    stmt = (
        select(
            col.label("key"),
            func.count(func.distinct(FactHeatIndicator.heat_no)).label("heats"),
            judged_cnt,
            hit_cnt,
        )
        .where(col.isnot(None))
        .group_by(col)
    )
    if process:
        stmt = stmt.where(FactHeatIndicator.process == process)
    stmt = stmt.order_by(judged_cnt.desc()).limit(20)
    rows = db.execute(stmt).all()
    return [
        {
            "key": r.key,
            "heats": int(r.heats or 0),
            "judged": int(r.judged or 0),
            "hit": int(r.hit or 0),
            "rate": round(100 * (r.hit or 0) / (r.judged or 1), 2),
        }
        for r in rows
    ]


def indicator_ranking(db: Session, process: str | None = None, order: str = "asc") -> list[dict]:
    """指标合格率排序：asc 找短板，desc 找优秀。"""
    judged_cnt = func.count().filter(FactHeatIndicator.judge.isnot(None))
    hit_cnt = func.count().filter(FactHeatIndicator.judge == 1)
    rate = func.round(100.0 * hit_cnt / func.nullif(judged_cnt, 0), 2)
    stmt = (
        select(
            FactHeatIndicator.indicator_name.label("name"),
            FactHeatIndicator.process.label("process"),
            judged_cnt.label("judged"),
            hit_cnt.label("hit"),
            rate.label("rate"),
        )
        .group_by(FactHeatIndicator.process, FactHeatIndicator.indicator_name)
        .having(judged_cnt > 0)
    )
    if process:
        stmt = stmt.where(FactHeatIndicator.process == process)
    stmt = stmt.order_by(rate.asc() if order == "asc" else rate.desc()).limit(15)
    rows = db.execute(stmt).all()
    return [
        {"name": r.name, "process": r.process, "judged": int(r.judged or 0),
         "hit": int(r.hit or 0), "rate": float(r.rate) if r.rate is not None else 0}
        for r in rows
    ]


def mechanical_stats(db: Session) -> dict:
    """力学性能统计（SWRCH22A）：均值/范围/合格率。"""
    r = db.execute(text("""
        SELECT COUNT(*) AS n,
            ROUND((AVG(yield_strength))::numeric, 1) AS ys_avg,
            MIN(yield_strength) AS ys_min,
            MAX(yield_strength) AS ys_max,
            ROUND((AVG(tensile_strength))::numeric, 1) AS ts_avg,
            MIN(tensile_strength) AS ts_min,
            MAX(tensile_strength) AS ts_max,
            ROUND((AVG(elongation))::numeric, 1) AS el_avg,
            ROUND((AVG(yield_ratio))::numeric, 2) AS yr_avg,
            COUNT(*) FILTER (WHERE result = '合格') AS pass_cnt
        FROM fact_inspect_mech
    """)).one()
    n = int(r.n or 0)
    pass_cnt = int(r.pass_cnt or 0)
    return {
        "sample_count": n,
        "pass_count": pass_cnt,
        "pass_rate": round(100 * pass_cnt / n, 2) if n else 0,
        "yield_strength": {"avg": float(r.ys_avg or 0), "min": float(r.ys_min or 0), "max": float(r.ys_max or 0)},
        "tensile_strength": {"avg": float(r.ts_avg or 0), "min": float(r.ts_min or 0), "max": float(r.ts_max or 0)},
        "elongation": {"avg": float(r.el_avg or 0)},
        "yield_ratio": {"avg": float(r.yr_avg or 0)},
    }


def mechanical_distribution(db: Session) -> dict:
    """力学性能 Min/Mean/Max/Std 分布（对应 demo S1 柱状图）。"""
    r = db.execute(text("""
        SELECT
          ROUND((MIN(yield_strength))::numeric,1) ys_min, ROUND((AVG(yield_strength))::numeric,1) ys_avg,
          ROUND((MAX(yield_strength))::numeric,1) ys_max, ROUND((STDDEV(yield_strength))::numeric,1) ys_std,
          ROUND((MIN(tensile_strength))::numeric,1) ts_min, ROUND((AVG(tensile_strength))::numeric,1) ts_avg,
          ROUND((MAX(tensile_strength))::numeric,1) ts_max, ROUND((STDDEV(tensile_strength))::numeric,1) ts_std,
          ROUND((MIN(elongation))::numeric,1) el_min, ROUND((AVG(elongation))::numeric,1) el_avg,
          ROUND((MAX(elongation))::numeric,1) el_max, ROUND((STDDEV(elongation))::numeric,1) el_std,
          ROUND((MIN(yield_ratio))::numeric,2) yr_min, ROUND((AVG(yield_ratio))::numeric,2) yr_avg,
          ROUND((MAX(yield_ratio))::numeric,2) yr_max, ROUND((STDDEV(yield_ratio))::numeric,2) yr_std,
          ROUND((MIN(reduction_area))::numeric,1) ra_min, ROUND((AVG(reduction_area))::numeric,1) ra_avg,
          ROUND((MAX(reduction_area))::numeric,1) ra_max
        FROM fact_inspect_mech
    """)).one()
    return {
        "labels": ["屈服强度", "抗拉强度", "断后伸长率", "屈强比", "断面收缩率"],
        "series": {
            "min": [float(r.ys_min or 0), float(r.ts_min or 0), float(r.el_min or 0), float(r.yr_min or 0), float(r.ra_min or 0)],
            "avg": [float(r.ys_avg or 0), float(r.ts_avg or 0), float(r.el_avg or 0), float(r.yr_avg or 0), float(r.ra_avg or 0)],
            "max": [float(r.ys_max or 0), float(r.ts_max or 0), float(r.el_max or 0), float(r.yr_max or 0), float(r.ra_max or 0)],
        },
        "std": {
            "屈服强度": float(r.ys_std or 0), "抗拉强度": float(r.ts_std or 0),
            "断后伸长率": float(r.el_std or 0), "屈强比": float(r.yr_std or 0),
        },
    }


CHEM_LABELS = ["C", "Si", "Mn", "P", "S", "Cr", "Ni", "Cu", "Al", "Mo"]


def chemical_radar(db: Session) -> dict:
    """化学成分均值（对应 demo S2 雷达图）。"""
    cols = ", ".join([f'ROUND((AVG("{e}"))::numeric,4) AS "{e}"' for e in CHEM_LABELS])
    r = db.execute(text(f'SELECT {cols} FROM fact_inspect_chem')).one()
    return {
        "labels": CHEM_LABELS,
        "values": [float(getattr(r, e) or 0) for e in CHEM_LABELS],
    }


def _z_item(src: str, name: str, actual, avg, std, p05=None, p95=None) -> dict:
    """计算单项 z-score 与五级评级（PDF 单块报告口径）。"""
    if actual is None:
        return {"source": src, "name": name, "actual": None, "avg": None, "std": None,
                "p05": None, "p95": None, "z": None, "grade": "无数据"}
    if std is None or float(std) == 0:
        return {"source": src, "name": name, "actual": float(actual),
                "avg": float(avg) if avg is not None else None, "std": float(std) if std is not None else None,
                "p05": float(p05) if p05 is not None else None, "p95": float(p95) if p95 is not None else None,
                "z": None, "grade": "无基线"}
    z = (float(actual) - float(avg)) / float(std)
    az = abs(z)
    grade = "严重" if az >= 3 else ("偏离" if az >= 2 else "正常")
    return {"source": src, "name": name, "actual": float(actual), "avg": float(avg), "std": float(std),
            "p05": float(p05) if p05 is not None else None, "p95": float(p95) if p95 is not None else None,
            "z": round(z, 2), "grade": grade}


def single_deviation(db: Session, sample_lot_no: str | None = None) -> dict:
    """单件物料偏差 z-score（对应 PDF 单块物料分析报告，五级评级 + 化学 z + p05/p95）。"""
    if not sample_lot_no:
        sample_lot_no = db.execute(text(
            "SELECT sample_lot_no FROM fact_inspect_mech WHERE sample_lot_no IS NOT NULL ORDER BY sample_lot_no LIMIT 1"
        )).scalar()
    if not sample_lot_no:
        return {"sample_lot_no": None, "items": [], "summary": {}}

    items = []
    # 力学基线（含 p05/p95）
    base = db.execute(text("""
        SELECT
          ROUND((AVG(yield_strength))::numeric,1) ys_avg, ROUND((STDDEV(yield_strength))::numeric,1) ys_std,
          PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY yield_strength) ys_p05,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY yield_strength) ys_p95,
          ROUND((AVG(tensile_strength))::numeric,1) ts_avg, ROUND((STDDEV(tensile_strength))::numeric,1) ts_std,
          PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY tensile_strength) ts_p05,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tensile_strength) ts_p95,
          ROUND((AVG(elongation))::numeric,1) el_avg, ROUND((STDDEV(elongation))::numeric,1) el_std,
          PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY elongation) el_p05,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY elongation) el_p95
        FROM fact_inspect_mech
    """)).one()
    single = db.execute(text(
        "SELECT yield_strength, tensile_strength, elongation FROM fact_inspect_mech "
        "WHERE sample_lot_no = :sl ORDER BY sample_no LIMIT 1"
    ), {"sl": sample_lot_no}).first()
    if single:
        for src, name, actual, avg, std, p05, p95 in [
            ("拉伸", "屈服强度", single.yield_strength, base.ys_avg, base.ys_std, base.ys_p05, base.ys_p95),
            ("拉伸", "抗拉强度", single.tensile_strength, base.ts_avg, base.ts_std, base.ts_p05, base.ts_p95),
            ("拉伸", "断后伸长率", single.elongation, base.el_avg, base.el_std, base.el_p05, base.el_p95),
        ]:
            items.append(_z_item(src, name, actual, avg, std, p05, p95))

    # 化学成分 z（C/Mn/P/S）
    cb = db.execute(text("""
        SELECT ROUND((AVG("C"))::numeric,4) c_avg, ROUND((STDDEV("C"))::numeric,4) c_std,
               ROUND((AVG("Mn"))::numeric,4) mn_avg, ROUND((STDDEV("Mn"))::numeric,4) mn_std,
               ROUND((AVG("P"))::numeric,4) p_avg, ROUND((STDDEV("P"))::numeric,4) p_std,
               ROUND((AVG("S"))::numeric,4) s_avg, ROUND((STDDEV("S"))::numeric,4) s_std
        FROM fact_inspect_chem
    """)).one()
    cs = db.execute(text(
        'SELECT "C", "Mn", "P", "S" FROM fact_inspect_chem WHERE sample_lot_no = :sl LIMIT 1'
    ), {"sl": sample_lot_no}).first()
    if cs:
        for src, name, actual, avg, std in [
            ("化学", "C", cs.C, cb.c_avg, cb.c_std),
            ("化学", "Mn", cs.Mn, cb.mn_avg, cb.mn_std),
            ("化学", "P", cs.P, cb.p_avg, cb.p_std),
            ("化学", "S", cs.S, cb.s_avg, cb.s_std),
        ]:
            items.append(_z_item(src, name, actual, avg, std))

    # 按 |z| 排序（无数据/无基线排后）
    items.sort(key=lambda x: (x["grade"] in ("无数据", "无基线"), -abs(x["z"]) if x["z"] is not None else 0))
    summary = {g: sum(1 for i in items if i["grade"] == g) for g in ["严重", "偏离", "正常", "无基线", "无数据"]}
    return {"sample_lot_no": sample_lot_no, "items": items, "summary": summary}


def heat_score(db: Session, limit: int = 20) -> list[dict]:
    """炉次质量评分（借鉴兴澄：以炉次符合率作为得分，judge=1 比例 × 100）。"""
    rows = db.execute(text("""
        SELECT heat_no, steel_grade, team, equipment,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit,
            ROUND(100.0 * COUNT(*) FILTER (WHERE judge = 1)
                  / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL), 0), 2) AS score
        FROM fact_heat_indicator
        GROUP BY heat_no, steel_grade, team, equipment
        HAVING COUNT(*) FILTER (WHERE judge IS NOT NULL) > 0
        ORDER BY score DESC, judged DESC
        LIMIT :limit
    """), {"limit": limit}).all()
    return [
        {"heat_no": r.heat_no, "steel_grade": r.steel_grade, "team": r.team,
         "equipment": r.equipment, "judged": int(r.judged), "hit": int(r.hit),
         "score": float(r.score) if r.score is not None else 0}
        for r in rows
    ]


def history_best(db: Session, limit: int = 10) -> list[dict]:
    """按钢种查历史最高分炉次（借鉴兴澄历史最优指导生产）。"""
    rows = db.execute(text("""
        SELECT * FROM (
            SELECT heat_no, steel_grade, team,
                COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
                COUNT(*) FILTER (WHERE judge = 1) AS hit,
                ROUND(100.0 * COUNT(*) FILTER (WHERE judge = 1)
                      / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL), 0), 2) AS score,
                ROW_NUMBER() OVER (PARTITION BY steel_grade
                    ORDER BY COUNT(*) FILTER (WHERE judge = 1)::float
                             / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL), 0) DESC) AS rn
            FROM fact_heat_indicator
            GROUP BY heat_no, steel_grade, team
            HAVING COUNT(*) FILTER (WHERE judge IS NOT NULL) > 0
        ) t WHERE rn = 1
        ORDER BY score DESC LIMIT :limit
    """), {"limit": limit}).all()
    return [
        {"heat_no": r.heat_no, "steel_grade": r.steel_grade, "team": r.team,
         "judged": int(r.judged), "hit": int(r.hit),
         "score": float(r.score) if r.score is not None else 0}
        for r in rows
    ]


def heat_trace(db: Session, heat_no: str | None = None) -> dict:
    """熔炼号全流程追溯一张图（借鉴兴澄⑧）：各工序符合率 + 异常指标红色高亮。"""
    if not heat_no:
        heat_no = db.execute(text(
            "SELECT heat_no FROM fact_heat_indicator GROUP BY heat_no ORDER BY COUNT(*) DESC LIMIT 1"
        )).scalar()
    if not heat_no:
        return {"heat_no": None, "processes": [], "abnormal": []}
    heat = db.execute(text("SELECT * FROM fact_heat WHERE heat_no = :h"), {"h": heat_no}).first()
    procs = db.execute(text("""
        SELECT process,
            COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
            COUNT(*) FILTER (WHERE judge = 1) AS hit,
            ROUND(100.0 * COUNT(*) FILTER (WHERE judge = 1)
                  / NULLIF(COUNT(*) FILTER (WHERE judge IS NOT NULL), 0), 2) AS rate
        FROM fact_heat_indicator WHERE heat_no = :h GROUP BY process ORDER BY process
    """), {"h": heat_no}).all()
    abnormal = db.execute(text("""
        SELECT process, indicator_name, std_value, actual_value
        FROM fact_heat_indicator WHERE heat_no = :h AND judge = 0
        ORDER BY process
    """), {"h": heat_no}).all()
    return {
        "heat_no": heat_no,
        "steel_grade": heat.steel_grade if heat else None,
        "team": heat.team if heat else None,
        "equipment": heat.equipment if heat else None,
        "tap_time": str(heat.tap_time) if heat and heat.tap_time else None,
        "processes": [
            {"process": p.process, "judged": int(p.judged or 0), "hit": int(p.hit or 0),
             "rate": float(p.rate) if p.rate is not None else 0}
            for p in procs
        ],
        "abnormal": [
            {"process": a.process, "indicator": a.indicator_name,
             "std": a.std_value, "actual": a.actual_value}
            for a in abnormal
        ],
    }


def heating_temperature(db: Session) -> dict:
    """加热工艺各段温度 Min/Mean/Max（对标 demo S3）。"""
    r = db.execute(text("""
        SELECT
          ROUND((MIN(preheat_temp))::numeric,1) pre_min, ROUND((AVG(preheat_temp))::numeric,1) pre_avg, ROUND((MAX(preheat_temp))::numeric,1) pre_max,
          ROUND((MIN(heat_section_temp))::numeric,1) hs_min, ROUND((AVG(heat_section_temp))::numeric,1) hs_avg, ROUND((MAX(heat_section_temp))::numeric,1) hs_max,
          ROUND((MIN(soak_temp))::numeric,1) sk_min, ROUND((AVG(soak_temp))::numeric,1) sk_avg, ROUND((MAX(soak_temp))::numeric,1) sk_max,
          ROUND((MIN(out_temp))::numeric,1) out_min, ROUND((AVG(out_temp))::numeric,1) out_avg, ROUND((MAX(out_temp))::numeric,1) out_max
        FROM fact_heating WHERE out_temp IS NOT NULL
    """)).one()
    labels = ["预热段", "加热段", "均热段", "出炉"]
    return {
        "labels": labels,
        "min": [float(r.pre_min or 0), float(r.hs_min or 0), float(r.sk_min or 0), float(r.out_min or 0)],
        "avg": [float(r.pre_avg or 0), float(r.hs_avg or 0), float(r.sk_avg or 0), float(r.out_avg or 0)],
        "max": [float(r.pre_max or 0), float(r.hs_max or 0), float(r.sk_max or 0), float(r.out_max or 0)],
    }


def rolling_temperature_series(db: Session, limit: int = 60) -> dict:
    """轧制温度时序（对标 demo S4，抽样到 limit 点）。"""
    rows = db.execute(text("""
        SELECT roll_start, start_roll_temp, finish_temp, laying_temp
        FROM fact_rolling WHERE start_roll_temp IS NOT NULL
        ORDER BY roll_start LIMIT :limit
    """), {"limit": limit}).all()
    return {
        "times": [str(r.roll_start)[5:16] if r.roll_start else "" for r in rows],
        "start": [float(r.start_roll_temp or 0) for r in rows],
        "finish": [float(r.finish_temp or 0) for r in rows],
        "laying": [float(r.laying_temp or 0) for r in rows],
    }


def hit_rate_distribution(db: Session) -> dict:
    """A/B/C 命中率分布（对标 demo S7）。"""
    r = db.execute(text("""
        SELECT
          COUNT(*) FILTER (WHERE hit_rate_a >= 100) AS a_full, COUNT(*) FILTER (WHERE hit_rate_a < 100 AND hit_rate_a IS NOT NULL) AS a_miss,
          COUNT(*) FILTER (WHERE hit_rate_b >= 100) AS b_full, COUNT(*) FILTER (WHERE hit_rate_b < 100 AND hit_rate_b IS NOT NULL) AS b_miss,
          COUNT(*) FILTER (WHERE hit_rate_c >= 100) AS c_full, COUNT(*) FILTER (WHERE hit_rate_c < 100 AND hit_rate_c IS NOT NULL) AS c_miss
        FROM fact_rolling WHERE hit_rate_a IS NOT NULL
    """)).one()
    return {
        "labels": ["A级命中率", "B级命中率", "C级命中率"],
        "full": [int(r.a_full or 0), int(r.b_full or 0), int(r.c_full or 0)],
        "miss": [int(r.a_miss or 0), int(r.b_miss or 0), int(r.c_miss or 0)],
    }


def indicator_detail(db: Session, process: str, indicator: str, limit: int = 50) -> dict:
    """指标根因下钻：符合率 + 异常炉次明细 + 实绩分布 + 趋势。

    对应第二阶段场景D：从洞察识别的短板指标，下钻定位异常炉次与参数偏离。
    """
    # 1. 符合率
    stat = db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
               COUNT(*) FILTER (WHERE judge = 1) AS hit
        FROM fact_heat_indicator WHERE process = :p AND indicator_name = :n
    """), {"p": process, "n": indicator}).one()
    judged = int(stat.judged or 0)
    hit = int(stat.hit or 0)
    rate = round(100 * hit / judged, 2) if judged else 0

    # 2. 异常炉次（judge=0）
    abnormal = db.execute(text("""
        SELECT heat_no, steel_grade, team, std_value, actual_value, tap_time
        FROM fact_heat_indicator
        WHERE process = :p AND indicator_name = :n AND judge = 0
        ORDER BY tap_time DESC NULLS LAST LIMIT :limit
    """), {"p": process, "n": indicator, "limit": limit}).all()

    # 3. 实绩分布（数值型）
    dist = db.execute(text("""
        WITH nums AS (
            SELECT actual_value::numeric AS v FROM fact_heat_indicator
            WHERE process = :p AND indicator_name = :n
              AND actual_value ~ '^[0-9]+\\.?[0-9]*$'
        )
        SELECT MIN(v) min_v, MAX(v) max_v, ROUND(AVG(v), 2) avg_v, COUNT(*) n FROM nums
    """), {"p": process, "n": indicator}).one()

    # 4. 趋势时序（抽样100点）
    trend = db.execute(text("""
        SELECT tap_time, actual_value::numeric AS v
        FROM fact_heat_indicator
        WHERE process = :p AND indicator_name = :n
          AND actual_value ~ '^[0-9]+\\.?[0-9]*$' AND tap_time IS NOT NULL
        ORDER BY tap_time LIMIT 100
    """), {"p": process, "n": indicator}).all()

    return {
        "process": process,
        "indicator": indicator,
        "judged": judged,
        "hit": hit,
        "rate": rate,
        "abnormal": [
            {"heat_no": a.heat_no, "steel_grade": a.steel_grade, "team": a.team,
             "std": a.std_value, "actual": a.actual_value,
             "tap_time": str(a.tap_time)[:16] if a.tap_time else None}
            for a in abnormal
        ],
        "abnormal_count": len(abnormal),
        "distribution": {
            "min": float(dist.min_v) if dist.min_v is not None else None,
            "max": float(dist.max_v) if dist.max_v is not None else None,
            "avg": float(dist.avg_v) if dist.avg_v is not None else None,
            "n": int(dist.n or 0),
        },
        "trend": {
            "times": [str(t.tap_time)[5:16] if t.tap_time else "" for t in trend],
            "values": [float(t.v) for t in trend],
        },
    }


# 成分-性能相关性分析（对标 demo S5/S6）
_ELEMS = [("C", "C"), ("Si", "Si"), ("Mn", "Mn"), ("P", "P"), ("S", "S")]
_MECHS = [("屈服强度", "yield_strength"), ("抗拉强度", "tensile_strength"), ("断后伸长率", "elongation")]
ALLOWED_X = {"C", "Si", "Mn", "P", "S"}
ALLOWED_Y = {"yield_strength", "tensile_strength", "elongation"}


def correlation(db: Session) -> list[dict]:
    """成分-性能 Pearson 相关系数（按 |r| 排序，对标 demo S5）。"""
    pairs = []
    for en, ec in _ELEMS:
        for mn, mc in _MECHS:
            r = db.execute(text(f"""
                SELECT CORR(m.{mc}, c."{ec}") AS r
                FROM fact_inspect_mech m
                JOIN fact_inspect_chem c ON m.sample_lot_no = c.sample_lot_no
                WHERE m.{mc} IS NOT NULL AND c."{ec}" IS NOT NULL
            """)).scalar()
            if r is not None:
                pairs.append({"pair": f"{en}-{mn}", "r": round(float(r), 3)})
    pairs.sort(key=lambda x: abs(x["r"]), reverse=True)
    return pairs


def scatter(db: Session, x: str, y: str) -> dict:
    """成分-性能散点（对标 demo S6）。"""
    if x not in ALLOWED_X or y not in ALLOWED_Y:
        return {"points": [], "x": x, "y": y, "n": 0, "error": "invalid param"}
    rows = db.execute(text(f"""
        SELECT c."{x}" AS xv, m.{y} AS yv
        FROM fact_inspect_mech m
        JOIN fact_inspect_chem c ON m.sample_lot_no = c.sample_lot_no
        WHERE c."{x}" IS NOT NULL AND m.{y} IS NOT NULL
    """)).all()
    return {"points": [[float(r.xv), float(r.yv)] for r in rows], "x": x, "y": y, "n": len(rows)}


def dimension_stats(db: Session) -> dict:
    """尺寸检验统计（对标 demo S9）。"""
    r = db.execute(text("""
        SELECT COUNT(*) n,
          ROUND((AVG(diagonal1))::numeric, 2) d1_avg, ROUND((AVG(diagonal2))::numeric, 2) d2_avg,
          ROUND((MIN(diagonal1))::numeric, 2) d1_min, ROUND((MAX(diagonal1))::numeric, 2) d1_max,
          ROUND((AVG(diag_diff))::numeric, 3) diff_avg, ROUND((AVG(spec))::numeric, 1) spec_avg,
          COUNT(*) FILTER (WHERE dim_result = '合格') dim_pass
        FROM fact_inspect_dim
    """)).one()
    n = int(r.n or 0)
    judges = []
    for item, col, ok in [
        ("外形质量", "appearance", "合格"), ("表面质量", "surface", "合格"),
        ("包装质量", "packaging", "合格"), ("标识质量", "identification", "合格"),
        ("酸洗质量", "pickling", "合格"), ("冷镦质量", "cold_upsetting", "合格"),
        ("尺寸外形", "dim_result", "合格"), ("符合标准", "conform_std", "符合"),
    ]:
        row = db.execute(text(
            f"SELECT COUNT(*) FILTER (WHERE {col} = '{ok}') AS pass_cnt, COUNT(*) AS n "
            f"FROM fact_inspect_dim WHERE {col} IS NOT NULL"
        )).one()
        judges.append({"item": item, "pass": int(row.pass_cnt or 0), "n": int(row.n or 0)})
    return {
        "sample_count": n,
        "diagonal1": {"avg": float(r.d1_avg or 0), "min": float(r.d1_min or 0), "max": float(r.d1_max or 0)},
        "diagonal2": {"avg": float(r.d2_avg or 0)},
        "diag_diff": {"avg": float(r.diff_avg or 0)},
        "spec": float(r.spec_avg or 0),
        "dim_pass_rate": round(100 * (r.dim_pass or 0) / n, 1) if n else 0,
        "judges": judges,
    }


def mechanical_histogram(db: Session) -> dict:
    """力学性能分布直方图（对标 demo S1 屈强比分布）。"""
    out = {}
    for name, col in [("屈服强度", "yield_strength"), ("抗拉强度", "tensile_strength"), ("断后伸长率", "elongation")]:
        vals = [float(r[0]) for r in db.execute(text(f"SELECT {col} FROM fact_inspect_mech WHERE {col} IS NOT NULL")).all()]
        if not vals:
            out[name] = {"bins": [], "min": 0, "max": 0, "n": 0}
            continue
        lo, hi = min(vals), max(vals)
        step = (hi - lo) / 10 if hi > lo else 1
        bins = []
        for i in range(10):
            bl, bh = lo + i * step, lo + (i + 1) * step
            cnt = sum(1 for v in vals if bl <= v < (bh if i < 9 else hi + 0.001))
            bins.append({"start": round(bl, 1), "end": round(bh, 1), "count": cnt})
        out[name] = {"bins": bins, "min": round(lo, 1), "max": round(hi, 1), "n": len(vals)}
    return out


def chemical_stats(db: Session) -> list[dict]:
    """化学成分统计卡（均值/标准差/范围，对标 demo S2）。"""
    out = []
    for el in ["C", "Si", "Mn", "P", "S", "Cr", "Ni", "Cu", "Al", "Mo"]:
        r = db.execute(text(f"""
            SELECT ROUND((AVG("{el}"))::numeric, 4) avg, ROUND((STDDEV("{el}"))::numeric, 4) std,
                   ROUND((MIN("{el}"))::numeric, 4) min_v, ROUND((MAX("{el}"))::numeric, 4) max_v
            FROM fact_inspect_chem WHERE "{el}" IS NOT NULL
        """)).one()
        out.append({
            "element": el,
            "avg": float(r.avg or 0), "std": float(r.std or 0),
            "min": float(r.min_v or 0), "max": float(r.max_v or 0),
        })
    return out


def compliance_by_grade(db: Session, process: str, limit: int = 8) -> dict:
    """钢种×指标 合格率矩阵（对标 demo S6 钢种综合分析）。"""
    top = db.execute(text("""
        SELECT steel_grade, COUNT(DISTINCT heat_no) AS heats
        FROM fact_heat_indicator WHERE process = :p AND steel_grade IS NOT NULL
        GROUP BY steel_grade ORDER BY heats DESC LIMIT :limit
    """), {"p": process, "limit": limit}).all()
    grades = [r.steel_grade for r in top]
    matrix = {}
    for g in grades:
        rows = db.execute(text("""
            SELECT indicator_name,
              COUNT(*) FILTER (WHERE judge IS NOT NULL) AS judged,
              COUNT(*) FILTER (WHERE judge = 1) AS hit
            FROM fact_heat_indicator WHERE process = :p AND steel_grade = :g
            GROUP BY indicator_name
        """), {"p": process, "g": g}).all()
        matrix[g] = {r.indicator_name: round(100 * r.hit / r.judged, 1) if r.judged else 0 for r in rows}
    indicators = sorted({ind for m in matrix.values() for ind in m})
    return {"process": process, "grades": grades, "indicators": indicators, "matrix": matrix}
