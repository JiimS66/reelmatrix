"""Phase 12 — LLMOps: systematic evaluation that gates agent/content quality. EvalSuite →
EvalCase → EvalRun, scored by graders (judge prompt as data). Mock-first: graders run the
existing DETERMINISTIC checks (policy/GEO) so eval tests real logic, not a stub; a real
LLM-as-judge for subjective quality swaps in behind the same grader interface. The per-suite
score feeds the agent reliability that drives autonomy."""
