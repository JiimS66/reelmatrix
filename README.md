# ReelMatrix — 人机协同的营销团队 OS（Digital Marketing Team OS）

## 产品概览（当前形态）

ReelMatrix 已从“填写 brief → 一键生成营销方案”的单次工具，演进为一个**人机混合的营销团队操作系统**（数字营销 ERP）：一场 campaign 是一张**可拆分、可指派**的任务图，由 AI 与人类**同一套接口**的成员在一位人类 market lead 的统筹下协作完成。同一套系统按租户的人:AI 比例不同地配置——无团队的创始人偏 AI，有团队的公司偏协作。

核心能力（均已落地，`mock` provider 下可零外部调用跑通）。覆盖**从受众定义 → 内容生产 → 热点反应 → 跨活动审核 → 发布度量**的完整闭环：

- **数字员工 + 多 Agent 流水线**：每个 AI 工人是统一 `Agent`（`core/agents/`）——Ideation 策略、Planning 规划、Copywriter 文案、**Auditor 审计**、**Designer 视觉**。编排采用 orchestrator-worker + 共享黑板：**先串行决策 → 锁定共享内容核 → 并行渲染各渠道 → 复核（一致性检查 + 人审）**。
- **受众细分（ICP）驱动每条内容**：品牌维护一份可复用的细分人群库（`BrandProfile.segments`：在哪些平台、痛点、价值主张、异议、触达方式）；每场 campaign 选定目标子集（`brief["target_segments"]`），每条 post 被路由到一个 `(细分, 痛点)`（`assign_segment` / `targeted_segments`），文案以该痛点开场、落到价值主张、预先回应异议。每条 post 都显示定位条：**对应哪类客户 · 哪个痛点/热点 · 在事件中的阶段**。
- **Post 即唯一交付物（图文一体 + 一键改进）**：一条 post = 文案 + 配图/视频，是一个交付单元（`CampaignAsset.visual`）。Designer 作为 post 渲染的**子步骤**产出配图与品牌契合度评审（与文案自纠错循环**解耦**，不会重复消耗或覆盖已批准的图）。支持**一键“应用 AI 改进”**（按检查/审计问题重渲染成一个新版本，`/tasks/{id}/improve`）、**“同步配图”**（按当前文案重生成图，`/tasks/{id}/sync-visual`）、以及 URL 附加图/视频。视觉模型可换（`core/media/` 的 `MediaProvider` / `VisionProvider` 抽象 + 工厂，业务代码只依赖接口）。
- **热点 → 快速反应内容（带品牌安全急停）**：检测到的热点话题逐条打分（0–100 品牌契合度）并通过**品牌安全急停**（`core/trends/safety.py`：敏感/悲剧类话题被**一票否决**、禁止蹭热点——是否决而非扣分），安全的话题可一键草拟成**事件计划内的限时 post**（`/campaigns/{id}/trends/draft`），且永远走人审、绝不自动外发。
- **质量护栏（taste 与 truth 分离）**：每条内容带 `format / brand / consistency / terminology` **确定性检查** + 0–100 内容评分（`content_score`）+ 术语库（`BrandTerm`，禁用/慎用/首选替换）+ 预测表现启发式（`predicted_performance`，与合规分相互独立）；之上叠加**跨模型 LLM-as-judge Auditor**（用与生成器不同的模型家族审，解耦错误）；任一失败都喂回**自诊断重试**（agent 自我修正重渲染，保留最干净稿）。事实/数字一律走 `claim_check` 真值轨（带逐条来源标注的事实核查工作台）。
- **跨活动统一审核队列 + directive → 可追踪任务**：lead 的“需你处理”跨**所有** campaign 汇总成一个队列（`get_review_queue`，按活动分组、处理即出队，Workfront 式），不再局限于当前活动。给员工下达的 **directive 会自动变成真实任务**：落入每租户的 “Direct assignments” 活动，关联回消息（`DirectMessage.task_id`），AI 员工立即起草并进入审核队列，人类员工得到一条待办。
- **三层记忆（按租户隔离）**：语义=持久 `BrandProfile`，情景=campaign 内的 lead 反馈/决策（`EpisodicNote`），工作=任务上下文切片；自上而下注入 agent 的上下文。
- **可配置组织 + 车队可观测**：组织写在成员自身上（`job_description / reports_to / handles_kinds`）；任务按 `handles_kinds` 路由，换谁负责某类任务即改路由、无需改代码。Team 标签页可查看组织架构、招聘/重配置 AI 员工，以及每个 AI 员工的车队统计（运行数/任务数/平均分/自纠错次数）。
- **度量与发布闭环（均为可换 provider + mock）**：GA4 回流（`AnalyticsSource`，按 UTM 把转化接回 post）、安全发布（`PublishProvider`，默认 `human_final` 人审后发，规避平台审核风险）、校对版本栈（`ContentVersion` 不可变快照 + `Annotation` 锚点批注 + 显式内容锁）。
- **有状态 + 多租户 + 按工作流重排的协作工作台**：SQLModel 持久化（`core/db/`，行级 `tenant_id`），团队 API（`/api/v1/team`），工作台 UI 按营销工作流重排为 **Overview · Plan · Create · Review · Brand · Team**（每个任务只落在一个阶段；Review 徽标为跨活动计数）；AI 是一等成员（assignee），人类可在任意阶段编辑、接管、或插入审核门。从第一天起埋点 `UsageEvent` 计费。

**增长引擎层（Phase 5–10，让系统从"内容生产线"变成"会学习的增长引擎"）**：建在一条统一骨架上——「**内容属性 → 市场结果 → 学习 → 注入生产**」：

