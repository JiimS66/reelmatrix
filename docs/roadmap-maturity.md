# Roadmap（最终）：从「人驱动的工具集」到「AI 自主运营、人监督决策」的系统

> 前两轮路线图补齐了**系统能做什么**（Phase 1–4 产品化、5–10 增长引擎）。这一份是
> **成熟度打磨**——让系统**学得对**（因果而非相关）、**管得住**（LLMOps + 透明度）、
> **有地基**（数据/身份/同意）、**能自主运营**（营销大脑），并且**界面配得上**
> （agentic 工作台,而非面板沼泽）。全部 web-research-validated。
>
> **统一主线 = 一个范式转变的前后端两面**：
>
> | 后端（让它有个会自主运营的大脑） | 前端（让人能信任并监督这个大脑） |
> |---|---|
> | Orchestrator 持续 observe→decide→act,emit `PlannedAction` | **Agent Inbox**:AI 提议排成一个队列,人 Accept/Edit/Respond/Ignore |
> | 因果去偏 → 信号可信 | 诚实可视化(CI/n/置信),否则不让人信 |
> | LLMOps:eval/回归门 → 质量可控 | `<Explain>` 原语:why · confidence · provenance |
> | 自治级别由 reliability 决定 | 每能力自治开关(suggest→draft→auto) |
>
> 一贯约束(同前):mock-first、provider 抽象、SQLModel、每阶段测试绿、commit+push、
> 保留 DESIGN.md 的 calm/technical/单色 forest 美学(**不是重做,是再安家 + 升级**)。

---

## 0. 关键库决策(研究结论,先定)

- **图表:Recharts v3**(不整体引入 Tremor)。Tremor 建在 Recharts 上、样式太重、缺
  waterfall/CI-bar;但**借它的 BarList / Sparkline 两个模式**手搓成 ~40 行组件。visx 留给
  日后 MMM 曲线的定制画布。
- **组件库:shadcn/ui(Radix + Tailwind, copy-in)**。通过 CSS 变量把 `canvas/ink/forest`
  映射进去 → 保留 calm 美学的同时白拿无障碍原语。拉取顺序:Dialog → Popover → Tooltip →
  DropdownMenu → Tabs → **Command** → Toast(Sonner)。
- **命令面板:`kbar`**(命令注册表模型,适合"实体+动词"全局动作)或 `cmdk`(更灵活的 JSX)。
- **三栏壳:`react-resizable-panels`**(sidebar + canvas + inspector,持久化宽度)。
- **Agentic:** mock-first 不需要真流式;参考 LangChain **Agent Inbox** 的 Accept/Edit/
  Respond/Ignore 语法、CopilotKit/Vercel AI SDK 的 generative-UI 卡片模式。

---

## Phase 11 — 信号可信 + 界面地基（最高优先,两件地基事）

把已上线但"可能学错"的回路修对,同时立起前端的成熟地基。

- **后端 · 因果去偏飞轮**（借 Meta GeoLift、Google Meridian、Meta Robyn、PyMC-Marketing、
  CausalImpact、EconML）:`IncrementalityTest`(holdout → lift readout)算一个 **lift
  multiplier = 实测增量 ÷ 朴素归因**,在飞轮更新 Beta 后验时缩放 "win" 伪计数(默认 1.0)。
  把"只是投给高意图人群"的属性**收缩回 baseline**。`IncrementalityProvider` mock(合成
  geo/时序)。可选起步 `ResponseCurve`(adstock+Hill)+ `MMMProvider` mock。
  **归因信用与实测增量分歧 → 自动 spawn 测试**(自我改进闭环)。
- **前端 · 数据可视化升级**（借 GrowthBook/Statsig 结果 UI、PostHog/Amplitude、Tufte/
  Datawrapper 克制）:引入 Recharts;实验=**CI bar + 零线 + chance-to-beat**(>95% 才点亮
  forest);飞轮=**ranked BarList + Δvs上期**;漏斗=**单色 heatmap**;summary card=
  **sparkline + delta-vs-target**;**永远显示 n + "95% CI"**,数据不足显式"not enough data"
  而非假结论(dot-and-whisker 避免 within-bar bias)。
- **前端 · shadcn/ui 引入**:映射 CSS 变量,先拉 Dialog/Popover/Tooltip/Tabs/Command,
  把现有 `.surface/.chip/.btn-*/.field` 再安家到 Radix 行为上(无障碍白拿)。
