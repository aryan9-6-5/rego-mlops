"""Write demo model bundles for the live demo.

    poetry run python scripts/make_demo_models.py            # into MODEL_ARTIFACT_DIR
    poetry run python scripts/make_demo_models.py --out ./artifacts/models

A bundle is a folder with `profile.json` (feature weights, named `<feature>_weight`)
and `evaluation.json` (held-out predictions). See docs/DEMO.md for what each one
shows. The numbers are made up for the demo; they are not a trained model.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

TRUTH = [1, 0, 1, 0, 1, 0, 1, 0]
GROUPS = ["a", "a", "b", "b"] * 2

ALLOWED = {
    "age_weight": 0.2,
    "occupation_weight": 0.15,
    "income_weight": 0.4,
    "credit_history_weight": 0.25,
}


def evaluation(predictions: list[int] | None = None) -> dict[str, Any]:
    return {
        "y_true": TRUTH,
        "y_pred": predictions if predictions is not None else list(TRUTH),
        "baseline_y_pred": list(TRUTH),
        "groups": GROUPS,
    }


BUNDLES: dict[str, dict[str, Any]] = {
    # Passes every gate against the three demo rules.
    "demo-compliant": {"weights": ALLOWED, "evaluation": evaluation()},
    # Reads the phone's contact list: breaks RBI Directions para 12(i).
    "demo-contact-list": {"weights": {**ALLOWED, "contact_list_weight": 0.12}, "evaluation": evaluation()},
    # Uses a biometric feature: breaks para 13(iii).
    "demo-biometric": {"weights": {**ALLOWED, "biometric_weight": 0.08}, "evaluation": evaluation()},
    # Ignores income: breaks the minimum information in para 7(i).
    "demo-no-income": {"weights": {**ALLOWED, "income_weight": 0.0}, "evaluation": evaluation()},
    # Obeys every rule but approves group a far more than group b: fails fairness.
    "demo-unfair": {"weights": ALLOWED, "evaluation": evaluation([1, 1, 0, 0, 1, 1, 0, 0])},
}


def write_bundles(out: Path) -> list[str]:
    written = []
    for name, bundle in BUNDLES.items():
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "profile.json").write_text(json.dumps({"weights": bundle["weights"]}, indent=2))
        (folder / "evaluation.json").write_text(json.dumps(bundle["evaluation"]))
        written.append(name)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.environ.get("MODEL_ARTIFACT_DIR", "artifacts/models"))
    args = parser.parse_args()
    out = Path(args.out)
    for name in write_bundles(out):
        sys.stdout.write(f"wrote {out / name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
