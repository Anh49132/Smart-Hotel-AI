"""Gemini Developer API transport. Credentials stay on the backend."""
import re

import httpx
from fastapi import HTTPException

from core.config import settings


def redact_secrets(value: str) -> str:
    for secret in (settings.gemini_api_key.get_secret_value(), settings.secret_key):
        if secret:
            value = value.replace(secret, "[ĐÃ ẨN]")
    return re.sub(r"AIza[\w-]{20,}", "[ĐÃ ẨN]", value)


def sanitize_free_text(value: str) -> str:
    """Best-effort filtering for free text, not structured prices/statistics."""
    value = redact_secrets(value)
    value = re.sub(
        r"(?i)((?:mật khẩu|password|api[_ -]?key|access[_ -]?token|token|số tài khoản|số thẻ|cccd|cmnd|hộ chiếu)\s*[:=]\s*)([^\s,;\"}]+)",
        r"\1[ĐÃ ẨN]",
        value,
    )
    value = re.sub(r"(?<!\w)(?:\d[ -]?){8,18}\d(?!\w)", "[ĐÃ ẨN]", value)
    value = re.sub(r"\b[A-Z]{1,2}\d{6,9}\b", "[ĐÃ ẨN]", value)
    return value


async def generate_content(contents: list[dict], system: str, response_schema: dict | None = None, temperature: float = 1) -> str:
    api_key = settings.gemini_api_key.get_secret_value().strip()
    if not api_key:
        raise HTTPException(503, "Chưa cấu hình GEMINI_API_KEY trong .env. Thêm API key rồi khởi động lại ứng dụng.")

    payload = {
        "systemInstruction": {"parts": [{"text": redact_secrets(system)}]},
        "contents": [
            {"role": item["role"], "parts": [{"text": redact_secrets(part["text"])} for part in item["parts"]]}
            for item in contents
        ],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": settings.gemini_max_output_tokens},
    }
    if response_schema is not None:
        # REST schema fields: https://ai.google.dev/api/generate-content#v1beta.GenerationConfig
        payload['generationConfig'].update(responseMimeType='application/json',responseJsonSchema=response_schema)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.gemini_timeout_seconds, connect=10)) as client:
            response = await client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
    except httpx.TimeoutException:
        raise HTTPException(503, "Gemini phản hồi quá lâu. Vui lòng thử lại sau.") from None
    except httpx.HTTPError:
        raise HTTPException(503, "Không thể kết nối Gemini. Hãy kiểm tra kết nối Internet.") from None

    if response.status_code in (401, 403):
        raise HTTPException(503, "API key Gemini không hợp lệ hoặc chưa có quyền truy cập. Kiểm tra GEMINI_API_KEY.")
    if response.status_code == 429:
        raise HTTPException(503, "Gemini đã hết hạn mức hoặc nhận quá nhiều yêu cầu. Kiểm tra quota và thử lại sau.")
    if response.status_code == 404:
        raise HTTPException(503, "Không tìm thấy model Gemini hoặc tài khoản chưa được truy cập. Kiểm tra GEMINI_MODEL.")
    if response.is_error:
        raise HTTPException(503, "Gemini chưa xử lý được yêu cầu. Kiểm tra cấu hình API hoặc thử lại sau.")

    try:
        data = response.json()
        if data.get("promptFeedback", {}).get("blockReason"):
            raise HTTPException(422, "Gemini từ chối nội dung này. Hãy điều chỉnh yêu cầu.")
        candidate = data["candidates"][0]
        finish = candidate.get("finishReason")
        if finish in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}:
            raise HTTPException(422, "Gemini từ chối nội dung này. Hãy điều chỉnh yêu cầu.")
        if finish not in (None, "STOP"):
            raise HTTPException(502, "Gemini chưa tạo được câu trả lời hoàn chỉnh. Hãy rút gọn yêu cầu và thử lại.")
        content = "\n".join(
            part["text"] for part in candidate["content"]["parts"]
            if not part.get("thought") and isinstance(part.get("text"), str)
        ).strip()
        if not content:
            raise ValueError("Empty model response")
    except (ValueError, TypeError, AttributeError, KeyError, IndexError):
        raise HTTPException(502, "Gemini trả về nội dung rỗng hoặc không hợp lệ. Vui lòng thử lại.") from None
    return redact_secrets(content)


async def generate_text(prompt: str, system: str) -> str:
    return await generate_content([{"role": "user", "parts": [{"text": prompt}]}], system)


async def generate_structured(prompt: str, system: str, schema: dict) -> str:
    return await generate_content([{'role':'user','parts':[{'text':prompt}]}],system,response_schema=schema)
