# ReelMatrix 工作流重构：从线性管道到事件驱动状态机

## 之前的问题

之前的六阶段闭环暗示了一个固定顺序：定位 → 客群 → 内容 → 分发 → 测试 → 优化 → 回到定位。

现实不是这样的。真实场景：

- 创始人带着已有的定位来，不需要阶段一，直接进客群研究
- 第一次做内容之前，先要做现状审计（现在有什么、竞品在做什么、用户在说什么）
- 内容发完了发现数据不好，不是走完整个闭环，而是直接改内容重发
- 创始人随时可能说"我们pivot了，定位变了"，整个策略要推倒重来
- 有些任务是持续运行的（社区监听），有些是一次性的（初始定位），有些是周期性的（周报）
- 人类的输入不是在固定节点插入的，而是随时可能出现的

**核心重构：把"管道"改成"状态机 + 事件系统"。**

---

## 新架构：事件驱动状态机

### 核心概念

```
旧模型：Pipeline（管道）
  阶段1 → 阶段2 → 阶段3 → 阶段4 → 阶段5 → 阶段6 → 回到阶段1
  问题：强制顺序，不允许跳跃、插入、并行

新模型：State Machine + Event Bus（状态机 + 事件总线）
  - 每个客户有一个"项目状态"
  - 任何事件（人类输入、定时触发、Agent输出、外部数据更新）都可以触发状态转换
  - 状态转换决定接下来执行什么任务
  - 多个任务可以并行执行
  - 人类输入随时可以打断或重定向
```

### 客户项目状态机

```
┌─────────────────────────────────────────────────────────────────┐
│                     客户项目状态机                                │
│                                                                 │
│   ┌───────────┐                                                 │
│   │  初始化    │ ← 新客户入驻                                    │
│   │ ONBOARDING│                                                 │
│   └─────┬─────┘                                                 │
│         │ 人类输入：产品信息 + 现有定位（可选）                    │
│         ↓                                                       │
│   ┌───────────┐    可并行     ┌───────────┐                     │
│   │  现状审计  │ ←──────────→ │ 基础研究   │                     │
│   │  AUDITING │              │ RESEARCHING│                     │
│   └─────┬─────┘              └─────┬─────┘                     │
│         │                          │                            │
│         └──────────┬───────────────┘                            │
│                    ↓                                            │
│   ┌────────────────────────────┐                                │
│   │  策略就绪                    │                                │
│   │  STRATEGY_READY            │ ← 人类审核确认                  │
│   └─────────────┬──────────────┘                                │
│                 ↓                                                │
│   ┌────────────────────────────┐                                │
│   │  运转中                     │ ← 主要运行状态                  │
│   │  OPERATING                 │                                │
│   │                            │                                │
│   │  内部子状态：               │                                │
│   │  - 内容生产中               │                                │
│   │  - 等待审核                 │                                │
│   │  - 发布中                   │                                │
│   │  - 数据收集中               │                                │
│   │  - 优化分析中               │                                │
│   └────────────┬───────────────┘                                │
│                │                                                │
│        ┌───────┴────────┐                                       │
│        ↓                ↓                                       │
│   ┌─────────┐    ┌───────────┐                                  │
│   │  暂停    │    │  重新定位  │ ← 人类输入："我们pivot了"         │
│   │ PAUSED  │    │ REPOSITIONING│                               │
│   └─────────┘    └─────┬─────┘                                  │
│                        │ 完成后回到 RESEARCHING                   │
│                        └──────────→ ...                         │
└─────────────────────────────────────────────────────────────────┘
```

### 事件总线

所有的状态转换都由事件驱动，不是由固定的pipeline顺序驱动：

