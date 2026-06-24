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

COPYWRITER = AgentRole(
    key="copywriter",
    title="Copywriter",
    job_description=(
        "Render one platform-optimized post from the shared campaign content core, "
        "the platform's format spec, and the brand — consistent with the other channels "
        "(same core message and approved claims), never inventing unsourced claims."
    ),
)

AUDITOR = AgentRole(
    key="auditor",
    title="Content auditor",
    job_description=(
        "Independently judge a rendered post for brand-tone fit, unsourced claims, "
        "cross-channel consistency, and clarity — the semantic layer above the "
        "deterministic checks. Runs on a different model family than the generator so "
        "their errors decorrelate; failures feed the self-correction retry."
    ),
)

DESIGNER = AgentRole(
    key="designer",
    title="Designer",
    job_description=(
        "Turn the shared campaign core into a per-channel visual: a creative concept, "
        "an image-generation prompt, and alt text, then render the image through the "
        "brand-aware MediaProvider."
    ),
)

ROLES: dict[str, AgentRole] = {
    role.key: role for role in (IDEATION, PLANNING, COPYWRITER, AUDITOR, DESIGNER)
}
