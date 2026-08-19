"""AssumptionSet: a named, serializable interpretation of the same data.

Two people looking at the Delphi numbers can disagree about the decision question
(what is most dangerous vs. where the largest reduction is achievable), about the
scenario they consider realistic, and about how expensive mitigation is per domain.
An AssumptionSet writes that disagreement down so two of them can be ranked and diffed.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: What the ranking maximizes.
#: - `catastrophic_probability`: the probability of the harm level under `scenario`
#:   ("which domain is worst if we act as assumed").
#: - `achievable_reduction`: bau minus the probability under `scenario`
#:   ("where does moving to that scenario buy the most").
OBJECTIVES = ("catastrophic_probability", "achievable_reduction")

SCENARIOS = ("bau", "pm")

_YAML_SUFFIXES = {".yaml", ".yml"}


@dataclass
class AssumptionSet:
    """A named set of assumptions a domain ranking is computed under.

    Fixed `cost_multipliers` and uncertain `cost_ranges` are relative mitigation costs
    per domain code. A domain's score is divided by its multiplier. Cost is the parameter
    the data does not contain, so it is an assumption by construction, and the default of
    1.0 for every domain is itself the assumption "mitigation costs the same everywhere".
    """

    name: str
    description: str = ""
    decision_question: str = ""
    objective: str = "catastrophic_probability"
    scenario: str = "bau"
    level: str = "catastrophic"
    cost_multipliers: dict[str, float] = field(default_factory=dict)
    default_cost_multiplier: float = 1.0
    cost_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    default_cost_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("an assumption set needs a name")
        if self.objective not in OBJECTIVES:
            raise ValueError(
                f"unknown objective {self.objective!r}; expected one of {list(OBJECTIVES)}"
            )
        if self.scenario not in SCENARIOS:
            raise ValueError(
                f"unknown scenario {self.scenario!r}; expected one of {list(SCENARIOS)}"
            )
        if self.objective == "achievable_reduction" and self.scenario == "bau":
            raise ValueError(
                "achievable_reduction measures bau minus the scenario, so the scenario "
                "has to be a mitigated one (pm), not bau"
            )
        self.cost_multipliers = {
            str(code): float(value) for code, value in self.cost_multipliers.items()
        }
        for code, value in self.cost_multipliers.items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"cost multiplier for {code} must be > 0, got {value}")
        self.default_cost_multiplier = float(self.default_cost_multiplier)
        if (
            not math.isfinite(self.default_cost_multiplier)
            or self.default_cost_multiplier <= 0
        ):
            raise ValueError("default_cost_multiplier must be > 0")

        self.cost_ranges = {
            str(code): self._validate_range(value, f"cost range for {code}")
            for code, value in self.cost_ranges.items()
        }
        overlap = sorted(set(self.cost_multipliers) & set(self.cost_ranges))
        if overlap:
            raise ValueError(
                "a domain cannot have both a fixed cost and a cost range: "
                f"{overlap}"
            )
        if self.default_cost_range is not None:
            self.default_cost_range = self._validate_range(
                self.default_cost_range, "default_cost_range"
            )

    @staticmethod
    def _validate_range(value: Any, label: str) -> tuple[float, float]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"{label} must be [minimum, maximum]")
        lower, upper = map(float, value)
        if (
            not math.isfinite(lower)
            or not math.isfinite(upper)
            or lower <= 0
            or upper <= 0
        ):
            raise ValueError(f"{label} bounds must be > 0")
        if lower > upper:
            raise ValueError(f"{label} minimum must not exceed maximum")
        return lower, upper

    def cost_for(self, domain: str) -> float:
        """Representative cost used by a single ranking.

        A range is represented by its geometric midpoint because costs are relative
        multipliers. Stability analysis samples the full range instead.
        """
        domain = str(domain)
        if domain in self.cost_ranges:
            lower, upper = self.cost_ranges[domain]
            return math.sqrt(lower * upper)
        if domain in self.cost_multipliers:
            return self.cost_multipliers[domain]
        if self.default_cost_range is not None:
            lower, upper = self.default_cost_range
            return math.sqrt(lower * upper)
        return self.default_cost_multiplier

    def cost_range_for(self, domain: str) -> tuple[float, float]:
        """Range sampled by stability analysis; fixed costs become zero-width ranges."""
        domain = str(domain)
        if domain in self.cost_ranges:
            return self.cost_ranges[domain]
        if domain in self.cost_multipliers:
            value = self.cost_multipliers[domain]
            return value, value
        if self.default_cost_range is not None:
            return self.default_cost_range
        return self.default_cost_multiplier, self.default_cost_multiplier

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "decision_question": self.decision_question,
            "objective": self.objective,
            "scenario": self.scenario,
            "level": self.level,
            "default_cost_multiplier": self.default_cost_multiplier,
            "cost_multipliers": dict(self.cost_multipliers),
            "default_cost_range": self.default_cost_range,
            "cost_ranges": dict(self.cost_ranges),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AssumptionSet":
        known = {f for f in cls.__dataclass_fields__}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise ValueError(f"unknown keys in assumption set: {unknown}")
        return cls(**payload)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def to_yaml(self) -> str:
        import yaml

        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        text = self.to_yaml() if path.suffix.lower() in _YAML_SUFFIXES else self.to_json()
        path.write_text(text, encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path | str) -> "AssumptionSet":
        """Read an assumption set from YAML or JSON, picked by file suffix."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in _YAML_SUFFIXES:
            import yaml

            payload = yaml.safe_load(text)
        else:
            payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: expected a mapping, got {type(payload).__name__}")
        return cls.from_dict(payload)