```python
# 事件类型定义

class EventType(Enum):
    # ===== 人类触发的事件 =====
    HUMAN_INPUT_POSITIONING = "human.positioning"      # 人类提供/更新了定位
    HUMAN_INPUT_FEEDBACK = "human.feedback"             # 人类对内容给了反馈
    HUMAN_APPROVE_CONTENT = "human.approve_content"     # 人类审核通过了内容
    HUMAN_REJECT_CONTENT = "human.reject_content"       # 人类打回了内容
    HUMAN_APPROVE_STRATEGY = "human.approve_strategy"   # 人类确认了策略方案
    HUMAN_REQUEST_PIVOT = "human.pivot"                 # 人类要求重新定位
    HUMAN_REQUEST_PAUSE = "human.pause"                 # 暂停
    HUMAN_REQUEST_RESUME = "human.resume"               # 恢复
    HUMAN_OVERRIDE = "human.override"                   # 人类直接覆盖Agent决策

    # ===== 系统定时触发的事件 =====
    SCHEDULE_DAILY_MONITOR = "schedule.daily_monitor"    # 每日社区监听
    SCHEDULE_WEEKLY_CONTENT = "schedule.weekly_content"   # 每周内容生产
    SCHEDULE_WEEKLY_REPORT = "schedule.weekly_report"     # 每周效果报告
    SCHEDULE_MONTHLY_REVIEW = "schedule.monthly_review"   # 每月策略回顾

    # ===== Agent输出触发的事件 =====
    AGENT_AUDIT_COMPLETE = "agent.audit_complete"         # 审计完成
    AGENT_RESEARCH_COMPLETE = "agent.research_complete"   # 研究完成
    AGENT_CONTENT_GENERATED = "agent.content_generated"   # 内容生成完成
    AGENT_QUALITY_PASSED = "agent.quality_passed"         # 质量检查通过
    AGENT_QUALITY_FAILED = "agent.quality_failed"         # 质量检查不通过
    AGENT_STRATEGY_UPDATE = "agent.strategy_update"       # 策略更新建议
    AGENT_ANOMALY_DETECTED = "agent.anomaly_detected"     # 检测到异常

    # ===== 外部数据触发的事件 =====
    DATA_NEW_REVIEWS = "data.new_reviews"                 # 新的竞品评价
    DATA_METRICS_UPDATED = "data.metrics_updated"         # 内容表现数据更新
    DATA_TRENDING_TOPIC = "data.trending_topic"           # 发现热点话题
    DATA_COMPETITOR_MOVE = "data.competitor_move"         # 竞品有新动作
    DATA_API_FAILURE = "data.api_failure"                 # 平台API故障
```

### 事件 → 任务的映射规则

