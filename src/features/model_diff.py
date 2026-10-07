from collections.abc import Mapping, Sequence
from pathlib import Path

from src.api.schemas.model import FeatureChange, ModelDiff
from src.lib.model_bundle import BundleSource, load_submission
from src.lib.regulation_graph import ActiveRule, GraphClient, fetch_active_rules
from src.lib.z3_client import Z3ClientError, rule_variables

WEIGHT_SUFFIX = "_weight"


def _used(weights: Mapping[str, float | bool]) -> dict[str, float]:
    """Features the model actually uses: non-zero weight."""
    return {k: float(v) for k, v in weights.items() if float(v) != 0.0}


def _rule_index(rules: Sequence[ActiveRule]) -> dict[str, list[str]]:
    """Feature variable -> ids of active rules that mention it."""
    index: dict[str, list[str]] = {}
    for rule in rules:
        try:
            variables = rule_variables(rule.formal_logic)
        except Z3ClientError:
            continue
        for variable in variables:
            index.setdefault(variable, []).append(rule.rule_id)
    return index


def diff_weights(
    before: Mapping[str, float | bool],
    after: Mapping[str, float | bool],
    rules: Sequence[ActiveRule],
    from_version: str,
    to_version: str,
) -> ModelDiff:
    """Features added, removed or re-weighted, with the active rules each touches.

    A change is compliance-impacting when its variable appears in an active rule.
    """
    old, new = _used(before), _used(after)
    index = _rule_index(rules)
    changes: list[FeatureChange] = []
    for variable in sorted(set(old) | set(new)):
        was, now = old.get(variable), new.get(variable)
        if was is not None and now is not None and was == now:
            continue
        kind = "added" if was is None else "removed" if now is None else "changed"
        changes.append(
            FeatureChange(
                feature=variable.removesuffix(WEIGHT_SUFFIX),
                kind=kind,
                before=was,
                after=now,
                affects_rules=index.get(variable, []),
            )
        )
    return ModelDiff(from_version=from_version, to_version=to_version, changes=changes)


def compare(
    graph: GraphClient,
    source: "Path | BundleSource",
    from_version: str,
    to_version: str,
) -> ModelDiff:
    """Diff two model bundles against the rules active now."""
    before = load_submission(from_version, source)
    after = load_submission(to_version, source)
    return diff_weights(
        before.weights,
        after.weights,
        fetch_active_rules(graph),
        before.model_version,
        after.model_version,
    )
