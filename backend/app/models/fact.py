"""事实表模型。核心：fact_heat_indicator 工艺指标长表(EAV)。"""
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class FactHeat(Base):
    """炉次身份：熔炼号为主键，来自炼钢 6 个 sheet 前 6 列去重。"""

    __tablename__ = "fact_heat"

    heat_no: Mapped[str] = mapped_column(String(32), primary_key=True)
    tap_time: Mapped[datetime | None] = mapped_column(DateTime)  # 出钢时刻
    steel_grade: Mapped[str | None] = mapped_column(String(64))  # 钢种
    process_route: Mapped[str | None] = mapped_column(String(16))  # 工艺路径 BALC/BARC...
    team: Mapped[str | None] = mapped_column(String(8))  # 班组 A/B/C/D
    equipment: Mapped[str | None] = mapped_column(String(8))  # 设备号


class FactHeatIndicator(Base):
    """★ 工艺指标长表(EAV)：覆盖转炉/精炼/真空/板坯/方坯/合金 全部三元组。

    每行 = 一炉某工序某指标的标准/实绩/判断。
    judge: 1=合格, 0=不合格, NULL=无判定。
    """

    __tablename__ = "fact_heat_indicator"
    __table_args__ = (UniqueConstraint("heat_no", "process", "indicator_name", name="uq_indicator"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    heat_no: Mapped[str] = mapped_column(String(32), index=True)
    tap_time: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    steel_grade: Mapped[str | None] = mapped_column(String(64), index=True)
    process_route: Mapped[str | None] = mapped_column(String(16))
    team: Mapped[str | None] = mapped_column(String(8))
    equipment: Mapped[str | None] = mapped_column(String(8))
    process: Mapped[str] = mapped_column(String(16), index=True)  # 转炉/精炼/...
    indicator_name: Mapped[str] = mapped_column(String(64), index=True)
    std_value: Mapped[str | None] = mapped_column(Text)  # 标准（区间/枚举/无要求用文本）
    actual_value: Mapped[str | None] = mapped_column(Text)  # 实绩（数值或文本）
    judge: Mapped[int | None] = mapped_column(SmallInteger, index=True)  # 1/0/null


class FactScrapRatio(Base):
    """钢种级废钢配比：废钢料型是钢种汇总非炉次级。snapshot_date=数据快照日。"""

    __tablename__ = "fact_scrap_ratio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    steel_grade: Mapped[str] = mapped_column(String(64), index=True)
    scrap_type: Mapped[str] = mapped_column(String(32), index=True)  # 一类废钢/普通压块...
    weight: Mapped[float | None] = mapped_column(Float)  # 重量(吨)
    ratio: Mapped[float | None] = mapped_column(Float)  # 占比
    heat_count: Mapped[int | None] = mapped_column(Integer)  # 该钢种炉数
    total_weight: Mapped[float | None] = mapped_column(Float)  # 该钢种总吨数
    snapshot_date: Mapped[str | None] = mapped_column(String(16))  # 如 2025-07-13


class FactHeatRelation(Base):
    """熔炼号-炉批号-试批号 追溯关系（三级键链）。来源：SWRCH22A sheet5。"""

    __tablename__ = "fact_heat_relation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    heat_no: Mapped[str] = mapped_column(String(32), index=True)
    furnace_batch_no: Mapped[str | None] = mapped_column(String(32), index=True)  # 炉批号
    sample_lot_no: Mapped[str | None] = mapped_column(String(32), index=True)  # 试批号


# --- SWRCH22A 轧钢段 ----------------------------------------------------------


class FactHeating(Base):
    """加热工艺实绩（SWRCH22A）。"""

    __tablename__ = "fact_heating"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    heat_no: Mapped[str | None] = mapped_column(String(32), index=True)
    furnace_batch_no: Mapped[str | None] = mapped_column(String(32), index=True)
    material_no: Mapped[str | None] = mapped_column(String(32))  # 材料号
    roll_plan_no: Mapped[str | None] = mapped_column(String(32))  # 轧制计划号
    in_out_flag: Mapped[str | None] = mapped_column(String(8))  # 入炉/出炉
    material_len: Mapped[float | None] = mapped_column(Float)  # 材料长度
    in_weight: Mapped[float | None] = mapped_column(Float)  # 入炉重
    in_actual_temp: Mapped[float | None] = mapped_column(Float)  # 实绩入炉温度
    in_time: Mapped[datetime | None] = mapped_column(DateTime)  # 入炉时刻
    out_time: Mapped[datetime | None] = mapped_column(DateTime)  # 出炉时刻
    out_temp: Mapped[float | None] = mapped_column(Float)  # 出炉温度
    total_heat_time: Mapped[float | None] = mapped_column(Float)  # 总加热时间
    preheat_temp: Mapped[float | None] = mapped_column(Float)  # 预热段温度
    heat_section_temp: Mapped[float | None] = mapped_column(Float)  # 加热段温度
    soak_temp: Mapped[float | None] = mapped_column(Float)  # 均热温度
    smoke_temp: Mapped[float | None] = mapped_column(Float)  # 换热器前烟气温度
    exhaust_temp: Mapped[float | None] = mapped_column(Float)  # 烟气外排温度
    furnace_pressure: Mapped[float | None] = mapped_column(Float)  # 炉膛压力
    steam_pressure: Mapped[float | None] = mapped_column(Float)  # 汽包压力
    hot_air_temp: Mapped[float | None] = mapped_column(Float)  # 热风温度
    team: Mapped[str | None] = mapped_column(String(8))  # 班组
    shift: Mapped[str | None] = mapped_column(String(8))  # 班次


class FactRolling(Base):
    """轧制工艺实绩（SWRCH22A）。"""

    __tablename__ = "fact_rolling"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    heat_no: Mapped[str | None] = mapped_column(String(32), index=True)
    furnace_batch_no: Mapped[str | None] = mapped_column(String(32), index=True)
    material_no: Mapped[str | None] = mapped_column(String(32))
    roll_plan_no: Mapped[str | None] = mapped_column(String(32))
    steel_grade: Mapped[str | None] = mapped_column(String(64))
    roll_start: Mapped[datetime | None] = mapped_column(DateTime)
    roll_end: Mapped[datetime | None] = mapped_column(DateTime)
    roll_time: Mapped[float | None] = mapped_column(Float)  # 轧制时间
    roll_count: Mapped[float | None] = mapped_column(Float)  # 轧制根数
    roll_weight: Mapped[float | None] = mapped_column(Float)  # 轧制重量
    start_roll_temp: Mapped[float | None] = mapped_column(Float)  # 开轧温度
    shear2_temp: Mapped[float | None] = mapped_column(Float)  # 2号剪温度
    pre_finish_temp: Mapped[float | None] = mapped_column(Float)  # 进精轧温度
    reduce_temp: Mapped[float | None] = mapped_column(Float)  # 进减径温度
    finish_temp: Mapped[float | None] = mapped_column(Float)  # 终轧温度
    laying_temp: Mapped[float | None] = mapped_column(Float)  # 吐丝温度
    coolbed_temp: Mapped[float | None] = mapped_column(Float)  # 上冷床温度
    hit_rate_a: Mapped[float | None] = mapped_column(Float)  # A级命中率
    hit_rate_b: Mapped[float | None] = mapped_column(Float)
    hit_rate_c: Mapped[float | None] = mapped_column(Float)
    team: Mapped[str | None] = mapped_column(String(8))
    shift: Mapped[str | None] = mapped_column(String(8))


class FactInspectMech(Base):
    """力学性能检验（SWRCH22A 力学部分）。"""

    __tablename__ = "fact_inspect_mech"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_lot_no: Mapped[str | None] = mapped_column(String(32), index=True)  # 试批号
    sample_no: Mapped[str | None] = mapped_column(String(16))  # 试样号
    heat_no: Mapped[str | None] = mapped_column(String(32), index=True)
    steel_grade: Mapped[str | None] = mapped_column(String(64))
    yield_strength: Mapped[float | None] = mapped_column(Float)  # 屈服强度
    tensile_strength: Mapped[float | None] = mapped_column(Float)  # 抗拉强度
    elongation: Mapped[float | None] = mapped_column(Float)  # 断后伸长率
    yield_ratio: Mapped[float | None] = mapped_column(Float)  # 屈强比
    tensile_ratio: Mapped[float | None] = mapped_column(Float)  # 强屈比
    reduction_area: Mapped[float | None] = mapped_column(Float)  # 断缩率
    max_force_elong: Mapped[float | None] = mapped_column(Float)  # 最大力总伸长率
    result: Mapped[str | None] = mapped_column(String(16))  # 性能判定结果


class FactInspectChem(Base):
    """化学成分检验（SWRCH22A 化学部分，28 元素宽表）。"""

    __tablename__ = "fact_inspect_chem"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_lot_no: Mapped[str | None] = mapped_column(String(32), index=True)
    heat_no: Mapped[str | None] = mapped_column(String(32), index=True)
    C: Mapped[float | None] = mapped_column(Float)
    Si: Mapped[float | None] = mapped_column(Float)
    Mn: Mapped[float | None] = mapped_column(Float)
    P: Mapped[float | None] = mapped_column(Float)
    S: Mapped[float | None] = mapped_column(Float)
    Cu: Mapped[float | None] = mapped_column(Float)
    Ni: Mapped[float | None] = mapped_column(Float)
    Cr: Mapped[float | None] = mapped_column(Float)
    Mo: Mapped[float | None] = mapped_column(Float)
    V: Mapped[float | None] = mapped_column(Float)
    Nb: Mapped[float | None] = mapped_column(Float)
    Ti: Mapped[float | None] = mapped_column(Float)
    Al: Mapped[float | None] = mapped_column(Float)
    Als: Mapped[float | None] = mapped_column(Float)
    Alt: Mapped[float | None] = mapped_column(Float)
    Ca: Mapped[float | None] = mapped_column(Float)
    B: Mapped[float | None] = mapped_column(Float)
    W: Mapped[float | None] = mapped_column(Float)
    Pb: Mapped[float | None] = mapped_column(Float)
    Zn: Mapped[float | None] = mapped_column(Float)
    O: Mapped[float | None] = mapped_column(Float)
    N: Mapped[float | None] = mapped_column(Float)
    H: Mapped[float | None] = mapped_column(Float)
    As: Mapped[float | None] = mapped_column(Float)
    Sn: Mapped[float | None] = mapped_column(Float)
    Ceq: Mapped[float | None] = mapped_column(Float)
    Sb: Mapped[float | None] = mapped_column(Float)


class FactInspectDim(Base):
    """产品尺寸检验（SWRCH22A 尺寸部分）。"""

    __tablename__ = "fact_inspect_dim"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_lot_no: Mapped[str | None] = mapped_column(String(32), index=True)
    heat_no: Mapped[str | None] = mapped_column(String(32), index=True)
    furnace_batch_no: Mapped[str | None] = mapped_column(String(32))
    spec: Mapped[float | None] = mapped_column(Float)  # 规格
    diagonal1: Mapped[float | None] = mapped_column(Float)  # 内径对角线1
    diagonal2: Mapped[float | None] = mapped_column(Float)  # 内径对角线2
    diag_diff: Mapped[float | None] = mapped_column(Float)  # 对角线差值
    curvature_per_m: Mapped[float | None] = mapped_column(Float)  # 每米弯曲度
    total_curvature: Mapped[float | None] = mapped_column(Float)  # 总弯曲度
    dim_result: Mapped[str | None] = mapped_column(String(16))  # 尺寸外形抽查结果
    appearance: Mapped[str | None] = mapped_column(String(16))  # 外形质量
    surface: Mapped[str | None] = mapped_column(String(16))  # 表面质量
    packaging: Mapped[str | None] = mapped_column(String(16))  # 包装质量
    identification: Mapped[str | None] = mapped_column(String(16))  # 标识质量
    pickling: Mapped[str | None] = mapped_column(String(16))  # 酸洗质量
    cold_upsetting: Mapped[str | None] = mapped_column(String(16))  # 冷镦质量
    conform_std: Mapped[str | None] = mapped_column(String(16))  # 是否符合标准


class FactLossDetail(Base):
    """★ 模拟损失明细长表(EAV)：每行 = 一炉某损失项的金额/系数/来源。

    覆盖质量损失(defect/downgrade/surplus/reblow)与效率损失(energy/overdue)。
    loss_category: quality / efficiency
    source: estimated(系数估算) / formula(精确公式口径)
    amount: 损失金额(元)。formula/params 落库留痕，便于审计与置信度区分。
    """

    __tablename__ = "fact_loss_detail"
    __table_args__ = (UniqueConstraint("heat_no", "loss_name", name="uq_loss_detail"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    heat_no: Mapped[str | None] = mapped_column(String(32), index=True)
    steel_grade: Mapped[str | None] = mapped_column(String(64), index=True)
    team: Mapped[str | None] = mapped_column(String(8))
    equipment: Mapped[str | None] = mapped_column(String(8))
    loss_category: Mapped[str] = mapped_column(String(16), index=True)  # quality/efficiency
    loss_name: Mapped[str] = mapped_column(String(64), index=True)  # defect_loss/reblow_loss/...
    amount: Mapped[float | None] = mapped_column(Float)  # 损失金额(元)
    qty: Mapped[float | None] = mapped_column(Float)  # 触发量(吨/次/分钟)
    unit: Mapped[str | None] = mapped_column(String(32))
    formula: Mapped[str | None] = mapped_column(Text)  # 如 "output*defect_rate*3000*(1-0.7)"
    params: Mapped[str | None] = mapped_column(Text)  # JSON 串：{"defect_rate":0.02,...}
    source: Mapped[str] = mapped_column(String(32))  # estimated/formula（不用smm/internal，语义不同）
    snapshot_date: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