```yaml
# event_handlers.yaml
# 定义每种事件触发什么任务，在什么状态下有效

handlers:

  # ===== 入驻阶段 =====
  - event: human.positioning
    valid_states: [ONBOARDING, REPOSITIONING]
    actions:
      - task: validate_positioning_input
        type: workflow  # 确定性：检查输入完整性
      - task: start_audit_and_research
        type: workflow  # 并行触发审计和研究
        parallel: true
        subtasks:
          - task: run_competitor_audit
            type: agent    # Agent：需要理解和分析
            skill: analyze_competitor
          - task: run_appstore_review_analysis
            type: agent
            skill: analyze_audience_sentiment
          - task: run_community_scan
            type: workflow  # Workflow：数据采集
          - task: run_existing_content_audit
            type: agent    # Agent：评估现有内容质量
            skill: audit_existing_content
    notes: >
      人类给了定位后，不是直接开始做内容。
      而是并行启动4个审计/研究任务，全部完成后
      汇总为一份"策略基础报告"，等人类确认后再进入内容生产。

  # ===== 审计研究完成 =====
  - event: agent.audit_complete
    valid_states: [AUDITING]
    actions:
      - task: check_all_audits_done
        type: workflow  # 检查是否所有并行任务都完成了
        on_all_done:
          - task: generate_strategy_brief
            type: agent  # 汇总所有研究结果为策略简报
            skill: generate_strategy_update
          - task: notify_human_for_review
            type: workflow  # 通知人类来审核策略
            transition_to: STRATEGY_READY

  # ===== 人类确认策略 =====
  - event: human.approve_strategy
    valid_states: [STRATEGY_READY]
    actions:
      - task: initialize_content_calendar
        type: workflow  # 根据策略生成第一版内容日历
      - task: setup_monitoring_schedule
        type: workflow  # 启动定时监听任务
      - task: transition_to_operating
        type: workflow
        transition_to: OPERATING

  # ===== 每周内容生产（系统进入OPERATING后） =====
  - event: schedule.weekly_content
    valid_states: [OPERATING]
    actions:
      - task: select_topics_from_calendar
        type: workflow  # 从内容日历中取本周选题
      - task: generate_content_batch
        type: agent
        skill: [write_blog_post, write_twitter_thread]  # 可能同时用多个Skill
      - task: run_quality_review
        type: agent
        skill: review_content_quality
      - task: route_by_quality_score
        type: workflow
        rules:
          - condition: "score >= 7"
            action: move_to_approval_queue
          - condition: "score < 7 AND retry_count < 3"
            action: regenerate_with_feedback
            emit_event: agent.quality_failed
          - condition: "score < 7 AND retry_count >= 3"
            action: escalate_to_human
            emit_event: human.reject_content

  # ===== 人类审核通过内容 =====
  - event: human.approve_content
    valid_states: [OPERATING]
    actions:
      - task: schedule_publication
        type: workflow  # 写入发布排期
      - task: adapt_to_other_channels
        type: agent     # 博客 → 推文串 → LinkedIn
        skill: [adapt_to_twitter, adapt_to_linkedin]
      - task: schedule_adapted_content
        type: workflow

  # ===== 内容表现数据更新（发布3天后） =====
  - event: data.metrics_updated
    valid_states: [OPERATING]
    actions:
      - task: update_episodic_memory
        type: workflow  # 写入经验记忆
      - task: check_for_anomalies
        type: workflow  # 简单阈值检查：互动率是否偏离均值2个标准差
        on_anomaly:
          - emit_event: agent.anomaly_detected

  # ===== 检测到异常表现 =====
  - event: agent.anomaly_detected
    valid_states: [OPERATING]
    actions:
      - task: analyze_anomaly
        type: agent
        skill: generate_strategy_update
      - task: notify_human_with_analysis
        type: workflow  # 发送分析报告给人类，不自动改策略

  # ===== 发现热点话题 =====
  - event: data.trending_topic
    valid_states: [OPERATING]
    actions:
      - task: evaluate_topic_relevance
        type: agent  # 判断：这个热点跟客户的定位相关吗？
        skill: analyze_audience_sentiment
      - task: route_by_relevance
        type: workflow
        rules:
          - condition: "relevance_score >= 0.7"
            action: insert_into_content_calendar  # 加入本周选题
            priority: high
            notify_human: true  # 通知人类有紧急选题建议
          - condition: "relevance_score < 0.7"
            action: log_and_skip

  # ===== 人类要求pivot =====
  - event: human.pivot
    valid_states: [OPERATING, PAUSED]
    actions:
      - task: pause_all_scheduled_tasks
        type: workflow  # 暂停所有定时任务和排期发布
      - task: archive_current_strategy
        type: workflow  # 归档当前策略，不删除
      - task: transition_to_repositioning
        type: workflow
        transition_to: REPOSITIONING
        # 回到REPOSITIONING后，等待人类输入新定位
        # 新定位输入后触发 human.positioning 事件
        # 重新走审计研究流程

  # ===== 人类直接覆盖 =====
  - event: human.override
    valid_states: [ANY]  # 任何状态下都可以
    actions:
      - task: apply_human_override
        type: workflow
        notes: >
          人类可以直接：
          - 修改内容日历（增删选题）
          - 修改内容稿件（跳过Agent重新生成）
          - 修改发布排期
          - 修改品牌调性参数
          - 强制发布被Agent标记为低分的内容
          所有override记录在审计日志中，
          并作为经验记忆供Agent学习。

  # ===== API故障 =====
  - event: data.api_failure
    valid_states: [OPERATING]
    actions:
      - task: activate_degradation_mode
        type: workflow
        rules:
          - condition: "failed_tool == twitter-publisher-mcp"
            action: queue_content_for_retry  # 排队等恢复
            alert: true
          - condition: "failed_tool == reddit-mcp"
            action: skip_reddit_monitoring   # 跳过Reddit，继续其他数据源
            alert: false  # 非关键，不告警
```

---

## 你提到的具体场景：第一次使用

用新架构走一遍"新客户第一次使用"的真实流程：

