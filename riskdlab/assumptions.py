"""AssumptionSet: a named, serializable interpretation of the same data.

Two people looking at the Delphi numbers can disagree about the decision question
(what is most dangerous vs. where the largest reduction is achievable), about the
scenario they consider realistic, and about how expensive mitigation is per domain.
An AssumptionSet writes that disagreement down so two of them can be ranked and diffed.
"""

from __future__ import annotations

import json
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

    `cost_multipliers` are relative mitigation costs per domain code (`{"6.4": 3.0}`);
    a domain's score is divided by its multiplier. Cost is the parameter the data does
    not contain, so it is an assumption by construction, and the default of 1.0 for
    every domain is itself the assumption "mitigation costs the same everywhere".
    """

    name: str
    description: str = ""
    decision_question: str = ""
    objective: str = "catastrophic_probability"
    scenario: str = "bau"
    level: str = "catastrophic"
    cost_multipliers: dict[str, float] = field(default_factory=dict)
    default_cost_multiplier: float = 1.0

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
            if value <= 0:
                raise ValueError(f"cost multiplier for {code} must be > 0, got {value}")
        self.default_cost_multiplier = float(self.default_cost_multiplier)
        if self.default_cost_multiplier <= 0:
            raise ValueError("default_cost_multiplier must be > 0")

    def cost_for(self, domain: str) -> float:
        return self.cost_multipliers.get(str(domain), self.default_cost_multiplier)

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
