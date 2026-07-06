"""Circuit A — the strategy co-creation loop, the first instance of the Loop engine.

One step = take everything fed so far + the user's latest reaction, ask the advisor (LLM
with industry priors) to update the one-page strategy, mark what's still a guess, and
surface the next hypothesis to react to. Stateful across turns (the draft + turn history
live in the StrategySession), so it's a real loop, not a goldfish. Done when the human says
"good enough, let's make content" (status → done), or the Loop's max_turns brake trips."""

from core.llm.base import BaseLLMClient
from core.loop.base import Loop, Signal, State
from core.strategy.advisor import draft_strategy


class StrategyLoop(Loop):
    def __init__(self, client: BaseLLMClient) -> None:
        self._client = client

    @property
    def goal(self) -> str:
        return "A marketing strategy the marketer recognizes as theirs."

    def is_done(self, state: State) -> bool:
        return state.get("status") == "done"

    async def step(self, state: State, signal: Signal) -> State:
        # observe: assemble everything fed so far + any new material this turn
        inputs = list(state.get("inputs") or [])
        inputs += list(signal.get("inputs") or [])
        feedback = signal.get("feedback")
        # decide + act: the advisor updates the draft from inputs + prior + feedback
        draft = await draft_strategy(
            self._client, inputs=inputs, prior=state.get("draft"), feedback=feedback
        )
        # observe: record the turn so the loop is replayable and the history is visible
        turns = list(state.get("turns") or [])
        turns.append({"feedback": feedback, "draft": draft})
        return {**state, "inputs": inputs, "draft": draft, "turns": turns}
