"""
Groq wrapper with schema validation, one repair retry, model fallback, template
fallback. Caches by input hash to disk so reruns cost nothing.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path

from groq import BadRequestError, Groq, InternalServerError, RateLimitError
from pydantic import BaseModel, ValidationError

from ..config import CACHE_ROOT, get_settings
from .prompts import REPAIR_TEMPLATE, EmailPromptInput, fallback_email, strip_em_dashes


class LLMClient:
    """Small facade over Groq's chat.completions with JSON-mode validation."""

    def __init__(self) -> None:
        s = get_settings()
        self.primary = s.llm_primary
        self.fallback = s.llm_fallback
        self.client = Groq(api_key=s.groq_api_key) if s.groq_api_key else None
        self.cache_dir = CACHE_ROOT / "llm"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Utilities ----------

    def _cache_key(self, model: str, messages: list[dict], schema_name: str) -> Path:
        body = json.dumps({"m": model, "msgs": messages, "s": schema_name}, sort_keys=True)
        digest = hashlib.blake2s(body.encode(), digest_size=12).hexdigest()
        return self.cache_dir / f"{schema_name}-{digest}.json"

    def _cache_get(self, path: Path) -> dict | None:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return None
        return None

    def _cache_put(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2))

    # ---------- Core call ----------

    def _call_once(self, model: str, messages: list[dict], response_format: dict, timeout: float) -> str:
        assert self.client is not None
        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
            temperature=0.3,
            timeout=timeout,
        )
        return resp.choices[0].message.content or ""

    def call_json(
        self,
        *,
        schema: type[BaseModel],
        messages: list[dict],
        fallback_factory: Callable[[], BaseModel],
        cache_key_ext: str = "",
        timeout: float = 20.0,
    ) -> BaseModel:
        """Return a validated `schema` instance; never raises."""
        if self.client is None:
            return fallback_factory()

        schema_json = schema.model_json_schema()
        response_format = {"type": "json_object"}
        schema_name = f"{schema.__name__}{cache_key_ext}"

        for model in (self.primary, self.fallback):
            cache_path = self._cache_key(model, messages, schema_name)
            cached = self._cache_get(cache_path)
            if cached:
                try:
                    return schema.model_validate(cached)
                except ValidationError:
                    cache_path.unlink(missing_ok=True)

            local_msgs = list(messages)
            for attempt in range(2):
                try:
                    raw = self._call_once(model, local_msgs, response_format, timeout)
                except (RateLimitError, InternalServerError, TimeoutError):
                    time.sleep(0.5 * (attempt + 1))
                    continue
                except BadRequestError:
                    break
                except Exception:
                    break

                try:
                    parsed = schema.model_validate_json(raw)
                    self._cache_put(cache_path, parsed.model_dump())
                    return parsed
                except ValidationError as ve:
                    if attempt == 0:
                        local_msgs = local_msgs + [
                            {"role": "user",
                             "content": REPAIR_TEMPLATE.format(
                                 error=str(ve.errors()[:1]),
                                 schema=json.dumps(schema_json),
                             )},
                        ]
                        continue
                    break
        return fallback_factory()

    # ---------- Public helpers ----------

    def draft_email(self, inp: EmailPromptInput) -> dict[str, str]:
        from ..memory.schemas import EmailDraft
        from .prompts import EMAIL_SYSTEM, email_user_prompt

        messages = [
            {"role": "system", "content": EMAIL_SYSTEM},
            {"role": "user", "content": email_user_prompt(inp)},
        ]
        draft = self.call_json(
            schema=EmailDraft,
            messages=messages,
            fallback_factory=lambda: EmailDraft(**fallback_email(inp)),
            cache_key_ext=f"-{inp.brand_alias.replace(' ', '_')}",
        )
        body = strip_em_dashes(draft.body)
        return {"subject": draft.subject, "body": body}
