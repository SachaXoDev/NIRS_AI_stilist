"""Explicit search settings, independent of a web framework."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RAGConfig:
    top_k: dict[str, int] = field(default_factory=lambda: {
        "tops": 3, "bottoms": 3, "shoes": 3, "outerwear": 2, "accessories": 2,
    })
    candidate_pool: int = 30
    rrf_c: int = 60
    outerwear_below_c: float = 12
    include_accessories: bool = True

    def __post_init__(self) -> None:
        if self.candidate_pool < 1 or self.rrf_c < 1:
            raise ValueError("candidate_pool and rrf_c must be positive")
        allowed = {"tops", "bottoms", "shoes", "outerwear", "accessories"}
        if set(self.top_k) != allowed or any(k < 1 for k in self.top_k.values()):
            raise ValueError("top_k must contain all five categories with positive budgets")
        if self.candidate_pool < max(self.top_k.values()):
            raise ValueError("candidate_pool must cover each slot budget")
