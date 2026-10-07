import asyncio
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from src.lib.llm_client import LLMClient, LLMError


def make_client() -> LLMClient:
    return LLMClient(api_key="k", default_model="main", fallback_model="backup")


def ok(text: str) -> Any:
    message = SimpleNamespace(content=text)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def rate_limit() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://example.test")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError("429", response=response, body=None)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", instant)


@pytest.mark.asyncio
async def test_429_falls_back_to_second_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    models: list[str] = []

    async def fake_create(**kw: Any) -> Any:
        models.append(kw["model"])
        if kw["model"] == "main":
            raise rate_limit()
        return ok("hello")

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)
    assert await client.complete("s", "u") == "hello"
    assert models == ["main", "backup"]


@pytest.mark.asyncio
async def test_gives_up_after_three_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    calls: list[int] = []

    async def always_fail(**kw: Any) -> Any:
        calls.append(1)
        raise rate_limit()

    monkeypatch.setattr(client._client.chat.completions, "create", always_fail)
    with pytest.raises(LLMError):
        await client.complete("s", "u")
    assert len(calls) == 3
