"""LLM 推理层编排：根因分析 + 三级整改建议（带降级兜底）。

数字铁律：LLM 输出不得编造数字，所有数值取自注入上下文 (Prompt 强制约束)。
降级兜底：LLM_API_KEY 为空 / 超时 / 失败 → 自动回退规则模式（返回规则引擎 findings），前端不报错。
"""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.services.llm_client import LLMClient, LLMError
from app.services import llm_context

logger = logging.getLogger(__name__)


# ---------------- Prompt（须含 "json" 关键词，DeepSeek 强制要求） ----------------

SYSTEM_ROOT_CAUSE = """你是钢铁行业工艺质量-成本-效率协同分析专家，服务于炼钢厂管理层。
你的任务：基于给定的量化数据做跨域根因分析（Root Cause Analysis）。

严格规则（务必遵守）：
1. 所有数字必须来自给定的 metrics/findings，不得编造或推测任何数值。
2. 对每个显著异常（符合率<90%、损失占比异常、命中率<80%等），给出最多3个根因假设。
3. 每个根因必须包含：root_cause(根因描述)、domain(质量/成本/效率/设备/数据)、
   confidence(置信度0-1，基于证据强度)、evidence(引用给定数据中的具体数值作为证据)。
4. 根因之间要体现跨域关联（如：终点命中率低→补吹→效率损失+质量损失）。
5. 若数据不足无法判断，明确写"证据不足"，不要臆测。
6. 输出严格 JSON，schema：
{
  "summary": "50字内综合研判",
  "risk_level": "高|中|低",
  "root_causes": [
    {"rank":1, "root_cause":"...", "domain":"质量", "confidence":0.92,
     "evidence":["终点温度符合率41.2%（119判定49命中）"], "impact":"货币化或量化影响描述"}
  ],
  "cross_domain_links": ["因果链描述1", "因果链描述2"]
}
请务必输出合法 JSON。"""

USER_ROOT_CAUSE_TEMPLATE = """以下是本周期（{date_range}，共{heats}炉）炼钢全流程的量化分析结果，请做跨域根因分析：

【关键指标】{metrics_json}

【规则引擎发现】{findings_json}

【跨域因果链】{chains_json}

请按系统规则输出 JSON 格式的根因分析结果。"""

SYSTEM_SUGGESTION = """你是钢铁企业降本增效顾问。基于给定的根因分析结果，输出三级整改建议。

严格规则：
1. 所有建议必须对应给定的 root_causes，不得脱离根因凭空建议。
2. 按紧急程度分三级：
   - urgent(紧急)：24小时内必须处理（停线风险/安全事故/批量废品）
   - short(短期)：1-2周内实施（工艺参数调整/设备维修）
   - long(长期)：月度/季度改进（管理机制/数字化改造/标准修订）
3. 每条建议包含：action(动作)、target(对象/工序)、expected_gain(预期收益，
   若给定数据含货币化损失则可写"预计降低X万元"，否则写定性描述并标注"估算")、
   effort(投入，人天/资金量级)、owner(建议责任角色：工艺/设备/生产/质量/信息化)。
4. 所有数字必须源自给定的 root_causes，不得编造。
5. 输出严格 JSON：
{"recommendations":[
  {"level":"urgent","action":"...","target":"...","expected_gain":"...","effort":"...","owner":"..."}
]}
请务必输出合法 JSON。"""

USER_SUGGESTION_TEMPLATE = """以下是跨域根因分析结果，请生成三级整改建议：

{root_causes_json}

请按系统规则输出 JSON 格式的三级整改建议。"""


# ---------------- 降级兜底 ----------------

def _fallback_rule_result(ctx: dict) -> dict:
    """LLM 不可用时的降级结果：返回规则引擎 findings 摘要，保证演示不中断。"""
    try:
        findings = json.loads(ctx.get("findings_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        findings = []
    root_causes = []
    for f in findings[:6]:
        root_causes.append({
            "rank": len(root_causes) + 1,
            "root_cause": f.get("content") or f.get("title", ""),
            "domain": "综合",
            "confidence": 0.6,
            "evidence": [f.get("evidence", "")] if f.get("evidence") else [f.get("title", "")],
            "impact": "规则引擎判定，非 LLM 生成",
        })
    return {
        "summary": "LLM 不可用，已降级为规则模式：以下为规则引擎发现摘要。",
        "risk_level": "中",
        "root_causes": root_causes,
        "cross_domain_links": [],
        "_meta": {"llm": False, "note": "LLM不可用，已降级为规则模式", "ts": datetime.now().isoformat()},
    }


def _fallback_suggestions(root_causes: list) -> dict:
    """LLM 不可用时的三级建议降级。"""
    recs = []
    for rc in root_causes[:4]:
        recs.append({
            "level": "short",
            "action": f"针对「{rc.get('root_cause', '')}」开展专项分析并制定整改措施",
            "target": rc.get("domain", "综合"),
            "expected_gain": "待量化（规则降级模式，估算）",
            "effort": "2-3人天",
            "owner": "工艺",
        })
    return {"recommendations": recs}


# ---------------- 主编排 ----------------

def analyze_root_causes(db: Session, domain: str = "comprehensive") -> dict:
    """LLM 根因分析（带降级）。"""
    ctx = llm_context.build_root_cause_context(db, domain)
    client = LLMClient()
    if not client.enabled:
        logger.info("LLM 未配置，使用规则降级模式")
        return _fallback_rule_result(ctx)

    try:
        result = client.chat_json(
            SYSTEM_ROOT_CAUSE,
            USER_ROOT_CAUSE_TEMPLATE.format(**ctx),
        )
        if not isinstance(result, dict):
            raise LLMError("根因分析返回非对象")
        result["_meta"] = {"llm": True, "model": client.model, "ts": datetime.now().isoformat()}
        return result
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 根因分析失败，降级为规则模式: %s", e)
        return _fallback_rule_result(ctx)


def generate_suggestions(root_cause_result: dict) -> dict:
    """三级整改建议（基于根因分析结果）。LLM 失败降级为规则模板。"""
    client = LLMClient()
    if not client.enabled:
        return _fallback_suggestions(root_cause_result.get("root_causes", []))
    try:
        rc_json = json.dumps(root_cause_result.get("root_causes", []), ensure_ascii=False, default=str)
        result = client.chat_json(
            SYSTEM_SUGGESTION,
            USER_SUGGESTION_TEMPLATE.format(root_causes_json=rc_json),
        )
        if not isinstance(result, dict) or not isinstance(result.get("recommendations"), list):
            raise LLMError("三级建议返回结构异常")
        return result
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 三级建议失败，降级为规则模板: %s", e)
        return _fallback_suggestions(root_cause_result.get("root_causes", []))


def full_lm_analysis(db: Session, domain: str = "comprehensive") -> dict:
    """根因分析 + 三级建议 完整编排（报告引擎调用）。"""
    rc = analyze_root_causes(db, domain)
    sug = generate_suggestions(rc)
    rc["recommendations"] = sug.get("recommendations", [])
    # 归一化 _meta：若建议走了 LLM 但根因未走，合并标记
    meta = dict(rc.get("_meta", {}))
    if "recommendations" in rc and isinstance(rc.get("_meta"), dict):
        meta["llm_suggestions"] = True
    rc["_meta"] = meta
    return rc