```
Day 0：客户入驻
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
状态：ONBOARDING

[人类输入] 创始人填写入驻问卷：
  - 产品URL：thepath.ai
  - 产品描述："AI驱动的心理治疗平台"
  - 已有定位："帮助大学生获得affordable的心理健康支持"
  - 已有营销渠道：Twitter账号（500 followers）、无博客
  - 目标："获取更多用户注册"

→ 触发事件：human.positioning
→ 状态转换：ONBOARDING → AUDITING + RESEARCHING（并行）


Day 0-3：并行审计和研究
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
状态：AUDITING（4个并行任务）

任务1：[Agent] 竞品分析
  输入：竞品列表（Woebot, Wysa, BetterHelp）
  过程：
    → [MCP] web-scraper 抓取竞品官网
    → [MCP] appstore-mcp 拉取竞品App Store评价
    → [Agent] 分析竞品定位、messaging、内容策略
  输出：竞品分析报告

任务2：[Agent] 用户评价分析
  输入：竞品App Store评价数据
  过程：
    → [Agent] 提取用户关切Top 10
    → [Agent] 情感分析和主题聚类
  输出：用户需求和痛点地图

任务3：[Workflow] 社区数据采集
  输入：关键词列表（"AI therapy", "online counseling", "mental health app"）
  过程：
    → [Workflow] Reddit API批量拉取相关帖子
    → [Workflow] 存入数据库
  输出：原始数据已入库（Agent后续分析用）

任务4：[Agent] 现有内容审计
  输入：客户Twitter账号的历史推文
  过程：
    → [MCP] twitter-mcp 拉取最近100条推文
    → [Agent] 分析内容主题分布、互动率、发布频率
    → [Agent] 识别表现好/差的内容模式
  输出：现有内容审计报告 + 改进建议

  ⬇️ 4个任务全部完成
  → 触发事件：agent.audit_complete（× 4）
  → Workflow检查：全部完成？→ 是


Day 3-4：策略汇总
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Agent] 策略汇总Agent
  输入：4份审计/研究报告
  输出：策略简报
  {
    "positioning_assessment": "当前定位'affordable心理支持'有效但不够差异化，
                              建议强化'大学生专属'和'waitlist替代方案'两个角度",
    "content_strategy": {
      "priority_topics": [
        "AI therapy是什么？消除误解",
        "大学counseling center排队太久怎么办",
        "学生心理健康自助工具对比"
      ],
      "recommended_channels": ["blog（SEO长期价值）", "twitter（已有基础）"],
      "content_cadence": "每周2篇博客 + 3条推文串",
      "tone": "warm, educational, honest about limitations"
    },
    "quick_wins": [
      "立即优化Twitter bio和pinned tweet",
      "写3篇针对高搜索量关键词的博客文章"
    ],
    "risks": [
      "mental health内容需要clinical review",
      "FTC health claims合规"
    ]
  }

→ [Workflow] 发送策略简报给人类
→ 状态转换：AUDITING → STRATEGY_READY
→ 等待人类反馈


Day 4-5：人类审核策略
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
状态：STRATEGY_READY

[人类输入] 创始人回复：
  "策略大方向同意。但我们的tone不要太clinical，
   更像朋友在聊天。另外加一个话题：
   '为什么我们选择AI而不是纯人工客服'。"

→ 触发事件：human.approve_strategy（附带修改）
→ [Workflow] 更新品牌调性记忆：tone = "像朋友聊天"
→ [Workflow] 更新内容日历：增加指定话题
→ [Workflow] 初始化定时任务（每日监听、每周内容生产）
→ 状态转换：STRATEGY_READY → OPERATING


Day 5+：进入正常运转
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
状态：OPERATING

→ 每日 09:00：社区监听Workflow自动跑
→ 每周一 10:00：内容生产流程自动触发
→ 人类随时可以：修改选题、审核内容、调整策略
→ 系统随时可以：发现热点话题、检测表现异常、建议策略调整
```

---

## 并行任务管理

之前的线性模型无法处理并行。新模型用任务依赖图：

```
任务依赖图示例：新客户入驻

                    ┌─ 竞品分析 ──────────┐
                    │                     │
人类输入定位 ───────┼─ 评价分析 ──────────┼─→ 汇总策略 → 人类审核 → 开始运转
                    │                     │
                    ├─ 社区数据采集 ──────┤
                    │         │          │
                    │         ↓          │
                    │   社区情感分析 ─────┤
                    │                     │
                    └─ 现有内容审计 ──────┘

规则：
  - 竞品分析、评价分析、社区采集、内容审计 → 可并行
  - 社区情感分析 → 必须等社区数据采集完成
  - 汇总策略 → 必须等所有分析任务完成
  - 人类审核 → 必须等汇总策略完成
```

