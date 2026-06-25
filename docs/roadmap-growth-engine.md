# Roadmap：从「内容生产线」到「会学习的增长引擎」

> 主题：把系统的智能从 **correctness（把一件事做对）** 升级到 **effectiveness +
> learning（知道该做哪件事、并从市场结果里越做越准）**。当前的 self-improvement
> 名不副实——它是 self-CORRECTION。这份 roadmap 给它装上真正的**效果飞轮**。
>
> 一贯约束（同 Phase 1–4）：mock-first、provider 抽象、SQLModel 实体、每阶段可独立
> 发布、`uv run pytest` + 前端 typecheck/test/build 全绿、审计并发敏感处、commit+push。
> 无 Alembic → 改模型后重建 `/tmp/rm_demo.db` 重新 seed。

---

## 0. 架构主线（先读这个）

四组竞品/开源调研收敛到**同一个底座**：一张被所有能力共享的「**内容属性词汇表**」+ 一个
「**属性 → 结果 → 学习 → 注入**」的闭环。

```
                       ┌──────────────────────────────────────────────┐
                       │   共享属性词汇表 (ContentAttribute)            │
                       │   hook / cta / length / emotion / visual /     │
                       │   channel / segment / funnel_stage / pillar    │
                       └──────────────────────────────────────────────┘
   生产时给内容打标签 ▲                                   │ 注入为「什么有效」先验
                      │                                   ▼
   ┌──────────────┐   │   ┌──────────────────┐   ┌──────────────────────┐
   │ Experiment   │───┴──▶│ AttributeOutcome │──▶│ agent 上下文 (第4层    │
   │ 变体=带标签   │ winner│ Beta(α,β) 后验   │priors│ 派生记忆「what's      │
   │ 的内容       │◀──────│ per 属性×渠道×段  │   │ working」memo)        │
   └──────────────┘ 种变体└──────────────────┘   └──────────────────────┘
        ▲                         ▲ 喂结果
        │                         │
   GA4/MetricSnapshot (已有) ──────┘
```

**为什么这是主线**：Persado / Adobe GenStudio 学的是**属性级**先验（不是"这条帖子分数"，
而是"curiosity 钩子在 LinkedIn×创始人 上 +38% 提升"）；GrowthBook / PostHog 的实验把
内容**打成带标签的变体**；两者写入**同一套属性**——实验产出 winner → winner 更新每属性
后验 → 后验作为先验注入 agent 上下文、并种下下一个实验的变体。先把这个骨架建出来，后面
每个能力（ICP 验证、漏斗、付费创意）都只是这个骨架的**属性来源或消费者**，而不是孤立功能。

---

## Phase 5 — 效果飞轮 + 实验骨架（公共底座，最高优先）

把 self-correction 升级成 outcome-learning。**这是后面所有阶段的地基**，建议先做。

### 5a — 飞轮（属性 + 学习先验 + 注入）
- **借鉴**：Persado（属性级语言学习）、Adobe GenStudio（asset/attribute/channel 三级表现）、
  HubSpot Breeze「Evolve」live loop、Einstein 冷启动全局回退。
- **做什么**：
  - `ContentAttribute`：渲染时给每条 post 打结构化标签（`hook_type / cta_style /
    length_bucket / emotion / visual_style` + 已有的 `channel / segment / funnel_stage`）。
    这是共享词汇表，所有阶段写它/读它。
  - `AttributeOutcome(attribute_type, attribute_value, channel, segment, impressions,
    conversions, n_posts, alpha, beta, updated_at)`：每属性一个 Beta(α,β) 后验。
  - `OutcomeLearner`（mock job）：从已有 `MetricSnapshot`/GA4 回流更新后验。
  - **注入**：copywriter/designer 跑前，取该 `channel×segment` 的 top/bottom 属性，作为
    "what's working" memo 注入工作上下文——你三层记忆的**第 4 层（派生记忆）**。
  - 冷启动：`n_posts < k` → 回退**全局先验**，避免新渠道/新段乱推荐。
- **验证**：跑若干带 outcome 的 mock 数据 → 后验更新 → 下一轮 brief 的上下文里出现排序后
  的属性指引；冷启动回退生效。

### 5b — 实验账本（变体 + 统计 + winner→知识）
- **借鉴**：GrowthBook / PostHog 数据模型与贝叶斯「chance to beat control」、Optimizely
  Opal「agent 自动设计实验」、Statsig/Eppo 经验先验+收缩（低流量友好）。
