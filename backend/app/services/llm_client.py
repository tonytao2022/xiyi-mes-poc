"""OpenAI 兼容 LLM 客户端，带超时/重试/降级。

供应商已确认：DeepSeek（LLM_BASE_URL=https://api.deepseek.com/v1）
关键约束：
- 模型用 deepseek-v4 系列（deepseek-v4-flash / deepseek-v4-pro），勿用 deepseek-chat（会404）
- DeepSeek 强制要求 prompt 文本中必须包含 "json" 字样，否则报 invalid_request_error。
  所有调用方 system/user prompt 中都须含「JSON」描述，本层若检测不到也兜底追加。
"""
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用失败统一异常。"""


class LLMClient:
    """轻量 OpenAI 兼容客户端（纯 httpx，不引入 openai 依赖）。"""

    def __init__(self):
        self.base_url = (settings.LLM_BASE_URL or "").rstrip("/")
        self.api_key = settings.LLM_API_KEY or ""
        self.model = settings.LLM_MODEL or ""
        self.enabled = bool(self.base_url and self.api_key and self.model)

    # ---- 内部工具 ----

    def _ensure_json_hint(self, text: str) -> str:
        """DeepSeek 强制要求 prompt 含 'json' 字样，缺则兜底追加。"""
        if not text or "json" not in text.lower():
            text = (text or "") + "\n\n（请确保输出为合法 JSON 结构。You must output valid JSON.）"
        return text

    # ---- 公开方法 ----

    def chat(self, system: str, user: str, temperature=None, max_tokens=None) -> str:
        """调用 chat/completions；失败抛 LLMError。"""
        if not self.enabled:
            raise LLMError("LLM 未配置（base_url/api_key/model 缺失）")
        system = self._ensure_json_hint(system)
        user = self._ensure_json_hint(user)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "response_format": {"type": "json_object"},  # 强制 JSON 输出
        }
        last_err: Exception | None = None
        for attempt in range(3):  # 简单重试
            try:
                resp = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=settings.LLM_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"].get("content")
                # 部分模型（deepseek v4）在 max_tokens/复杂性下 content 可能为空，只有 reasoning_content
                if not content:
                    rc = data["choices"][0]["message"].get("reasoning_content", "")
                    logger.warning("LLM content 为空，reasoning_content 长度=%s，按失败处理重试", len(rc))
                    raise LLMError("LLM 返回空 content")
                return content
            except Exception as e:  # noqa: BLE001
                last_err = e
                logger.warning("LLM chat 尝试 %d 失败: %s", attempt + 1, e)
                if attempt < 2:
                    import time

                    time.sleep(1.5 * (attempt + 1))
        raise LLMError(f"LLM 调用失败（3次重试后）: {last_err}")

    def chat_json(self, system: str, user: str, **kw) -> dict:
        """调用并解析 JSON；解析失败抛 LLMError。"""
        text = self.chat(system, user, **kw)
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            raise LLMError("LLM 返回非对象 JSON")
        except json.JSONDecodeError:
            # 容错：提取首个 { ... } 块（DeepSeek 偶尔带 reasoning/前后缀）
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            raise LLMError(f"LLM 返回非 JSON: {text[:300]}")