- **效果飞轮**（`core/growth/`）：发布后的转化按内容属性沉淀为 Beta 后验，作为"什么有效"的先验注入下一轮生成——真正的 self-improvement，而非只是 self-correction。
- **实验账本**：变体带属性标签 → 贝叶斯"chance-to-beat-control"判定赢家 → 赢家晋升为可复用的生成规则（`WinningPattern`），喂回飞轮。
- **ICP 验证与发现 + 市场情报**：细分人群从"人手填的假设"变成"被转化验证的结论"（0–100 分 + 状态 + drivers），并能从数据发现新人群；竞品定位/SOV/受众问题/白空间进入 brief。
- **品牌叙事 + 内容原子化 + 漏斗覆盖**：贯穿所有活动的 messaging 金字塔、一个 pillar 裂变多渠道衍生、`funnel × segment` 覆盖矩阵（空缺一键补齐）。
- **视频形态**（`core/media/video.py`,`clips.py`）：post → VideoSpec（脚本→分镜→渲染）、长内容 → 排序短片候选，兑现 “Reel” 之名。
- **治理**（`core/policy/`）：全链路合规闸（广告法绝对化「最/第一」、PII、品牌安全、#ad 披露；决策与执行解耦的 OPA 式裁决对象）+ 按可靠度自适应的自治级别。
- **付费创意环 + 规模化 1:1 outbound**（`core/paid/`,`core/outbound/`）：投前打分 → 预算分配；waterfall 富集 → 个性化首句 → 合规 + 送达闸。

**企业落地（本地部署 + 数据隐私 + 数据融入）**：企业的营销数据不能出域,产品因此**面向本地部署**——一个 `DeploymentProfile`（cloud/hybrid/on_prem/air_gapped）把 provider 默认翻转为本地（开源权重 vLLM+Qwen3 / ComfyUI+FLUX / faster-whisper / pgvector / HDBSCAN / PyMC / Presidio,单盒 1×H100+1×4090 即可全栈离线,~9/10 能力今天可跑）,并在发送/出云前串一条隐私 gate 链（`PolicyGate` 合规 → `ConsentGate` 同意 → `EgressGate` 出云前 mask/block PII；air-gapped 阻断任何外发）。企业带着历史进来时,**数据融入**把老内容+成效写成「已完成的带成效 post」,现有学习回路自然 **warm-start**（飞轮/ICP day-1 即有真实先验）,品牌文档则提取为品牌知识。详见 `docs/deployment-onprem.md`。

> 详细路线图见 `docs/roadmap-growth-engine.md`、`docs/roadmap-maturity.md`、`docs/deployment-onprem.md` 与 `DESIGN.md`；旧的单次生成接口（`/api/v1/campaign/generate`）与下文 “Phase 1 / Phase 2” 仍保留并可用，但已被上述团队 OS 取代——阅读时请以本节为准。均 mock-first、provider 可换。当前后端 **177** 个测试 + 前端 typecheck/build/Vitest 全绿。

## 本地运行（优先阅读）

项目由 FastAPI 后端和 Next.js 前端组成。以下命令均在仓库内执行，不会修改系统级 Python、Node.js 或 npm 配置。默认使用无网络调用的 `mock` 模型，可直接完成本地开发和测试。

### 1. 环境要求

