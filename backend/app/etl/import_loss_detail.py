"""ETL：模拟损失明细落库 fact_loss_detail。

运行：docker compose exec backend python -m app.etl.import_loss_detail
幂等：导入前 TRUNCATE fact_loss_detail RESTART IDENTITY CASCADE。

复用 comprehensive 的 calc_heat_cost（确保口径与综合成本模型一致）。
损失项带 source 标注：estimated(系数估算) / formula(精确口径，如合金富裕 actual>std)。
"""
import json
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from app.database import engine
from app.services import comprehensive as comp
from app.services import cost_factors as cf

SNAPSHOT_DATE = "2025-07-13"  # 与 fact_scrap_ratio 快照对齐


def truncate(tables: list[str]):
    with engine.connect() as conn:
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))
        conn.commit()


def import_loss_detail():
    # 1. 取每炉聚合行（同 comprehensive._HEAT_SQL，不限量）
    heats = pd.read_sql(text(comp._HEAT_SQL), engine, params={"limit": 100000})

    # 2. P95 超时阈值 + 精确合金富裕口径
    durs = [float(d) for d in heats["avg_dur"].dropna().tolist()]
    overdue_threshold = comp._percentile(durs, 0.95) if durs else cf.get("std_duration")
    with engine.connect() as conn:
        surplus_map = comp.alloy_surplus_by_heat(conn)

    # 3. 逐炉算成本，展开为损失明细行
    rows = []
    now = datetime.now()
    for h in heats.itertuples(index=False):
        cost = comp.calc_heat_cost(h, overdue_threshold, surplus_map.get(h.heat_no))
        lb = cost["loss_breakdown"]
        raw = cost["_raw"]
        common = {
            "heat_no": h.heat_no, "steel_grade": h.steel_grade, "team": h.team,
            "equipment": h.equipment, "snapshot_date": SNAPSHOT_DATE, "created_at": now,
        }

        def add(category, name, amount, qty, unit, formula, params, source="estimated"):
            rows.append({**common, "loss_category": category, "loss_name": name,
                         "amount": round(float(amount), 2) if amount is not None else None,
                         "qty": qty, "unit": unit, "formula": formula,
                         "params": json.dumps(params, ensure_ascii=False), "source": source})

        # 质量损失
        add("quality", "defect_loss", lb["defect_loss"], raw["output"], "元",
            "output*defect_rate*ton_steel_cost*(1-residual_rate)",
            {"defect_rate": raw["defect_rate_val"], "output": raw["output"]})
        add("quality", "downgrade_loss", lb["downgrade_loss"], raw["output"], "元",
            "output*defect_rate*downgrade_loss_per_ton",
            {"defect_rate": raw["defect_rate_val"]})
        add("quality", "surplus_loss", lb["surplus_loss"], raw["alloy_cost"], "元",
            "Σ(actual-std_upper)*price" if lb["surplus_source"] == "formula"
            else "alloy_cost*(1-rate)*surplus_loss_factor",
            {"alloy_cost": raw["alloy_cost"], "rate": raw["rate"], "source": lb["surplus_source"]},
            source=lb["surplus_source"])
        add("quality", "reblow_loss", lb["reblow_loss"], int(getattr(h, "reblow", 0) or 0), "元",
            "reblow_count*reblow_cost", {"reblow_count": int(getattr(h, "reblow", 0) or 0)})
        # 效率损失
        add("efficiency", "energy_loss", lb["energy_loss"], raw["dur"], "元",
            "avg_dur*energy_per_min", {"dur": raw["dur"]})
        over_min = max(0, raw["dur"] - raw["overdue_threshold"])
        add("efficiency", "overdue_loss", lb["overdue_loss"], over_min, "元",
            "max(0,avg_dur-P95)*energy_per_min",
            {"dur": raw["dur"], "p95": raw["overdue_threshold"]})

    # 4. 落库
    truncate(["fact_loss_detail"])
    pd.DataFrame(rows).to_sql("fact_loss_detail", engine, if_exists="append",
                              index=False, method="multi", chunksize=2000)
    print(f"  -> fact_loss_detail {len(rows)} 行（{len(heats)} 炉 × 6 损失项），P95={overdue_threshold:.1f}min")
    # source 分布
    src = pd.DataFrame(rows).groupby("source")["amount"].agg(["count", "sum"])
    print(f"  source 分布:\n{src}")


if __name__ == "__main__":
    t0 = datetime.now()
    print("【损失明细】模拟计算落库 ...")
    import_loss_detail()
    print(f"\n✓ 完成，耗时 {(datetime.now() - t0).total_seconds():.1f}s")
