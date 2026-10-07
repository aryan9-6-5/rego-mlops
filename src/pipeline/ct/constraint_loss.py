from collections.abc import Sequence
from typing import TYPE_CHECKING

from src.lib.regulation_graph import ActiveRule
from src.lib.z3_client import forced_zero_variables

if TYPE_CHECKING:
    import torch


def prohibited_features(rules: Sequence[ActiveRule]) -> list[str]:
    """Feature columns that active rules force to zero weight.

    A rule such as `(assert (= pin_code_weight 0))` prohibits `pin_code`.
    Found with Z3: a variable is prohibited when the rule cannot hold with it
    non-zero.
    """
    names: set[str] = set()
    for rule in rules:
        names.update(forced_zero_variables(rule.formal_logic))
    return sorted(n.removesuffix("_weight") for n in names)


def prohibited_indices(
    feature_names: Sequence[str], prohibited: Sequence[str]
) -> list[int]:
    banned = set(prohibited)
    return [i for i, name in enumerate(feature_names) if name in banned]


def constraint_penalty(
    weights: "torch.Tensor",
    prohibited_idx: Sequence[int],
    strength: float = 10.0,
) -> "torch.Tensor":
    """Penalty added to a PyTorch model's loss for using prohibited features.

    `weights` holds one weight per input feature (for example the first layer's
    column norms). The result is `strength * sum(|w_i|)` over prohibited
    features, so training is pushed to zero them out.
    """
    import torch

    if not prohibited_idx:
        return torch.zeros((), dtype=weights.dtype, device=weights.device)
    index = torch.tensor(list(prohibited_idx), device=weights.device)
    return strength * weights[index].abs().sum()