- **为什么先做**:因果是后端**正确性地基**(其他学习都建其上);dataviz+shadcn 是前端
  地基。因果数据更需要诚实可视化——两件事天然配对。

## Phase 12 — 治理与信任（管得住,是"大脑"的前置）

- **后端 · LLMOps**（借 LangSmith、Braintrust、Langfuse、promptfoo、DeepEval）:
  `EvalSuite/EvalCase/EvalRun` + **polymorphic `Score`**(人审/代码/judge/真实结果共一张表)
  + judge prompt as data + **CI 回归门**(候选 vs 基线,paired-bootstrap CI 全在零下则 block)
  + per-agent eval 分**喂回现有 reliability**。
- **前端 · 透明度层**（借 Anthropic Citations、Perplexity、Salesforce Atlas、Google PAIR、
  Microsoft HAX）:一个可复用 **`<Explain why · confidence · provenance />`** 原语,
  **标准化到所有 AI 表面**(audit/policy/score/segment/priors/orchestrator);置信用
  **分级(高/中/低)+ n**,不裸给数字;一个 **feedback/override 原语**喂回飞轮(分歧=训练信号);
  progressive disclosure(badge→Popover→"show reasoning")。a11y baseline(focus/键盘/ARIA/
  reduced-motion/Sonner toast/optimistic+error)。
- **为什么**:LLMOps(后端质量门) ↔ 透明度(前端信任)是同一件事的两面,都是"让 AI 决策
  可信可审"。**这是让大脑值得自主的前置。**

## Phase 13 — 数据地基 + 同意（合规底线）

- **后端**（借 Segment Unify、RudderStack Profiles、Snowplow、Presidio、Consent Mode v2、
  OneTrust）:`IdentityGraph`/`UnifiedProfile`(union-find 确定性 stitch + 优先级 main_id +
  Segment 式 limits/blocked-values 护栏);`ConsentRecord` + **`ConsentGate` 复用 PolicyGate
  路径**(发送前按 `purpose` 检查,无记录=不发);`PiiRedactor`(Presidio 形,落库前最小化)。
- **前端**(轻):profile 360 视图 + consent 状态,outbound 卡片显示"consent ✓/缺失"。
- **为什么**:outbound **已经在发**却没有 consent gate——合规裸奔。系统假设数据干净,真实
  数据碎片化。

## Phase 14 — 营销大脑 + Agent Inbox（质变高潮,前后端同一范式）

- **后端 · 自主编排**（借 Salesforce Agentforce ReAct、Copilot Studio generative orchestration、
  LangGraph plan-execute、BabyAGI、Reflexion）:`MarketingGoal(objective,target_metric,
  horizon)` → 自重排的 `PlannedAction(type,rationale,priority,autonomy_level)` 队列;
  `Orchestrator.tick()` 的 **observe→decide→act**——读已有飞轮/实验/漏斗/情报/预算/合规
  状态,emit+排序下一步;动作是**已有能力的注册表**(planner 按描述选,不自创);
  Reflexion 式**文本教训**与数值后验并行喂回;`RunBudget` 防失控;自治用 reliability gate,
  outbound/付费永远 draft-then-approve(`Approval` 队列,LangGraph interrupt 式可恢复)。
- **前端 · Agent Inbox**（借 LangChain Agent Inbox、Copilot Workspace、Devin、Anthropic
  human-agent teams）:一个新顶层面 **渲染 `PlannedAction` 队列**——每条是 `<ProposalCard>`
  (标题=动作 · why 一行 · 变更预览/diff · 固定按钮 **Accept/Edit/Respond/Ignore**),
  **横跨全部能力**(把面板沼泽倒过来:不是人翻 6 个 tab,是 AI 把"下一步建议"汇成一个队列);
  持久 **Cmd-K ask bar**(匹配动作 OR 自由提示→新建提议);各面板 **suggestion chips**(点击→
  预填提议入 Inbox);**Agent Activity timeline**(proposed·approved·running·done 状态点,
  让自主可见);**每能力自治开关**(suggest→draft-ask→auto-low-risk,避免审批疲劳)。
- **为什么**:这是 plan 的高潮,也是前后端对称的兑现。**前置 = 因果(11)就位、LLMOps+
  透明度(12)就位**——否则"自主"只是更高效地放大错误。

