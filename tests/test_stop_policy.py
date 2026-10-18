from evidence_research.config import Heuristics
from evidence_research.models import StopReason
from evidence_research.orchestration.stop_policy import CriticalClaim, StopInputs, decide

H = Heuristics()


def _inputs(**kw) -> StopInputs:
    base = dict(iteration=1, max_iterations=5, exhausted_resource=None,
                critical_claims=[CriticalClaim("c1", 0.4, False, 1.0)], researchable_gaps=3, new_independent_roots_last_round=2)
    return StopInputs(**{**base, **kw})


def test_stops_on_sufficient_evidence():
    d = decide(_inputs(critical_claims=[CriticalClaim("c1", 0.8, False, 1.0), CriticalClaim("c2", 0.75, False, 0.6)]), 0.7, H)
    assert d.stop and d.reason is StopReason.SUCCESS


def test_open_high_importance_contradiction_blocks_success():
    d = decide(_inputs(critical_claims=[CriticalClaim("c1", 0.9, True, 1.0)]), 0.7, H)
    assert not d.stop


def test_stops_on_convergence():
    history = [{"c1": 0.60}, {"c1": 0.61}, {"c1": 0.62}]
    d = decide(_inputs(iteration=3, posterior_history=history, new_independent_roots_last_round=1), 0.7, H)
    assert d.stop and d.reason is StopReason.CONVERGENCE


def test_no_convergence_while_beliefs_move():
    history = [{"c1": 0.50}, {"c1": 0.70}, {"c1": 0.45}]
    assert not decide(_inputs(iteration=3, posterior_history=history, new_independent_roots_last_round=1), 0.7, H).stop


def test_stops_on_budget_exhaustion():
    assert decide(_inputs(exhausted_resource="search"), 0.7, H).reason is StopReason.BUDGET_EXHAUSTED
    assert decide(_inputs(iteration=5), 0.7, H).reason is StopReason.BUDGET_EXHAUSTED


def test_stops_on_diminishing_returns():
    d = decide(_inputs(iteration=2, new_independent_roots_last_round=0), 0.7, H)
    assert d.stop and d.reason is StopReason.DIMINISHING_RETURNS


def test_unresolvable_when_only_dead_gaps_remain():
    d = decide(_inputs(researchable_gaps=0, unresolvable_gaps=2), 0.7, H)
    assert d.stop and d.reason is StopReason.UNRESOLVABLE


def test_continues_otherwise():
    d = decide(_inputs(), 0.7, H)
    assert not d.stop and "below sufficiency" in d.explanation
