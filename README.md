# reelmatrix 核心技术架构与目录说明

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

当前基线为 34 个测试，覆盖 schema、两个 Agent、工作流双分支、API 路由、provider factory，以及 OpenAI-compatible 客户端响应校验。

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
