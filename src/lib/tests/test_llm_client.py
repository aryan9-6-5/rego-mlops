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


@pytest.mark.asyncio
async def test_a_first_try_success_makes_one_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    calls: list[str] = []

    async def fake_create(**kw: Any) -> Any:
        calls.append(kw["model"])
        return ok("hello")

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)
    assert await client.complete("s", "u") == "hello"
    assert calls == ["main"]


@pytest.mark.asyncio
async def test_an_empty_reply_is_an_error_not_a_blank_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    async def empty(**kw: Any) -> Any:
        return ok("")

    monkeypatch.setattr(client._client.chat.completions, "create", empty)
    with pytest.raises(LLMError, match="empty"):
        await client.complete("s", "u")


@pytest.mark.asyncio
async def test_server_errors_are_retried_on_the_same_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()
    models: list[str] = []

    async def server_error(**kw: Any) -> Any:
        models.append(kw["model"])
        request = httpx.Request("POST", "https://example.test")
        raise openai.APIStatusError(
            "boom", response=httpx.Response(500, request=request), body=None
        )

    monkeypatch.setattr(client._client.chat.completions, "create", server_error)
    with pytest.raises(LLMError):
        await client.complete("s", "u")
    assert models == ["main", "main", "main"]


def test_an_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError):
        LLMClient()


def test_models_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "env/default")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "env/fallback")
    client = LLMClient(api_key="k")
    assert (client._default_model, client._fallback_model) == (
        "env/default", "env/fallback",
    )