- **做什么**：
  - `Experiment / Variant(一个必为 control) / ExperimentMetric(role: goal|secondary|
    guardrail) / ExperimentResult(point_estimate, ci, chance_to_beat_control, status:
    winner|loser|inconclusive)`——直接抄 GrowthBook 的 metric 角色 + 95%/5%/灰 判定。
  - `StatsProvider`（mock = Beta/Monte-Carlo 算 win-probability，可随时 peek；保留
    frequentist z-test 同接口）。你的「内容分/品牌契合」天然是 **guardrail metric**。
  - `ExperimentDesigner` agent：brief → N 个**预打 5a 属性标签**的变体（A=fear钩子+短CTA，
    B=curiosity钩子+长CTA），让每个实验同时是一份带标签的训练信号。
  - `WinningPattern(pattern_attributes, evidence_experiment_id, lift, confidence)`：winner
    自动晋升为可复用生成先验，喂回 5a 的同一个注入 memo。**这是 agentic OS 的差异点——别人
    把结果当数据存，我们把 winner 变成生成先验。**
  - 预留字段：`sequential`（always-valid p 值，早看不罚）、`srm_check`（曝光split偏差告警）。
- **验证**：建一个 2 变体实验 → 灌 mock 曝光/转化 → StatsProvider 判 winner → 自动生成
  一条 WinningPattern → 下一轮生产上下文里出现。

> 规模提示：5 比较大，按 5a → 5b 两次发布。

---

## Phase 6 — ICP：从假设到验证（+ 发现 + 市场情报）

让细分人群从「人手填的假设」变成「被市场验证的结论」，并能发现新段、看见竞争环境。

- **借鉴**：6sense/Demandbase（fit×intent×stage 分层）、MadKudu/Pocus（Fit 与
  Likelihood 双分）、HubSpot Breeze（规则 fit 层 + ML propensity 层分离）、Keyplay/Clay
  （seed→lookalike、透明加权评分 + drivers）、SparkToro（按 affinity 而非热度发现受众）；
  竞品：Crayon/Klue（page-diff + battlecard）、Brandwatch（SOV = 自家 ÷ 总提及）、
  AlsoAsked/AnswerThePublic（PAA/autocomplete 问题树）、Exploding Topics（rising/peaked）。
- **做什么**：
  - `SegmentPerformance(segment, impressions, conversions, score 0–100, status:
    validated|underperforming|unproven, top_drivers[])`——**直接复用 Phase 5 骨架**
    （segment 本就是一个属性维度），加一个可解释的加权分（`SegmentScorer` provider，
    mock=加权公式存 top-3 drivers；real=LightGBM+SHAP）。
  - `DiscoveredSegmentCandidate(features, why_lift, status)` + `SegmentDiscoverer`
    （mock=对参与/转化事件做规则聚类；real=HDBSCAN+UMAP）→ 进**审核队列**："发现一个在
    转化的人群簇 X，要不要晋升为追踪段？"（复用 Phase 4 队列）。
  - surge-over-baseline 标志：段相对**自己的滚动基线**升温 → 注入 brief（配合现有
    timely_angles）。
  - 市场情报（可作 6b）：`CompetitorPositioning`（page-diff messaging 变化，mock 合成；
    real=changedetection.io/Playwright+trafilatura+difflib）、`ShareOfVoice`（`MentionSource`
    算）、`AudienceQuestion`（`QuestionSource` PAA mock）；**消息白空间检测**（竞品没覆盖、
    受众一直在问的痛点）→ 自动 spawn directive（复用 Phase 4 directives→tasks）。
  - **注入**：brief 增加「market context」块——段的 fit 分+状态+drivers、SOV 趋势、top
    受众问题、rising 话题。
- **验证**：跑出 segment 分与状态；mock 发现一个候选段进队列；brief 带上 market context。

---

## Phase 7 — Always-on 品牌叙事 + 内容原子化 + 漏斗覆盖（杠杆）

补「贯穿叙事」「一鱼多吃」「漏斗意识」三个结构性缺口。

- **借鉴**：Writer.com（brand voice 是治理层 + 知识图 + term bank）、Writer 的 messaging
  框架（value prop → 3–5 pillar → proof points 金字塔）、HubSpot Content Remix（pillar →
  ≤6 衍生，remix 视图内联编辑）、Jasper Campaigns（一个 brief 扇出全渠道）、TOFU/MOFU/BOFU
  覆盖矩阵 + HubSpot workflow（stage 是路由键不只是标签）。
