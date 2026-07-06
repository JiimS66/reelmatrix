"""The all-outbound compliance gate (Phase 9). A pluggable PolicyGate evaluates content
against a versioned rule pack and returns a decision object {allow, violations} —
decision decoupled from enforcement (OPA/Rego pattern). The newsjacking kill-switch is
just one rule in the pack. Mock rule pack now; a real policy engine swaps in later."""
