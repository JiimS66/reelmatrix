# reelmatrix

## Repository Structure

```text
reelmatrix/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── package.json
├── Makefile
│
├── apps/
│   ├── api/                          # FastAPI / BFF layer
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   ├── middleware/
│   │   │   ├── routes/
│   │   │   │   ├── clients.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── events.py
│   │   │   │   ├── approvals.py
│   │   │   │   ├── content.py
│   │   │   │   ├── publishing.py
│   │   │   │   └── health.py
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   └── security/
│   │   └── tests/
│   │
│   ├── orchestrator/                # LangGraph state machine + event routing
│   │   ├── app/
│   │   │   ├── graph/
│   │   │   │   ├── state.py
│   │   │   │   ├── builder.py
│   │   │   │   ├── routing.py
│   │   │   │   └── transitions.py
│   │   │   ├── handlers/
│   │   │   │   ├── human_handlers.py
│   │   │   │   ├── schedule_handlers.py
│   │   │   │   ├── agent_handlers.py
│   │   │   │   └── data_handlers.py
│   │   │   ├── runners/
│   │   │   │   ├── workflow_runner.py
│   │   │   │   ├── agent_runner.py
│   │   │   │   └── approval_runner.py
│   │   │   └── policies/
│   │   │       ├── trust_levels.py
│   │   │       ├── quality_gate.py
│   │   │       └── permission_gate.py
│   │   └── tests/
│   │
│   ├── worker/                      # Celery workers / beat
│   │   ├── app/
│   │   │   ├── celery_app.py
│   │   │   ├── beat_schedule.py
│   │   │   ├── tasks/
│   │   │   │   ├── audit_tasks.py
│   │   │   │   ├── research_tasks.py
│   │   │   │   ├── content_tasks.py
│   │   │   │   ├── distribution_tasks.py
│   │   │   │   ├── analytics_tasks.py
│   │   │   │   ├── memory_tasks.py
│   │   │   │   ├── tool_health_tasks.py
│   │   │   │   └── notification_tasks.py
│   │   │   └── queues.py
│   │   └── tests/
│   │
│   └── web/                         # Next.js dashboard
│       ├── app/
│       │   ├── dashboard/
│       │   ├── clients/
│       │   ├── approvals/
│       │   ├── content/
│       │   ├── experiments/
│       │   └── settings/
│       ├── components/
│       ├── lib/
│       └── public/
│
├── core/
│   ├── agents/
│   │   ├── base.py
│   │   ├── research_agent.py
│   │   ├── content_generation_agent.py
│   │   ├── quality_review_agent.py
│   │   ├── optimization_agent.py
│   │   └── ab_test_agent.py
│   │
│   ├── workflows/
│   │   ├── onboarding.py
│   │   ├── auditing.py
│   │   ├── research_pipeline.py
│   │   ├── brief_assembly.py
│   │   ├── publishing.py
│   │   ├── metrics_ingestion.py
│   │   └── anomaly_detection.py
│   │
│   ├── harness/
│   │   ├── context_builder.py
│   │   ├── skill_loader.py
│   │   ├── memory_loader.py
│   │   ├── tool_discovery.py
│   │   ├── execution_policy.py
│   │   └── certification_gate.py
│   │
│   ├── memory/
│   │   ├── models.py
│   │   ├── stores/
│   │   │   ├── short_term.py
│   │   │   ├── warm_memory.py
│   │   │   └── long_term.py
│   │   ├── retrieval.py
│   │   ├── compression.py
│   │   └── forgetting.py
│   │
│   ├── skills/
│   │   ├── registry.yaml
│   │   ├── content/
│   │   │   ├── write_blog_post.yaml
│   │   │   ├── write_twitter_thread.yaml
│   │   │   └── adapt_to_linkedin.yaml
│   │   ├── research/
│   │   │   ├── analyze_competitor.yaml
│   │   │   └── analyze_audience_sentiment.yaml
│   │   └── review/
│   │       └── review_content_quality.yaml
│   │
│   ├── tools/
│   │   ├── registry.yaml
│   │   ├── health.py
│   │   ├── permissions.py
│   │   └── adapters/
│   │       ├── mcp_client.py
│   │       ├── search_adapter.py
│   │       ├── seo_adapter.py
│   │       └── brand_kb_adapter.py
│   │
│   ├── events/
│   │   ├── types.py
│   │   ├── schemas.py
│   │   ├── bus.py
│   │   ├── handlers.yaml
│   │   └── dispatcher.py
│   │
│   ├── domain/
│   │   ├── clients/
│   │   ├── projects/
│   │   ├── strategy/
│   │   ├── content/
│   │   ├── approvals/
│   │   ├── experiments/
│   │   └── analytics/
│   │
│   └── utils/
│       ├── logging.py
│       ├── tracing.py
│       ├── idempotency.py
│       └── time.py
│
├── mcp_servers/
│   ├── brand-kb-mcp/
│   ├── web-scraper-mcp/
│   ├── twitter-publisher-mcp/
│   ├── reddit-mcp-server/
│   ├── seo-analyzer-mcp/
│   ├── wordpress-mcp/
│   └── linkedin-mcp-server/
│
├── data/
│   ├── migrations/
│   ├── seed/
│   ├── fixtures/
│   └── samples/
│
├── infra/
│   ├── docker/
│   ├── railway/
│   ├── flyio/
│   └── scripts/
│
├── configs/
│   ├── environments/
│   ├── llm/
│   ├── trust/
│   └── observability/
│
├── docs/
│   ├── architecture/
│   ├── product/
│   ├── api/
│   ├── runbooks/
│   └── adr/
│
└── tests/
    ├── unit/
    ├── integration/
    ├── e2e/
    └── fixtures/
