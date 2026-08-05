"""应用配置。通过环境变量注入，本地开发可写 .env 文件。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL 连接串，docker-compose 注入；本地直连可用 localhost
    DATABASE_URL: str = "postgresql://mes:mes@localhost:5432/mespoc"

    # 前端来源（CORS）
    CORS_ORIGINS: str = "http://localhost:5176,http://localhost:5174,http://localhost:5173,http://localhost"

    # 价格爬取相关
    SMM_BASE_URL: str = "https://hq.smm.cn/h5"
    CRAWLER_ENABLED: bool = True

    # ---- LLM 推理层（OpenAI 兼容 API）----
    # 供应商：DeepSeek（陶先生 2026-08-05 提供 key，已实测生效）
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""           # 为空自动降级为纯规则模式
    LLM_MODEL: str = "deepseek-v4-flash"  # ★ DeepSeek v4 系列（勿用 deepseek-chat 会404）
    LLM_TIMEOUT: int = 60            # 秒
    LLM_TEMPERATURE: float = 0.2     # 低温度保证确定性
    LLM_MAX_TOKENS: int = 4096

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