## Phase 15 — IA 重构（治面板沼泽,配合 Inbox）

- **前端**（借 Linear、Stripe、Notion、Superhuman、VS Code）:**sidebar + canvas +
  inspector 三栏壳**替代 tab-stuffing(列表在中、详情滑入右栏 inspector);
  租户级 **"Needs you" inbox**(把现有跨活动审核队列升级成 Linear 式 focus-order 优先流,
  J/K 键导航、行内 triage);**progressive disclosure**(summary card 每屏 5–9 元素,展开见
  detail);density 开关;**IA 治理规则**(新功能必须挂到现有组或论证新组,季度导航审计——
  防止下一批功能再造沼泽)。
- **为什么**:6 个 tab 塞满卡片已不可持续。和 Agent Inbox 一起,把"沼泽"变成"队列 + 收敛 +
  聚焦"。可与 14 同期或紧随。

## Phase 16 — 能力扩展（建在成熟地基上,按业务择优）

- **旅程编排**（Braze Canvas/Iterable/SFMC + 开源 Temporal、Vowpal Wabbit/River）:
  `Journey`/`JourneyStep`/`JourneyState` + event-driven `JourneyRunner`(mock 时钟→Temporal);
  `NextBestAction` 决策器(rules→**复用飞轮后验做 Thompson 采样的 bandit**);frequency cap。
- **预算全局优化**(Meridian/Robyn/PyMC `BudgetOptimizer`):`BudgetOptimizer`(marginal-ROI
  均衡,SLSQP,max_response/target_efficiency)替代单活动比例分配 + what-if 端点。
- **GEO / AEO —— 可随时插入的低成本快赢**(Princeton GEO 论文:加统计+40%/引用/FAQ 结构;
  llms.txt;Profound 追踪 AI 引用):一个 `geo` check group(照搬 `policy_issues` 模式)+
  schema.org/FAQ JSON-LD + llms.txt 生成器 + `AICitation` 追踪器——**填上空的
  `mcp_servers/seo_geo/`**,且喂回飞轮(学"什么结构被引用")。

---

## 优先级与依赖

```
Phase 11 因果去偏(后端正确性) + dataviz/shadcn(前端地基) ──┐
Phase 12 LLMOps + 透明度Explain(信任,大脑前置) ───────────┤
Phase 13 数据地基 + consent(合规) ────────────────────────┼──▶ Phase 14 营销大脑 + Agent Inbox(高潮)
                                                          │         │
                                                          │         ▼
                                                          └──▶ Phase 15 IA 重构(配合 Inbox)
Phase 16 旅程 / 预算优化 / GEO(扩展; GEO 可随时插,独立快赢)
```

**建议起点:Phase 11。** 它一次修两个地基——后端把飞轮从"相关"校正到"因果"(否则系统在
自信地学错),前端立起 Recharts+shadcn+诚实可视化。**如果只做一轮,做 11。** 营销大脑(14)
留到 11+12 就位——那才是让"自主"放大正确东西的时机。GEO(16)成本最低、最当下,可任意时点插入。

一句话:**上一轮让系统「会做」;这一轮让系统「学得对、管得住、有地基、能自主、且界面配得
上」——而后端的自主大脑与前端的 Agent Inbox,是同一次进化的两面,必须一起到来。**

## 复用现有资产(别重建)
- `PlannedAction` 队列(14 后端) → Agent Inbox(14 前端)直接渲染。
- 跨活动审核队列(Phase 4) → "Needs you" inbox(15)的底座。
- 飞轮 Beta 后验 → 因果 lift multiplier 校正它(11)、bandit 先验(16)。
- 跨模型 Auditor → LLMOps 的 judge(12)。
- reliability 分(Phase 9) → 自治 gate(14)+ per-agent eval 汇入点(12)。
- PolicyGate(Phase 9) → ConsentGate 复用同一闸路径(13)。
- `policy_issues` 模式 → `geo` check group(16)同形。
- DESIGN.md tokens(`canvas/ink/forest`) → 映射进 shadcn CSS 变量(11),美学不变。
- `core/<domain>/{base,mock,factory}` 约定 → 新增 incrementality/mmm/identity/consent/
  journey/aeo provider 全照此,real 实现后续换。
