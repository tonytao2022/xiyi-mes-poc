# 部署指南

钢铁 MES · 工艺质量成本效率协同系统 — 可部署包。

## 环境要求

- **Docker 20.10+** 与 **Docker Compose v2**（目标服务器需可联网拉取镜像/依赖）
- 端口：`8003`（后端API）、`5176`（前端）、`5433`（PostgreSQL），确保未被占用
- 磁盘：≥ 2GB（镜像构建 + 数据）

## 一键部署

```bash
# 1. 解压部署包
unzip mes-poc-deploy.zip
cd mes-poc

# 2. 构建并启动三服务（postgres + backend + frontend）
docker compose up -d --build
# 首次构建需拉取 python:3.11-slim / node:20-alpine / postgres:15，
# 国内服务器已配阿里云 pypi 源与 npmmirror，如仍慢可配 docker 镜像加速器。

# 3. 等待 postgres 健康（约 10-30s）
docker compose exec db pg_isready -U mes -d mespoc

# 4. 建表（Alembic 迁移，含 fact_loss_detail 等全部表）
docker compose exec backend alembic upgrade head

# 5. 导入数据（3份Excel + 派生损失明细，约 1-3 分钟）
docker compose exec backend python -m app.etl.import_all
```

完成后访问：
- 前端：http://<服务器IP>:5176/
- 后端 API 文档：http://<服务器IP>:8003/docs

## 验证

```bash
# 健康检查
curl http://localhost:8003/health        # {"status":"ok"}
# 综合AI分析
curl -o /dev/null -w "%{http_code}" http://localhost:8003/api/comprehensive/ai-analysis  # 200
# 数据行数核对
docker compose exec db psql -U mes -d mespoc -c \
  "SELECT 'indicator' AS t, COUNT(*) FROM fact_heat_indicator
   UNION ALL SELECT 'loss_detail', COUNT(*) FROM fact_loss_detail;"
```

## 端口/凭证修改

全部固化在 `docker-compose.yml`，按需修改：
- 数据库：`POSTGRES_USER/PASSWORD/DB`（默认 mes/mes/mespoc）
- 后端端口：`8003:8000`
- 前端端口：`5176:5173`
- DB 端口：`5433:5432`
- CORS：`CORS_ORIGINS`（默认允许 localhost:5176）

## 数据重置

```bash
docker compose exec backend python -m app.etl.import_all   # 幂等，TRUNCATE 后重导
```

## 服务管理

```bash
docker compose logs -f backend     # 看后端日志
docker compose restart backend     # 重启（热重载已开，改代码自动生效）
docker compose down                # 停止（保留数据卷）
docker compose down -v             # 停止并清空数据库卷
```

## 包结构

```
mes-poc/
├─ docker-compose.yml          # 三服务编排
├─ DEPLOY.md                   # 本文档
├─ README.md
├─ docs/                       # 3份Excel源数据（ETL输入）+ 设计文档
├─ backend/                    # FastAPI（源码 + Dockerfile + alembic + requirements）
│  └─ app/
│     ├─ api/                  # 路由（质量/成本/效率/综合/价格/交叉）
│     ├─ services/             # 业务逻辑 + AI分析（comprehensive_ai 等）
│     ├─ models/               # ORM（含 fact_loss_detail）
│     ├─ etl/                  # 数据导入（import_all 一键）
│     ├─ crawler/              # SMM 价格爬取
│     └─ alembic/             # 数据库迁移
└─ frontend/                   # Vue3+Vite（源码 + Dockerfile + package.json）
   └─ src/views/v2/            # 4域5Tab看板（质量/成本/效率/综合）
```

## 注意

- 本包为 **POC/演示版**：系数为估算值（集中在 `services/cost_factors.py`，待客户真实数据替换），前端为 dev 模式（含HMR）。
- 生产部署建议：前端改 `npm run build` 静态托管、后端去掉 `--reload`、数据库加密码与备份策略、配置反向代理（nginx）。
- 旧版（综合分析域重构前）未做版本备份；本包为当前可用状态快照。
