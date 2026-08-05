"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import ai, comprehensive, cost, cross, efficiency, overview, price, quality
from .config import settings

# 前端静态文件目录（统一单端口访问：FastAPI 托管 Vue 构建产物）
FRONTEND_DIST = Path("/opt/mes-poc/frontend/dist")
if not FRONTEND_DIST.exists():
    FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
FRONTEND_DIST = FRONTEND_DIST.resolve()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动后台任务：SMM 价格定时爬取。"""
    scheduler = None
    if settings.CRAWLER_ENABLED:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            from app.crawler.smm import crawl_smm

            scheduler = BackgroundScheduler()
            # 每日 18:00 爬取 SMM 价格
            scheduler.add_job(crawl_smm, "cron", hour=18, minute=0, id="smm_crawl")
            scheduler.start()
            print("[scheduler] SMM 价格爬取已注册（每日 18:00）")
        except Exception as e:
            print(f"[scheduler] 启动失败: {e}")
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="MES POC API",
    description="钢铁 MES 工艺质量·成本·效率协同分析系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mes-poc-api"}


# --- 三主线 + 综合 + 价格 路由 ---
app.include_router(quality.router, prefix="/api/quality", tags=["质量"])
app.include_router(cost.router, prefix="/api/cost", tags=["成本"])
app.include_router(efficiency.router, prefix="/api/efficiency", tags=["效率"])
app.include_router(overview.router, prefix="/api/overview", tags=["综合"])
app.include_router(price.router, prefix="/api/price", tags=["价格"])
app.include_router(cross.router, prefix="/api/crossover", tags=["综合分析"])
app.include_router(comprehensive.router, prefix="/api/comprehensive", tags=["综合成本模型"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI智体"])


# --- 前端静态托管（单端口 10080 统一访问） ---
if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    else:
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIST / "index.html")

    # SPA fallback：非 /api、非静态资源的路径都交给前端路由
    from fastapi.responses import JSONResponse

    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        path = request.url.path
        # API / 元数据路径 → 真 404
        if path.startswith("/api/") or path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        # 带扩展名的静态资源不存在 → 真 404（避免把 index.html 当 JS/CSS 返回导致白屏）
        last_seg = path.rsplit("/", 1)[-1]
        ext = last_seg.rsplit(".", 1)[-1].lower() if "." in last_seg else ""
        if ext in ("js", "css", "png", "jpg", "jpeg", "gif", "svg", "ico", "woff", "woff2", "ttf", "map", "webp"):
            f = FRONTEND_DIST / path.lstrip("/")
            if not f.is_file():
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            return FileResponse(f)
        # 其他前端路由 → SPA fallback 到 index.html
        f = FRONTEND_DIST / path.lstrip("/")
        if f.is_file():
            return FileResponse(f)
        return FileResponse(FRONTEND_DIST / "index.html")
    print(f"[static] 前端托管已启用: {FRONTEND_DIST}")
