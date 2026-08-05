"""报告生成引擎：7段式 HTML 报告（移植柳钢 Step6 CSS 体系）+ ai_report 入库。

数字铁律：HTML 内所有数值取自确定性引擎（comprehensive_model/ai_analysis）与 LLM JSON 原文，
绝不二次编造；报告与页面数字同源一致。
"""
import html
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai_report import AiReport
from app.services import comprehensive, comprehensive_ai
from app.services.llm_analyzer import full_lm_analysis

logger = logging.getLogger(__name__)


# ---------------- CSS（移植柳钢 Step6 体系，v2 浅色科技蓝） ----------------
_REPORT_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #f0f2f5;
  color: #333; line-height: 1.8; padding: 20px; }
.container { max-width: 1100px; margin: 0 auto; }
.header { background: linear-gradient(135deg, #0c4a6e, #0284c7); color: white;
  padding: 40px 30px; border-radius: 12px; margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15); }
.header h1 { font-size: 26px; margin-bottom: 8px; }
.header .meta { font-size: 13px; opacity: 0.88; }
.header .badge { display: inline-block; background: rgba(255,255,255,0.22);
  padding: 4px 12px; border-radius: 20px; font-size: 12px; margin: 10px 6px 0 0; }
.section { background: white; border-radius: 10px; padding: 26px; margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section h2 { font-size: 19px; color: #0c4a6e; border-left: 4px solid #0284c7;
  padding-left: 12px; margin-bottom: 16px; }
.section h3 { font-size: 15px; color: #555; margin: 14px 0 8px; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr));
  gap: 14px; margin-bottom: 16px; }
.stat-card { background: linear-gradient(135deg, #f8fafc, #e0f2fe); border-radius: 8px;
  padding: 16px; text-align: center; border: 1px solid #bae6fd; }
.stat-card .value { font-size: 26px; font-weight: bold; color: #0284c7; }
.stat-card .label { font-size: 12px; color: #666; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }
th { background: #0284c7; color: white; padding: 9px 12px; text-align: left; font-weight: 600; }
td { padding: 7px 12px; border-bottom: 1px solid #e5e7eb; }
tr:nth-child(even) { background: #f8fafc; }
tr:hover { background: #e0f2fe; }
.success-box { background: #d1fae5; border-left: 4px solid #059669; padding: 14px 18px;
  border-radius: 6px; margin: 12px 0; }
.warning-box { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 14px 18px;
  border-radius: 6px; margin: 12px 0; }
.danger-box { background: #fee2e2; border-left: 4px solid #dc2626; padding: 14px 18px;
  border-radius: 6px; margin: 12px 0; }
.info-box { background: #e0f2fe; border-left: 4px solid #0284c7; padding: 14px 18px;
  border-radius: 6px; margin: 12px 0; }
.tag { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.tag-green { background: #d1fae5; color: #065f46; }
.tag-orange { background: #fef3c7; color: #92400e; }
.tag-red { background: #fee2e2; color: #991b1b; }
.tag-blue { background: #e0f2fe; color: #075985; }
.tag-gray { background: #e5e7eb; color: #374151; }
.rc-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 14px 18px; margin-bottom: 12px; border-left: 4px solid #0284c7; }
.rc-rank { display:inline-block; width: 26px; height: 26px; line-height: 26px;
  background: #0284c7; color: #fff; border-radius: 50%; text-align: center;
  font-weight: bold; font-size: 13px; margin-right: 8px; }
.conf-bar { height: 6px; background: #e2e8f0; border-radius: 3px; margin-top: 6px; }
.conf-fill { height: 100%; background: #0284c7; border-radius: 3px; }
.recommendation-list { list-style: none; counter-reset: rec; }
.recommendation-list li { counter-increment: rec; position: relative;
  padding: 12px 16px 12px 44px; margin-bottom: 10px; background: #f8fafc;
  border-radius: 8px; border-left: 3px solid #0284c7; }
.recommendation-list li::before { content: counter(rec); position: absolute; left: 12px;
  top: 50%; transform: translateY(-50%); width: 24px; height: 24px; background: #0284c7;
  color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-weight: bold; font-size: 13px; }
.footer { text-align: center; padding: 20px; color: #888; font-size: 12px; }
"""


def _esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def _fmt(v, nd=1):
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return str(v if v is not None else "")


def _level_box(level: str) -> str:
    """根据风险等级返回 box HTML。"""
    cls = {"高": "danger-box", "中": "warning-box", "低": "success-box"}.get(str(level), "info-box")
    return cls


def _level_tag(level: str) -> str:
    cls = {"高": "tag-red", "中": "tag-orange", "低": "tag-green"}.get(str(level), "tag-gray")
    return f"<span class='tag {cls}'>{_esc(level)}</span>"


# ---------------- 各段 HTML 生成 ----------------

def _header_html(data: dict) -> str:
    meta = data["meta"]
    badges = ""
    if meta.get("llm_used"):
        badges += "<span class='badge'>🤖 LLM 深度分析</span>"
    if meta.get("model_used"):
        badges += f"<span class='badge'>模型: {_esc(meta['model_used'])}</span>"
    return f"""
<div class="header">
  <h1>{_esc(data['title'])}</h1>
  <div class="meta">{_esc(meta['period'])} ｜ 样本 {_esc(meta['heats'])} 炉 ｜ 生成时间 {_esc(meta['generated_at'])}</div>
  <div class="meta">分析数据：质量 · 成本 · 效率协同（确定性引擎）+ AI 根因推理</div>
  {badges}
</div>"""


def _kpi_html(kpi: dict) -> str:
    cards = ""
    items = [
        ("炉次样本", f"{_fmt(kpi.get('heats'), 0)} 炉"),
        ("直接成本", f"{_fmt(kpi.get('direct_wan'))} 万元"),
        ("质量损失", f"{_fmt(kpi.get('quality_wan'))} 万元"),
        ("效率损失", f"{_fmt(kpi.get('efficiency_wan'))} 万元"),
        ("综合成本", f"{_fmt(kpi.get('total_wan'))} 万元"),
        ("终点命中", f"{_fmt(kpi.get('endpoint_hit'))}%"),
        ("补吹率", f"{_fmt(kpi.get('reblow_rate'))}%"),
        ("超时炉数", f"{_fmt(kpi.get('overdue_heats'), 0)} 炉"),
    ]
    for label, val in items:
        cards += f"<div class='stat-card'><div class='value'>{_esc(val)}</div><div class='label'>{label}</div></div>"
    return f"""
<div class="section">
  <h2>① 数据概览</h2>
  <div class="summary-grid">{cards}</div>
  <div class="info-box">成本口径：直接成本 + 质量损失 + 效率损失（货币化统一，单位万元）。
  损失系数来自 cost_factors（估算值，待客户真实数据替换）。</div>
</div>"""


def _cost_structure_html(s: dict) -> str:
    rows = ""
    for name, pct, val in [("直接成本", s.get("direct_pct"), s.get("direct")),
                           ("质量损失", s.get("quality_pct"), s.get("quality")),
                           ("效率损失", s.get("efficiency_pct"), s.get("efficiency"))]:
        rows += f"<tr><td>{name}</td><td>{_fmt(pct)}%</td><td>{_fmt(val/1e4)} 万元</td></tr>"
    return f"""
<div class="section">
  <h2>② 成本结构分析</h2>
  <table><tr><th>成本项</th><th>占比</th><th>金额</th></tr>{rows}</table>
</div>"""


def _quality_html(q: dict) -> str:
    hits = ""
    for label, val in [
        ("终点温度符合率", q.get("temp_rate")), ("终点碳符合率", q.get("c_rate")),
        ("终点综合命中率", q.get("endpoint_hit")), ("补吹率", q.get("reblow_rate"))]:
        hits += f"<tr><td>{label}</td><td>{_fmt(val)}%</td></tr>"
    return f"""
<div class="section">
  <h2>③ 质量维度分析</h2>
  <table><tr><th>指标</th><th>数值</th></tr>{hits}</table>
  <div class="warning-box">质量损失 {_fmt(q.get('quality_wan'))} 万元，多源于补吹/废品/合金富裕，建议从终点命中率切入。</div>
</div>"""


def _efficiency_html(e: dict) -> str:
    rows = ""
    for label, val in [("有效精炼时长 P95", f"{_fmt(e.get('overdue_p95'))} 分钟"),
                       ("超时炉数", f"{_fmt(e.get('overdue_heats'), 0)} 炉"),
                       ("超时总时长", f"{_fmt(e.get('overdue_min'), 0)} 分钟"),
                       ("效率损失", f"{_fmt(e.get('efficiency_wan'))} 万元")]:
        rows += f"<tr><td>{label}</td><td>{_esc(val)}</td></tr>"
    return f"""
<div class="section">
  <h2>④ 效率维度分析</h2>
  <table><tr><th>指标</th><th>数值</th></tr>{rows}</table>
</div>"""


def _root_cause_html(llm: dict) -> str:
    cards = ""
    for rc in llm.get("root_causes", []):
        conf = rc.get("confidence", 0)
        try:
            conf_pct = round(float(conf) * 100)
        except (TypeError, ValueError):
            conf_pct = 0
        ev = "".join(f"<li>{_esc(x)}</li>" for x in rc.get("evidence", []))
        cards += f"""
<div class="rc-card">
  <span class="rc-rank">{_esc(rc.get('rank', '·'))}</span>
  <strong>{_esc(rc.get('root_cause'))}</strong>
  <span class='tag tag-blue'>{_esc(rc.get('domain'))}</span>
  <div style="margin-top:6px">置信度 {conf_pct}%
    <div class="conf-bar"><div class="conf-fill" style="width:{conf_pct}%"></div></div>
  </div>
  <div style="font-size:12px;color:#555;margin-top:4px">影响：{_esc(rc.get('impact'))}</div>
  {"<ul style='font-size:12px;color:#666;margin-top:6px'>" + ev + "</ul>" if ev else ""}
</div>"""
    links = "".join(f"<li>{_esc(x)}</li>" for x in llm.get("cross_domain_links", []))
    summ = llm.get("summary", "")
    return f"""
<div class="section">
  <h2>⑥ LLM 根因分析 <span class='tag tag-blue'>{'LLM 100% AI' if llm.get('_meta',{}).get('llm') else '规则降级'}</span></h2>
  <div class="{_level_box(llm.get('risk_level'))}"><strong>综合研判（{_esc(llm.get('risk_level'))}风险）：</strong>{_esc(summ)}</div>
  {cards}
  {"<h3>跨域因果链</h3><ul style='font-size:13px;color:#444'>" + links + "</ul>" if links else ""}
  {("<div class='info-box'>" + _esc(llm.get('_meta',{}).get('note','')) + "</div>") if not llm.get('_meta',{}).get('llm') else ""}
</div>"""


def _suggestion_html(llm: dict) -> str:
    level_names = {"urgent": ("紧急 · 24小时内", "tag-red"), "short": ("短期 · 1-2周", "tag-orange"),
                   "long": ("长期 · 月度/季度", "tag-green")}
    blocks = ""
    for lvl in ["urgent", "short", "long"]:
        items = [r for r in llm.get("recommendations", []) if r.get("level") == lvl]
        if not items:
            continue
        name, tag = level_names.get(lvl, (lvl, "tag-gray"))
        li = ""
        for r in items:
            li += (f"<li><strong>{_esc(r.get('action'))}</strong>"
                   f"<div style='font-size:12px;color:#555'>对象：{_esc(r.get('target'))} ｜ "
                   f"预期：{_esc(r.get('expected_gain'))} ｜ 投入：{_esc(r.get('effort'))} ｜ "
                   f"责任：{_esc(r.get('owner'))}</div></li>")
        blocks += f"<h3><span class='tag {tag}'>{name}</span></h3><ul class='recommendation-list'>{li}</ul>"
    if not blocks:
        blocks = "<div class='info-box'>无整改建议（规则降级模式）。</div>"
    return f"""
<div class="section">
  <h2>⑦ 三级整改建议</h2>
  {blocks}
</div>"""


# ---------------- 汇总编排 + 入库 ----------------

def _collect_metrics(db: Session) -> dict:
    """确定性 KPI（与综合分析页同源）。"""
    structure = comprehensive.comprehensive_model(db, 100000)["structure"]
    air = comprehensive_ai.comprehensive_ai_analysis(db)
    xm = air.get("overview", {}).get("metrics", {})
    if not isinstance(xm, dict) or "total" not in xm:
        xm = structure
    return {
        "heats": structure.get("heats_count") or 0,
        "direct_wan": round(structure.get("direct", 0) / 1e4, 1),
        "quality_wan": round(structure.get("quality", 0) / 1e4, 1),
        "efficiency_wan": round(structure.get("efficiency", 0) / 1e4, 1),
        "total_wan": round(structure.get("total", 0) / 1e4, 1),
        "direct_pct": structure.get("direct_pct"),
        "quality_pct": structure.get("quality_pct"),
        "efficiency_pct": structure.get("efficiency_pct"),
        "endpoint_hit": xm.get("endpoint_hit"),
        "temp_rate": xm.get("temp_rate"),
        "c_rate": xm.get("c_rate"),
        "reblow_rate": xm.get("reblow_rate"),
        "overdue_heats": xm.get("overdue_heats"),
        "overdue_p95": xm.get("overdue_p95"),
        "overdue_min": xm.get("overdue_min"),
    }


def generate_report(db: Session, domain: str = "comprehensive", include_llm: bool = True) -> dict:
    """生成 7 段式 HTML 报告并入库。返回 {report_id, html, data, llm_used, model_used}。"""
    from app.services import comprehensive as _c

    # 1. 确定性数据（0% AI）
    structure = _c.comprehensive_model(db, 100000)["structure"]
    metric = _collect_metrics(db)

    # 2. LLM 根因 + 三级建议
    llm = {}
    llm_used, model_used = False, None
    if include_llm:
        llm = full_lm_analysis(db, domain)
        llm_used = bool(llm.get("_meta", {}).get("llm"))
        model_used = llm.get("_meta", {}).get("model")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    period = "全量历史样本"
    title = f"炼钢质量·成本·效率协同分析报告（{now_str[:10]}）"

    data = {
        "title": title,
        "meta": {
            "period": period, "heats": metric["heats"],
            "generated_at": now_str, "llm_used": llm_used, "model_used": model_used,
        },
        "kpi": metric,
        "cost_structure": structure,
        "quality": metric,
        "efficiency": metric,
        "llm": llm,
    }

    # 3. HTML 渲染（7段式）
    html_str = (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'>"
        f"<title>{_esc(title)}</title><style>{_REPORT_CSS}</style></head><body><div class='container'>"
        + _header_html(data)
        + _kpi_html(metric)
        + _cost_structure_html(structure)
        + _quality_html(metric)
        + _efficiency_html(metric)
        + ("<div class='section'><h2>⑤ 规则引擎发现</h2><div class='info-box'>统计/对标/异常检测均为确定性引擎（0% AI），详见各维度分析页。</div></div>")
        + (_root_cause_html(llm) if llm else "")
        + (_suggestion_html(llm) if llm else "")
        + "<div class='footer'>MES-POC · 兮易智造数字化事业部 ｜ 本报告由确定性引擎生成统计结果，AI 根因分析仅供参考 ｜ 免责声明：损失系数为估算值</div>"
        + "</div></body></html>"
    )

    # 4. 入库
    report = AiReport(
        domain=domain, title=title, period=period,
        meta_json=metric,
        llm_json=llm if llm else None,
        html=html_str, llm_used=llm_used, model_used=model_used,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info("AI 报告已入库 id=%s llm_used=%s", report.id, llm_used)
    return {"report_id": report.id, "html": html_str, "data": data,
            "llm_used": llm_used, "model_used": model_used}
