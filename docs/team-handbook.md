# 团队交接手册 — 内容测试 · TestSprite Loop · LLM 配置

给新加入同学的三份操作指南。前提：你已经按 [README](../README.md) 的
Quickstart 把项目在本地跑起来了（mock 模式，不需要任何 key）。

---

## 一、内容质量测试（产品的生死线）

**为什么这是第一优先级**：这个产品对客户唯一真正重要的问题是——
"AI 写出来的东西我敢不敢直接发出去"。架构、图表、集成都只是这个问题的
放大器。在真模型上测出"可发布率"并持续提升它，比加任何新功能都重要。

### 盲评协议（每次模型/prompt 变更后跑一轮）

1. **准备 brief**：用 TestSprite 的真实产品信息（`scripts/demo_prep.py` 里的
   BRIEF 是基准），加上 2-3 个你自己找的真实 dev-tool 公司做对照。
2. **生成**：`.env` 配好真模型（见第三节），`ASSET_DRAFT_FANOUT=3`，跑
   一个 campaign，收集所有渠道的产出（LinkedIn / X / Email / Blog /
   GitHub / Community 各至少 3 条，总数 ≥20 条）。
3. **盲评**：把内容去掉来源标记后发给评审人（最好是真的做营销的人，
   实在没有就团队互评但不评自己调的 prompt 版本）。每条三档：
   - **A 可发布** —— 改两个词以内就能发
   - **B 要大改** —— 结构可用但需要重写段落
   - **C 不能用** —— 不如自己从头写
4. **记录**：结果记进下面的表格（直接 append 到本文件），标注模型、
   fanout、prompt 版本（commit sha）。

| 日期 | 模型 | fanout | A% | B% | C% | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| _待填_ | | | | | | |

**目标线**：A 率 ≥50% 才算过生死线；≥70% 才能拿去主动演示给客户。

### 可发布率低时按序调这些（成本从低到高）

1. **范文（最有效）**：Brand tab → Onboarding 导入客户历史爆款
   （`import_history`），copywriter 会自动把同渠道表现最好的 2 条作为
   few-shot 注入（`core/content/continuity.py: channel_exemplars`）。
2. **格式合同**：`core/content/platform_specs.py` —— 每个渠道的结构模板
   直接进 prompt，改这里比改 agent prompt 见效快。
3. **Agent prompt**：`core/agents/` 下各角色。改动必须跑
   `uv run pytest` 确认 220+ 测试不破。
4. **fanout 调参**：3 → 5（开源 API 便宜，边际成本可忽略）。
5. **换更大的模型**（最后手段）：qwen3-32b → 72b。

### 评估基线（防退化）

`POST /api/v1/team/evals/run` 跑现有 eval suite（policy/GEO 可判定项）。
**待补**：内容质量的 LLM-as-judge case（用 SiliconFlow 的 DeepSeek 当裁判，
和生成方 Qwen 不同族）——如果你接手这块，把盲评协议里的 A/B/C 标准写成
judge prompt，加进 `core/evals/`。

---

## 二、TestSprite Loop（hackathon 主线 + 回归防线）

**是什么**：用 TestSprite 开源 CLI 对**线上部署**跑端到端测试，每一轮
create → run → failure bundle → fix → rerun 都留证据。这既是 hackathon
"Build the Loop" 的参赛主线，也是我们自己的回归防线。

### 核心约定（不要破坏）

- **[LOOP.md](../LOOP.md) 是实时日志**，轮次发生时就记，不事后补写。
  每轮记录：失败摘要（bundle 里的关键日志/截图）→ 诊断 → 修复 commit
  （引用 test ID）→ rerun 结果。
- **修复必须先确认上线再 rerun**：`GET /health` 返回部署的 commit sha，
  rerun 前核对它等于你的 fix commit。
- 平台账号、项目 ID、CLI 版本都在 LOOP.md 的 Meta 表里。

### 常用命令

