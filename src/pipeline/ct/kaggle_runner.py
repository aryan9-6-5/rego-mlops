import json
import logging
import os
import shutil

# The only subprocess use: the fixed kaggle CLI, never a shell.
import subprocess  # nosec B404
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_PLACEHOLDER = "__CT_CONFIG__"
KERNEL_NAME = "rego-ct-retrain"
CommandRunner = Callable[[list[str]], str]


class KaggleError(Exception):
    """Raised when a Kaggle command or the training run fails."""


def cli_runner(args: list[str]) -> str:
    """Run the `kaggle` CLI (credentials come from KAGGLE_USERNAME / KAGGLE_KEY)."""
    try:
        # Fixed executable, arguments built from our own config, no shell.
        done = subprocess.run(  # nosec B603 B607
            ["kaggle", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        logger.error(
            "Kaggle command failed command=%s error=%s", args[:2], type(e).__name__
        )
        raise KaggleError(f"Kaggle command '{' '.join(args[:2])}' failed.") from e
    return done.stdout


class KaggleRunner:
    """Pushes the CT notebook to Kaggle, waits for it, and pulls the output.

    Training runs on Kaggle (P100 GPU), never locally or on Modal.
    """

    def __init__(
        self,
        notebook_path: Path,
        username: str | None = None,
        dataset: str | None = None,
        run: CommandRunner = cli_runner,
        poll_seconds: float = 30.0,
        timeout_seconds: float = 3600.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._notebook = notebook_path
        self._username = username or os.environ.get("KAGGLE_USERNAME", "")
        self._dataset = dataset or os.environ.get("KAGGLE_TRAIN_DATASET", "")
        if not self._username or not self._dataset:
            raise KaggleError("KAGGLE_USERNAME and KAGGLE_TRAIN_DATASET must be set.")
        self._run = run
        self._poll_seconds = poll_seconds
        self._timeout_seconds = timeout_seconds
        self._sleep = sleep

    @property
    def slug(self) -> str:
        return f"{self._username}/{KERNEL_NAME}"

    def push_notebook(self, config: dict[str, Any]) -> None:
        """Start a run. `config` is embedded in the notebook, since Kaggle
        notebooks take no parameters."""
        payload = json.dumps(config)
        if "'''" in payload:
            raise KaggleError("Training config contains an unsafe sequence.")
        source = self._notebook.read_text(encoding="utf-8")
        if CONFIG_PLACEHOLDER not in source:
            raise KaggleError("Notebook has no config placeholder.")
        workdir = Path(tempfile.mkdtemp(prefix="rego-ct-"))
        try:
            (workdir / "ct_retrain.ipynb").write_text(
                source.replace(CONFIG_PLACEHOLDER, payload.replace("\\", "\\\\")),
                encoding="utf-8",
            )
            (workdir / "kernel-metadata.json").write_text(
                json.dumps(
                    {
                        "id": self.slug,
                        "title": KERNEL_NAME,
                        "code_file": "ct_retrain.ipynb",
                        "language": "python",
                        "kernel_type": "notebook",
                        "is_private": True,
                        "enable_gpu": True,
                        "enable_internet": False,
                        "dataset_sources": [self._dataset],
                        "competition_sources": [],
                        "kernel_sources": [],
                    }
                ),
                encoding="utf-8",
            )
            self._run(["kernels", "push", "-p", str(workdir)])
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def poll_until_complete(self) -> None:
        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            status = self._run(["kernels", "status", self.slug]).lower()
            if "complete" in status:
                return
            if "error" in status or "cancel" in status:
                raise KaggleError("The Kaggle training run failed.")
            self._sleep(self._poll_seconds)
        raise KaggleError("The Kaggle training run timed out.")

    def pull_output(self, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        self._run(["kernels", "output", self.slug, "-p", str(destination)])
