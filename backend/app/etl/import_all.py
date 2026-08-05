"""ETL：导入 3 份 Excel 到 PostgreSQL。

运行：docker compose exec backend python -m app.etl.import_all
幂等：每次导入前 TRUNCATE 对应表，可重复执行。
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.database import engine

DOCS = Path("/app/docs")
SCRAP_SNAPSHOT = "2025-07-13"

# 废钢 11 料型
SCRAP_TYPES = [
    "一类废钢", "普通压块", "剪料", "热饼", "冷饼",
    "渣钢", "生铁", "低镍生铁", "铸铁块", "耐候系列合金", "含铬钼合金",
]
# 化学元素 27 项（对应 FactInspectChem 列）
CHEM_ELEMENTS = [
    "C", "Si", "Mn", "P", "S", "Cu", "Ni", "Cr", "Mo", "V", "Nb", "Ti",
    "Al", "Als", "Alt", "Ca", "B", "W", "Pb", "Zn", "O", "N", "H",
    "As", "Sn", "Ceq", "Sb",
]


# --- 清洗工具 ---------------------------------------------------------------


def clean_str(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return None
    return s


def parse_judge(v):
    s = clean_str(v)
    if s is None:
        return None
    if s in ("1", "1.0", "True", "合格"):
        return 1
    if s in ("0", "0.0", "False", "不合格"):
        return 0
    return None


def to_dt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    t = pd.to_datetime(v, errors="coerce")
    return None if pd.isna(t) else t.to_pydatetime()


def truncate(tables: list[str]):
    with engine.connect() as conn:
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))
        conn.commit()


# --- 1. 炼钢工艺执行 ---------------------------------------------------------


def import_steelmaking():
    path = DOCS / "炼钢工艺执行.xlsx"
    sheets = ["转炉", "精炼", "真空", "板坯", "方坯", "合金"]
    indicator_rows: list[dict] = []
    heat_rows: dict[str, dict] = {}
    indicator_dict: dict[tuple, dict] = {}

    for sheet in sheets:
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        row0 = raw.iloc[0].ffill()  # 指标组名向前填充（合并单元格）
        data = raw.iloc[2:].reset_index(drop=True)
        is_alloy = sheet == "合金"
        n_cols = len(raw.columns)

        for _, r in data.iterrows():
            heat_no = clean_str(r[1])
            if not heat_no:
                continue
            if heat_no not in heat_rows:
                heat_rows[heat_no] = {
                    "heat_no": heat_no,
                    "tap_time": to_dt(r[0]),
                    "steel_grade": clean_str(r[2]),
                    "process_route": clean_str(r[3]),
                    "team": clean_str(r[4]),
                    "equipment": clean_str(r[5]),
                }
            for c in range(6, n_cols, 3):
                grp = clean_str(row0[c])
                if not grp:
                    continue
                indicator_rows.append({
                    "heat_no": heat_no,
                    "tap_time": to_dt(r[0]),
                    "steel_grade": clean_str(r[2]),
                    "process_route": clean_str(r[3]),
                    "team": clean_str(r[4]),
                    "equipment": clean_str(r[5]),
                    "process": sheet,
                    "indicator_name": grp,
                    "std_value": clean_str(r[c]),
                    "actual_value": clean_str(r[c + 1]),
                    "judge": parse_judge(r[c + 2]),
                })
                key = (sheet, grp)
                if key not in indicator_dict:
                    indicator_dict[key] = {
                        "process": sheet,
                        "name": grp,
                        "category": "alloy_input" if is_alloy else "process_param",
                        "unit": None,
                        "std_type": None,
                    }
        print(f"  {sheet}: 数据 {len(data)} 行")

    truncate(["fact_heat_indicator", "fact_heat", "dim_indicator"])
    pd.DataFrame(heat_rows.values()).to_sql("fact_heat", engine, if_exists="append", index=False)
    pd.DataFrame(indicator_dict.values()).to_sql("dim_indicator", engine, if_exists="append", index=False)
    pd.DataFrame(indicator_rows).to_sql(
        "fact_heat_indicator", engine, if_exists="append", index=False, chunksize=2000, method="multi"
    )
    print(f"  → fact_heat {len(heat_rows)} | fact_heat_indicator {len(indicator_rows)} | dim_indicator {len(indicator_dict)}")


# --- 2. 废钢料型 -------------------------------------------------------------


def import_scrap():
    path = DOCS / "废钢料型250713.xlsx"
    df = pd.read_excel(path, sheet_name=0)
    rows = []
    scrap_dim = [{"scrap_type": s, "recovery_rate": None, "impurity_note": None} for s in SCRAP_TYPES]

    for _, r in df.iterrows():
        grade = clean_str(r["钢种"])
        if not grade or grade == "合计":
            continue
        heat_count = r["实际重量"]  # 列0：炉数
        total_w = r["实际重量.1"]  # 列1：总吨数
        for i, st in enumerate(SCRAP_TYPES):
            w = r[f"{st}重量"]
            ratio = r[f"{st}重量.1"]
            if pd.isna(w) and pd.isna(ratio):
                continue
            rows.append({
                "steel_grade": grade,
                "scrap_type": st,
                "weight": None if pd.isna(w) else float(w),
                "ratio": None if pd.isna(ratio) else float(ratio),
                "heat_count": None if pd.isna(heat_count) else int(heat_count),
                "total_weight": None if pd.isna(total_w) else float(total_w),
                "snapshot_date": SCRAP_SNAPSHOT,
            })

    truncate(["fact_scrap_ratio", "dim_scrap_type"])
    pd.DataFrame(scrap_dim).to_sql("dim_scrap_type", engine, if_exists="append", index=False)
    pd.DataFrame(rows).to_sql("fact_scrap_ratio", engine, if_exists="append", index=False, method="multi")
    print(f"  → fact_scrap_ratio {len(rows)} (钢种 {df['钢种'].nunique() - 1}) | dim_scrap_type {len(scrap_dim)}")


# --- 3. SWRCH22A 轧钢段 ------------------------------------------------------


def import_swrch22a():
    path = DOCS / "SWRCH22A(1).xls"

    # (a) 力学性能及化学成分 -> 拆力学 + 化学
    df = pd.read_excel(path, sheet_name="力学性能及化学成分", engine="xlrd")
    df.columns = [str(c).strip() for c in df.columns]
    mech_rows, chem_rows, grade_rows = [], [], []

    def col(name):
        return df[name] if name in df.columns else pd.Series([None] * len(df))

    for _, r in df.iterrows():
        heat_no = clean_str(r.get("熔炼号"))
        sl = clean_str(r.get("试批号"))
        common = {"sample_lot_no": sl, "heat_no": heat_no}
        mech_rows.append({
            **common,
            "sample_no": clean_str(r.get("试样号")),
            "steel_grade": clean_str(r.get("牌号")),
            "yield_strength": _f(r.get("屈服强度")),
            "tensile_strength": _f(r.get("抗拉强度")),
            "elongation": _f(r.get("断后伸长率")),
            "yield_ratio": _f(r.get("屈强比")),
            "tensile_ratio": _f(r.get("强屈比")),
            "reduction_area": _f(r.get("断缩率")),
            "max_force_elong": _f(r.get("最大力总伸长率")),
            "result": clean_str(r.get("性能判定结果")),
        })
        chem = {**common}
        for el in CHEM_ELEMENTS:
            chem[el] = _f(r.get(el))
        chem_rows.append(chem)
        grade_rows.append({
            "steel_grade": clean_str(r.get("牌号")) or "",
            "brand": clean_str(r.get("牌号")),
            "standard": clean_str(r.get("标准")),
            "spec_code": clean_str(r.get("冶金规范码")),
        })

    # (b) 加热工艺
    dh = pd.read_excel(path, sheet_name="加热工艺", engine="xlrd")
    dh.columns = [str(c).strip() for c in dh.columns]
    heat_rows = []
    for _, r in dh.iterrows():
        heat_rows.append({
            "heat_no": clean_str(r.get("熔炼号")),
            "furnace_batch_no": clean_str(r.get("炉批号")),
            "material_no": clean_str(r.get("材料号")),
            "roll_plan_no": clean_str(r.get("轧制计划号")),
            "in_out_flag": clean_str(r.get("出入炉标记")),
            "material_len": _f(r.get("材料长度")),
            "in_weight": _f(r.get("入炉重")),
            "in_actual_temp": _f(r.get("实绩入炉温度")),
            "in_time": to_dt(r.get("入炉时刻")),
            "out_time": to_dt(r.get("出炉时刻")),
            "out_temp": _f(r.get("出炉温度")),
            "total_heat_time": _f(r.get("总加热时间")),
            "preheat_temp": _f(r.get("预热段温度")),
            "heat_section_temp": _f(r.get("加热段温度")),
            "soak_temp": _f(r.get("均热温度")),
            "smoke_temp": _f(r.get("换热器前烟气温度")),
            "exhaust_temp": _f(r.get("烟气外排温度")),
            "furnace_pressure": _f(r.get("炉膛压力")),
            "steam_pressure": _f(r.get("汽包压力")),
            "hot_air_temp": _f(r.get("热风温度")),
            "team": clean_str(r.get("入炉班组")),
            "shift": clean_str(r.get("入炉班次")),
        })

    # (c) 轧制工艺
    dr = pd.read_excel(path, sheet_name="轧制工艺", engine="xlrd")
    dr.columns = [str(c).strip() for c in dr.columns]
    roll_rows = []
    for _, r in dr.iterrows():
        roll_rows.append({
            "heat_no": clean_str(r.get("熔炼号")),
            "furnace_batch_no": clean_str(r.get("炉批号")),
            "material_no": clean_str(r.get("材料号")),
            "roll_plan_no": clean_str(r.get("轧制计划号")),
            "steel_grade": clean_str(r.get("牌号")),
            "roll_start": to_dt(r.get("轧制开始时刻")),
            "roll_end": to_dt(r.get("轧制结束时刻")),
            "roll_time": _f(r.get("轧制时间")),
            "roll_count": _f(r.get("轧制根数")),
            "roll_weight": _f(r.get("轧制重量")),
            "start_roll_temp": _f(r.get("开轧温度")),
            "shear2_temp": _f(r.get("2号剪温度")),
            "pre_finish_temp": _f(r.get("进精轧温度")),
            "reduce_temp": _f(r.get("进减径温度")),
            "finish_temp": _f(r.get("终轧温度")),
            "laying_temp": _f(r.get("吐丝温度")),
            "coolbed_temp": _f(r.get("上冷床温度")),
            "hit_rate_a": _f(r.get("A级命中率（%）")),
            "hit_rate_b": _f(r.get("B级命中率（%）")),
            "hit_rate_c": _f(r.get("C级命中率（%）")),
            "team": clean_str(r.get("轧制班组")),
            "shift": clean_str(r.get("轧制班次")),
        })

    # (d) 产品尺寸
    dd = pd.read_excel(path, sheet_name="产品尺寸", engine="xlrd")
    dd.columns = [str(c).strip() for c in dd.columns]
    dim_rows = []
    for _, r in dd.iterrows():
        dim_rows.append({
            "sample_lot_no": clean_str(r.get("试批号")),
            "heat_no": clean_str(r.get("熔炼号")),
            "furnace_batch_no": clean_str(r.get("炉批号")),
            "spec": _f(r.get("规格")),
            "diagonal1": _f(r.get("内径对角线1(mm)")),
            "diagonal2": _f(r.get("内径对角线2(mm)")),
            "diag_diff": _f(r.get("对角线差值")),
            "curvature_per_m": _f(r.get("每米弯曲度(mm)")),
            "total_curvature": _f(r.get("总弯曲度(mm)")),
            "dim_result": clean_str(r.get("尺寸外形抽查结果")),
            "appearance": clean_str(r.get("外形质量")),
            "surface": clean_str(r.get("表面质量")),
            "packaging": clean_str(r.get("包装质量")),
            "identification": clean_str(r.get("标识质量")),
            "pickling": clean_str(r.get("酸洗质量")),
            "cold_upsetting": clean_str(r.get("冷镦质量")),
            "conform_std": clean_str(r.get("是否符合标准")),
        })

    # (e) 追溯关系
    drel = pd.read_excel(path, sheet_name="熔炼号炉批号试批号的关系", engine="xlrd")
    rel_rows = [{
        "heat_no": clean_str(r["熔炼号"]),
        "furnace_batch_no": clean_str(r.get("炉批号")),
        "sample_lot_no": clean_str(r.get("试批号")),
    } for _, r in drel.iterrows()]

    # 钢种维度去重
    grade_seen = {}
    for g in grade_rows:
        if g["steel_grade"] and g["steel_grade"] not in grade_seen:
            grade_seen[g["steel_grade"]] = g

    truncate([
        "fact_inspect_mech", "fact_inspect_chem", "fact_inspect_dim",
        "fact_heating", "fact_rolling", "fact_heat_relation", "dim_steel_grade",
    ])
    pd.DataFrame(grade_seen.values()).to_sql("dim_steel_grade", engine, if_exists="append", index=False)
    pd.DataFrame(mech_rows).to_sql("fact_inspect_mech", engine, if_exists="append", index=False, method="multi")
    pd.DataFrame(chem_rows).to_sql("fact_inspect_chem", engine, if_exists="append", index=False, method="multi")
    pd.DataFrame(heat_rows).to_sql("fact_heating", engine, if_exists="append", index=False, method="multi")
    pd.DataFrame(roll_rows).to_sql("fact_rolling", engine, if_exists="append", index=False, method="multi")
    pd.DataFrame(dim_rows).to_sql("fact_inspect_dim", engine, if_exists="append", index=False, method="multi")
    pd.DataFrame(rel_rows).to_sql("fact_heat_relation", engine, if_exists="append", index=False, method="multi")
    print(f"  → 力学{len(mech_rows)} 化学{len(chem_rows)} 加热{len(heat_rows)} 轧制{len(roll_rows)} 尺寸{len(dim_rows)} 追溯{len(rel_rows)}")


def _f(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    t0 = datetime.now()
    print("【1/4】炼钢工艺执行 ...")
    import_steelmaking()
    print("【2/4】废钢料型 ...")
    import_scrap()
    print("【3/4】SWRCH22A 轧钢段 ...")
    import_swrch22a()
    print("【4/4】综合损失明细（派生计算） ...")
    from app.etl.import_loss_detail import import_loss_detail
    import_loss_detail()
    print(f"\n✓ 导入完成，耗时 {(datetime.now() - t0).total_seconds():.1f}s")
