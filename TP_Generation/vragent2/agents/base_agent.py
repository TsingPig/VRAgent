"""
Base Agent — Abstract interface that all four agents must implement.

Enforces the Contract-based Interaction Protocol (§B2.4):
every agent has typed input and typed output conforming to ``contracts.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base for Planner / Verifier / Executor / Observer."""

    name: str = "BaseAgent"

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's task and return a contract-conforming output.

        Parameters
        ----------
        input_data : dict
            Agent-specific input payload.

        Returns
        -------
        dict
            Must match the agent's output schema defined in ``contracts.py``.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.name}>"
