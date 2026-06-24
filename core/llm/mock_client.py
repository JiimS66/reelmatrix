import json
from typing import Any, Dict, List, Type

from core.llm.base import BaseLLMClient, LLMResponseValidationError, StructuredModel


class MockLLMClient(BaseLLMClient):
    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        return "Deterministic mock LLM response."

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[StructuredModel],
    ) -> StructuredModel:
        payload = self._parse_prompt_payload(user_prompt)
        builders = {
            "IdeationResult": self._build_ideation_result,
            "CampaignPlan": self._build_campaign_plan,
        }
        builder = builders.get(response_model.__name__)
        if builder is None:
            raise LLMResponseValidationError(
                f"MockLLMClient has no deterministic response for {response_model.__name__}"
            )
        return self.validate_object_response(builder(payload), response_model)

    @staticmethod
    def _parse_prompt_payload(user_prompt: str) -> Dict[str, Any]:
        try:
            payload = json.loads(user_prompt)
        except json.JSONDecodeError as exc:
            raise LLMResponseValidationError(
                "MockLLMClient expected the agent user prompt to be valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise LLMResponseValidationError(
                "MockLLMClient expected a JSON object prompt payload"
            )
        return payload

    @staticmethod
    def _build_ideation_result(payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        prompt = str(request.get("user_prompt", ""))
        combined = " ".join(
            str(request.get(field, ""))
            for field in (
                "product_description",
                "target_audience",
                "marketing_goal",
                "user_prompt",
            )
        ).lower()
        incomplete_markers = ("needs more ideation", "unknown", "tbd", "not sure")
        explicitly_incomplete = "needs more ideation" in prompt.lower()
        explicitly_ready = "ready for planning" in prompt.lower()
        sufficiently_detailed = (
            len(str(request.get("product_description", ""))) >= 20
            and len(str(request.get("target_audience", ""))) >= 12
            and len(str(request.get("marketing_goal", ""))) >= 12
            and not any(marker in combined for marker in incomplete_markers[1:])
        )
        is_ready = not explicitly_incomplete and (explicitly_ready or sufficiently_detailed)
        product_name = str(request.get("product_name", "the product"))
        audience = str(request.get("target_audience", "the target audience"))
        goal = str(request.get("marketing_goal", "the campaign goal"))
        is_developer_tool = MockLLMClient._is_developer_tool_template(request)

        if not is_ready:
            return {
                "campaign_concept": f"Clarify the strongest launch idea for {product_name}.",
                "core_message": "The campaign promise needs more evidence and specificity.",
                "target_audience_insight": f"More detail is needed about {audience} and their buying trigger.",
                "recommended_angles": [
                    "Lead with the audience's highest-cost current problem",
                    "Demonstrate a concrete before-and-after outcome",
                ],
                "risks_or_assumptions": [
                    "The primary pain point has not been validated",
                    "The desired conversion action may be too broad",
                ],
                "follow_up_questions": [
                    "What single pain point should this campaign prioritize?",
                    "What proof or customer evidence can support the campaign promise?",
                    "What exact action should the audience take after seeing the campaign?",
                ],
                "is_ready_for_planning": False,
            }

        if is_developer_tool:
            return {
                "campaign_concept": f"The Developer Trust Launch for {product_name}",
                "core_message": (
                    f"Give AI-native engineering teams a verification loop they can trust "
                    f"while they work toward {goal}."
                ),
                "target_audience_insight": (
                    f"{audience} adopt tools when the workflow fits their terminal, IDE, "
                    "and pull-request habits without asking them to babysit another dashboard."
                ),
                "recommended_angles": [
                    "Make the verification gap concrete for AI-generated code",
                    "Show the product living inside developer workflows",
                    "Use sourced proof and technical walkthroughs instead of vague AI claims",
                ],
                "risks_or_assumptions": [
                    "Developer audiences will reject unsourced performance claims",
                    "The campaign needs a working quickstart or live demo path",
                ],
                "follow_up_questions": [],
                "is_ready_for_planning": True,
            }

        return {
            "campaign_concept": f"The Lean Growth Launch for {product_name}",
            "core_message": f"Turn a clear product story into measurable marketing momentum toward {goal}.",
            "target_audience_insight": f"{audience} need credible, practical progress without adding operational overhead.",
            "recommended_angles": [
                "Replace fragmented campaign work with one guided workflow",
                "Show measurable progress for a resource-constrained team",
                "Use founder-relevant examples instead of generic AI claims",
            ],
            "risks_or_assumptions": [
                "The audience already recognizes campaign planning as a bottleneck",
                "Organic proof can establish enough trust for the initial conversion",
            ],
            "follow_up_questions": [],
            "is_ready_for_planning": True,
        }

    @staticmethod
    def _build_campaign_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        ideation = payload.get("ideation_result", {})
        product_name = str(request.get("product_name", "Product"))
        marketing_goal = str(request.get("marketing_goal", "Generate qualified demand"))
        target_audience = str(request.get("target_audience", "Target buyers"))
        target_market = str(request.get("target_market") or "United States")
        output_language = str(request.get("output_language") or "English")
        campaign_duration = str(request.get("campaign_duration") or "4 weeks")
        selected_channels = MockLLMClient._selected_channels(request)
        brand_context = MockLLMClient._brand_context(request)
        is_developer_tool = MockLLMClient._is_developer_tool_template(request)
        core_message = str(ideation.get("core_message", "Create measurable marketing momentum."))

        return {
            "campaign_name": (
                f"{product_name} Developer Trust Launch"
                if is_developer_tool
                else f"{product_name} Cross-Border Launch Sprint"
            ),
            "campaign_objective": marketing_goal,
            "target_audience": target_audience,
            "core_message": core_message,
            "channels": MockLLMClient._build_channel_plans(
                selected_channels,
                core_message,
                campaign_duration,
                is_developer_tool,
            ),
            "content_pillars": MockLLMClient._build_content_pillars(is_developer_tool),
            "timeline": MockLLMClient._build_timeline(is_developer_tool),
            "deliverables": MockLLMClient._build_deliverables(
                selected_channels,
                is_developer_tool,
            ),
            "success_metrics": MockLLMClient._build_success_metrics(is_developer_tool),
            "assumptions": MockLLMClient._build_assumptions(is_developer_tool),
            "execution_notes": MockLLMClient._build_execution_notes(
                output_language,
                target_market,
                brand_context,
                is_developer_tool,
            ),
            "market_adaptation": MockLLMClient._build_market_adaptation(
                target_market,
                output_language,
                is_developer_tool,
            ),
            "draft_assets": MockLLMClient._build_draft_assets(
                product_name,
                target_market,
                output_language,
                core_message,
                selected_channels,
                brand_context,
                is_developer_tool,
            ),
            "claim_checks": MockLLMClient._build_claim_checks(brand_context),
            "timely_angles": (
                [
                    "Ride the surge in AI coding agents shipping unverified code",
                    "Tie the launch to open-source CLI momentum on GitHub",
                    "Make 'verification' the season's developer-trust theme",
                ]
                if is_developer_tool
                else [
                    "Lead with the shift to lean, AI-assisted marketing teams",
                    "Tie the launch to the quarter's cross-border go-to-market push",
                ]
            ),
        }

    @staticmethod
    def _selected_channels(request: Dict[str, Any]) -> List[str]:
        channels = request.get("selected_channels") or [
            "LinkedIn",
            "Email",
            "Landing Page",
            "X / Twitter",
        ]
        return [str(channel) for channel in channels if str(channel).strip()]

    @staticmethod
    def _is_developer_tool_template(request: Dict[str, Any]) -> bool:
        return str(request.get("campaign_template") or "").strip().lower() == "developer_tool"

    @staticmethod
    def _brand_context(request: Dict[str, Any]) -> Dict[str, Any]:
        context = request.get("brand_context") or {}
        return context if isinstance(context, dict) else {}

    @staticmethod
    def _context_list(brand_context: Dict[str, Any], key: str) -> List[str]:
        value = brand_context.get(key) or []
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _proof_points(brand_context: Dict[str, Any]) -> List[Dict[str, str]]:
        value = brand_context.get("proof_points") or []
        if not isinstance(value, list):
            return []
        proof_points = []
        for item in value:
            if isinstance(item, dict):
                claim = str(item.get("claim") or "").strip()
                source = str(item.get("source") or "").strip()
                if claim:
                    proof_points.append({"claim": claim, "source": source})
        return proof_points

    @staticmethod
    def _build_channel_plans(
        selected_channels: List[str],
        core_message: str,
        campaign_duration: str,
        is_developer_tool: bool,
    ) -> List[Dict[str, Any]]:
        plans = {
            "linkedin": {
                "channel_name": "LinkedIn",
                "role_in_campaign": "Build category awareness and founder credibility",
                "content_types": ["Founder posts", "Problem-solution carousels"],
                "key_messages": [core_message],
                "cadence": f"Three posts per week for {campaign_duration}",
                "success_metrics": ["Qualified profile visits", "Waitlist conversions"],
            },
            "email": {
                "channel_name": "Email",
                "role_in_campaign": "Convert interested prospects into waitlist signups",
                "content_types": ["Launch sequence", "Use-case proof email"],
                "key_messages": ["A practical campaign system for lean teams"],
                "cadence": "One email per week plus launch-day email",
                "success_metrics": ["Click-through rate", "Waitlist conversion rate"],
            },
            "landing page": {
                "channel_name": "Landing Page",
                "role_in_campaign": "Turn campaign traffic into a clear conversion path",
                "content_types": ["Hero section", "Proof block", "CTA module"],
                "key_messages": ["Create the first campaign package without a full marketing team"],
                "cadence": "Publish before the first social push",
                "success_metrics": ["Visitor-to-signup conversion", "CTA click rate"],
            },
            "x / twitter": {
                "channel_name": "X / Twitter",
                "role_in_campaign": "Test sharp founder-facing hooks quickly",
                "content_types": ["Launch thread", "Short proof posts"],
                "key_messages": ["Move from idea to editable assets in one focused sprint"],
                "cadence": "Two short posts and one thread per week",
                "success_metrics": ["Profile visits", "Thread engagement", "Waitlist clicks"],
            },
            "blog": {
                "channel_name": "Blog",
                "role_in_campaign": "Explain the product category with enough detail to earn developer trust",
                "content_types": ["Launch essay", "Technical walkthrough"],
                "key_messages": [core_message],
                "cadence": "One launch post plus one proof-led follow-up",
                "success_metrics": ["Qualified demo clicks", "Time on page", "Newsletter signups"],
            },
            "github / cli": {
                "channel_name": "GitHub / CLI",
                "role_in_campaign": "Turn interest into hands-on evaluation inside the developer workflow",
                "content_types": ["README quickstart", "CLI install snippet", "Example command"],
                "key_messages": ["A verifier should be easy for an agent or developer to run"],
                "cadence": "Update before every launch push",
                "success_metrics": ["CLI installs", "API key starts", "GitHub stars"],
            },
            "community": {
                "channel_name": "Community",
                "role_in_campaign": "Start technical conversations where AI builders already compare workflows",
                "content_types": ["Discord post", "Hacker News style launch note", "Founder reply prompts"],
                "key_messages": ["AI coding needs a live verification loop, not another static checklist"],
                "cadence": "Two community posts during launch week",
                "success_metrics": ["Qualified replies", "Demo requests", "Community signups"],
            },
        }
        if is_developer_tool:
            plans["linkedin"]["role_in_campaign"] = "Reach engineering leaders with a concise verification-gap narrative"
            plans["email"]["role_in_campaign"] = "Convert engineering leaders and developer-tool buyers into demos"
            plans["x / twitter"]["role_in_campaign"] = "Test sharp developer hooks around agentic coding regressions"

        result = []
        for channel in selected_channels:
            key = channel.strip().lower()
            result.append(plans.get(key, plans["linkedin"]) | {"channel_name": channel})
        return result or [plans["linkedin"]]

    @staticmethod
    def _build_content_pillars(is_developer_tool: bool) -> List[str]:
        if is_developer_tool:
            return [
                "The verification gap created by AI-generated code",
                "Live-browser and API testing inside agent workflows",
                "Source-backed proof that earns developer trust",
                "A quickstart path from curiosity to first test run",
            ]
        return [
            "The cost of fragmented campaign work",
            "Practical AI workflows for lean marketing teams",
            "Proof that a small team can move faster without adding headcount",
        ]

    @staticmethod
    def _build_timeline(is_developer_tool: bool) -> List[Dict[str, Any]]:
        if is_developer_tool:
            return [
                {
                    "phase_name": "Proof foundation",
                    "timing": "Week 1",
                    "objective": "Turn sourced claims into developer-safe launch messaging",
                    "key_activities": [
                        "Validate every funding, user-count, performance, and customer claim",
                        "Publish the CLI quickstart and launch blog draft",
                    ],
                },
                {
                    "phase_name": "Developer activation",
                    "timing": "Weeks 2-3",
                    "objective": "Drive hands-on trials from engineering and AI-agent users",
                    "key_activities": [
                        "Ship technical social posts and community launch notes",
                        "Send engineering-lead emails with one concrete workflow example",
                    ],
                },
                {
                    "phase_name": "Evidence loop",
                    "timing": "Week 4",
                    "objective": "Convert initial interest into proof-led follow-up content",
                    "key_activities": [
                        "Collect demo objections and failed-message patterns",
                        "Rewrite the strongest proof points into follow-up assets",
                    ],
                },
            ]
        return [
            {
                "phase_name": "Foundation",
                "timing": "Week 1",
                "objective": "Establish the problem and campaign promise",
                "key_activities": [
                    "Publish the category narrative",
                    "Finalize the landing-page hero message",
                ],
            },
            {
                "phase_name": "Activation",
                "timing": "Weeks 2-3",
                "objective": "Drive qualified prospects to the waitlist",
                "key_activities": [
                    "Publish proof-led social content",
                    "Run the email launch sequence",
                ],
            },
            {
                "phase_name": "Learning loop",
                "timing": "Week 4",
                "objective": "Identify the message that creates the strongest intent",
                "key_activities": [
                    "Compare channel engagement",
                    "Refine the strongest angle for the next sprint",
                ],
            },
        ]

    @staticmethod
    def _build_deliverables(
        selected_channels: List[str],
        is_developer_tool: bool,
    ) -> List[Dict[str, Any]]:
        if is_developer_tool:
            return [
                {
                    "name": "Developer launch blog",
                    "channel": "Blog",
                    "format": "Problem, proof, workflow, CTA",
                    "purpose": "Explain why AI-generated code needs an autonomous verifier",
                },
                {
                    "name": "CLI quickstart block",
                    "channel": "GitHub / CLI",
                    "format": "Install command, first run, expected output",
                    "purpose": "Turn developer interest into a first hands-on test run",
                },
                {
                    "name": "Engineering-lead email",
                    "channel": "Email",
                    "format": "Short outbound sequence",
                    "purpose": "Start qualified conversations with teams adopting AI coding agents",
                },
                {
                    "name": "Technical social thread",
                    "channel": "X / Twitter",
                    "format": "Launch thread",
                    "purpose": "Make the verification gap easy to understand and share",
                },
            ]
        return [
            {
                "name": "Founder launch narrative",
                "channel": "LinkedIn",
                "format": "Text post",
                "purpose": "Introduce the campaign problem and point of view",
            },
            {
                "name": "Waitlist conversion sequence",
                "channel": "Email",
                "format": "Three-email sequence",
                "purpose": "Convert campaign interest into qualified signups",
            },
            {
                "name": "Landing-page hero section",
                "channel": "Landing Page",
                "format": "Headline, subhead, and CTA",
                "purpose": "Turn campaign traffic into a clear next step",
            },
        ]

    @staticmethod
    def _build_success_metrics(is_developer_tool: bool) -> List[str]:
        if is_developer_tool:
            return [
                "Qualified developer signups",
                "CLI installs or API key starts",
                "Demo requests from engineering teams",
                "Source-backed asset approval rate",
            ]
        return [
            "Qualified waitlist signups",
            "Landing-page conversion rate",
            "Content-to-waitlist conversion rate",
        ]

    @staticmethod
    def _build_assumptions(is_developer_tool: bool) -> List[str]:
        if is_developer_tool:
            return [
                "A working quickstart or demo path is available before launch",
                "All numeric claims have a source or will be marked for validation",
            ]
        return [
            "The product has a functioning waitlist destination",
            "The team can provide one proof point or founder example per week",
        ]

    @staticmethod
    def _build_execution_notes(
        output_language: str,
        target_market: str,
        brand_context: Dict[str, Any],
        is_developer_tool: bool,
    ) -> List[str]:
        notes = [
            "Keep calls to action consistent across channels",
            "Review results weekly and refine messages without changing the core promise",
            f"Write primary campaign materials in {output_language} for {target_market} buyers",
        ]
        forbidden_words = MockLLMClient._context_list(brand_context, "forbidden_words")
        tone_rules = MockLLMClient._context_list(brand_context, "tone_rules")
        competitors = MockLLMClient._context_list(brand_context, "competitors")
        if is_developer_tool:
            notes.append("Prefer technical specificity over broad AI productivity language")
        if forbidden_words:
            notes.append(f"Avoid these words or phrases: {', '.join(forbidden_words)}")
        if tone_rules:
            notes.append(f"Follow tone rules: {'; '.join(tone_rules)}")
        if competitors:
            notes.append(f"Differentiate carefully from: {', '.join(competitors)}")
        return notes

    @staticmethod
    def _build_market_adaptation(
        target_market: str,
        output_language: str,
        is_developer_tool: bool,
    ) -> Dict[str, Any]:
        if is_developer_tool:
            return {
                "target_market": target_market,
                "language_strategy": (
                    f"Use precise {output_language} for developer audiences. Explain the "
                    "workflow, show the command or proof path, and avoid vague AI magic language."
                ),
                "positioning_recommendations": [
                    "Lead with the verification gap, not generic test automation",
                    "Show where the product fits inside terminal, IDE, and pull-request workflows",
                    "Make every numeric or customer claim source-backed or marked for validation",
                ],
                "localization_notes": [
                    "Developer-tool buyers expect concrete setup steps and failure examples",
                    "Use technical language that is direct but not overloaded with jargon",
                    "Pair every high-level claim with a workflow artifact or proof source",
                ],
                "cultural_risks": [
                    "Do not overstate autonomous testing if human review is still required",
                    "Do not imply support for integrations that are not live",
                ],
                "suggested_phrases": [
                    "A QA loop your coding agent can actually run",
                    "Verify AI-generated code before it reaches users",
                    "Turn failure bundles into fixes your agent can act on",
                ],
            }
        return {
            "target_market": target_market,
            "language_strategy": (
                f"Use concise {output_language} copy with concrete outcomes, practical proof, "
                "and no literal translation of founder jargon."
            ),
            "positioning_recommendations": [
                "Lead with the cost of doing campaign work manually",
                "Show a before-and-after workflow instead of broad AI claims",
                "Make privacy and model choice visible for cost-sensitive small teams",
            ],
            "localization_notes": [
                "Use direct benefit-led headlines for English-speaking buyers",
                "Translate product value, not Chinese startup phrasing, when adapting copy",
                "Use proof points that match the target market's buying expectations",
            ],
            "cultural_risks": [
                "Avoid exaggerated automation promises before integrations exist",
                "Avoid implying external platform publishing is already supported",
            ],
            "suggested_phrases": [
                "Build your first campaign package before your next standup",
                "Choose local, Qwen, or GPT based on cost, privacy, and copy quality",
                "Turn a product idea into editable channel-ready marketing assets",
            ],
        }

    @staticmethod
    def _build_draft_assets(
        product_name: str,
        target_market: str,
        output_language: str,
        core_message: str,
        selected_channels: List[str],
        brand_context: Dict[str, Any],
        is_developer_tool: bool,
    ) -> List[Dict[str, Any]]:
        if is_developer_tool:
            assets = MockLLMClient._developer_tool_assets(
                product_name,
                target_market,
                output_language,
                core_message,
                brand_context,
            )
        else:
            assets = [
                {
                    "asset_type": "Social post",
                    "channel": "LinkedIn",
                    "title": f"Founder narrative for {product_name}",
                    "content": (
                        f"Most lean teams do not need another blank content calendar. They need a "
                        f"clear way to turn product context into campaign-ready work. {product_name} "
                        f"helps small teams move from brief to plan to first-draft assets without "
                        f"waiting for a full marketing function.\n\n{core_message}"
                    ),
                    "call_to_action": "Join the waitlist to build your first campaign sprint.",
                    "notes": ["Keep the tone founder-led and practical", "Add one concrete proof point before posting"],
                },
                {
                    "asset_type": "Email sequence",
                    "channel": "Email",
                    "title": f"Three-email waitlist sequence for {target_market}",
                    "content": (
                        "Email 1: Name the campaign planning bottleneck and introduce the new workflow.\n"
                        "Email 2: Show how model choice changes cost, privacy, and copy quality.\n"
                        "Email 3: Invite the reader to generate one campaign package and compare outputs."
                    ),
                    "call_to_action": "Generate a campaign package this week.",
                    "notes": [f"Write in {output_language}", "Keep each email under 180 words"],
                },
                {
                    "asset_type": "Landing page hero",
                    "channel": "Landing Page",
                    "title": "Hero section",
                    "content": (
                        "Headline: Build your first cross-border campaign package in one focused session.\n"
                        "Subhead: Enter your product, market, and goal, then generate an editable plan, "
                        "channel assets, and localization notes with local, Qwen, or GPT models."
                    ),
                    "call_to_action": "Create my campaign package",
                    "notes": ["Use this as the first above-the-fold test", "Pair with a short product screenshot"],
                },
                {
                    "asset_type": "Launch thread",
                    "channel": "X / Twitter",
                    "title": "Problem-solution thread",
                    "content": (
                        "1/ Small teams often know the product, but not the campaign structure.\n"
                        "2/ The hard part is turning scattered context into channel-ready work.\n"
                        "3/ ReelMatrix creates the strategy, first drafts, and market notes in one workflow.\n"
                        "4/ Start with the plan, edit the assets, export the campaign package."
                    ),
                    "call_to_action": "Try the campaign studio with your next product idea.",
                    "notes": ["Swap in a real founder pain point", "Use one metric if available"],
                },
            ]
        selected = {channel.strip().lower() for channel in selected_channels}
        matched = [asset for asset in assets if asset["channel"].lower() in selected]
        return matched or assets[:3]

    @staticmethod
    def _developer_tool_assets(
        product_name: str,
        target_market: str,
        output_language: str,
        core_message: str,
        brand_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        proof_points = MockLLMClient._proof_points(brand_context)
        target_personas = MockLLMClient._context_list(brand_context, "target_personas")
        primary_claim = proof_points[0]["claim"] if proof_points else "Add one verified proof point before launch."
        persona_line = ", ".join(target_personas) or "AI-native engineering teams"
        source_note = proof_points[0].get("source") if proof_points else "Needs validation"
        return [
            {
                "asset_type": "Founder post",
                "channel": "LinkedIn",
                "title": f"Developer trust narrative for {product_name}",
                "content": (
                    f"AI coding has made shipping faster, but verification is now the bottleneck. "
                    f"{product_name} should lead with a concrete workflow for {persona_line}: "
                    "run the product against a live app, return an actionable failure bundle, and help "
                    "the agent fix its own work.\n\n"
                    f"Proof to cite: {primary_claim}.\n\n{core_message}"
                ),
                "call_to_action": "Try the verifier on a live app or book a technical walkthrough.",
                "notes": [
                    f"Source: {source_note}",
                    "Keep the post technical and avoid vague productivity claims",
                ],
            },
            {
                "asset_type": "Launch thread",
                "channel": "X / Twitter",
                "title": "AI coding verification gap thread",
                "content": (
                    "1/ AI agents can write code fast. The slower question is whether it works.\n"
                    "2/ Unit tests and static checks miss user journeys that fail in a real browser or API flow.\n"
                    f"3/ {product_name} gives agents a QA loop they can run and learn from.\n"
                    f"4/ Source-backed proof to include: {primary_claim}.\n"
                    "5/ The launch angle: do not ship AI-generated code without a verifier."
                ),
                "call_to_action": "Run the first verification loop on your own app.",
                "notes": ["Replace generic numbers with sourced claims only", f"Write in {output_language}"],
            },
            {
                "asset_type": "Developer blog",
                "channel": "Blog",
                "title": "Launch blog outline",
                "content": (
                    "Title: AI coding moved the bottleneck from writing code to proving it works\n"
                    "1. Open with the verification gap and a real failure mode.\n"
                    "2. Explain why mocks and static assertions are not enough for agentic coding.\n"
                    f"3. Show how {product_name} runs live app checks and returns a fixable failure bundle.\n"
                    "4. Add sourced proof points and mark unsourced claims for validation.\n"
                    "5. Close with the CLI or live-app quickstart."
                ),
                "call_to_action": "Paste a URL or install the CLI to run your first check.",
                "notes": ["Use screenshots or command output if available", "Keep proof sources visible"],
            },
            {
                "asset_type": "README quickstart",
                "channel": "GitHub / CLI",
                "title": "CLI quickstart block",
                "content": (
                    "## Verify your agent's work\n\n"
                    "```bash\n"
                    "npm install -g @testsprite/testsprite-cli\n"
                    "testsprite run --url https://your-app.example\n"
                    "```\n\n"
                    "What you get back: failing step, nearby context, screenshot, DOM snapshot, "
                    "root-cause hypothesis, and a recommended fix."
                ),
                "call_to_action": "Install the CLI and run one verification loop.",
                "notes": ["Confirm the exact package name before publishing", "Keep commands copy-pasteable"],
            },
            {
                "asset_type": "Outbound email",
                "channel": "Email",
                "title": f"Engineering-lead email for {target_market}",
                "content": (
                    "Subject: A QA loop for AI-generated code\n\n"
                    "Hi {{first_name}},\n\n"
                    "If your team is using coding agents, the risk is no longer only code generation - "
                    "it is knowing whether agent-written changes still work in the product.\n\n"
                    f"{product_name} helps teams verify live app behavior and turn failures into "
                    "actionable bundles an agent can use to fix its own work.\n\n"
                    "Worth a 15-minute technical walkthrough?"
                ),
                "call_to_action": "Book a technical walkthrough.",
                "notes": ["Use only sourced claims in the proof sentence", "Keep under 140 words"],
            },
            {
                "asset_type": "Community post",
                "channel": "Community",
                "title": "Builder community launch note",
                "content": (
                    "We are testing a simple thesis: AI coding agents need their own verification loop.\n\n"
                    f"{product_name} runs checks against a live product and returns failure context that "
                    "a developer or agent can act on. We are looking for builders who use Codex, Cursor, "
                    "Claude Code, or similar tools and want to catch regressions earlier."
                ),
                "call_to_action": "Share a live app URL or CLI workflow you want us to test.",
                "notes": ["Invite concrete feedback", "Avoid sounding like a generic launch ad"],
            },
        ]

    @staticmethod
    def _build_claim_checks(brand_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        proof_points = MockLLMClient._proof_points(brand_context)
        claim_checks = [
            {
                "claim": proof_point["claim"],
                "status": "source_backed" if proof_point.get("source") else "needs_validation",
                "source": proof_point.get("source") or None,
            }
            for proof_point in proof_points
        ]
        if proof_points:
            claim_checks.append(
                {
                    "claim": "Any additional funding, customer, user-count, or performance claim not listed here must be validated before publishing.",
                    "status": "needs_validation",
                    "source": None,
                }
            )
        return claim_checks
