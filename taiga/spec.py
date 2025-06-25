from dataclasses import dataclass

import numpy as np


@dataclass(kw_only=True, frozen=True)
class Grade:
    """The grade to return within the mcp.grade_problem tool."""

    subscores: dict[str, float]
    weights: dict[str, float]
    metadata: dict[str, str] | None = None

    @property
    def score(self):
        assert self.subscores.keys() == self.weights.keys()
        assert np.isclose(sum(self.weights.values()), 1)
        assert min(self.subscores.values()) >= 0
        assert max(self.subscores.values()) <= 1

        score = sum([self.subscores[key] * self.weights[key] for key in self.subscores.keys()])
        assert score >= 0 and score <= 1

        return score
