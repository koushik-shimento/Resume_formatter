"""Optional LLM-backed ResumeData normalizer.

The module is intentionally dependency-light and imports no SDK at module load
 time. It can be enabled with RESUME_LLM_PROVIDER=openai or anthropic and a
 corresponding API key. Without configuration, callers should use the existing
 deterministic parser as the fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from urllib import error, request

from .model import Education, Job, ResumeData, SkillGroup


class LLMNormalizerError(RuntimeError):
    """Raised when the configured LLM cannot produce valid ResumeData."""


SYSTEM_PROMPT = r"""You normalize raw resume text for a staffing/recruiting delivery team.
Return ONLY valid JSON matching this schema:
{
  "name": string,
  "summary": string[],
  "skills": [{"category": string, "values": string}],
  "experience": [{"company": string, "dates": string, "title": string, "project": string, "bullets": string[]}],
  "certifications": string[],
  "education": [{"degree": string, "institution": string, "year": string}],
  "dropped_sections": string[]
}

Rules:
- Never invent, infer, embellish, reconcile, or silently correct facts.
- Preserve employer names, dates, titles, projects, degree names, certifications, and technologies.
- Normalize dates to MM/YY only when the source supports the month/year; otherwise preserve the source value.
- Use 5-7 summary bullets when sufficient source material exists; first bullet should state role, experience, and domains.
- Group actual technologies under: Frontend, Backend, Architecture, Real-Time & Messaging, State Management, Performance Optimization, DevOps & Cloud, Testing, Databases, Tools, AI-Assisted Development as applicable.
- Experience is reverse chronological. Responsibility bullets are concise, single-sentence, and start with an action verb unless preserving a current-role statement requires present tense.
- Do not create measurable impact unless it appears in the source.
- Strip contact/address/photos/marital status/age and similar personal details.
- Do not use first-person pronouns.
- Only use sections represented by the source. Unmapped source sections must be listed in dropped_sections instead of being silently discarded.
- Output JSON only; no markdown and no commentary."""


def configured() -> bool:
    provider = os.getenv("RESUME_LLM_PROVIDER", "").strip().lower()
    return provider in {"openai", "anthropic"} and bool(_api_key(provider))


def normalize(raw_text: str, fallback: ResumeData | None = None) -> ResumeData:
    """Normalize raw resume text with the configured provider and validate output."""
    provider = os.getenv("RESUME_LLM_PROVIDER", "").strip().lower()
    if provider not in {"openai", "anthropic"}:
        raise LLMNormalizerError("RESUME_LLM_PROVIDER must be 'openai' or 'anthropic'.")
    key = _api_key(provider)
    if not key:
        raise LLMNormalizerError(f"Missing API key for {provider} provider.")
    payload = _call_provider(provider, key, raw_text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LLMNormalizerError("LLM returned invalid JSON.") from exc
    try:
        normalized = ResumeData.from_dict(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise LLMNormalizerError("LLM JSON did not match the ResumeData schema.") from exc
    _validate(normalized, raw_text, fallback)
    return normalized


def _api_key(provider: str) -> str:
    return os.getenv("OPENAI_API_KEY", "").strip() if provider == "openai" else os.getenv("ANTHROPIC_API_KEY", "").strip()


def _call_provider(provider: str, key: str, raw_text: str) -> str:
    if provider == "openai":
        model = os.getenv("RESUME_LLM_MODEL", "gpt-5.6-mini")
        url = "https://api.openai.com/v1/chat/completions"
        body = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    else:
        model = os.getenv("RESUME_LLM_MODEL", "claude-sonnet-4-5")
        url = "https://api.anthropic.com/v1/messages"
        body = {
            "model": model,
            "max_tokens": int(os.getenv("RESUME_LLM_MAX_TOKENS", "7000")),
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": raw_text}],
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    req = request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        raise LLMNormalizerError(f"LLM request failed: {exc}") from exc

    try:
        if provider == "openai":
            content = result["choices"][0]["message"]["content"]
        else:
            blocks = result["content"]
            content = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMNormalizerError("LLM response did not contain text content.") from exc
    return content.strip()


def _validate(data: ResumeData, raw_text: str, fallback: ResumeData | None) -> None:
    if not data.name and fallback and fallback.name:
        data.name = fallback.name
    for skill in data.skills:
        if not isinstance(skill.category, str) or not isinstance(skill.values, str):
            raise LLMNormalizerError("Invalid skill group.")
    for job in data.experience:
        if not all(isinstance(value, str) for value in (job.company, job.dates, job.title, job.project)):
            raise LLMNormalizerError("Invalid experience record.")
        if not all(isinstance(item, str) for item in job.bullets):
            raise LLMNormalizerError("Invalid experience bullets.")
    if len(raw_text.strip()) < 20:
        raise LLMNormalizerError("Resume source text is too short to normalize safely.")


def to_dict(data: ResumeData) -> dict:
    """Return JSON-serializable ResumeData for logging or testing."""
    return asdict(data)
