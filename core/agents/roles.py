"""Role definitions — the job descriptions of the AI digital employees.

The org (which roles exist, and which are AI vs human) becomes per-tenant
configurable in a later phase; this is the built-in default roster.
"""

from core.agents.base import AgentRole

IDEATION = AgentRole(
    key="ideation",
    title="Ideation strategist",
    job_description=(
        "Sharpen the campaign concept, core message, audience insight, and creative "
        "angles before planning; flag when the brief is too vague to proceed."
    ),
)

PLANNING = AgentRole(
    key="planning",
    title="Campaign planner",
    job_description=(
        "Turn the approved concept into a coherent multi-channel plan: channel roles, "
        "content pillars, timeline, deliverables, success metrics, and claim checks."
    ),
)

ROLES: dict[str, AgentRole] = {role.key: role for role in (IDEATION, PLANNING)}
