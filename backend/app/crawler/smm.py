"""SMM 价格爬取：hq.smm.cn/h5/{slug} 静态表格（免费、无需登录）。

实测要点：
- requests 默认自动解压 gzip，无需特殊处理（curl 调试需 --compressed，否则乱码）
- 页面为静态 HTML，lxml 解析 <table>
- SMM 仅覆盖部分品种（硅锰/锑锭/铬矿/电解铜/电解镍），废钢及多数铁合金不在覆盖范围，
  缺口品种用 services.overview.ESTIMATED_* 估算值占位。
"""
import re
from datetime import date

import requests
from lxml import html
from sqlalchemy import text

from app.database import SessionLocal

SMM_BASE = "https://hq.smm.cn/h5"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# slug -> (category, item_name)；item_name 与 ESTIMATED_ALLOY key 对齐，便于成本估算替换
SMM_SLUGS = {
    "silicon-manganese-alloy": ("alloy", "硅锰合金"),
    "antimony-ingot-price": ("alloy", "锑锭"),
    "electrolytic-copper-price": ("alloy", "铜板"),
    "electrolytic-nickel-price": ("alloy", "镍板"),
    "chrome-ore-price": ("alloy", "铬矿"),
}


def _fnum(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def fetch_slug(slug: str) -> list[dict]:
    """抓取单个品种页面，解析表格行。"""
    url = f"{SMM_BASE}/{slug}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    tree = html.fromstring(r.text)
    rows = []
    for tr in tree.xpath("//table//tr"):
        tds_el = tr.xpath("./td")
        if len(tds_el) < 6:
            continue
        tds = [" ".join(t.xpath(".//text()")).strip() for t in tds_el]
        if len(tds) < 6:
            continue
        name, price_range, avg, change, unit, pdate = tds[0], tds[1], tds[2], tds[3], tds[4], tds[5]
        m = re.match(r"([\d.]+)\s*-\s*([\d.]+)", price_range)
        rows.append({
            "name": name,
            "price_min": float(m.group(1)) if m else None,
            "price_max": float(m.group(2)) if m else None,
            "avg": _fnum(avg),
            "change": _fnum(change),
            "unit": unit,
            "date": pdate,
        })
    return rows


def crawl_smm() -> dict:
    """爬取全部 SMM 品种，写入 dim_price。返回汇总。"""
    today = date.today()
    db = SessionLocal()
    results = []
    errors = []
    try:
        for slug, (cat, name) in SMM_SLUGS.items():
            try:
                rows = fetch_slug(slug)
                for r in rows:
                    db.execute(text("""
                        INSERT INTO dim_price
                          (category, item_name, region, price_date, unit_price,
                           price_min, price_max, change_pct, source, created_at)
                        VALUES (:cat, :name, :region, :pdate, :avg, :pmin, :pmax, :chg, 'smm', now())
                    """), {
                        "cat": cat, "name": name, "region": r["name"], "pdate": today,
                        "avg": r["avg"], "pmin": r["price_min"],
                        "pmax": r["price_max"], "chg": r["change"],
                    })
                    results.append({"slug": slug, "region": r["name"], "avg": r["avg"]})
                db.commit()
                print(f"  {slug} ({name}): {len(rows)} 条")
            except Exception as e:
                db.rollback()
                errors.append({"slug": slug, "error": str(e)})
                print(f"  {slug} 失败: {e}")
    finally:
        db.close()
    return {"fetched": len(results), "errors": errors, "items": results[:12]}