```bash
testsprite project list                     # 前端 reelmatrix / 后端 reelmatrix-api
testsprite test list --project <id>
testsprite test run <test-id>               # 跑一条
testsprite test artifact get <run-id>       # 拉失败 bundle（日志+截图）
testsprite test code put <test-id> --expected-version vN   # 更新测试代码
```

### 已知坑

- 后端测试的 `BASE_URL` 由平台注入，来自 project 的默认 URL —— project
  创建时必须带 `--url`，否则测试 blocked（LOOP.md 记录过这轮）。
- 前端测试跑在真浏览器上，UI 大改（比如本次的 Launch Timeline / KPI 带）
  之后**必须**把 banked 的前端测试全部重跑一遍，失败了按流程记录修复，
  不要静默改测试。

### 本次改版后待办

UI 结构变了（首页 KPI 带、Campaigns 页时间轴、Results 页漏斗），已 bank
的前端测试的选择器和步骤大概率要更新 —— 这是接手人的第一个练手任务，
正好完整走一遍 fail → fix → rerun 并记进 LOOP.md。

---

## 三、LLM 采购与配置清单

**选型原则（已定，不要重开讨论）**：全线国产开源权重模型 ——
现在走便宜的托管 API，将来私有化时同一族模型搬进客户机房，
provider 抽象保证零代码迁移。写手（Qwen）和审计员（DeepSeek）
**必须不同族**，否则跨模型审计名存实亡。

### 需要注册/购买的

| 平台 | 用途 | 拿什么 | 量级参考 |
| --- | --- | --- | --- |
| 阿里云百炼 DashScope | 主 LLM（Qwen3 系）+ 生图（Qwen-Image）+ VLM（Qwen3-VL） | API Key | 开源模型端点 ¥2-4/百万 token；一条成品帖 <¥0.5 |
| SiliconFlow | 审计员（DeepSeek-V3 系） | API Key | 同量级，用量约为主模型的 1/5 |
| Plausible（可选） | 真实网站分析 | site + API key（或客户自托管） | 免费层够用 |

注意：模型具体型号更新很快（本手册写于 2026-07），下单前花十分钟确认
DashScope 上 Qwen 最新一代的型号名和价格，改 `DASHSCOPE_MODEL` 即可。

### .env 完整配置（拿到 key 后照抄）

```dotenv
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=<key>
DASHSCOPE_MODEL=qwen3-32b        # 确认当时最新型号

SILICONFLOW_API_KEY=<key>
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V3

ASSET_DRAFT_FANOUT=3             # 多稿自选
TREND_SOURCE=hackernews          # 真实热点源（免 key）
# NOTIFY_WEBHOOK_URL=<飞书/Slack incoming webhook>
# MEDIA_PROVIDER=dashscope       # 生图，确认 Qwen-Image 型号后开
# VISION_PROVIDER=dashscope      # VLM 审图
# DASHSCOPE_IMAGE_MODEL=qwen-image
# DASHSCOPE_VL_MODEL=qwen3-vl-plus
```

**最后一步在界面里做**：Team tab → Content auditor → provider 改成
`siliconflow`。不做这一步，审计员会跟着部署默认走 Qwen，跨模型审计失效。

### 接通后的验证清单

1. 顶栏徽章显示 `live on Qwen · qwen3-32b`（不再是 mock）
2. 跑一个 campaign，Team tab 的 AI usage 卡出现真实 runs/tokens
3. 任务详情里某条 SELF_CORRECTED 事件带 `draft_fanout` payload
   （多稿自选生效的证据）
4. 审计员跑过的帖子 checks 里有 `audit` 项，且 Team tab 确认它的
   provider 是 siliconflow
5. 跑第一节的盲评协议，把结果填进表格

### 私有化路线（现在不做，别删相关代码）

`local` provider（vLLM/Ollama）、`zimage` provider（Z-Image-Turbo，16GB
显存）、`deployment_profile` 开关都是为私有化预留的。有客户真要私有化时
从 [docs/deployment-onprem.md](deployment-onprem.md) 和
[docs/architecture-enterprise-loop.md](architecture-enterprise-loop.md) 开始。
