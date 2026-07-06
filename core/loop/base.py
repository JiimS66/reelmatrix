"""The Loop abstraction — loop engineering made concrete.

A Loop is a *recursive goal*: define a purpose, and the agent iterates toward it one step
at a time, where each step is observe → decide(LLM) → act → verify, feeding the result back
into the next turn. Both product loops are instances of this one engine — circuit A
(strategy co-creation) and, later, circuit B (marketing operations) — differing only in
goal / step / when-to-escalate.

The brakes here are deliberate (the anti-'loopmaxxing' discipline): an explicit `is_done`
so termination is a decision not an accident, and a `max_turns` budget so a loop that isn't
converging hands back to the human instead of spinning. "Build the loop like someone who
intends to stay the engineer, not just the person who presses go."
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

State = dict[str, Any]
Signal = dict[str, Any]


class Loop(ABC):
    @property
    @abstractmethod
    def goal(self) -> str:
        """The recursive goal this loop iterates toward."""

    @property
    def max_turns(self) -> int:
        """Loopmaxxing guard: stop iterating past this many turns even if not 'done',
        and hand back to the human rather than spin forever."""
        return 12

    @abstractmethod
    def is_done(self, state: State) -> bool:
        """Has the goal been met / did the human hand off? Termination is explicit."""

    @abstractmethod
    async def step(self, state: State, signal: Signal) -> State:
        """One turn: observe(state + signal) → decide(LLM) → act → verify → new state."""

    async def advance(self, state: State, signal: Signal) -> State:
        """Run one *guarded* turn: refuse if already done; stop and hand back if the turn
        budget is spent; otherwise take a real step. This is where the brakes live so every
        instance inherits them."""
        if self.is_done(state):
            return state
        if len(state.get("turns", [])) >= self.max_turns:
            return {**state, "status": "done", "stop_reason": "max_turns"}
        return await self.step(state, signal)