```
任务依赖图示例：每周内容生产

                    ┌─ 博客文章A ─→ 质检A ─┐
                    │                      │
选题从日历取出 ─────┼─ 博客文章B ─→ 质检B ─┼─→ 通过的进审核队列
                    │                      │      ↓
                    └─ 推文串C ──→ 质检C ──┘   人类审核
                                                 ↓
                                          ┌─ 排期发布博客
                                          ├─ 适配推文串版本 → 排期发布
                                          └─ 适配LinkedIn版本 → 排期发布

规则：
  - 多篇内容可并行生成
  - 每篇独立质检
  - 质检通过的独立进入审核队列（不用等其他内容）
  - 人类可以逐篇审核，不用等全部生成完
  - 适配其他渠道可以在人类审核后并行跑
```

---

## 人类介入点的设计

### 三种介入模式

```
模式1：审批型（Approval Gate）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  系统产出 → 等待人类approve/reject → 继续/重做

  适用于：
  - 策略确认（影响大，不可逆）
  - 内容发布（V0阶段所有内容都要审）
  - 新渠道开通

  技术实现：
  任务完成 → 状态设为 PENDING_APPROVAL
  → 通知人类（邮件/Slack/Dashboard）
  → 人类操作触发 human.approve 或 human.reject 事件
  → 超过48小时未响应 → 自动提醒 → 超过7天 → 自动取消


模式2：通知型（Notification Only）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  系统产出 → 通知人类 → 继续执行（不等待）
  人类如果不满意可以事后覆盖

  适用于：
  - 社区监听周报
  - 数据表现更新
  - 非关键的策略微调建议
  - V2阶段的常规内容（建立信任后减少审批）

  技术实现：
  任务完成 → 发送通知 → 继续下一步
  → 人类随时可以触发 human.override 事件回溯修改


模式3：输入型（Human Input Required）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  系统需要人类提供信息才能继续

  适用于：
  - 初始定位输入
  - 品牌调性确认
  - 预算分配决策
  - 合规问题（"这条内容涉及medical claim，需要clinical review"）

  技术实现：
  任务执行中 → 遇到需要人类输入的节点
  → 暂停当前任务链 → 通知人类需要输入
  → 人类输入后触发对应事件 → 恢复任务链
```

### 哪些节点用哪种模式

```
                        │ V0（建立信任期）│ V1（信任建立后）│ V2（充分信任后）
━━━━━━━━━━━━━━━━━━━━━━━┼━━━━━━━━━━━━━━━┼━━━━━━━━━━━━━━━┼━━━━━━━━━━━━━━━
初始定位                 │ 输入型         │ 输入型         │ 输入型
策略方案                 │ 审批型         │ 审批型         │ 通知型
内容日历/选题             │ 审批型         │ 通知型         │ 自动
博客文章                 │ 审批型         │ 审批型         │ 通知型
推文串                   │ 审批型         │ 通知型         │ 自动
LinkedIn帖子             │ 审批型         │ 通知型         │ 自动
渠道适配版本              │ 审批型         │ 自动           │ 自动
发布排期                 │ 审批型         │ 自动           │ 自动
社区监听周报              │ 通知型         │ 通知型         │ 自动
表现数据周报              │ 通知型         │ 通知型         │ 自动
策略调整建议              │ 审批型         │ 审批型         │ 通知型
A/B测试设计              │ 审批型         │ 通知型         │ 自动
异常告警                 │ 通知型         │ 通知型         │ 通知型
Skill更新                │ 审批型         │ 审批型         │ 审批型
```

**信任是逐步建立的。** V0每一步都要人类审，V2只有关键决策需要人类介入。这也回应了Joel"留下一个自动化pipeline"的要求——自动化程度随信任线性增长。

---

## 技术实现方案

### LangGraph的StateGraph

LangGraph天生适合这种事件驱动的状态机模式：

