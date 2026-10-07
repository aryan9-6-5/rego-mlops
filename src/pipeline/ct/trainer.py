import argparse
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.lib.regulation_graph import GraphClient, fetch_active_rules
from src.pipeline.ct.constraint_loss import prohibited_features
from src.pipeline.ct.drift_detector import mark_checked
from src.pipeline.ct.kaggle_runner import KaggleRunner

logger = logging.getLogger(__name__)

_SAFE_VERSION = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


class TrainerError(Exception):
    """Raised when a CT run cannot produce a usable model bundle."""


class ModelTracker(Protocol):
    def log_run(
        self,
        *,
        model_version: str,
        regulation_version: str,
        artifact_dir: Path,
        params: dict[str, str],
        metrics: dict[str, float],
    ) -> str: ...


class Trainer(Protocol):
    def push_notebook(self, config: dict[str, object]) -> None: ...
    def poll_until_complete(self) -> None: ...
    def pull_output(self, destination: Path) -> None: ...


@dataclass(frozen=True)
class TrainingOutcome:
    model_version: str
    artifact_dir: Path
    prohibited_features: list[str]
    mlflow_run_id: str


def run_training(
    graph: GraphClient,
    trainer: Trainer,
    tracker: ModelTracker,
    regulation_version: str,
    artifact_root: Path,
) -> TrainingOutcome:
    """Retrain for a regulation version and register the result in MLflow.

    Returns a model bundle that still has to pass every CI gate. Training never
    deploys anything.
    """
    if not _SAFE_VERSION.match(regulation_version):
        raise TrainerError("Invalid regulation version.")
    rules = fetch_active_rules(graph)
    if not rules:
        raise TrainerError("No active rules to train against.")
    prohibited = prohibited_features(rules)
    model_version = f"ct-{regulation_version}"
    artifact_dir = artifact_root / model_version

    trainer.push_notebook(
        {"regulation_version": regulation_version, "prohibited_features": prohibited}
    )
    trainer.poll_until_complete()
    trainer.pull_output(artifact_dir)
    if not (artifact_dir / "profile.json").exists():
        raise TrainerError("Training finished but produced no profile.json.")

    run_id = tracker.log_run(
        model_version=model_version,
        regulation_version=regulation_version,
        artifact_dir=artifact_dir,
        params={"prohibited_features": ",".join(prohibited)},
        metrics={"prohibited_feature_count": float(len(prohibited))},
    )
    logger.info(
        "CT run registered model_version=%s regulation_version=%s run_id=%s",
        model_version,
        regulation_version,
        run_id,
    )
    return TrainingOutcome(model_version, artifact_dir, prohibited, run_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regulation-version", required=True)
    parser.add_argument("--detected-at", default="")
    args = parser.parse_args()

    from src.lib.mlflow_client import MlflowTracker
    from src.lib.neo4j_client import neo4j_client

    root = Path(os.environ.get("MODEL_ARTIFACT_DIR", "artifacts/models"))
    outcome = run_training(
        neo4j_client,
        KaggleRunner(Path("notebooks/ct_retrain.ipynb")),
        MlflowTracker(),
        args.regulation_version,
        root,
    )
    if args.detected_at:
        mark_checked(neo4j_client, args.detected_at)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"model_version={outcome.model_version}\n")


if __name__ == "__main__":
    main()