- **做什么**：
  - `BrandNarrative(value_proposition, term_bank)` + `MessagingPillar[](name, proof_points)`
    ——**campaign 无关的持久层**；post 引用 `pillar_id`；现有 auditor 增「pillar 贴合 +
    禁用词」检查（Acrolinx/Writer 式，跨多帖抓品牌漂移）。
  - `PillarAsset(kind, source_ref)`（长内容/研究/转写）+ `Post.pillar_id / derived_from`
    FK → hub-and-spoke 衍生图；`RepurposeProvider.atomize(pillar, channels, funnel_stage)`
    （mock 返回 canned 衍生，`max_derivatives` 旋钮抄 HubSpot 的 6）。衍生共享 pillar 的
    实体/术语 = consistency-by-construction。
  - `funnel_stage`（`TOFU|MOFU|BOFU`）+ `desired_action` 字段（**最高杠杆/最低成本：一个
    枚举 + 一个聚合查询**）→ campaign 级 **`funnel × segment` 2-D 覆盖矩阵**，空格标记为
    gap 并可一键 spawn 成 directive。
- **验证**：一个 pillar → 多渠道衍生且术语一致；覆盖矩阵标出空缺并能转任务。

---

## Phase 8 — 视频形态（兑现「Reel」之名）

当前视频是 human-first 占位——产品叫 ReelMatrix，最该强的形态却最弱。

- **借鉴**：HeyGen/Synthesia（script → scenes → **async render + 回调/manifest**）、
  Opus Clip/Vizard（长转短，0–99 virality + Hook/Flow/Value 维度）、开源
  SamurAIGPT shorts（分块→框架打分→重叠去重→竖屏裁剪；faster-whisper+ffmpeg）、FunClip、
  FFmpeg 8 原生 whisper。
- **做什么**：
  - `VideoSpec(scenes[])`，`Scene = {visual_prompt, caption, duration, voiceover_text}`——
    把视频也变成结构化交付物（同 Phase 2 post 思路），由 pipeline 产出、`VideoProvider`
    mock 消费（返回 stub render + status + manifest，**async 契约**让 mock 与未来真渲染器同形）。
  - `ClipProvider.rank(transcript) → [{clip_score 0–100, reason, hook_sentence, start, end}]`
    （mock 启发式）——长内容（Phase 7 的 PillarAsset transcript）裂变成排序候选短片；**永远
    存 reason 并让人选**（公开测评：虚荣分常误判，~40% 片段被弃）。
- **验证**：一个 transcript → 排序短片候选；一个 VideoSpec → mock 异步渲染回 manifest。

---

## Phase 9 — 治理：自适应自治 + 全链路合规闸

把「信任」和「合规」从固定/单点，变成自适应、全覆盖。

- **借鉴**：Salesforce Agentforce（Topics+Actions+Testing Center 暴露推理）、Copilot
  Studio（least-privilege + HITL 审批暂停）、LangGraph `interrupt()` 四动作
  （approve/edit/reject/respond）、OpenAI Evals（夜间跑、追每 agent 可靠性）；合规：
  Open Policy Agent/Rego（决策与执行解耦、返回决策对象）、NeMo Guardrails（分层 rail）、
  Guardrails AI（validator + `on_fail`）、Presidio（PII）、IAS/DoubleVerify（投放前分类拦截）。
- **做什么**：
  - `AgentReliabilityScore(agent_id, task_type, approval_rate, avg_edit_distance,
    violation_count, n)`——**复用已有 fleet 数据**，每 (agent, 任务类型) 一条滚动信任分。
  - **score-modulated `execution_mode`**：不再是写死字段，而是 `EscalationPolicy` 的输出
    （低→human_only，中→ai_draft_human_review，持续高+低风险→ai_auto）。它擅长且历史好的
    地方放手，生疏/高风险的地方收紧。
  - `ConfidenceGate`：self-reported confidence + **现有跨模型 auditor 当 judge**；低置信/
    judge 分歧 → 人审队列（采纳 LangGraph 四动作动词）。
  - `PolicyGate`（first-class **发布前** provider）+ **版本化规则包**（抄 OPA：传结构化
    输入{文本,locale,渠道,claim 标志}，返回 `{allow|deny|warn, violations[], required_fixes[]}`）。
    现有热点 kill-switch **收编为规则包里的一条规则**。起步规则（mock-first，规则即 YAML 数据，
    各带 `on_fail: block|warn|rewrite`）：
    - **FTC 披露**：material_connection 时要 `#ad`/清晰披露，拒绝埋藏式。
    - **中国广告法绝对化用语**：最/第一/"best/#1" → 拦截，除非附可验证例外（罚则 20万–100万，高价值）。
    - **PII 泄露**：包 Presidio 当 validator（也供 Phase 10 outbound 复用）。
    - **品牌安全/受监管断言**：健康/金融超级断言、禁用词。
