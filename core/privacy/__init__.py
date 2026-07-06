"""Privacy + deployment controls for enterprise on-prem. A DeploymentProfile flips
provider defaults toward local; an EgressGate masks/blocks data leaving the environment;
PII redaction + consent gating compose with the existing PolicyGate (same decision-object
shape). Mock-first; Presidio / a real LLM gateway swap in behind the providers."""
