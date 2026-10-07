import json
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.pipeline.ct import kaggle_runner, trigger
from src.pipeline.ct.kaggle_runner import CONFIG_PLACEHOLDER, KaggleError, KaggleRunner


def notebook(tmp_path: Path, text: str = f"x = '''{CONFIG_PLACEHOLDER}'''") -> Path:
    path = tmp_path / "nb.ipynb"
    path.write_text(text)
    return path


def test_the_cli_runner_returns_what_the_command_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def run(cmd: list[str], **kw: Any) -> Any:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="complete", stderr="")

    monkeypatch.setattr("src.pipeline.ct.kaggle_runner.subprocess.run", run)
    assert kaggle_runner.cli_runner(["kernels", "status", "me/x"]) == "complete"
    assert seen == [["kaggle", "kernels", "status", "me/x"]]


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, "kaggle", stderr="secret detail"),
        subprocess.TimeoutExpired("kaggle", 600),
        FileNotFoundError("kaggle"),
    ],
)
def test_a_failing_cli_becomes_a_kaggle_error_without_its_output(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def run(cmd: list[str], **kw: Any) -> Any:
        raise error

    monkeypatch.setattr("src.pipeline.ct.kaggle_runner.subprocess.run", run)
    with pytest.raises(KaggleError) as caught:
        kaggle_runner.cli_runner(["kernels", "push", "-p", "x"])
    assert "secret detail" not in str(caught.value)


def test_the_runner_needs_a_username_and_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_TRAIN_DATASET", raising=False)
    with pytest.raises(KaggleError, match="KAGGLE_USERNAME"):
        KaggleRunner(notebook(tmp_path))


def test_a_notebook_without_the_config_placeholder_is_refused(tmp_path: Path) -> None:
    runner = KaggleRunner(notebook(tmp_path, "print('no placeholder')"), "me", "me/data", run=lambda a: "")
    with pytest.raises(KaggleError, match="placeholder"):
        runner.push_notebook({})


def test_the_run_times_out_instead_of_waiting_forever(tmp_path: Path) -> None:
    runner = KaggleRunner(
        notebook(tmp_path), "me", "me/data",
        run=lambda a: "running", poll_seconds=0, timeout_seconds=0, sleep=lambda s: None,
    )
    with pytest.raises(KaggleError, match="timed out"):
        runner.poll_until_complete()


def test_pull_output_creates_the_destination_and_asks_kaggle_for_the_kernel(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def record(args: list[str]) -> str:
        calls.append(args)
        return ""

    runner = KaggleRunner(notebook(tmp_path), "me", "me/data", run=record)
    destination = tmp_path / "out" / "model"
    runner.pull_output(destination)
    assert destination.is_dir()
    assert calls == [["kernels", "output", "me/rego-ct-retrain", "-p", str(destination)]]


def test_a_config_with_a_backslash_survives_the_embedding(tmp_path: Path) -> None:
    pushed: dict[str, str] = {}

    def run(args: list[str]) -> str:
        folder = Path(args[args.index("-p") + 1])
        pushed["nb"] = (folder / "ct_retrain.ipynb").read_text()
        return ""

    KaggleRunner(notebook(tmp_path), "me", "me/data", run=run).push_notebook({"note": "a\\b"})
    embedded = pushed["nb"].split("'''")[1]
    assert json.loads(embedded.replace("\\\\", "\\")) == {"note": "a\\b"}


# ---- GitHub dispatch ---------------------------------------------------------


@pytest.mark.asyncio
async def test_a_network_failure_is_reported_without_internals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "me/rego")

    def boom(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failure for internal-host")

    async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as client:
        with pytest.raises(trigger.TriggerError) as caught:
            await trigger.dispatch_ct_workflow("v", client)
    assert "internal-host" not in str(caught.value)


@pytest.mark.asyncio
async def test_dispatch_opens_and_closes_its_own_client_when_given_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "me/rego")
    monkeypatch.setenv("CT_WORKFLOW_FILE", "train.yml")
    monkeypatch.setenv("CT_WORKFLOW_REF", "release")
    seen: dict[str, Any] = {}
    real = httpx.AsyncClient

    def factory(*a: Any, **kw: Any) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["body"] = json.loads(request.content)
            return httpx.Response(204)

        return real(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("src.pipeline.ct.trigger.httpx.AsyncClient", factory)
    await trigger.dispatch_ct_workflow("RBI-4.1-x")
    assert seen["url"].endswith("/workflows/train.yml/dispatches")
    assert seen["body"]["ref"] == "release"
