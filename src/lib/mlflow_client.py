import os
from collections.abc import Mapping
from pathlib import Path


class MlflowTracker:
    """MLflow experiment tracking. `mlflow` is imported on first use, since it is
    an optional (`ct` group) dependency."""

    def __init__(
        self, tracking_uri: str | None = None, experiment: str | None = None
    ) -> None:
        self._tracking_uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI")
        self._experiment = experiment or os.environ.get(
            "MLFLOW_EXPERIMENT_NAME", "rego-compliance"
        )

    def log_run(
        self,
        *,
        model_version: str,
        regulation_version: str,
        artifact_dir: Path,
        params: Mapping[str, str],
        metrics: Mapping[str, float],
    ) -> str:
        """Create a run tagged with `regulation_version`; return its run ID."""
        import mlflow

        if self._tracking_uri:
            mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment)
        with mlflow.start_run(run_name=model_version) as run:
            mlflow.set_tag("regulation_version", regulation_version)
            mlflow.set_tag("model_version", model_version)
            mlflow.log_params(dict(params))
            mlflow.log_metrics(dict(metrics))
            mlflow.log_artifacts(str(artifact_dir))
            return str(run.info.run_id)
