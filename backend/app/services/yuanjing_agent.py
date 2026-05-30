import json

from app.config import settings


SYSTEM_PROMPT = """
You are an AI assistant for an elderly fall detection and caregiver notification system.

Your task is to analyze fall detection events, elderly profile data, activity information, and risk context.

Return only valid JSON with this schema:
{
"risk_level": "low | medium | high | critical",
"notify_caregiver": true,
"message": "short message for caregiver",
"recommendation": "what should be done next",
"reason": "short explanation"
}

Rules:
* Do not provide medical diagnosis.
* Do not claim certainty if data is incomplete.
* Focus on safety.
* If a fall is detected with high confidence, usually notify the caregiver.
* If confidence is low, recommend checking camera/event manually.
* If the elder is very old, has chronic disease, or the location is dangerous, increase risk level.
* Keep the caregiver message short and clear.
* Return JSON only. Do not use Markdown.
""".strip()

VALID_RISK_LEVELS = {"low", "medium", "high", "critical", "unknown"}


def _missing_api_key_response() -> dict:
    return {
        "risk_level": "unknown",
        "notify_caregiver": False,
        "message": "Yuanjing API key is not configured.",
        "recommendation": "Add YUANJING_API_KEY to backend/.env",
        "reason": "Missing API key.",
    }


def _sdk_missing_response() -> dict:
    return {
        "risk_level": "unknown",
        "notify_caregiver": False,
        "message": "OpenAI Python SDK is not installed.",
        "recommendation": "Run pip install -r requirements.txt.",
        "reason": "Missing openai package.",
    }


def _api_error_response(error: Exception) -> dict:
    return {
        "risk_level": "unknown",
        "notify_caregiver": False,
        "message": "Yuanjing agent request failed.",
        "recommendation": "Check Yuanjing API configuration and network access.",
        "reason": f"{type(error).__name__}: {error}",
    }


def _json_parse_fallback(raw_response: str) -> dict:
    return {
        "risk_level": "unknown",
        "notify_caregiver": False,
        "message": raw_response,
        "recommendation": "Agent did not return valid JSON.",
        "reason": "JSON parsing failed.",
    }


def _normalize_agent_response(agent_response: dict) -> dict:
    risk_level = str(agent_response.get("risk_level", "unknown")).lower()

    if risk_level not in VALID_RISK_LEVELS:
        risk_level = "unknown"

    return {
        "risk_level": risk_level,
        "notify_caregiver": bool(agent_response.get("notify_caregiver", False)),
        "message": str(agent_response.get("message", "")),
        "recommendation": str(agent_response.get("recommendation", "")),
        "reason": str(agent_response.get("reason", "")),
    }


async def analyze_fall_event(event_data: dict) -> dict:
    if not settings.yuanjing_api_key:
        return _missing_api_key_response()

    try:
        from openai import AsyncOpenAI
    except ImportError:
        return _sdk_missing_response()

    client = AsyncOpenAI(
        api_key=settings.yuanjing_api_key,
        base_url=settings.yuanjing_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.yuanjing_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(event_data, ensure_ascii=False),
                },
            ],
        )
    except Exception as exc:
        return _api_error_response(exc)

    raw_response = response.choices[0].message.content or ""

    try:
        parsed_response = json.loads(raw_response)
    except json.JSONDecodeError:
        return _json_parse_fallback(raw_response)

    if not isinstance(parsed_response, dict):
        return _json_parse_fallback(raw_response)

    return _normalize_agent_response(parsed_response)
