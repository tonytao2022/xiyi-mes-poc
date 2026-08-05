"""LLM 上下文打包：把规则引擎产出物压缩为 LLM 可消费的 JSON 上下文。

设计原则（兮易 AI vs 非AI 边界）：
- 统计计算、标准对标、异常检测 → 确定性引擎（现有 *_ai.py），0% AI
- 本模块只负责「搬运」这些确定性结果给 LLM，不在此做任何推断
- 控制 token：只取高价值字段，content/evidence 截断
"""
import json
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _compact_findings(findings: list) -> list:
    """findings 精简：只保留 title/level/content/evidence/chain，content 截断 120 字。"""
    out = []
    for f in (findings or []):
        item = {
            "title": str(f.get("title", "")),
            "level": str(f.get("level", "")),
            "content": str(f.get("content", ""))[:120],
            "evidence": str(f.get("evidence", ""))[:80],
        }
        if f.get("chain"):
            item["chain"] = [str(c)[:60] for c in f["chain"]][:6]
        out.append(item)
    return out


def _safe_num(v, nd=1):
    try:
        f = float(v)
        return round(f, nd)
    except (TypeError, ValueError):
        return None


def build_root_cause_context(db: Session, domain: str = "comprehensive") -> dict:
    """打包跨域根因分析上下文（metrics + findings + chains）。

    domain: comprehensive（默认，融合质量/成本/效率）/ quality / cost / efficiency
    """
    # ---- 1. 复用现有规则引擎结果 ----
    from app.services import comprehensive, comprehensive_ai

    model = comprehensive.comprehensive_model(db, 100000)
    structure = model.get("structure", {})
    air = comprehensive_ai.comprehensive_ai_analysis(db)

    # 汇总所有 findings（含 chain）——跨域因果链是核心亮点
    all_findings = []
    for key, sub in air.items():
        if isinstance(sub, dict) and sub.get("findings"):
            all_findings.extend(sub["findings"])

    # 收集跨域因果链
    chains = []
    for f in all_findings:
        if f.get("chain"):
            chains.append(f["chain"])

    # ---- 2. 关键指标（跨域根因的量化基础） ----
    xm = air.get("overview", {}).get("metrics", {})  # 可能是 structure
    # overview 的 metrics 实际是 structure；guard
    if not isinstance(xm, dict) or "total" not in xm:
        xm = structure

    reblow_heats = _safe_num(xm.get("reblow_heats"))
    reblow_rate = _safe_num(xm.get("reblow_rate"))
    endpoint_hit = _safe_num(xm.get("endpoint_hit"))
    temp_rate = _safe_num(xm.get("temp_rate"))
    c_rate = _safe_num(xm.get("c_rate"))
    overdue_heats = _safe_num(xm.get("overdue_heats"))
    overdue_p95 = _safe_num(xm.get("overdue_p95"))

    metrics = {
        "total_heats": _safe_num(xm.get("heats")) or _safe_num(structure.get("heats")),
        "reblow_heats": reblow_heats,
        "reblow_rate": reblow_rate,                 # 补吹率%
        "endpoint_hit_rate": endpoint_hit,          # 终点命中率%（min温/碳）
        "endpoint_temp_rate": temp_rate,
        "endpoint_c_rate": c_rate,
        "overdue_heats": overdue_heats,
        "overdue_p95_min": overdue_p95,
        "overdue_min_total": _safe_num(xm.get("overdue_min")),
        "direct_cost_wan": _safe_num(structure.get("direct") / 1e4) if structure.get("direct") else None,
        "quality_loss_wan": _safe_num(structure.get("quality") / 1e4) if structure.get("quality") else None,
        "efficiency_loss_wan": _safe_num(structure.get("efficiency") / 1e4) if structure.get("efficiency") else None,
        "total_cost_wan": _safe_num(structure.get("total") / 1e4) if structure.get("total") else None,
        "direct_pct": _safe_num(structure.get("direct_pct")),
        "quality_loss_pct": _safe_num(structure.get("quality_pct")),
        "efficiency_loss_pct": _safe_num(structure.get("efficiency_pct")),
        "overall_compliance_rate": _safe_num(xm.get("overall_compliance_rate")),
        "alloy_compliance_rate": _safe_num(xm.get("alloy_compliance_rate")),
    }

    # 清洗 None 以便 JSON 序列化
    metrics = {k: v for k, v in metrics.items()}

    # ---- 3. findings 精简 ----
    findings_compact = _compact_findings(all_findings)
    # 数量控制：最多 18 条，优先保留 严重/警告
    severity_order = {"严重": 0, "警告": 1, "提示": 2, "亮点": 3}
    findings_compact.sort(
        key=lambda x: severity_order.get(x.get("level"), 9)
    )
    findings_compact = findings_compact[:18]

    ctx = {
        "date_range": "本期（全量样本）",
        "heats": metrics.get("total_heats") or 0,
        "metrics_json": json.dumps(metrics, ensure_ascii=False, default=str),
        "findings_json": json.dumps(findings_compact, ensure_ascii=False),
        "chains_json": json.dumps(chains[:8], ensure_ascii=False),
        "domain": domain,
    }
    return ctx
