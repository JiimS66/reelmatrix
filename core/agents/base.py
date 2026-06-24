"""The digital-employee abstraction.

Every AI worker is an ``Agent`` with a ``role`` (who they are, what they own) and
a uniform ``run(context) -> dict`` interface: it reads its context slice off the
shared blackboard and produces a json-able, schema-validated output. The runner
treats humans and AI agents the same way behind this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.llm.base import BaseLLMClient


@dataclass(frozen=True)
class AgentRole:
    key: str
    title: str
    job_description: str


class Agent(ABC):
    role: AgentRole

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm_client = llm_client

    @abstractmethod
    async def run(self, context: dict) -> dict:
        """Produce this role's output (json-able dict) from its context slice."""
        raise NotImplementedError
