import asyncio
import logging
import os

import openai

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_TOKENS_RULE_EXTRACTION = 2000
TEMPERATURE_RULE_EXTRACTION = 0.1


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


class LLMError(Exception):
    """Raised when the LLM call fails after retries and fallback."""


class LLMClient:
    """OpenRouter client (OpenAI-compatible). Offline/batch use only.

    Returns raw text. Parsing into domain models belongs to the pipeline layer,
    because /lib/ may not import from anything internal.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        fallback_model: str | None = None,
    ) -> None:
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY must be set.")
        self._client = openai.AsyncOpenAI(
            api_key=key,
            base_url=base_url
            or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,  # retries are handled here so fallback can interleave
        )
        self._default_model: str = default_model or _env(
            "LLM_DEFAULT_MODEL", "anthropic/claude-3.5-sonnet"
        )
        self._fallback_model: str = fallback_model or _env(
            "LLM_FALLBACK_MODEL", "anthropic/claude-3-haiku"
        )

    async def complete(self, system: str, user: str) -> str:
        """Return the model's text reply. 429 switches to the fallback model."""
        model: str = self._default_model
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    max_tokens=MAX_TOKENS_RULE_EXTRACTION,
                    temperature=TEMPERATURE_RULE_EXTRACTION,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMError("LLM returned an empty response.")
                return content
            except LLMError:
                raise
            except openai.RateLimitError as e:
                last_error = e
                model = self._fallback_model
                logger.warning(
                    "LLM rate limited, switching to fallback model "
                    "attempt=%d model=%s",
                    attempt + 1,
                    model,
                )
            except (openai.APIConnectionError, openai.APIStatusError) as e:
                last_error = e
                logger.warning(
                    "LLM call failed attempt=%d model=%s error=%s",
                    attempt + 1,
                    model,
                    type(e).__name__,
                )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
        logger.error("LLM call failed after retries model=%s", model)
        raise LLMError(f"LLM call failed after {MAX_RETRIES} attempts.") from last_error
