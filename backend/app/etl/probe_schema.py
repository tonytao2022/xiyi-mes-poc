"""探测 Excel 数据结构，为 ORM 建表提供精确字段清单。

运行：docker compose exec backend python -m app.etl.probe_schema
"""
from pathlib import Path

import pandas as pd

DOCS = Path("/app/docs")


def probe_simple(path: Path, engine: str | None = None) -> None:
    """单行表头 sheet：输出列名 + 样本。"""
    xls = pd.ExcelFile(path, engine=engine)
    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, engine=engine)
        print(f"\n## [{path.name}] sheet='{sheet}'  shape={df.shape}")
        print("列名:")
        for i, c in enumerate(df.columns):
            s1 = df[c].iloc[0] if len(df) else ""
            print(f"  [{i:2d}] {c}  | 样本: {s1}")


def probe_steelmaking(path: Path) -> None:
    """炼钢工艺执行：汇总单行 + 明细双行表头解析。"""
    # 汇总 sheet 分块布局，看前若干行
    df_sum = pd.read_excel(path, sheet_name="汇总", header=None)
    print(f"\n## [{path.name}] sheet='汇总'  shape={df_sum.shape}")
    for i in range(min(10, len(df_sum))):
        vals = [str(v) for v in df_sum.iloc[i].dropna().values if str(v) != "nan"]
        print(f"  行{i}: {vals[:14]}")

    detail_sheets = ["转炉", "精炼", "真空", "板坯", "方坯", "合金"]
    for sheet in detail_sheets:
        raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=3)
        n_cols = len(raw.columns)
        row0, row1 = raw.iloc[0], raw.iloc[1]
        # 身份列（前6）
        id_cols = [str(row0[c]) if pd.notna(row0[c]) else "" for c in range(6)]
        # 指标组名（去重保序）
        groups: list[str] = []
        for c in range(6, n_cols):
            g = row0[c]
            if pd.notna(g) and str(g).strip():
                gn = str(g).strip()
                if gn not in groups:
                    groups.append(gn)
        # 子列模式确认
        subs = [str(row1[c]) if pd.notna(row1[c]) else "" for c in range(6, min(9, n_cols))]
        df_full = pd.read_excel(path, sheet_name=sheet, header=None)
        print(f"\n## [{path.name}] sheet='{sheet}'  数据行={len(df_full)} 列={n_cols}")
        print(f"  身份列(前6): {id_cols}")
        print(f"  子列模式(6-8): {subs}")
        print(f"  指标组数={len(groups)}")
        print(f"  指标组名: {groups}")


if __name__ == "__main__":
    print("=" * 70)
    print("【SWRCH22A(1).xls】")
    probe_simple(DOCS / "SWRCH22A(1).xls", engine="xlrd")

    print("\n" + "=" * 70)
    print("【废钢料型250713.xlsx】")
    probe_simple(DOCS / "废钢料型250713.xlsx", engine="openpyxl")

    print("\n" + "=" * 70)
    print("【炼钢工艺执行.xlsx】")
    probe_steelmaking(DOCS / "炼钢工艺执行.xlsx")
