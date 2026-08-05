"""ORM 模型包。导入所有模型以供 Alembic autogenerate 检测表结构。"""
from .ai_report import AiReport
from .dimension import (
    DimAlloy,
    DimIndicator,
    DimPrice,
    DimScrapType,
    DimSteelGrade,
)
from .fact import (
    FactHeat,
    FactHeatIndicator,
    FactHeatRelation,
    FactHeating,
    FactInspectChem,
    FactInspectDim,
    FactInspectMech,
    FactLossDetail,
    FactRolling,
    FactScrapRatio,
)

__all__ = [
    "AiReport",
    "DimAlloy",
    "DimIndicator",
    "DimPrice",
    "DimScrapType",
    "DimSteelGrade",
    "FactHeat",
    "FactHeatIndicator",
    "FactHeatRelation",
    "FactHeating",
    "FactInspectChem",
    "FactInspectDim",
    "FactInspectMech",
    "FactLossDetail",
    "FactRolling",
    "FactScrapRatio",
]
