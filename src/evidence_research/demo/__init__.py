"""SYNTHETIC offline scenarios: fictional entities, scripted model, fake corpus. Never real-world evidence."""

from .base import FakeSearch, Scenario, ScriptedLLM


def get_scenario(name: str) -> Scenario:
    from .business import SCENARIO as business
    from .science import SCENARIO as science

    scenarios = {"business": business, "science": science}
    if name not in scenarios:
        raise KeyError(f"unknown demo scenario {name!r}; choose one of {sorted(scenarios)}")
    return scenarios[name]


SCENARIO_NAMES = ("business", "science")
__all__ = ["FakeSearch", "Scenario", "ScriptedLLM", "get_scenario", "SCENARIO_NAMES"]
