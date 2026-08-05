"""维度表模型。"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class DimSteelGrade(Base):
    """钢种/牌号维度。来源：炼钢钢种列 + SWRCH22A 牌号/标准/规范码。"""

    __tablename__ = "dim_steel_grade"

    steel_grade: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand: Mapped[str | None] = mapped_column(String(64))  # 牌号（如 SWRCH22A）
    standard: Mapped[str | None] = mapped_column(String(128))  # 标准（如 JIS G 3507-1:2021）
    spec_code: Mapped[str | None] = mapped_column(String(32))  # 冶金规范码（如 D00024）


class DimScrapType(Base):
    """废钢料型维度（11 种）。来源：废钢料型表头。"""

    __tablename__ = "dim_scrap_type"

    scrap_type: Mapped[str] = mapped_column(String(32), primary_key=True)  # 一类废钢/普通压块...
    recovery_rate: Mapped[float | None] = mapped_column(Float)  # 收得率（估算）
    impurity_note: Mapped[str | None] = mapped_column(Text)  # 杂质说明（估算）


class DimAlloy(Base):
    """合金维度（23 种）。来源：炼钢合金 sheet 指标组。"""

    __tablename__ = "dim_alloy"

    alloy_name: Mapped[str] = mapped_column(String(32), primary_key=True)  # 硅锰合金/硅铁...
    main_element: Mapped[str | None] = mapped_column(String(32))  # 主元素
    recovery_rate: Mapped[float | None] = mapped_column(Float)  # 收得率（估算）


class DimIndicator(Base):
    """工艺指标字典（长表配套）。覆盖炼钢 6 个 sheet 的全部指标组 + 合金。

    category 区分：process_param(工艺参数) / alloy_input(合金投入)
    """

    __tablename__ = "dim_indicator"

    indicator_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    process: Mapped[str] = mapped_column(String(16))  # 转炉/精炼/真空/板坯/方坯/合金
    name: Mapped[str] = mapped_column(String(64))  # 指标/合金名
    category: Mapped[str] = mapped_column(String(16))  # process_param / alloy_input
    unit: Mapped[str | None] = mapped_column(String(32))
    std_type: Mapped[str | None] = mapped_column(String(32))  # 区间/枚举/无要求


class DimPrice(Base):
    """价格维度：废钢/合金/能源市场价。来源：SMM 爬取 + 估算值。"""

    __tablename__ = "dim_price"

    price_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(16))  # scrap / alloy / energy
    item_code: Mapped[str | None] = mapped_column(String(64))
    item_name: Mapped[str] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(32))
    price_date: Mapped[date] = mapped_column(Date)
    unit_price: Mapped[float | None] = mapped_column(Float)  # 均价
    price_min: Mapped[float | None] = mapped_column(Float)  # 区间下限
    price_max: Mapped[float | None] = mapped_column(Float)  # 区间上限
    change_pct: Mapped[float | None] = mapped_column(Float)  # 涨跌
    source: Mapped[str] = mapped_column(String(32))  # smm / estimated / internal
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
