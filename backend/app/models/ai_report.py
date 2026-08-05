"""AI 报告表模型（LLM 推理层产物持久化）。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AiReport(Base):
    """AI 智体报告：根因分析 + 三级建议 + 7段式 HTML。

    created_at 倒序查询；llm_used 标记本次是否走了 LLM。
    """

    __tablename__ = "ai_report"
    __table_args__ = (
        Index("idx_ai_report_domain_time", "domain", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)  # comprehensive/quality/cost/efficiency
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    period: Mapped[str | None] = mapped_column(String(64))           # 数据周期
    meta_json: Mapped[dict | None] = mapped_column(JSONB)            # KPI/样本量等
    llm_json: Mapped[dict | None] = mapped_column(JSONB)            # 根因分析+三级建议（LLM输出）
    html: Mapped[str | None] = mapped_column(Text)                  # 完整报告 HTML
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)  # 本次是否走了 LLM
    model_used: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
