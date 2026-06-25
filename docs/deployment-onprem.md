# 企业落地：本地部署 + 数据隐私 + 数据融入

> 为什么这三件一起：企业的营销数据（客户名单、成效、策略）敏感、**不能出域** → 本地部署 +
> 数据隐私是落地前提；而企业**带着多年历史进来**（老内容/成效/品牌文档）→ 数据融入让系统
> day-1 **warm-start**（飞轮/ICP 有真实先验,不是空跑）。本地部署正是让企业敢交出这份历史
> 数据的前提。全部 web-research-validated（2025–2026 现状）。

---

## 1. DeploymentProfile —— 一个开关翻转全局姿态

`configs/settings.py` 的 `deployment_profile`（env `DEPLOYMENT_PROFILE`）：

| Profile | LLM/视觉等 provider | 出云(EgressGate) | 适用 |
|---|---|---|---|
| `cloud` | 云 API（OpenAI/DashScope）或 mock | 允许（带 PII/consent 控制） | SaaS / SMB |
| `hybrid` | 敏感任务走本地、其余云 | **出云前 mask PII** | 中型,部分上云可接受 |
| `on_prem` | 强制 local | mask PII | 企业自托管 |
| `air_gapped` | 强制 local | **BLOCK 任何非本地出口** | 受监管/隔离网 |

`GET /api/v1/team/deployment` 返回当前 profile、各 provider 是 local 还是 cloud、以及启用的
gate（Team 页 DeploymentCard 可视）。

## 2. 本地 provider 可行性（诚实审计，~9/10 今天可跑）

| 能力 | Verdict | 推荐本地栈（开源权重 + 推理） | 单盒硬件 |
|---|---|---|---|
| 文案/创意/审计 | ✅ | **vLLM** + Qwen3-32B / gpt-oss-120b | 1×H100 80GB（FP8） |
| Agent 工具调用 | 🟡 需约束解码 | vLLM + **XGrammar** guided JSON,32B+ | 1×H100 80GB |
| 图像（Designer） | ✅ | **ComfyUI + FLUX.1-dev** + 每客户 LoRA | 1×RTX 4090 24GB |
| 转写（clips） | ✅ | **faster-whisper** large-v3-turbo + ffmpeg | 任意 8GB GPU/CPU |
| embeddings + 向量 | ✅ | **BGE-M3** + **pgvector**（已在 Postgres） | CPU 可,8GB GPU 更快 |
| 聚类（segment 发现） | ✅ | **HDBSCAN** + scikit-learn + UMAP | CPU |
| 贝叶斯实验 | ✅ | **PyMC** / SciPy | CPU |
| 因果/增量 | 🟡 R 运行时 | GeoLift / CausalImpact（R）或换 Python | CPU |
| MMM | 🟡 | **PyMC-Marketing**（纯 Python,不用 Meridian） | CPU |
| PII | ✅ | **Microsoft Presidio**（全离线） | CPU |

**两个诚实的 🟡**：(a) agentic 工具调用——开源权重需 vLLM+XGrammar 约束解码,且多步编排仍逊于
闭源前沿,要预算重试/校验；(b) 因果/MMM——GeoLift/Robyn 是 R（shell out 或小 R 微服务）,或
统一用纯 Python 的 PyMC-Marketing。

**单盒企业最小配置**：1×H100 80GB（LLM+embeddings+全部 CPU ML）+ 1×RTX 4090 24GB（图像/视频）+
Postgres/pgvector 共置。我们的 provider 抽象 + LLM factory 已支持 `local`,本地化主要是**补实现,
不是改架构**。

## 3. 隐私 gate 链（发送/出云前）

复用现有「决策对象、决策与执行解耦」的 `PolicyGate` 范式,串成一条 pre-egress 链：

```
内容/触达 ──▶ PolicyGate(合规:广告法/PII/品牌安全/披露)
            ──▶ ConsentGate(按 subject+purpose 检查同意;denied/withdrawn → block)
            ──▶ EgressGate(air_gapped→block 非本地; hybrid/on_prem→mask PII before cloud)
            ──▶ 送达/发送
```

- `core/privacy/`：`PIIRedactor`（mock regex,Presidio 可换）、`EgressGate`（LiteLLM 式 MASK/BLOCK）。
- `ConsentRecord`（OneTrust/IAB-TCF 形）+ `consent_status` —— 无记录默认 legitimate_interest。
- `send_outbound` 已串入 consent + egress gate（air-gapped 连外发都阻止）。

## 4. 租户隔离

- **cloud/SMB**：row-level `tenant_id`（每表都有）+ 建议加 **Postgres Row-Level Security** 硬化。
- **企业**：**single-tenant on-prem 部署** = 天然 DB-per-tenant + 数据驻留,一步到位（受监管买家
  要的「无共享基础设施」）。**不建议** schema-per-tenant——on-prem 实例是更干净的隔离故事,且本就要建。

## 5. 打包（演进路径）

`Docker Compose`（现在：API + Postgres + 可选 local-LLM 容器,`DATABASE_URL` 已支持 SQLite→Postgres）
→ `Helm chart`（k8s）→ `Replicated/Embedded Cluster + air-gap bundle`（受限网,premium）。air-gap =
**无遥测/更新 phone-home**（由 DeploymentProfile 关闭出口）。企业功能可 license-key 门控（n8n 式）。

## 6. 数据融入（warm-start onboarding）

企业的历史 = 冷启动燃料。设计上**不新建 seeding 路径**,而是把历史写成「已完成的、带成效的 post」,
现有 `learn_outcomes`/`score_segments` 自然 warm-start：

- **历史内容+成效**（`POST /import/historical`,CSV/CRM/GA4 导出 → rows）→ "Imported history" campaign
  的 done ASSET task + Post + MetricSnapshot → 飞轮 day-1 有真实 Beta 先验、ICP 有 SegmentPerformance。
- **品牌文档/网站**（`POST /import/brand-knowledge`）→ 提取 voice/value-prop/pillars/tone → BrandProfile
  + messaging_pillars（mock 提取,真实换 LlamaIndex/Unstructured RAG ingestion）。
- 真实连接器（CRM、GA4、DAM 自动打标、Splink 去重）后续按 `ImportProvider` 接口换入,无 schema 变更。

## 7. 落地清单（mock → real 的接入项）

vLLM+Qwen3 / ComfyUI+FLUX / faster-whisper / pgvector+BGE-M3 / HDBSCAN / PyMC(-Marketing) /
Presidio 接真实；真实 CRM/GA4/DAM 连接器；Postgres RLS；Helm chart；R 微服务（GeoLift/Robyn,
如选 R 路线）。架构与 provider 接口均已就位。
