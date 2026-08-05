# 钢铁 MES 工艺质量·成本·效率协同分析系统（POC）

基于客户提供的炼钢/轧钢原始数据（Excel）与 demo（HTML/PDF），构建以熔炼号为追溯主键、
**质量·成本·效率三主线协同**的分析系统。设计理念与数据模型见 [`docs/系统设计方案.md`](docs/系统设计方案.md)。

## 技术栈

- 前端：Vue 3 + Vite + Pinia + Vue Router + Element Plus + ECharts 5 + VueUse
- 后端：FastAPI + SQLAlchemy 2.0 + Alembic + pandas + APScheduler
- 数据库：PostgreSQL 15
- 部署：Docker Compose 一键起（db + backend + frontend）

## 快速启动

```bash
# 一键启动（首次构建镜像约 2-3 分钟，pip 走阿里云源、npm 走 npmmirror）
docker compose up -d --build

# 前端看板：浏览器打开 http://localhost:5176
# 后端 API 文档：http://localhost:8003/docs
```

## 数据导入

```bash
# 导入 3 份 Excel（炼钢工艺执行 / 废钢料型 / SWRCH22A）到 PostgreSQL
docker compose exec backend python -m app.etl.import_all
```

导入行数（与原始 Excel 一致）：
- 炼钢：fact_heat 1949 炉 · fact_heat_indicator 176,859 条（长表）· dim_indicator 119 指标
- 废钢：fact_scrap_ratio 1,518 条（138 钢种 × 11 料型）· dim_scrap_type 11
- SWRCH22A：力学 50 · 化学 50 · 加热 910 · 轧制 881 · 尺寸 47 · 追溯 25

## 价格爬取

```bash
# 手动触发 SMM 价格爬取（写入 dim_price）
curl -X POST localhost:8003/api/price/crawl
```

- 数据源：上海有色网 `hq.smm.cn/h5/{slug}`（免费、静态 HTML、requests 自动解压 gzip）
- 已覆盖：硅锰合金、锑锭、电解铜(铜板)、电解镍(镍板)、铬矿（共 24 条真实价）
- 定时：APScheduler 每日 18:00 自动爬取
- 缺口（废钢 11 料型、多数铁合金）：用 `services/overview.py` 的估算值占位，已爬取的真实价自动替换估算值

## 看板

| 路由 | 看板 | 内容 |
|------|------|------|
| `/` | 首页 | 系统就绪检查 |
| `/overview` | 综合 | KPI + 直接成本估算（废钢+合金×价格） |
| `/quality` | 质量 | 各工序符合率 + 班组对比 + 指标短板 Top15 |
| `/cost` | 成本 | 废钢料型结构 + 钢种用量 Top + 合金投入统计 |
| `/efficiency` | 效率 | 各工序时长分布 + 班组产能 + 轧钢班次产量 + 加热统计 |

API 共 16 个端点，详见 http://localhost:8003/docs 。

## ⚠️ 数据口径确认点（与客户确认重点）

> 本系统的价值在于数据逻辑可核对，以下口径点需与客户确认：

1. **符合率口径**：`judge IS NOT NULL` 为判定，`judge = 1` 为命中。
   - 板坯 90.31%、方坯 90.53% 与客户汇总**完全吻合** ✓
   - 转炉(92.99%)/精炼(91.11%)/真空(95.54%) 与汇总(87.75%/89.76%/90.47%) 有差异，因汇总判定数(53453)大于炉次三元组数(48725)，疑似按**试样级展开**统计，口径待确认。

2. **废钢总炉数修正**：原始 Excel 合计行 = **4582 炉 / 230159.7 吨**（本系统口径，正确）。
   - 原 demo HTML 写"9164 炉"是 **2 倍错误**（已发现并修正）。
   - 总重量 230159.7 吨与 demo(230160)吻合 ✓

3. **价格来源**：5 种合金用 SMM 真实价（硅锰 5825、锑锭 88000、铜 106495、镍 132550 元/吨），
   其余用估算值占位并标注 `source`。

4. **关键业务发现**（数据揭示）：
   - 转炉最差指标「终点温度」符合率仅 41.18%（119 判定 49 命中）
   - 合金整体符合率 53.99%，多数合金加入量超标准（成本优化空间）
   - 直接成本：废钢 6.18 亿 + 合金 1.98 亿 = 8.16 亿（估算口径）

## 项目结构

```
mes-poc/
├─ docs/                  # 客户原始数据 + 设计文档 + demo
├─ backend/               # FastAPI 后端
│  ├─ app/
│  │  ├─ api/             # 路由（quality/cost/efficiency/overview/price）
│  │  ├─ services/       # 分析逻辑
│  │  ├─ models/          # ORM（dimension + fact，工艺指标长表 fact_heat_indicator）
│  │  ├─ etl/             # Excel 导入（双行表头解析、哨兵值清洗）
│  │  └─ crawler/         # SMM 价格爬取
│  ├─ alembic/            # 数据库迁移
│  └─ requirements.txt
├─ frontend/              # Vue3 前端
│  └─ src/
│     ├─ styles/theme.scss        # 暗色玻璃拟态设计系统
│     ├─ composables/             # useLazyChart/useCountUp/useNavScroll
│     ├─ components/              # layout/cards/charts 组件库
│     └─ views/                   # 5 个看板
└─ docker-compose.yml
```

## 数据模型核心

围绕熔炼号的星型模型，**工艺指标采用长表(EAV)**：
- `fact_heat_indicator`：每行 = 一炉某工序某指标的标准/实绩/判断（176,859 行，覆盖转炉/精炼/真空/板坯/方坯/合金）
- 跨指标分析（短板指标排序）天然方便，新增指标无需改表

## 后续规划（第二阶段）

- 全流程质量追溯链（场景A）
- 单件 z-score 偏差与根因下钻（场景D）
- 配料成本-质量权衡、合金收得率优化（场景B/C）
- 配料优化线性规划（场景E）
- 综合炉次成本模型（直接成本 + 质量损失 + 效率损失，场景G/H）
- SPC 控制图 / Cp·Cpk