- **验证**：低可靠分的 agent 任务被收紧到人审；一条含「最」的文案被 PolicyGate 拦下并给
  required_fix；热点 kill-switch 仍作为规则之一生效。

---

## Phase 10 — 新维度：付费创意 + 规模化 1:1 outbound（最大、最独立）

补「付费这半壁江山」和「规模化触达」——数字营销不止 organic inbound。

- **借鉴**：Google PMax（资产池→按位组合，Low/Good/Best 评级）、Meta Advantage+（动态创意
  测最多 150 组合、分钟级把预算挪向赢家）、AdCreative.ai（CNN 创意分，投前预测 CTR 0–100）、
  Smartly（模板+feed+规则预算）；outbound：Clay（waterfall 富集 + per-lead AI 研究）、
  Apollo/Outreach（多渠道序列 + 行为分支）、Instantly/Smartlead（warmup/限额/轮换/坏箱自动停）。
- **做什么**：
  - `PaidCreativeVariant` + `CreativeScoreProvider`（**扩展现有 content_score** → 投前 0–100
    CTR/awareness 预测）+ `BudgetAllocator`（mock 把模拟预算挪向赢家）——**create→test→
    reallocate 循环直接复用 Phase 5 实验骨架**，全程 mock spend/metrics 直到真广告 API 落地。
  - `OutboundProspect` + waterfall `EnrichmentProvider`（A→B→C 命中即停）+ per-lead AI 研究
    （写个性化首句）+ `OutboundSequence`（多渠道有序步骤 + 行为分支 + A/B）+ `DeliverabilityGuard`
    （warmup 爬坡、每箱日上限 ~30–40、轮换、bounce<1%/spam<0.3% 自动停）。**每封发送都过
    Phase 9 的 PolicyGate**。
- **验证**：一条 post → N 个付费变体投前打分 → mock 预算重分配到赢家；一个 prospect 走
  waterfall 富集 + 个性化首句 + 序列，且过合规/送达闸。

---

## 优先级与依赖

```
Phase 5 (飞轮+实验骨架) ──┬──▶ Phase 6 (ICP 验证/发现)  ── 复用骨架(段=属性维度)
   [先做, 是地基]         │
                         ├──▶ Phase 10 (付费创意环)     ── 复用实验骨架
                         │
Phase 7 (叙事/原子化/漏斗) ┴──▶ Phase 8 (视频)           ── 复用 PillarAsset
   [漏斗字段可与 5 并行]
Phase 9 (治理: 自治+合规) ── 复用 fleet 数据 + 跨模型 auditor; 相对独立, 可随时插入
```

- **强烈建议起点：Phase 5**——它是把「生产线」变「增长引擎」的分水岭，且 6/10 都复用它的骨架。
  哪怕先用 mock 数据把**回路设计**搭出来，价值都大于再加一个生产功能。
- `funnel_stage`（Phase 7 的一部分）极廉价且 Phase 5 的属性词汇表要用 → 可提前并入 5a。
- Phase 9（治理）相对独立，受监管行业/B2C 上线前价值最高，可在任意点插入。
- Phase 8（视频）、Phase 10（付费/outbound）是最大的新表面，按业务目标排期。

## 复用现有资产（别重建）

- 三层记忆 → 飞轮的「第 4 层派生记忆」直接挂上去。
- `MetricSnapshot`/GA4 回流 → `OutcomeLearner` 的输入。
- `content_score`/`recompute_asset_checks` → guardrail metric、CreativeScoreProvider、
  pillar-adherence 检查的底座。
- 跨模型 Auditor → ConfidenceGate 的 judge。
- Phase 4 审核队列 + directives→tasks → 候选段晋升、白空间、覆盖 gap 都转成任务。
- `agent_fleet` 统计 → AgentReliabilityScore 的数据源。
- 热点 kill-switch（`core/trends/safety.py`）→ 收编为 PolicyGate 规则包的一条。
- provider+mock+factory 模式（llm/media/trends/analytics/publish）→ 新增的 StatsProvider /
  OutcomeLearner / SegmentScorer / RepurposeProvider / VideoProvider / PolicyGate /
  EnrichmentProvider 全照此模式，real 实现后续换。