```python
from langgraph.graph import StateGraph, END

# 定义项目状态
class ProjectState(TypedDict):
    status: str              # ONBOARDING | AUDITING | STRATEGY_READY | OPERATING | ...
    client_id: str
    positioning: dict | None
    audit_results: dict
    strategy: dict | None
    content_queue: list
    pending_approvals: list
    active_tasks: list       # 当前正在并行执行的任务ID

# 构建状态图
graph = StateGraph(ProjectState)

# 添加节点
graph.add_node("receive_positioning", receive_positioning)  # Workflow
graph.add_node("run_parallel_audits", run_parallel_audits)  # 并行触发4个任务
graph.add_node("wait_for_audits", wait_for_audits)          # 等待并行任务完成
graph.add_node("generate_strategy", generate_strategy)       # Agent
graph.add_node("wait_for_human_approval", wait_for_human)   # 等待人类
graph.add_node("initialize_operating", initialize_operating) # Workflow
graph.add_node("operating_loop", operating_loop)             # 主运行循环

# 添加边（状态转换）
graph.add_edge("receive_positioning", "run_parallel_audits")
graph.add_edge("run_parallel_audits", "wait_for_audits")
graph.add_edge("wait_for_audits", "generate_strategy")
graph.add_edge("generate_strategy", "wait_for_human_approval")

# 条件边（人类决策分支）
graph.add_conditional_edges(
    "wait_for_human_approval",
    route_human_decision,
    {
        "approved": "initialize_operating",
        "rejected_with_feedback": "generate_strategy",  # 带反馈重新生成
        "pivot": "receive_positioning",                  # 重新定位
    }
)

graph.add_edge("initialize_operating", "operating_loop")
```

### 并行任务的实现

```python
# 用Celery group实现并行任务

from celery import group, chord

def run_parallel_audits(state):
    """并行启动所有审计任务，全部完成后汇总"""

    audit_tasks = group(
        run_competitor_audit.s(state["client_id"]),
        run_appstore_analysis.s(state["client_id"]),
        run_community_scan.s(state["client_id"]),
        run_content_audit.s(state["client_id"]),
    )

    # chord = 并行任务全部完成后，执行回调
    callback = merge_audit_results.s(state["client_id"])
    result = chord(audit_tasks)(callback)

    return {**state, "audit_task_id": result.id}
```

### 人类介入的实现

```python
# 人类审批通过webhook或dashboard操作触发

# 方式1：Dashboard UI
# 前端展示待审核列表 → 人类点击approve/reject → POST /api/approve

# 方式2：Slack集成
# Bot发送审核消息 → 人类点击按钮 → Webhook回调

# 方式3：邮件
# 发送审核邮件 → 人类回复approve/reject → 邮件解析触发事件

# 后端统一处理
@app.post("/api/events")
def handle_event(event: Event):
    """所有事件的统一入口"""
    
    # 验证事件合法性
    validate_event(event)
    
    # 查找当前项目状态
    project = get_project(event.client_id)
    
    # 查找匹配的handler
    handler = find_handler(event.type, project.status)
    
    if handler is None:
        raise InvalidStateTransition(
            f"事件 {event.type} 在状态 {project.status} 下无效"
        )
    
    # 执行handler定义的actions
    for action in handler.actions:
        if action.type == "workflow":
            execute_workflow(action.task, project)
        elif action.type == "agent":
            execute_agent_task(action.task, action.skill, project)
    
    # 如果handler定义了状态转换
    if handler.transition_to:
        project.update_status(handler.transition_to)
```

---

## 和之前文档的关系

这份文档替代了之前的"六阶段闭环"模型。之前的其他文档仍然有效：

| 文档 | 状态 | 说明 |
|------|------|------|
| 创业方案（商业模式、定价、GTM） | ✅ 有效 | 商业逻辑不变 |
| Workflow/Agent/MCP拆分 | ✅ 有效 | 每个任务是Workflow还是Agent的判断不变 |
| 记忆/Skill/Tool管理 | ✅ 有效 | 管理机制不变 |
| **六阶段线性闭环** | ❌ **替换为本文档的状态机模型** | 执行顺序和触发机制重新设计 |
| 面试prep（The Path AI） | ✅ 有效 | 面试策略不变 |
