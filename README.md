# ReelMatrix — AI Marketing Strategy Copilot + Human-AI Marketing Team OS

> Type one sentence about your product. Co-create a one-page strategy with an AI CMO that
> **offers options and flags its own guesses** — then lock it and watch an AI marketing
> team draft your first cross-channel content, on a human↔AI team OS with review gates
> and brand guardrails underneath.

**Built for TestSprite Hackathon Season 3 (Build the Loop).**

**Live Demo:** http://121.43.99.199:3000 · API: http://121.43.99.199:8000 (health: [`/health`](http://121.43.99.199:8000/health))

### Team

| Name | GitHub | Discord |
| --- | --- | --- |
| Pengcheng Lu | [pengchenglu1997](https://github.com/pengchenglu1997) | `davidlu97` |
| Taixin Zhang | [HarryZ66](https://github.com/HarryZ66) | `harryzhang2595` |

### How the TestSprite CLI loop was used

We use the open-source TestSprite CLI as the checker for the live deployment: banked
frontend tests drive the real strategy-co-creation flow (idea → advisor draft → feedback
round → lock → first content) and backend tests hit the team-OS API, then every failure's
bundle is pulled locally, root-caused, fixed in a dedicated commit citing the test ID,
redeployed (verified via the commit hash in `/health`), and rerun until green. The full
create → run → failure-bundle → fix → rerun log, with per-round evidence, lives in
[LOOP.md](LOOP.md).

---

> 以下为详细中文文档(产品、架构、本地运行、部署)。 Detailed docs below are in Chinese.

# ReelMatrix — AI 营销策略副驾 + 人机协同营销团队 OS

> **一句话**：帮不懂营销的中小团队**把策略想清楚**，并立刻把策略变成**第一批内容**——背后是一个人机协同、会自我迭代的营销团队操作系统。

ReelMatrix 不和大模型比"谁写得好"，而是做模型**之上**的那一层：**记忆 · 闭环 · 主动 · 护栏 · "不需要你懂"**。中小团队没有精力做这套循环工程，我们替他们做。

---

## 给谁用 · 做什么

**目标客户**：SMB（创始人 / 没有营销团队）+ 有小型营销团队的中小公司。数据从无到中等，**不假设大流量、大预算**——所以越是依赖大数据的能力（因果去偏、MMM、增量实验）越往后放，作为"用着用着自然解锁"的**渐进能力**，而不是 day-1 卖点。

**MVP 锚点 = AI CMO 式策略副驾**：主动提问、**给出受众候选和定位角度让你挑/改**（react，而不是填空），产出一页纸策略（目标 · 受众+痛点 · 定位 · 内容支柱 · 怎么衡量）。它的数据门槛最低——**只要一个 LLM**——所以最适合中小团队。

**产品 = 两个自迭代循环（loop engineering）**：

- **Circuit A — 把策略想清楚**：有状态的策略共创循环。你喂任何输入（一句话 / 一个网址 / 几条旧帖，哪怕是错的），顾问基于行业先验给出最佳猜测、**标注哪些是"猜的"（confidence + assumptions）**，你逐轮纠偏，猜测变确认。
- **A→B 交接（the five-minute hook）**：锁定策略 → **立刻草拟出第一批内容**。锁定策略还会**重塑品牌经营上下文**（选定受众→ICP 细分、定位→价值主张、支柱→messaging pillars），让内容由"你刚定的策略"驱动，而不是旧品牌。
- **Circuit B — 跑营销运营**：goal → observe → draft → 人审 → publish → measure → adjust 的持续运营循环（路线图推进中）。

两个循环都是同一个 **Loop 引擎**（`core/loop/base.py`：observe→decide→act→verify）的实例，带显式 `is_done` 与 `max_turns` **刹车**（反"loopmaxxing"——终止是决策，不是意外）。

> **两条产品判断（已锁定）**：① 营销没有 100% 正确答案 → 卖"一个好的起点 + 廉价快速迭代"，不卖"标准答案"；② 假设用户不懂、没素材、可能说错 → 帮他**认出**策略（对选项做反应），而非凭空**发明**；AI 从任何输入 + 行业先验出发，标注置信度、标记猜测、用证据温和地推，**绝不说"你错了"**。

---

## 现在能做什么

以下能力**均已落地**，在 `mock` provider 下**零外部调用**即可完整跑通，覆盖 **策略共创 → 内容生产 → 热点反应 → 跨活动审核 → 发布度量** 的闭环。每个对外能力都是「**抽象接口 + mock + 工厂**」，要换真实/本地实现只改配置、不动业务代码。

- **策略共创循环 + A→B 交接**（`core/loop/`, `core/strategy/`）：上面说的 circuit A 与 the five-minute hook。
- **数字员工 + 多 Agent 流水线**（`core/agents/`）：每个 AI 工人是统一 `Agent`——Ideation 策略、Planning 规划、Copywriter 文案、**Auditor 审计**、**Designer 视觉**。编排是 orchestrator-worker + 共享黑板：**先串行决策 → 锁定共享内容核 → 并行渲染各渠道 → 复核（一致性检查 + 人审）**。
- **ICP 受众驱动每条内容**：品牌维护可复用的细分人群库（平台/痛点/价值主张/异议/触达）；每条 post 路由到一个 `(细分, 痛点)`，文案以痛点开场、落到价值主张。每条 post 显示定位条：**给哪类客户 · 哪个痛点/热点 · 漏斗阶段**。
- **Post 即唯一交付物（图文一体 + 一键改进）**：一条 post = 文案 + 配图/视频。Designer 作为渲染**子步骤**产出配图与品牌契合度评审（与文案自纠错**解耦**）。支持"应用 AI 改进"、"同步配图"、URL 附图/视频。
- **质量护栏（taste 与 truth 分离）**：每条内容带 `format / brand / consistency / terminology` **确定性检查** + 0–100 评分 + 术语库 + 预测表现启发式；之上叠加**跨模型 LLM-as-judge Auditor**（用不同模型家族审，解耦幻觉）；任一失败喂回**自诊断重试**。事实/数字一律走 `claim_check` 真值轨。
- **三层记忆（按租户隔离）**：语义=持久 `BrandProfile`，情景=lead 反馈/决策（`EpisodicNote`），工作=任务上下文切片。
- **可配置组织 + 车队可观测**：组织写在成员自身（`job_description / reports_to / handles_kinds`），换谁负责某类任务即改路由、不改代码。
- **跨活动审核队列 + directive→可追踪任务**、**度量发布闭环**（GA4 回流 / 安全发布默认人审后发 / 校对版本栈 + 锚点批注 + 内容锁）。
- **增长引擎层（渐进解锁）**：效果飞轮、实验账本、ICP 验证与发现、市场情报、品牌叙事、内容原子化、漏斗覆盖、视频、合规治理闸、付费创意环 + 规模化 1:1 outbound。
- **企业落地**：`DeploymentProfile`（cloud/hybrid/on_prem/air_gapped）把 provider 默认翻转为本地开源权重；发送/出云前串一条隐私 gate 链（合规 → 同意 → 出云前 mask/block PII）；带历史数据进来时 **warm-start** 飞轮/ICP。

> 路线图与设计详见 [`docs/`](docs/)（`roadmap-growth-engine.md`、`roadmap-maturity.md`、`deployment-onprem.md`）与 [`DESIGN.md`](DESIGN.md)。当前 **199 个后端测试 + 6 个前端测试** 全绿。

---

## 架构（真实、简单、可换）

刻意保持轻量：**没有消息队列、没有向量库、没有 LangChain**——一个 FastAPI 后端 + 一个 Next.js 前端，靠 provider 抽象保持可换与可离线。

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 前端 | Next.js 16 · React 19 · TypeScript · TailwindCSS | `apps/web/`，按营销工作流分区：Overview · Strategy · Plan · Create · Review · Brand · Team |
| 后端 | FastAPI · Uvicorn · Python 3.13 | `apps/api/`，`/api/v1/team` 团队 OS API + 旧的 `/api/v1/campaign` 单次生成接口 |
| 领域核心 | 纯 Python（框架无关） | `core/`，业务逻辑都在这里，可被 API 之外的入口复用 |
| 数据 | SQLModel + SQLAlchemy 2.0（默认 SQLite） | 单库，**行级 `tenant_id`** 多租户隔离 |
| 契约 | Pydantic v2（`StrictSchema`，`extra="forbid"`） | agent 交接处用 schema 约束，杜绝结构漂移 |
| 模型 | provider 抽象 + 工厂 | `mock` / `openai` / `dashscope`(Qwen) / `local`(任意 OpenAI 兼容) |

**核心模式 = provider 工厂**：LLM、图像/视觉、分析、发布、市场情报、富集……每个外部能力都是 `抽象基类 + Mock 实现 + create_*() 工厂`。默认全 mock，所以 clone 下来零配置即可跑通全链路；要上真实或本地模型，改一个环境变量即可。

```text
reelmatrix/
├── apps/
│   ├── api/                # FastAPI：routes / services / schemas（HTTP 边界，薄）
│   └── web/                # Next.js 前端
├── core/                   # 领域核心（框架无关）
│   ├── loop/               # Loop 引擎（两个循环共用的抽象）
│   ├── strategy/           # circuit A：策略顾问 + 循环 + A→B 交接 handoff
│   ├── agents/             # 数字员工：Agent 抽象 + 角色 + 注册表
│   ├── workflows/          # 编排：campaign 实例化 + task_runner（并行渲染/自纠错/审计）
│   ├── llm/                # 模型 provider 抽象 + mock/openai/dashscope/local + 工厂
│   ├── db/                 # SQLModel 模型 + engine + seed
│   ├── schemas/            # Pydantic 严格契约
│   ├── content/            # 平台规格 / 校验 / 评分 / 术语 / 预测表现 / GEO / 追踪
│   ├── media/              # 图像/视觉/视频 provider
│   ├── growth/             # 飞轮 / 实验 / ICP / 因果增量
│   ├── analytics/  publish/  trends/  market/  paid/  outbound/   # 各能力 provider
│   ├── policy/  privacy/  identity/  ingest/  evals/              # 治理 / 隐私 / 数据 / 评测
├── configs/                # settings（环境变量读取）
├── docs/                   # 路线图 + 部署文档
└── tests/                  # 199 个后端测试
```

---

## 本地运行

后端 FastAPI + 前端 Next.js。默认 `mock` provider，无网络调用、结果确定，可直接开发测试。

### 1. 环境要求

- Python 3.13 与 [uv](https://docs.astral.sh/uv/)
- Node.js 20+ 与 npm

### 2. 首次安装（仓库根目录）

```bash
uv python install 3.13
uv sync --locked

test -f .env || cp .env.example .env
test -f apps/web/.env.local || cp apps/web/.env.example apps/web/.env.local

cd apps/web && npm ci && cd ../..
```

Python 依赖装到 `.venv/`，前端依赖装到 `apps/web/node_modules/`，均为项目本地目录、不提交 Git。

### 3. mock 配置

根目录 `.env`：

```dotenv
APP_ENV=development
LLM_PROVIDER=mock
WEB_ORIGIN=http://localhost:3000
```

`apps/web/.env.local`（浏览器访问后端的地址）：

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> 真实 API Key 只放根目录 `.env`，**绝不**写入 `.env.example`、`apps/web/.env.local` 或任何 `NEXT_PUBLIC_*` 变量。

### 4. 准备演示数据并启动

```bash
# 一次性 seed 演示数据（创建租户、Adam 等成员、ICP 细分）
DATABASE_URL=sqlite:///./reelmatrix.db LLM_PROVIDER=mock uv run python -m core.db.seed

# 终端一：后端
DATABASE_URL=sqlite:///./reelmatrix.db LLM_PROVIDER=mock WEB_ORIGIN=http://localhost:3000 \
  uv run uvicorn apps.api.main:app --reload

# 终端二：前端
cd apps/web && npm run dev
```

访问：

- Web：`http://localhost:3000` → 左侧 **Strategy** 标签即策略共创循环（输入想法 → 逐轮打磨 → **"Lock it → draft my first content"** 一键出第一批内容）
- 健康检查：`http://localhost:8000/health` ｜ API 文档：`http://localhost:8000/docs`

> **没有数据库迁移系统**：改了 `core/db/models.py` 的字段后，删掉 sqlite 文件重新 seed 即可（`rm reelmatrix.db && … python -m core.db.seed`）。

### 5. 测试与构建

```bash
# 后端（conftest 强制 mock，绝不调真实模型/消耗额度）
uv run pytest

# 前端
cd apps/web && npm run typecheck && npm test && npm run build
```

---

## LLM Provider 配置

只改根目录 `.env` 的 `LLM_PROVIDER` 及对应字段即可切换；业务代码不变。

```dotenv
# mock（默认，离线确定）
LLM_PROVIDER=mock

# OpenAI / ChatGPT
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# 阿里云 DashScope（通义千问，OpenAI 兼容）
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# 若账号使用业务空间，再加 DASHSCOPE_WORKSPACE_ID=...

# 任意 OpenAI 兼容的本地运行时（Ollama / vLLM 等）
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5
```

前端可在请求时通过 `X-LLM-Provider` header 临时指定 provider（不传则用 `.env` 的默认值）。

---

## 部署到阿里云（Docker Compose，一键起）

仓库已自带整套部署文件：`Dockerfile.api`、`Dockerfile.web`、`docker-compose.yml`、`deploy.sh`、`.env.deploy.example`。线上用**真·通义千问（DashScope）**。

**完整傻瓜步骤见 [`docs/deploy-aliyun.md`](docs/deploy-aliyun.md)**，三步概括：

1. **阿里云 ECS**（Ubuntu，2核4G 起，装 Docker）安全组**放行 3000 / 8000**端口。
2. SSH 登服务器，拉代码（私有仓库需 GitHub token；代码在 `team-os-phase0` 分支）：
   ```bash
   git clone -b team-os-phase0 https://<TOKEN>@github.com/JiimS66/reelmatrix.git
   cd reelmatrix
   cp .env.deploy.example .env   # 填 PUBLIC_IP 和 DASHSCOPE_API_KEY
   ```
3. 一键起：
   ```bash
   chmod +x deploy.sh && ./deploy.sh
   ```
   浏览器打开 `http://你的IP:3000`。

**怎么工作**：`web` 容器构建时把 `NEXT_PUBLIC_API_BASE_URL=http://${PUBLIC_IP}:8000` 烤进前端；`api` 容器首次启动自动 seed 演示数据；SQLite 落在挂载卷 `./data/`，重建容器不丢数据。`PUBLIC_IP` 同时用于前端访问地址和后端 CORS——必须和你浏览器里打开的地址一致。

**更新**：本地 `git push` → 服务器上 `./deploy.sh`（自动 `git pull` + 重建 + 重启）。

> ⚠️ **改了数据库模型字段后再更新**：本项目无迁移系统，挂载卷里的旧 `data/reelmatrix.db` 不会自动加新列。这种情况要在服务器上 `docker compose down && rm -f data/reelmatrix.db && ./deploy.sh`（会丢演示数据并重新 seed）。仅改业务逻辑/前端时无需此步。

> 想验证 on-prem 卖点：把 `.env` 的 `LLM_PROVIDER` 改成 `local` 指向你的 Ollama/vLLM 即可，业务代码一行不动。

---

## 文档

- [`DESIGN.md`](DESIGN.md) — 设计系统与视觉生成方向
- [`docs/deploy-aliyun.md`](docs/deploy-aliyun.md) — 阿里云部署傻瓜版
- [`docs/deployment-onprem.md`](docs/deployment-onprem.md) — 企业本地部署 / 隐私 / 数据融入
- [`docs/roadmap-growth-engine.md`](docs/roadmap-growth-engine.md) · [`docs/roadmap-maturity.md`](docs/roadmap-maturity.md) — 路线图

## 历史接口（legacy）

最早的"填 brief → 一键生成方案"单次接口 `POST /api/v1/campaign/generate` 仍保留并可用，但已被上述团队 OS / 策略副驾取代；新功能请以本文档为准。