- Python 3.13 与 [uv](https://docs.astral.sh/uv/)
- Node.js 24.x
- npm 11.x

```bash
python3 --version
uv --version
node --version
npm --version
```

### 2. 首次安装

在仓库根目录执行：

```bash
uv python install 3.13
uv sync --locked

test -f .env || cp .env.example .env
test -f apps/web/.env.local || cp apps/web/.env.example apps/web/.env.local

cd apps/web
npm ci --cache .npm-cache --ignore-scripts
cd ../..
```

- Python 依赖安装到根目录 `.venv/`，uv 缓存保存在根目录 `.uv-cache/`。
- 前端依赖安装到 `apps/web/node_modules/`，npm 缓存保存在 `apps/web/.npm-cache/`。
- 上述目录均为项目本地目录且不提交 Git。
- `npm ci` 会严格按照 `apps/web/package-lock.json` 重建 `node_modules/`；日常已有完整依赖时不需要重复执行。

### 3. 使用 mock 配置

根目录 `.env` 至少确认以下配置：

```dotenv
APP_ENV=development
LLM_PROVIDER=mock
LLM_TIMEOUT_SECONDS=60
WEB_ORIGIN=http://localhost:3000
```

`apps/web/.env.local` 配置浏览器访问的后端地址：

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

真实 API Key 只能放在根目录 `.env`，不要写入 `.env.example`、`apps/web/.env.local` 或任何 `NEXT_PUBLIC_*` 变量。OpenAI、Qwen 和本地模型的详细配置见后文“LLM Provider 配置”。

### 4. 启动项目

终端一，在仓库根目录启动后端：

```bash
uv run uvicorn apps.api.main:app --reload
```

终端二，在仓库根目录启动前端：

```bash
cd apps/web
npm run dev
```

启动后访问：

- Web 页面：`http://localhost:3000`
- FastAPI 健康检查：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`
- Campaign API：`http://localhost:8000/api/v1/campaign/generate`

页面会显式展示当前可用的 Local、ChatGPT、Qwen 和 Mock provider。未完成后端配置的 provider 会被禁用；选择 Mock 可在不调用外部网络、不消耗模型额度的情况下验证完整流程。

### 5. 测试与构建

在仓库根目录执行后端验证：

```bash
uv lock --check
uv run python -m compileall -q apps configs core tests
uv run pytest
```

执行前端验证：

```bash
cd apps/web
npm run typecheck
npm test
npm run build
```

当前项目没有配置 Python 或前端 lint 命令；不要将不存在的 `lint` script 作为运行前置条件。前端已知依赖审计问题及处理限制见后文“已知依赖问题”。

## Phase 1：本地可运行的 Agent 后端 MVP

Phase 1 在既有 monorepo 分层内实现两个角色明确的业务 Agent：Marketing Ideation ChatBot 和 Marketing Planning MasterBot。`core/workflows/` 只负责编排，`core/llm/` 隔离模型提供方，`apps/api/` 只暴露 HTTP 接口。本阶段不包含前端、数据库、认证、MCP、浏览器自动化、外部发布或任务队列。

### 环境要求与安装

- Python 3.13
- 包管理：`uv`
- 依赖声明：`pyproject.toml`
- 版本锁定：`uv.lock`
- Python 版本约定：`.python-version`

```bash
uv python install 3.13
uv sync --locked
cp .env.example .env
```

`dev` dependency group 已配置为默认组，因此 `uv sync` 会同时安装 pytest、httpx 等开发依赖，不再使用 `--extra dev`。日常执行命令直接使用 `uv run`，不要求手动激活虚拟环境。

### uv 与环境文件约定

| 文件/目录 | 作用 | 是否提交 Git |
| --- | --- | --- |
| `.python-version` | 告诉 uv 使用 Python 3.13 | 是 |
| `pyproject.toml` | 声明运行依赖、开发依赖和项目配置 | 是 |
| `uv.lock` | 锁定完整依赖版本，保证环境可复现 | 是 |
| `uv.toml` | 配置项目级 uv 缓存目录 `.uv-cache/` | 是 |
| `.uv-cache/` | uv 下载、构建和解析依赖时使用的可重建缓存 | 否 |
| `.venv/` | `uv sync` 自动创建的本地 Python 与依赖环境 | 否 |
| `.env.example` | 可提交的应用环境变量模板，不包含真实密钥 | 是 |
| `.env` | 当前机器的真实运行配置和 API Key | 否 |

本项目通过 `uv.toml` 将缓存放在仓库内的 `.uv-cache/`，避免依赖用户级 `~/.cache/uv`。`.uv-cache/` 只用于复用下载包和构建结果，`.venv/` 才是项目实际运行的 Python 环境；两者都不应提交，也都可以安全重建。

`.venv/` 不应手动维护。环境损坏时可以删除后重新执行 `uv sync --locked`。`.env.example` 与 uv 依赖管理无关；它用于告诉开发者应用需要哪些环境变量。配置模块会在运行时读取复制后的 `.env`。

`.env` 是复制后由当前机器独立维护的本地文件，后续修改 `.env.example` 不会自动同步到它。模板字段变化后，应手动合并新增或重命名的字段，同时保留 `.env` 中的真实密钥。

常用依赖管理命令：

```bash
uv add <package>          # 添加运行依赖并更新 uv.lock
uv add --dev <package>    # 添加开发依赖并更新 uv.lock
uv remove <package>       # 删除依赖并更新 uv.lock
uv lock --check           # 检查 pyproject.toml 与 uv.lock 是否同步
uv sync --locked          # 严格按锁文件同步 .venv
```

### LLM Provider 配置

默认配置是无网络调用、结果确定的 mock provider：

```dotenv
APP_ENV=development
LLM_PROVIDER=mock
LLM_TIMEOUT_SECONDS=60
```

使用 OpenAI / ChatGPT API：

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=replace-with-your-key
OPENAI_MODEL=gpt-4o-mini
```

使用阿里云 Model Studio 新加坡区域的 Qwen OpenAI-compatible API：

```dotenv
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=replace-with-your-singapore-workspace-key
DASHSCOPE_WORKSPACE_ID=your-workspace-id
DASHSCOPE_MODEL=qwen-plus
```

将 `your-workspace-id` 替换为百炼控制台业务空间详情页中的 Workspace ID。应用会自动生成 `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`，不需要在 `.env` 中重复维护完整 URL。

`DASHSCOPE_BASE_URL` 仍可用于旧域名或特殊 endpoint，但仅在未配置 `DASHSCOPE_WORKSPACE_ID` 时生效。Base URL 到 `/compatible-mode/v1` 为止，不要追加 `/chat/completions`。旧的 `LLM_PROVIDER=qwen` 以及 `QWEN_API_KEY/QWEN_WORKSPACE_ID/QWEN_BASE_URL/QWEN_MODEL` 仍作为兼容别名支持，但新配置应统一使用 `dashscope` 和 `DASHSCOPE_*`。

使用任意 OpenAI-compatible 本地服务（例如兼容 `/v1/chat/completions` 的运行时）：

```dotenv
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_API_KEY=
LOCAL_LLM_MODEL=llama3.1
```

本地 API Key 可以为空。当前支持 `mock`、`openai`、`dashscope`、`local`，并兼容旧的 `qwen` provider 名称。OpenAI/DashScope 缺少 API Key，DashScope 缺少 Workspace ID/Base URL，local 缺少 URL 或模型，或 provider 名称未知时，应用会在启动时给出明确配置错误。

### 真实调用前的离线验证

测试入口会在 `tests/conftest.py` 中强制设置 `APP_ENV=test` 和 `LLM_PROVIDER=mock`。因此即使 `.env` 已填写真实 API Key，执行 pytest 也不会访问 DashScope/OpenAI，不会消耗模型额度。

```bash
uv lock --check
uv run python -m compileall -q apps configs core tests
uv run pytest
```

当前后端测试覆盖 schema、两个 Agent、工作流双分支、API 路由、CORS preflight、provider factory，以及 OpenAI-compatible 客户端响应校验。

可以在不发起网络请求的情况下检查 DashScope 必填配置并构造客户端：

```bash
uv run python -c 'from configs.settings import AppSettings; from core.llm.factory import create_llm_client; s = AppSettings(); assert s.dashscope_api_key and s.dashscope_workspace_id; create_llm_client(s.model_copy(update={"llm_provider": "dashscope"})); print("DashScope configuration preflight passed")'
```

该命令不会输出 API Key，也不会调用模型。真实测试前还需要确认 `.env` 中 `DASHSCOPE_WORKSPACE_ID` 已替换占位符，并将 `LLM_PROVIDER` 设置为 `dashscope`。

### 启动与测试

```bash
uv run uvicorn apps.api.main:app --reload
uv run pytest
```

健康检查：`GET http://localhost:8000/health`。

`GET /health` 不会调用模型。`POST /api/v1/campaign/generate` 才会进入 Agent 工作流；当构思结果可进入规划阶段时，一次 API 请求会依次调用 IdeationBot 和 PlanningBot，因此真实 provider 通常产生两次模型调用。

### 生成 Campaign

```bash
curl -X POST http://localhost:8000/api/v1/campaign/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "TensorGrowth",
    "product_description": "An AI marketing workspace that helps founders generate and plan campaigns.",
    "target_audience": "early-stage startup founders and lean marketing teams",
    "marketing_goal": "generate qualified waitlist signups",
    "brand_voice": "sharp, practical, founder-friendly",
    "constraints": ["small team", "limited budget", "organic-first"],
    "user_prompt": "ready for planning: create a launch campaign concept for this product"
  }'
```

mock 模式下，将 `user_prompt` 设为包含 `needs more ideation` 可稳定触发补充构思分支：

```json
{
  "status": "needs_more_ideation",
  "ideation_result": {
    "campaign_concept": "Clarify the strongest launch idea for TensorGrowth.",
    "core_message": "The campaign promise needs more evidence and specificity.",
    "target_audience_insight": "More detail is needed about early-stage startup founders and lean marketing teams and their buying trigger.",
    "recommended_angles": [
      "Lead with the audience's highest-cost current problem",
      "Demonstrate a concrete before-and-after outcome"
    ],
    "risks_or_assumptions": [
      "The primary pain point has not been validated",
      "The desired conversion action may be too broad"
    ],
    "follow_up_questions": [
      "What single pain point should this campaign prioritize?",
      "What proof or customer evidence can support the campaign promise?",
      "What exact action should the audience take after seeing the campaign?"
    ],
    "is_ready_for_planning": false
  },
  "campaign_plan": null
}
```

将 `user_prompt` 设为包含 `ready for planning` 可稳定生成计划：

```json
{
  "status": "plan_generated",
  "ideation_result": {
    "campaign_concept": "The Lean Growth Launch for TensorGrowth",
    "core_message": "Turn a clear product story into measurable marketing momentum toward generate qualified waitlist signups.",
    "target_audience_insight": "early-stage startup founders and lean marketing teams need credible, practical progress without adding operational overhead.",
    "recommended_angles": [
      "Replace fragmented campaign work with one guided workflow",
      "Show measurable progress for a resource-constrained team",
      "Use founder-relevant examples instead of generic AI claims"
    ],
    "risks_or_assumptions": [
      "The audience already recognizes campaign planning as a bottleneck",
      "Organic proof can establish enough trust for the initial conversion"
    ],
    "follow_up_questions": [],
    "is_ready_for_planning": true
  },
  "campaign_plan": {
    "campaign_name": "TensorGrowth Lean Growth Launch",
    "campaign_objective": "generate qualified waitlist signups",
    "target_audience": "early-stage startup founders and lean marketing teams",
    "core_message": "Turn a clear product story into measurable marketing momentum toward generate qualified waitlist signups.",
    "channels": [
      {
        "channel_name": "LinkedIn",
        "role_in_campaign": "Build category awareness and founder credibility",
        "content_types": ["Founder posts", "Problem-solution carousels"],
        "key_messages": ["Turn a clear product story into measurable marketing momentum."],
        "cadence": "Three posts per week for four weeks",
        "success_metrics": ["Qualified profile visits", "Waitlist conversions"]
      }
    ],
    "content_pillars": [
      "The cost of fragmented campaign work",
      "Practical AI workflows for lean marketing teams"
    ],
    "timeline": [
      {
        "phase_name": "Foundation",
        "timing": "Week 1",
        "objective": "Establish the problem and campaign promise",
        "key_activities": ["Publish category narrative", "Launch waitlist landing message"]
      }
    ],
    "deliverables": [
      {
        "name": "Founder launch narrative",
        "channel": "LinkedIn",
        "format": "Text post",
        "purpose": "Introduce the campaign problem and point of view"
      }
    ],
    "success_metrics": ["Qualified waitlist signups", "Landing-page conversion rate"],
    "assumptions": ["The product has a functioning waitlist destination"],
    "execution_notes": ["Keep calls to action consistent across channels"]
  }
}
```

## Phase 2：Campaign Studio Web 应用

Phase 2 在 `apps/web/` 中增加独立管理的 Next.js 16、React 19、TypeScript 和 TailwindCSS 前端。页面调用 Phase 1 的 `POST /api/v1/campaign/generate`，支持 campaign brief 表单、本地校验、IdeationResult 展示、follow-up 补充上下文，以及 CampaignPlan 的结构化展示。前端依赖由 `apps/web/package.json` 和 `apps/web/package-lock.json` 管理，不加入仓库根目录 npm workspace。

### Phase 2 环境要求

- Node.js 24.x；当前已验证版本为 `24.14.0`
- npm 11.x；当前已验证版本为 `11.9.0`
- 依赖声明：`apps/web/package.json`
- 版本锁定：`apps/web/package-lock.json`

```bash
node --version
npm --version
```

当前 Node.js 和 npm 版本通过 README 约定，`apps/web/package.json` 尚未使用 `engines` 或 `packageManager` 字段强制限制。升级 Node.js、npm、Next.js 或 React 后，必须重新通过前端 typecheck、测试和 production build。

### Phase 2 环境配置

后端继续读取仓库根目录 `.env`。浏览器本地开发至少需要：

```dotenv
LLM_PROVIDER=mock
WEB_ORIGIN=http://localhost:3000
```

前端从 `apps/web/.env.local` 读取公开的 API 地址：

```bash
cp apps/web/.env.example apps/web/.env.local
```

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`NEXT_PUBLIC_*` 变量会进入浏览器 bundle，只能放公开配置，不能放 API Key。所有模型密钥仍只保存在根目录 `.env`，由 FastAPI 后端读取。

### 请求级模型选择

Campaign Studio 会从 `GET /api/v1/llm/providers` 读取后端 provider catalog，并按以下类别显示：

- **Local model**：`local`，使用 `LOCAL_LLM_BASE_URL` 和 `LOCAL_LLM_MODEL`。
- **Remote models**：`dashscope` 显示为 Qwen，`openai` 显示为 ChatGPT。
- **Development**：`mock`，用于确定性本地演示和测试。

Catalog 只返回 provider ID、显示名、模型名、类别和是否已配置，不返回 API Key、Base URL 或其他秘密。缺少必要后端配置的 provider 会在页面中禁用。

前端提交 campaign 时通过请求 header 传递选择结果：

```http
X-LLM-Provider: dashscope
```

不传该 header 时，后端继续使用根目录 `.env` 中的 `LLM_PROVIDER`，因此现有 API 客户端和 request JSON 保持兼容。follow-up 请求固定沿用上一轮 provider，避免多轮上下文中途切换模型。

新增 provider 时，在 `core/llm/` 增加客户端和 factory 分支，并在 `apps/api/services/campaign_generation.py` 注册 catalog metadata。前端根据 catalog 自动分组，不需要在表单或 API client 中增加 provider 专用逻辑。

### 安装前端依赖

```bash
cd apps/web
npm ci --cache .npm-cache --ignore-scripts
```

`npm ci` 会删除已有 `node_modules/`，并严格按 `package-lock.json` 重建依赖。依赖安装到 `apps/web/node_modules/`，下载缓存为 `apps/web/.npm-cache/`；两者都不提交 Git。

`apps/web/.next/` 和 `apps/web/tsconfig.tsbuildinfo` 也是可重建的生成文件，不提交 Git。前端目录中只有依赖声明 `package.json` 和锁文件 `package-lock.json` 需要共同提交。仅在明确新增、删除或升级依赖时使用 `npm install <package>` 或 `npm uninstall <package>`，并同时检查两个依赖文件的变更。

检查当前安装目录是否与依赖声明一致：

```bash
cd apps/web
npm ls --depth=0
```

当前在 macOS ARM64、Node.js 24 和 npm 11 环境中，即使完成干净的 `npm ci`，`npm ls` 仍可能将 `@emnapi/runtime@1.11.1` 标记为 `extraneous`。该包已存在于锁文件中，是 Next.js 使用的 `sharp` WASM 可选依赖链的一部分；只要锁文件检查、typecheck、测试和 build 通过，不需要手动删除。若出现其他 extraneous 包，应先重新执行 `npm ci`，再单独调查来源。

### 本地启动

终端一启动 FastAPI：

```bash
uv run uvicorn apps.api.main:app --reload
```

终端二启动 Next.js：

```bash
cd apps/web
npm run dev
```

- 浏览器页面：`http://localhost:3000`
- 后端健康检查：`http://localhost:8000/health`
- Campaign API：`http://localhost:8000/api/v1/campaign/generate`

mock provider 下点击 **Use Demo Input** 会填充包含 `ready for planning` 的稳定示例并生成完整计划。输入包含 `needs more ideation` 时，页面会展示 follow-up questions，并在补充回答后把前序用户输入、Agent 摘要和本轮回答放入 `conversation_history` 再次调用同一 workflow。

### Phase 2 测试与构建

后端：

```bash
uv run pytest
```

前端：

```bash
cd apps/web
npm run typecheck
npm test
npm run build
```

`npm run build` 当前使用 Next.js 的 Webpack production builder，避免 Turbopack 在受限本地环境中创建内部端口。提交代码前应同时通过后端 pytest、前端 Vitest 测试、TypeScript 检查和 production build。

### 代码质量工具现状

- 后端已配置 pytest，并使用 `python -m compileall` 做基础语法检查。
- 后端暂未配置 Ruff、Black、Mypy 或 Pyright，因此当前没有正式的 Python lint、format 或 typecheck 命令。
- 前端已配置 TypeScript `tsc --noEmit`、Vitest 和 Next.js production build。
- 前端暂未配置 ESLint、Biome 或其他 lint 工具，因此当前没有 `npm run lint` 命令。

在正式引入质量工具前，不应把未配置的 lint 或 typecheck 检查写入 CI 必过项。新增工具时需要同步更新依赖文件、锁文件、本节命令和 CI 配置。

### 已知依赖问题

当前锁文件保留 Next.js `16.2.9`。项目级 `postcss` 是 `8.5.15`，但 Next.js `16.2.9` 内嵌 `postcss` `8.4.31`，因此 `npm audit` 会报告 `GHSA-qx2v-qp2m-jg93`。当前 typecheck、测试和 production build 均通过。

不要使用 `npm audit fix --force`：npm 建议的自动修复会把 Next.js 降级到 `9.3.3`，属于破坏性变更。在获得明确批准前，也不要添加 PostCSS override、降级 Next.js、升级 canary，或绕过当前锁文件。后续仅在稳定版 Next.js 内嵌 `postcss >= 8.5.10` 且通过完整测试/build 时，单独评估升级。

Python 依赖审计目前会报告开发依赖 `pytest 8.4.2` 的 `CVE-2025-71176`，修复版本为 `9.0.3`。当前 `pyproject.toml` 将 pytest 限制在 `>=8.0,<9.0`，因此不能在未验证兼容性的情况下直接升级。该问题只存在于开发/测试依赖，不进入生产运行依赖；后续升级 pytest 主版本时必须先通过完整后端测试。

### Phase 2 Non-goals

本阶段不包含数据库、认证、多租户、campaign 持久化、外部平台发布、MCP、RAG、任务队列或新 Agent。前端只消费 Phase 1 现有 schema 和 workflow，不改变 Agent、Workflow、LLM provider 的主设计。

## 1. 工程目录结构总览

```text
reelmatrix/
├── apps/                 # 核心应用入口层：Frontend, API, Workers
│   ├── api/
│   ├── web/
│   └── workers/
├── core/                 # AI 引擎与核心业务层：AI Brain & Logic
│   ├── agents/
│   ├── llm/              # 模型提供方抽象与实现
│   ├── schemas/          # 严格的业务输入输出契约
│   ├── workflows/
│   ├── evaluation/
│   └── memory/
├── mcp_servers/          # 外部工具与防腐层：MCP Middleware
│   ├── rag_knowledge/
│   ├── social_x/
│   ├── professional_in/
│   └── seo_geo/
├── data/                 # 支撑性基础设施层：数据存储与迁移
├── infra/                # 支撑性基础设施层：运维与部署
├── configs/              # 支撑性基础设施层：全局配置管理
├── docs/                 # 支撑性基础设施层：项目文档
└── tests/                # 支撑性基础设施层：质量保障与自动化测试
```

## 2. 技术栈总览

本项目的技术栈围绕 AI Agent 驱动的营销自动化系统展开，整体包括前端交互、后端 API、异步任务调度、AI Agent 编排、RAG 检索、外部平台工具封装、数据存储、部署运维与测试体系。

| 技术领域 | 使用技术 | 对应目录 | 主要用途 |
| --- | --- | --- | --- |
| 前端框架 | Next.js、React | apps/web/ | 构建用户交互界面、数据看板、人工确认弹窗 |
| 前端语言 | TypeScript | apps/web/ | 提升前端代码的类型安全与可维护性 |
| 前端样式 | TailwindCSS | apps/web/ | 快速构建统一、可复用的 UI 样式 |
| 后端 API 框架 | FastAPI | apps/api/ | 提供高并发异步 API 服务 |
| 后端语言 | Python | apps/api/、apps/workers/、core/、mcp_servers/ | 承载后端业务逻辑、AI 调用、任务调度与工具封装 |
| 异步任务队列 | Celery | apps/workers/ | 处理定时发布、热点抓取、批量发送、模型推理等长周期异步任务 |
| 消息队列 / 缓存 | Redis | apps/workers/ | 作为 Celery Broker 或任务状态存储 |
| AI Agent 框架 | LangChain 或 LlamaIndex | core/agents/ | 构建具备工具调用能力的 AI 智能体 |
| 工作流编排 | Python 状态机 / Workflow Engine | core/workflows/ | 管理多 Agent、多渠道、多事件的任务流转 |
| 内容安全与质量校验 | Python 规则逻辑、轻量级模型 | core/evaluation/ | 对生成内容进行合规性、品牌敏感词和幻觉校验 |
| 长期记忆管理 | Python、数据库或向量存储 | core/memory/ | 存储用户偏好、品牌风格、历史表现数据 |
| RAG 检索 | Sentence-BERT | mcp_servers/rag_knowledge/ | 对品牌文档、产品手册进行语义向量化 |
| 向量数据库 | Pinecone 或 Milvus | mcp_servers/rag_knowledge/ | 存储和检索高维语义向量 |
| 外部工具协议 | Model Context Protocol | mcp_servers/ | 将外部平台能力封装为 Agent 可调用工具 |
| 社交平台集成 | Twitter、Reddit API 或自动化接口 | mcp_servers/social_x/ | 支持热点抓取、自动化发帖、用户动态获取 |
| 职场平台集成 | LinkedIn API 或自动化接口 | mcp_servers/professional_in/ | 支持职场平台内容分发和用户触达 |
| GEO 优化 | Python、内容结构化规则 | mcp_servers/seo_geo/ | 优化内容结构，使其更容易被 AI 搜索引擎引用 |
| 数据库迁移 | Migration Scripts | data/ | 管理数据库结构变更 |
| 初始数据 | Seed Data | data/ | 提供初始化数据和测试固件 |
| 容器化 | Docker、Docker Compose | infra/ | 保证本地开发、测试和部署环境一致 |
| CI/CD | 云平台部署流水线脚本 | infra/ | 实现自动化构建、测试和部署 |
| 配置管理 | 环境变量、配置模板 | configs/ | 管理 API Key、模型参数、环境配置 |
| 测试框架 | 单元测试、集成测试、端到端测试 | tests/ | 验证核心逻辑、Agent 协同和完整业务流程 |

## 3. 分层目录与技术栈说明

整体架构划分为四大核心层：

1. 核心应用入口层
2. AI 引擎与核心业务层
3. 外部工具与防腐层
4. 支撑性基础设施层

每一层都对应明确的目录结构、技术栈选择和工程任务边界，用于保证前端入口、后端服务、AI 核心逻辑、外部平台接入和基础设施之间保持清晰解耦。

### 1. 核心应用入口层：apps/

`apps/` 是整个系统所有可运行服务的入口层，主要负责用户交互、API 请求接收以及异步任务调度。该层直接面向用户请求和外部流量，因此需要具备良好的并发能力、可扩展能力和服务隔离能力。

| 目录 | 技术栈 | 主要任务 |
| --- | --- | --- |
| apps/web/ | TypeScript、Next.js、React、TailwindCSS | 构建前端用户界面、数据监测看板、试用引流页面和人工确认弹窗 |
| apps/api/ | Python、FastAPI | 提供后端 API 网关，接收前端请求，返回初始规划结果，并将耗时任务分发给 Worker |
| apps/workers/ | Python、Celery、Redis | 处理定时发布、热点抓取、批量发送、模型推理等长周期异步任务 |

#### 1.1 apps/web/

**技术栈**：TypeScript、Next.js、React、TailwindCSS。

**主要任务**：

- 构建系统的前端用户交互界面。
- 展示营销数据监测看板。
- 提供试用引流 Hook 页面。
- 承载 Human-in-the-loop 的确认弹窗。
- 在 AI 内容外发前设置人工 Approve 机制。

**设计说明**：

AI 生成的外部触达内容存在品牌、合规和事实风险，因此前端不仅承担展示功能，也承担关键的人为拦截功能。用户必须在前端确认后，系统才可以执行最终的平台外发动作。

#### 1.2 apps/api/

**技术栈**：Python、FastAPI。

**主要任务**：

- 作为系统的后端 API 网关。
- 接收来自前端的轻量级请求。
- 调用 core 层中的 Agent、Workflow 或 Evaluation 逻辑。
- 快速返回初始规划或任务状态。
- 将耗时任务提交给异步 Worker 处理。

**设计说明**：

FastAPI 适合处理高并发、I/O 密集型请求。将 API 层作为轻量级入口，可以避免复杂 AI 推理、外部 API 调用和批量任务阻塞主服务。

#### 1.3 apps/workers/

**技术栈**：Python、Celery、Redis。

**主要任务**：

- 执行后台异步任务。
- 处理定时发布任务。
- 执行全自动热点抓取任务。
- 处理大规模 Cold Email 批量发送。
- 执行耗时的 AI 模型推理任务。
- 与外部平台 API 进行长周期交互。

**设计说明**：

AI 推理和外部平台请求通常耗时较长，不能直接阻塞 API 主进程。通过 Celery 和 Redis 将任务放入异步队列，可以提升系统并发能力和稳定性，也便于后续单独扩容 Worker 节点。

### 2. AI 引擎与核心业务层：core/

`core/` 是系统的 AI 大脑和核心业务逻辑层，负责 Agent 构建、任务编排、内容校验和长期记忆管理。该层不直接硬编码任何外部平台接口，而是通过 mcp_servers/ 调用外部工具，从而保持核心逻辑的纯粹性和可迁移性。

| 目录 | 技术栈 | 主要任务 |
| --- | --- | --- |
| core/agents/ | Python、LangChain 或 LlamaIndex | 构建负责策略规划、内容生成、渠道适配和工具调用的 AI Agent |
| core/llm/ | Python、OpenAI SDK、Provider Adapter | 隔离 mock、OpenAI 与本地 OpenAI-compatible 模型调用 |
| core/schemas/ | Python、Pydantic | 定义 Agent、Workflow 与 API 共用的严格数据契约 |
| core/workflows/ | Python、Workflow Engine 或状态机逻辑 | 管理多 Agent、多事件、多渠道之间的任务流转 |
| core/evaluation/ | Python、规则逻辑、轻量级模型 | 对外发内容进行合规性、品牌敏感词和幻觉校验 |
| core/memory/ | Python、数据库或向量存储 | 存储用户偏好、品牌风格、历史表现数据和长期上下文 |

#### 2.1 core/agents/

**技术栈**：Python、LangChain 或 LlamaIndex。

**主要任务**：

- 构建不同职责的 AI Agent。
- 支持用户交互、营销创意生成和高层策略规划。
- 根据不同渠道生成适配内容。
- 调用 MCP 工具完成外部平台动作。
- 实现从策略到执行的半自动化或自动化闭环。

**典型 Agent 类型**：

- Marketing Ideation ChatBot：负责用户交互和营销创意生成。
- Planning MasterBot：负责高层策略规划和任务拆解。
- Channel Execution Agent：负责不同渠道的内容改写、格式适配和执行准备。

**设计说明**：

Agent 是系统中最核心的智能决策单元。通过 LangChain 或 LlamaIndex，可以让 Agent 具备推理、记忆、工具调用和多步骤任务执行能力。

#### 2.2 core/workflows/

**技术栈**：Python、Workflow Engine 或状态机逻辑。

**主要任务**：

- 管理多 Agent 之间的协作流程。
- 编排跨事件、跨渠道的营销任务。
- 控制任务从创建、规划、生成、审核到执行的完整生命周期。
- 记录任务状态，避免流程停留在零散对话层面。

**设计说明**：

营销自动化任务通常不是单次问答，而是一个包含多个阶段的流程。Workflow 层负责把 Agent 的输出组织成可追踪、可恢复、可管理的状态流转。

#### 2.3 core/evaluation/

**技术栈**：Python、规则校验逻辑、轻量级模型。

**主要任务**：

- 检查生成内容是否符合平台和行业规则。
- 检查品牌敏感词、禁用词和高风险表达。
- 检查内容是否存在明显事实幻觉。
- 在内容外发前进行质量拦截。
- 为 Human-in-the-loop 审核提供风险提示。

**设计说明**：

该层相当于 AI 内容外发前的安全防火墙。它不能完全替代人工审核，但可以在系统层面先过滤明显不合规、不准确或不符合品牌调性的内容。

#### 2.4 core/memory/

**技术栈**：Python、数据库或向量存储。

**主要任务**：

- 存储用户长期偏好。
- 记录品牌历史表现较好的内容风格。
- 保存客户产品调性、禁用表达和常用表达。
- 为后续 Agent 生成内容提供长期上下文。
- 支持系统随着使用时间增长而逐渐个性化。

**设计说明**：

大模型本身存在上下文窗口限制，无法天然记住长期偏好。Memory 层用于沉淀品牌、用户和历史任务数据，使系统在后续生成中更稳定地贴合客户需求。

### 3. 外部工具与防腐层：mcp_servers/

`mcp_servers/` 是系统连接外部世界的工具层，也是核心业务逻辑与第三方平台之间的防腐层。该层将外部平台 API、RAG 检索服务和 GEO 优化能力封装为 Agent 可以调用的工具，避免外部接口变化直接污染 core/ 层。

| 目录 | 技术栈 | 主要任务 |
| --- | --- | --- |
| mcp_servers/rag_knowledge/ | Python、Sentence-BERT、Pinecone 或 Milvus | 对品牌资料和产品文档进行向量化、语义检索和上下文召回 |
| mcp_servers/social_x/ | Python、Model Context Protocol、Twitter、Reddit API 或自动化接口 | 封装社交平台的发帖、热点抓取、用户动态获取能力 |
| mcp_servers/professional_in/ | Python、Model Context Protocol、LinkedIn API 或自动化接口 | 封装职场平台内容分发、线索触达和用户动态获取能力 |
| mcp_servers/seo_geo/ | Python、内容结构化规则、GEO 优化逻辑 | 优化内容结构，使其更容易被 AI 搜索引擎检索和引用 |

#### 3.1 mcp_servers/rag_knowledge/

**技术栈**：Python、Sentence-BERT、Pinecone 或 Milvus。

**主要任务**：

- 处理用户上传的品牌指南、产品手册和历史资料。
- 使用 Sentence-BERT 将文本转化为语义向量。
- 将向量存储到 Pinecone 或 Milvus。
- 根据 Agent 的任务需求召回相关上下文。
- 为内容生成提供准确的品牌和产品信息。

**设计说明**：

通用大模型无法天然掌握每个客户的品牌资料和产品细节。RAG 检索层可以在生成前提供相关上下文，减少内容空泛、品牌偏差和事实幻觉。

#### 3.2 mcp_servers/social_x/

**技术栈**：Python、Model Context Protocol、Twitter、Reddit API 或自动化接口。

**主要任务**：

- 封装社交平台发帖能力。
- 抓取热点话题和用户讨论。
- 获取目标用户动态。
- 收集内容反馈数据。
- 将社交平台操作包装成 Agent 可调用工具。

**设计说明**：

社交平台接口经常变化，因此不应直接写入 core/ 层。通过 MCP Server 封装平台能力，可以让 Agent 只关注任务目标，不需要关心底层 API 细节。

#### 3.3 mcp_servers/professional_in/

**技术栈**：Python、Model Context Protocol、LinkedIn API 或自动化接口。

**主要任务**：

- 封装职场平台内容发布能力。
- 支持 B2B 线索触达。
- 获取目标公司或目标用户动态。
- 支持职业社交场景下的内容分发和互动准备。

**设计说明**：

职场平台的内容风格、互动方式和线索价值与普通社交平台不同，因此单独封装为 professional_in/，便于针对 B2B 和职业关系场景做独立优化。

#### 3.4 mcp_servers/seo_geo/

**技术栈**：Python、内容结构化规则、GEO 优化逻辑。

**主要任务**：

- 优化生成内容的标题、结构和语义层次。
- 提高内容被 Perplexity、ChatGPT 等 AI 搜索引擎引用的可能性。
- 为品牌内容增加更清晰的实体、问题和答案结构。
- 支持生成式引擎优化场景下的内容改写。

**设计说明**：

在 AI 搜索时代，内容不仅需要面向传统搜索引擎，也需要面向生成式搜索引擎。GEO 层用于让内容结构更容易被大模型理解、检索和引用。

### 4. 支撑性基础设施层

支撑性基础设施层为整个系统提供数据管理、部署运维、配置管理、项目文档和测试保障。该层不直接参与 AI 推理或营销内容生成，但决定了系统能否稳定开发、部署和迭代。

| 目录 | 技术栈 | 主要任务 |
| --- | --- | --- |
| data/ | Migration Scripts、Seed Data、测试固件数据 | 管理数据库结构变更、初始化数据和测试数据 |
| infra/ | Docker、Docker Compose、CI/CD Pipeline | 管理容器化环境、部署脚本和自动化流水线 |
| configs/ | 环境变量、API Key 模板、模型参数配置 | 管理全局配置、密钥模板和模型调用参数 |
| docs/ | Markdown、API 文档、Runbooks | 存放架构说明、接口文档和系统维护手册 |
| tests/ | 单元测试、集成测试、端到端测试 | 验证核心逻辑、Agent 协同流程和完整业务链路 |

#### 4.1 data/

**技术栈**：Migration Scripts、Seed Data、测试固件数据。

**主要任务**：

- 存放数据库迁移脚本。
- 管理数据库结构变更。
- 存放初始化数据。
- 存放测试用固件数据。
- 保持开发、测试和生产环境的数据结构一致。

**设计说明**：

系统在快速迭代过程中，数据库结构会不断变化。通过 data/ 统一管理迁移和初始化数据，可以降低环境不一致带来的问题。

#### 4.2 infra/

**技术栈**：Docker、Docker Compose、CI/CD Pipeline。

**主要任务**：

- 存放 Dockerfile。
- 管理 Docker Compose 本地开发环境。
- 存放云平台部署脚本。
- 支持自动化构建、测试和部署。
- 保证本地、测试和生产环境的一致性。

**设计说明**：

AI 系统依赖较多，包括 Web 服务、API 服务、Worker、Redis、数据库和向量数据库。通过容器化和 CI/CD，可以降低部署复杂度，并提升环境可复现性。

#### 4.3 configs/

**技术栈**：环境变量、API Key 模板、模型参数配置。

**主要任务**：

- 统一管理全局环境变量。
- 存放 API Key 配置模板。
- 管理大模型 Temperature、Top-p、最大输出长度等参数。
- 管理不同环境的配置差异。
- 避免密钥硬编码进入代码仓库。

**设计说明**：

配置管理需要与业务代码隔离。configs/ 用于集中管理可变参数和敏感配置模板，提升安全性和可维护性。

#### 4.4 docs/

**技术栈**：Markdown、API 文档、Runbooks。

**主要任务**：

- 存放系统架构说明。
- 存放 API 使用文档。
- 存放系统维护应急手册。
- 沉淀开发规范和协作说明。
- 降低团队成员理解系统的成本。

**设计说明**：

复杂系统需要清晰的文档体系。docs/ 用于沉淀系统设计、接口规范和维护经验，避免知识只停留在个人脑中。

#### 4.5 tests/

**技术栈**：单元测试、集成测试、端到端测试。

**主要任务**：

- 测试单个函数和模块的稳定性。
- 测试 Agent 与工具之间的协同流程。
- 测试从用户请求到内容生成、审核和执行的完整链路。
- 在 Prompt、Workflow 或 Agent 逻辑变更后验证系统稳定性。

**设计说明**：

AI 系统的 Prompt、Agent 和 Workflow 会频繁变化，因此测试不仅要覆盖传统代码逻辑，也要覆盖关键的 Agent 协同流程和业务链路，防止系统在迭代中出现不可控退化。
