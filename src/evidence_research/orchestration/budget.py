"""Hard budget enforcement. Every search, extraction and model call is charged here first."""

from __future__ import annotations

import threading

from ..config import Budget


class BudgetExceeded(RuntimeError):
    def __init__(self, resource: str, limit: int) -> None:
        super().__init__(f"{resource} budget exhausted (limit {limit})")
        self.resource = resource


class BudgetTracker:
    def __init__(self, budget: Budget, reserve_model_calls: int = 3) -> None:
        self.budget = budget
        self.reserve = min(reserve_model_calls, max(0, budget.max_model_calls - 1))  # kept for synthesis
        self.searches = 0
        self.extractions = 0
        self.model_calls = 0
        self._lock = threading.Lock()

    def _charge(self, attr: str, limit: int, n: int, name: str) -> None:
        with self._lock:
            if getattr(self, attr) + n > limit:
                raise BudgetExceeded(name, limit)
            setattr(self, attr, getattr(self, attr) + n)

    def charge_search(self) -> None:
        self._charge("searches", self.budget.max_search_queries, 1, "search")

    def charge_extractions(self, n: int) -> None:
        self._charge("extractions", self.budget.max_extracted_sources, n, "extraction")

    def charge_model_call(self, final: bool = False) -> None:
        """Research calls stop at max - reserve, so the report can always be written."""
        limit = self.budget.max_model_calls if final else self.budget.max_model_calls - self.reserve
        self._charge("model_calls", limit, 1, "model call")

    def remaining_extractions(self) -> int:
        return max(0, self.budget.max_extracted_sources - self.extractions)

    def remaining_searches(self) -> int:
        return max(0, self.budget.max_search_queries - self.searches)

    def nearly_exhausted(self) -> str | None:
        """Model calls are needed for synthesis, so stop researching before they run out."""
        if self.searches >= self.budget.max_search_queries:
            return "search"
        if self.extractions >= self.budget.max_extracted_sources:
            return "extraction"
        if self.model_calls >= self.budget.max_model_calls - self.reserve - 2:
            return "model call"
        return None
