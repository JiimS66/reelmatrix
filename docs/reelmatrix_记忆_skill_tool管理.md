# ReelMatrix 记忆管理、Skill管理、Tool管理

## 为什么这三个层面重要

上一份文档解决了"Workflow还是Agent"和"MCP怎么接"的问题。但还有三个关键问题没回答：

1. **记忆管理：** Agent怎么记住之前学到的东西？客户A的品牌偏好、上周哪条推文表现好、某个话题已经写过了——这些信息存在哪里、怎么取、什么时候忘？
2. **Skill管理：** Agent的"能力"怎么组织？写博客是一个skill，写推文串是另一个skill，做竞品分析又是一个——怎么让Agent在对的时机调用对的skill？
3. **Tool管理：** MCP Server越来越多，怎么注册、发现、版本管理、权限控制？Agent怎么知道自己能用哪些工具？

这三者的关系：**Skill告诉Agent"怎么做"，Tool给Agent"做的手段"，Memory给Agent"做的上下文"。**

---

## 一、记忆管理

### 核心设计：三层记忆架构

```
┌──────────────────────────────────────────────────────────────┐
│                     ReelMatrix 记忆架构                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         短期记忆 (Short-term / Working Memory)          │  │
│  │                                                        │  │
│  │  存储位置：LLM Context Window（内存中）                   │  │
│  │  生命周期：单次任务执行期间                                │  │
│  │  内容：当前brief、当前工具输出、推理中间步骤              │  │
│  │  管理方式：FIFO + 重要性评分（超出window时先丢低分内容）   │  │
│  └────────────────────────────────────────────────────────┘  │
│                           ↕ 提升/驱逐                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         中期记忆 (Warm Memory / Session Memory)          │  │
│  │                                                        │  │
│  │  存储位置：Redis                                        │  │
│  │  生命周期：一次pipeline运行周期（如"本周内容生产"）        │  │
│  │  内容：本轮已生成的内容摘要、本轮各Agent的决策记录、       │  │
│  │       阶段间传递的结构化handoff artifacts                 │  │
│  │  管理方式：Pipeline结束后由Workflow汇总写入长期记忆        │  │
│  └────────────────────────────────────────────────────────┘  │
│                           ↕ 沉淀/检索                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         长期记忆 (Long-term Memory)                      │  │
│  │                                                        │  │
│  │  存储位置：PostgreSQL + pgvector（向量检索）              │  │
│  │  生命周期：持久化，按TTL策略衰减                          │  │
│  │  内容分三类（见下方详细说明）                              │  │
│  │  管理方式：写入需过认证门（certification gate）           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 长期记忆的三种类型

借鉴认知科学的分类，ReelMatrix的长期记忆分为三类：

#### 1. 事实记忆 (Semantic Memory)

**存什么：** 关于客户和市场的稳定事实

```json
// 示例：客户A的事实记忆
{
  "type": "semantic",
  "client_id": "client_a",
  "facts": [
    {
      "key": "brand_voice",
      "value": "专业但不呆板，偶尔用比喻，避免俚语",
      "source": "onboarding",
      "confidence": 0.95,
      "updated_at": "2026-03-15"
    },
    {
      "key": "target_audience",
      "value": "25-40岁的工程管理者，关注团队效率和工程文化",
      "source": "audience_research_agent",
      "confidence": 0.85,
      "updated_at": "2026-04-01"
    },
    {
      "key": "competitor_list",
      "value": ["LinearB", "Jellyfish", "Swarmia"],
      "source": "positioning_agent",
      "confidence": 0.90,
      "updated_at": "2026-03-20"
    }
  ]
}
```

**怎么用：** 内容生成Agent每次启动时，从事实记忆中加载品牌调性、目标受众、竞品列表作为context。

**怎么更新：** 只有分析类Agent（定位Agent、客群研究Agent）可以写入。写入时必须附带source和confidence，不接受无来源的"观点"。

#### 2. 经验记忆 (Episodic Memory)

**存什么：** 过去发生的具体事件和结果

```json
// 示例：某次内容发布的经验记忆
{
  "type": "episodic",
  "client_id": "client_a",
  "episode": {
    "event": "published_blog_post",
    "date": "2026-04-07",
    "topic": "Engineering Manager的5个时间管理技巧",
    "format": "listicle",
    "channel": "blog + twitter_thread",
    "metrics": {
      "blog_views": 1200,
      "twitter_impressions": 8500,
      "twitter_engagement_rate": 0.034,
      "sign_ups_attributed": 3
    },
    "learnings": [
      "listicle格式在这个受众中表现好（vs 上周的deep-dive只有400 views）",
      "推文串的第一条用数字开头比用提问开头互动率高40%"
    ]
  }
}
```

**怎么用：** A/B测试Agent和学习优化Agent读取经验记忆来识别模式。内容生成Agent读取近期高表现内容作为few-shot参考。

**怎么更新：** 每次内容发布后，Workflow自动记录发布事件；3天后Workflow自动拉取表现数据补充metrics；学习优化Agent定期（每周）扫描经验记忆生成learnings。

#### 3. 程序记忆 (Procedural Memory) ← 这就是Skill的存储形式

**存什么：** "怎么做某件事"的知识——即Agent的Skills

```json
// 示例：写Twitter推文串的程序记忆
{
  "type": "procedural",
  "skill_id": "write_twitter_thread",
  "description": "将一个内容主题转化为Twitter推文串",
  "procedure": {
    "steps": [
      "从brief中提取核心论点",
      "第一条推文用hook（数字、反直觉观点、或痛点共鸣）",
      "中间3-5条每条一个论点，每条独立可读",
      "最后一条做CTA（关注/转发/访问链接）",
      "总长度控制在5-8条推文"
    ],
    "constraints": [
      "每条推文 ≤ 280字符",
      "不用emoji（除非品牌调性允许）",
      "不用hashtag超过2个"
    ],
    "quality_criteria": [
      "第一条推文能独立获得互动",
      "删掉任何一条中间推文不影响整体逻辑"
    ]
  },
  "performance_history": {
    "avg_engagement_rate": 0.028,
    "best_performing_variant": "数字开头 + 反直觉观点",
    "total_executions": 47
  }
}
```

**关键点：程序记忆是可以进化的。** 随着经验记忆积累，学习优化Agent会发现"某种写法效果更好"，然后更新对应的程序记忆。这就是系统"自我提升"的机制。

### 记忆管理的关键规则

#### 写入认证门 (Certification Gate)

不是所有信息都能进入长期记忆。这是最容易出错的地方——如果什么都往长期记忆里塞，记忆会被噪音污染，Agent会变得"自信地犯错"。

```
写入长期记忆的规则：

事实记忆：
  ✅ 允许写入：有明确来源（URL、API数据、用户确认）
  ✅ 允许写入：confidence ≥ 0.8
  ❌ 拒绝写入：Agent推测的结论（没有数据支撑）
  ❌ 拒绝写入：与已有高confidence事实矛盾（需要人工审核）

经验记忆：
  ✅ 允许写入：有完整的事件记录（时间、动作、结果）
  ✅ 允许写入：metrics来自平台API（不是Agent估算）
  ❌ 拒绝写入：不完整的事件（只有动作没有结果）

程序记忆：
  ✅ 允许写入/更新：有至少10次执行记录支撑的改进
  ❌ 拒绝写入：基于单次成功的"最佳实践"（样本太小）
```

#### 遗忘策略 (Forgetting Policy)

长期记忆不能无限增长。遗忘策略：

| 记忆类型 | 衰减规则 | 理由 |
|---------|---------|------|
| 事实记忆 | 90天未被引用 → 标记为stale → 下次引用时触发重新验证 | 市场信息会过时 |
| 经验记忆 | 180天前的具体事件 → 压缩为统计摘要（"Q1共发布32篇博客，平均互动率2.8%"）→ 原始记录归档 | 细节不重要了，模式才重要 |
| 程序记忆 | 不自动衰减，但每30天由学习优化Agent审核一次 | 技能需要主动更新，不能静默过期 |

#### V0阶段的简化实现

上面是完整架构，但V0不需要全做。简化版：

```
V0记忆方案（够用就行）：

短期记忆：LLM context window，不做额外管理
中期记忆：Redis key-value，pipeline结束清空
长期记忆：PostgreSQL普通表，不上pgvector

V0不做的：
  - 向量语义检索（用关键词匹配就够了）
  - 自动遗忘策略（手动管理）
  - 跨客户记忆聚合
  - 程序记忆的自动进化
```

---

## 二、Skill管理

### 什么是Skill

Skill = 结构化的提示模板 + 约束规则 + 质量标准 + 所需工具清单

**Skill不是Agent。** Agent是执行者，Skill是Agent的"工作手册"。同一个Agent可以加载不同的Skill来完成不同任务。

```
类比：
  Agent = 一个员工
  Skill = 这个员工手里的SOP手册
  Tool  = 这个员工桌上的工具（电脑、电话、数据库）
  Memory = 这个员工的工作经验和公司知识库
```

### Skill注册表

所有Skill集中管理在一个注册表中：

```yaml
# skills/registry.yaml

skills:
  # ===== 内容生成类 =====
  - id: write_blog_post
    name: 博客文章写作
    description: 根据content brief生成SEO优化的博客文章
    agent_type: content_generation  # 哪个Agent可以加载这个Skill
    version: "1.2"
    input_schema:
      required:
        - topic: string          # 选题
        - target_keyword: string # 目标关键词
        - brand_voice_id: string # 品牌调性配置ID
        - word_count_range: [int, int]  # 字数范围
      optional:
        - reference_urls: list[string]  # 参考资料
        - competitor_angles: list[string]  # 竞品已有角度（用于差异化）
    required_tools:              # 这个Skill需要用到的MCP工具
      - brand-kb-mcp:read_brand_voice
      - seo-analyzer-mcp:get_keyword_data
      - web-scraper-mcp:fetch_url    # 用于读取参考资料
    required_memory:             # 这个Skill需要读取的记忆类型
      - semantic: [brand_voice, target_audience]
      - episodic: [recent_blog_performance]  # 最近博客表现，用于参考
      - procedural: [write_blog_post]  # 自身的程序记忆
    quality_gate:
      min_score: 7
      evaluation_criteria:
        - brand_voice_consistency  # 品牌调性一致性
        - seo_keyword_coverage     # 关键词覆盖度
        - readability_score        # 可读性评分
        - originality              # 原创度
    constraints:
      - "不得做出未经验证的事实声明"
      - "必须包含至少一个具体数据点或案例"
      - "标题不超过60个字符（SEO最佳实践）"
      - "meta description不超过155个字符"

  - id: write_twitter_thread
    name: 推文串写作
    description: 将内容主题转化为Twitter推文串
    agent_type: content_generation
    version: "1.0"
    input_schema:
      required:
        - topic: string
        - core_argument: string  # 核心论点
        - thread_length: [int, int]  # 推文条数范围
      optional:
        - source_blog_id: string  # 如果是从博客改编
    required_tools:
      - brand-kb-mcp:read_brand_voice
    required_memory:
      - semantic: [brand_voice]
      - episodic: [recent_thread_performance]
      - procedural: [write_twitter_thread]
    quality_gate:
      min_score: 7
      evaluation_criteria:
        - hook_strength           # 首条推文吸引力
        - thread_coherence        # 推文串连贯性
        - standalone_readability  # 单条可独立阅读
    constraints:
      - "每条推文 ≤ 280字符"
      - "第一条必须是hook，不能是'Thread:'"
      - "hashtag ≤ 2个"

  - id: adapt_to_linkedin
    name: LinkedIn适配
    description: 将已有内容适配为LinkedIn帖子格式
    agent_type: content_generation
    version: "1.0"
    input_schema:
      required:
        - source_content: string  # 原始内容（博客或推文串）
        - content_type: enum[blog, thread, original]
    required_tools:
      - brand-kb-mcp:read_brand_voice
    required_memory:
      - semantic: [brand_voice, target_audience]
    quality_gate:
      min_score: 6
      evaluation_criteria:
        - professional_tone
        - value_density  # LinkedIn用户期望高信息密度
    constraints:
      - "字数 ≤ 3000字符"
      - "开头3行必须有hook（LinkedIn折叠后只显示3行）"
      - "结尾要有CTA或讨论引导"

  # ===== 研究分析类 =====
  - id: analyze_competitor
    name: 竞品分析
    description: 分析指定竞品的市场定位、内容策略和用户反馈
    agent_type: research
    version: "1.1"
    input_schema:
      required:
        - competitor_name: string
        - competitor_url: string
      optional:
        - focus_areas: list[string]  # 重点关注的维度
    required_tools:
      - web-scraper-mcp:fetch_url
      - appstore-mcp:get_reviews
      - search-engine-mcp:search
    required_memory:
      - semantic: [competitor_list, positioning]
      - episodic: [previous_competitor_analyses]  # 避免重复分析
    quality_gate:
      min_score: 7
      evaluation_criteria:
        - evidence_based    # 结论有数据支撑
        - actionable        # 能转化为具体行动
    constraints:
      - "所有结论必须附带数据来源"
      - "不做主观价值判断（'他们的产品很差'），只做客观比较"

  - id: analyze_audience_sentiment
    name: 受众情感分析
    description: 分析社区讨论中的用户关切、需求和情感倾向
    agent_type: research
    version: "1.0"
    input_schema:
      required:
        - data_source: enum[reddit, twitter, appstore, quora]
        - raw_data_ids: list[string]  # 数据库中的原始数据ID
    required_tools:
      - brand-kb-mcp:read_brand_voice  # 了解品牌视角来判断相关性
    required_memory:
      - semantic: [target_audience]
      - episodic: [previous_sentiment_analyses]
    quality_gate:
      min_score: 6
    constraints:
      - "样本量 < 50条时必须标注'低置信度'"
      - "情感标签限定为：positive / negative / neutral / mixed"

  # ===== 评审类 =====
  - id: review_content_quality
    name: 内容质量评审
    description: 评估生成内容的品牌一致性、准确性和质量
    agent_type: quality_review
    version: "1.0"
    input_schema:
      required:
        - content: string
        - content_type: enum[blog, thread, linkedin, newsletter]
        - original_brief: object  # 原始brief，用于对比
    required_tools:
      - brand-kb-mcp:read_brand_voice
      - brand-kb-mcp:read_compliance_rules
      - search-engine-mcp:search  # 用于事实核查
    required_memory:
      - semantic: [brand_voice, compliance_rules]
      - procedural: [review_content_quality]  # 审核标准本身也会进化
    quality_gate: null  # 评审Agent本身不需要被评审
    constraints:
      - "评分必须附带逐项理由"
      - "对事实性声明必须尝试验证（通过搜索工具）"
      - "评分 < 5 时必须给出具体修改建议"

  # ===== 策略类 =====
  - id: design_ab_experiment
    name: A/B实验设计
    description: 设计内容A/B测试方案
    agent_type: optimization
    version: "1.0"
    input_schema:
      required:
        - test_hypothesis: string  # 测试假设
        - available_channels: list[string]
      optional:
        - budget_constraint: object
    required_tools: []  # 纯推理任务，不需要外部工具
    required_memory:
      - episodic: [all_ab_test_results]  # 历史实验结果
      - procedural: [design_ab_experiment]
    quality_gate:
      min_score: 7
      evaluation_criteria:
        - hypothesis_clarity
        - measurability
        - feasibility
    constraints:
      - "每次实验只测一个变量"
      - "必须定义success metric和最小样本量"
      - "预估样本量不足时必须标注并建议替代方案"

  - id: generate_strategy_update
    name: 策略更新建议
    description: 基于近期数据生成营销策略调整建议
    agent_type: optimization
    version: "1.0"
    input_schema:
      required:
        - time_range: [date, date]
    required_tools:
      - client-kb-mcp:read_performance_data
    required_memory:
      - semantic: [positioning, target_audience]
      - episodic: [recent_content_performance, recent_ab_results]
      - procedural: [generate_strategy_update]
    quality_gate:
      min_score: 7
    constraints:
      - "建议必须基于数据，不接受'我觉得'"
      - "每条建议附带预期影响和置信度"
      - "限制为3-5条建议，按优先级排序"
```

### Skill的加载和调度

Agent不会一次加载所有Skill。Harness层根据当前任务选择正确的Skill注入：

```
任务调度流程：

1. [Workflow] 收到任务："为客户A生成本周Twitter推文串"
       ↓
2. [Harness] 查Skill注册表 → 匹配到 "write_twitter_thread" (v1.0)
       ↓
3. [Harness] 检查required_tools → 确认 brand-kb-mcp 可用
       ↓
4. [Harness] 检查required_memory → 从各层记忆中加载：
       - semantic: 客户A的brand_voice
       - episodic: 客户A最近5条推文串的表现数据
       - procedural: write_twitter_thread的当前最佳实践
       ↓
5. [Harness] 组装Agent的context：
       = System Prompt（Agent基础身份）
       + Skill Prompt（write_twitter_thread的步骤和约束）
       + Memory Context（加载的记忆内容）
       + Task Input（具体的topic和brief）
       + Available Tools（MCP工具列表和描述）
       ↓
6. [Agent] 执行任务
       ↓
7. [Harness] 将输出送入quality_gate检查
```

### Skill的版本管理和进化

```
Skill进化流程：

1. 学习优化Agent每周分析经验记忆
2. 发现模式："数字开头的推文串平均互动率比提问开头高40%"
3. 生成Skill更新建议：
   {
     "skill_id": "write_twitter_thread",
     "proposed_change": "在constraints中增加'优先使用数字开头'",
     "evidence": "基于过去47条推文串的表现数据，p < 0.05",
     "impact": "预计互动率提升15-25%"
   }
4. [Harness规则] 检查证据强度：
   - 样本量 ≥ 30 ✅
   - 有统计显著性 ✅
   → 自动更新Skill版本 v1.0 → v1.1
   
   如果样本量 < 30：
   → 标记为"待验证建议"，不自动更新
```

---

## 三、Tool管理

### Tool注册表

所有MCP工具集中注册和管理：

```yaml
# tools/registry.yaml

tools:
  # ===== 数据源类工具 =====
  - id: reddit-mcp
    name: Reddit数据接口
    type: data_source
    mcp_server_url: "http://localhost:3001"
    status: active
    version: "1.0"
    capabilities:
      - name: search_subreddit
        description: 在指定subreddit中搜索帖子
        params: {subreddit: string, query: string, limit: int}
        rate_limit: {max_per_minute: 60}
        cost: free
      - name: get_post_comments
        description: 获取指定帖子的所有评论
        params: {post_id: string, limit: int}
        rate_limit: {max_per_minute: 60}
        cost: free
    auth:
      type: api_key
      credentials_ref: "vault://reddit_api_credentials"
    health_check:
      endpoint: "/health"
      interval_seconds: 300
    permissions:
      allowed_agents: [research]        # 只有研究类Agent可用
      denied_agents: [content_generation]  # 内容Agent不应该直接访问原始数据

  - id: twitter-mcp
    name: Twitter/X数据接口
    type: data_source
    mcp_server_url: "http://localhost:3002"
    status: active
    version: "1.0"
    capabilities:
      - name: search_tweets
        description: 搜索公开推文
        params: {query: string, max_results: int, date_range: [date, date]}
        rate_limit: {max_per_minute: 30}
        cost: "$100/mo for Basic API tier"
      - name: get_tweet_metrics
        description: 获取指定推文的互动数据
        params: {tweet_id: string}
        rate_limit: {max_per_minute: 30}
    auth:
      type: oauth2
      credentials_ref: "vault://twitter_api_credentials"
    permissions:
      allowed_agents: [research, optimization]

  - id: appstore-mcp
    name: App Store评价接口
    type: data_source
    mcp_server_url: "http://localhost:3003"
    status: active
    version: "1.0"
    capabilities:
      - name: get_app_reviews
        description: 获取指定应用的用户评价
        params: {app_id: string, store: enum[apple, google], limit: int}
        rate_limit: {max_per_minute: 10}
        cost: free
    auth:
      type: none  # 公开数据
    permissions:
      allowed_agents: [research]

  # ===== 发布类工具 =====
  - id: twitter-publisher-mcp
    name: Twitter发布接口
    type: publisher
    mcp_server_url: "http://localhost:3010"
    status: active
    version: "1.0"
    capabilities:
      - name: post_tweet
        description: 发布单条推文
        params: {text: string, media_ids: list[string]}
        rate_limit: {max_per_hour: 50}
        cost: "included in Basic API"
        requires_approval: true  # 需要人工审核（V0阶段）
      - name: post_thread
        description: 发布推文串
        params: {tweets: list[string]}
        rate_limit: {max_per_hour: 10}
        cost: "included in Basic API"
        requires_approval: true
    auth:
      type: oauth2
      credentials_ref: "vault://twitter_publish_credentials"
    permissions:
      allowed_agents: []  # 没有Agent可以直接调用发布
      allowed_workflows: [distribution_workflow]  # 只有分发Workflow可以调用
    # ⬆️ 关键设计：发布类工具只允许Workflow调用，Agent不可直接发布

  - id: wordpress-mcp
    name: WordPress发布接口
    type: publisher
    mcp_server_url: "http://localhost:3011"
    status: planned  # V1再实现
    version: null

  # ===== 工具类 =====
  - id: seo-analyzer-mcp
    name: SEO分析工具
    type: utility
    mcp_server_url: "http://localhost:3020"
    status: active
    version: "1.0"
    capabilities:
      - name: get_keyword_data
        description: 获取关键词的搜索量、竞争度、相关词
        params: {keyword: string, region: string}
        rate_limit: {max_per_minute: 20}
        cost: free  # 基于Google Search Console免费数据
      - name: analyze_content_seo
        description: 分析一篇内容的SEO得分
        params: {content: string, target_keyword: string}
        rate_limit: {max_per_minute: 10}
        cost: free
    auth:
      type: api_key
      credentials_ref: "vault://gsc_credentials"
    permissions:
      allowed_agents: [content_generation, quality_review]

  - id: search-engine-mcp
    name: 联网搜索工具
    type: utility
    mcp_server_url: "http://localhost:3021"
    status: active
    version: "1.0"
    capabilities:
      - name: search
        description: 联网搜索
        params: {query: string, max_results: int}
        rate_limit: {max_per_minute: 30}
        cost: free  # 使用Serper API免费额度
    permissions:
      allowed_agents: [research, quality_review]  # 内容Agent不能直接联网搜索
    # ⬆️ 内容Agent如果需要查资料，应该先生成search query，
    #    由Workflow调用搜索，结果作为context注入。避免Agent在生成过程中失焦。

  # ===== 知识库类 =====
  - id: brand-kb-mcp
    name: 品牌知识库
    type: knowledge_base
    mcp_server_url: "http://localhost:3030"
    status: active
    version: "1.0"
    capabilities:
      - name: read_brand_voice
        description: 读取客户的品牌调性文档
        params: {client_id: string}
        read_only: true
      - name: read_compliance_rules
        description: 读取行业合规规则
        params: {industry: string}
        read_only: true
      - name: get_best_content_examples
        description: 获取历史高表现内容作为参考
        params: {client_id: string, content_type: string, limit: int}
        read_only: true
    auth:
      type: internal
    permissions:
      allowed_agents: [content_generation, quality_review, research]

  - id: client-kb-mcp
    name: 客户专属知识库
    type: knowledge_base
    mcp_server_url: "http://localhost:3031"
    status: planned  # V2
    version: null
```

### Tool发现机制

Agent不硬编码工具列表。启动时通过Harness动态发现可用工具：

```
Agent启动流程：

1. Harness查询Skill注册表 → 获取当前Skill的 required_tools
2. Harness查询Tool注册表 → 检查每个tool的：
   - status == active?
   - 当前Agent在 allowed_agents 中?
   - health_check通过?
   - rate_limit未超限?
3. 将可用工具的描述（name + description + params）注入Agent的context
4. Agent只能看到和使用通过检查的工具
```

### 权限矩阵

```
              │ 数据源工具  │ 发布工具  │ 搜索工具  │ 知识库(读) │ 知识库(写) │
──────────────┼────────────┼──────────┼──────────┼──────────┼──────────┤
研究Agent      │    ✅      │    ❌    │    ✅    │    ✅    │    ✅    │
内容生成Agent  │    ❌      │    ❌    │    ❌    │    ✅    │    ❌    │
质量评审Agent  │    ❌      │    ❌    │    ✅    │    ✅    │    ❌    │
优化Agent      │    ✅(读)  │    ❌    │    ✅    │    ✅    │    ✅    │
分发Workflow   │    ❌      │    ✅    │    ❌    │    ❌    │    ❌    │
数据采集WF    │    ✅      │    ❌    │    ❌    │    ❌    │    ❌    │
```

**设计原则：**

- **内容生成Agent不能联网搜索。** 听起来反直觉，但原因是：如果Agent在生成过程中自由上网，容易被搜索结果带偏，跑题或引入不可靠信息。需要参考资料的话，由Workflow提前搜好放进brief。
- **没有Agent能直接发布。** 发布是不可逆操作，必须经过质量Gate和（V0阶段的）人工审核，只有分发Workflow在所有检查通过后才能调用发布工具。
- **知识库写权限严格限制。** 只有研究Agent和优化Agent可以写入，而且要通过认证门。

### Tool健康监控

```python
# 伪代码：Tool健康检查Workflow（Celery Beat每5分钟跑一次）

def check_tool_health():
    for tool in ToolRegistry.get_all_active():
        try:
            response = requests.get(
                f"{tool.mcp_server_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                tool.update_status("healthy")
                tool.reset_failure_count()
            else:
                tool.increment_failure_count()
        except Timeout:
            tool.increment_failure_count()

        # 连续3次失败 → 标记为degraded
        if tool.failure_count >= 3:
            tool.update_status("degraded")
            alert_team(f"MCP Server {tool.name} 连续{tool.failure_count}次健康检查失败")

        # 连续10次失败 → 自动禁用
        if tool.failure_count >= 10:
            tool.update_status("disabled")
            alert_team(f"MCP Server {tool.name} 已自动禁用")
```

---

## 四、三者如何协同工作：完整示例

以"为客户A生成本周Twitter推文串"为例，展示Memory + Skill + Tool的完整协作：

```
第1步 - 任务触发
[Celery Beat Workflow] 周一09:00 → 触发"weekly_content_generation"任务

第2步 - Skill选择
[Harness] 本周内容计划中有一条Twitter推文串任务
         → 从Skill注册表加载 "write_twitter_thread" v1.1

第3步 - 记忆加载
[Harness] 根据Skill的required_memory，从三层记忆中检索：
  短期记忆：无（新任务开始）
  中期记忆：本周已生成的博客文章摘要（避免推文串和博客内容重复）
  长期记忆：
    ├── 事实记忆：客户A的品牌调性 = "专业但不呆板"
    ├── 经验记忆：最近5条推文串表现 → 最佳：数字开头，互动率3.4%
    └── 程序记忆：write_twitter_thread当前最佳实践
        "v1.1更新：优先使用数字开头（基于47次执行数据）"

第4步 - 工具准备
[Harness] 根据Skill的required_tools，检查可用性：
  brand-kb-mcp:read_brand_voice → status: healthy ✅
  → 将工具描述注入Agent context

第5步 - Context组装
[Harness] 组装Agent的完整输入：
  {
    "system_prompt": "你是ReelMatrix内容生成Agent...",
    "skill_prompt": "[write_twitter_thread v1.1的完整步骤和约束]",
    "memory_context": {
      "brand_voice": "专业但不呆板，偶尔用比喻...",
      "recent_performance": "最近5条中，数字开头的互动率最高(3.4%)...",
      "best_practice": "优先使用数字开头..."
    },
    "task_input": {
      "topic": "工程团队的技术债管理",
      "core_argument": "技术债不是bug，是战略选择",
      "thread_length": [5, 8]
    },
    "available_tools": [
      {"name": "read_brand_voice", "description": "...", "params": "..."}
    ]
  }

第6步 - Agent执行
[Content Generation Agent] 
  → 调用 brand-kb-mcp:read_brand_voice 获取完整品牌文档
  → 生成7条推文串
  → 输出结构化JSON

第7步 - 质量检查
[Harness] 加载 "review_content_quality" Skill → 注入Quality Review Agent
[Quality Review Agent]
  → 评分：8/10
  → 品牌一致性：9/10
  → hook强度：8/10
  → 单条可独立阅读：7/10
  → 通过 quality_gate (≥ 7) ✅

第8步 - 记忆写入
[Workflow] 记录到中期记忆（Redis）：
  "本周已生成：1条关于技术债管理的推文串，评分8/10"
[Workflow] 写入长期经验记忆（PostgreSQL）：
  {
    "event": "generated_twitter_thread",
    "topic": "技术债管理",
    "format": "数字开头",
    "quality_score": 8,
    "status": "pending_publish"
  }

第9步 - 进入发布队列
[Workflow] 内容写入发布排期表 → 等待排期时间到达或人工审核

第10步 - 发布（由分发Workflow执行，不经过Agent）
[Distribution Workflow]
  → 检查人工审核状态：approved ✅
  → 调用 twitter-publisher-mcp:post_thread()
  → 记录发布状态

第11步 - 后续数据追踪（3天后）
[Celery Beat Workflow]
  → 调用 twitter-mcp:get_tweet_metrics()
  → 更新经验记忆中的metrics字段
  → 如果表现异常好/差，标记给优化Agent下次分析
```

---

## 五、V0阶段的简化实现

| 完整架构 | V0简化版 | 理由 |
|---------|---------|------|
| 三层记忆（短/中/长） | 短期用context window，长期用PostgreSQL普通表 | 不需要Redis中间层，pipeline没那么复杂 |
| pgvector语义检索 | 关键词匹配 + 客户ID过滤 | 5个试用客户，数据量不需要向量检索 |
| Skill注册表（YAML） | 硬编码在代码中的prompt模板 | 5个Skill以内，不需要动态加载 |
| Skill自动进化 | 人工根据数据手动更新prompt | 样本量不够自动进化 |
| Tool注册表 + 健康监控 | 3个MCP Server手动管理 | 工具少，不需要自动发现 |
| 权限矩阵 | 代码层面控制谁调用什么 | 团队只有自己，不需要细粒度权限 |
| 记忆认证门 | 所有写入都经过自己review | 数据量小，人工把关 |
| 记忆遗忘策略 | 不遗忘（数据量增长慢） | 6个月内不会有记忆过载问题 |

**V0的核心是：用最简单的方式跑通完整流程，验证每个环节的价值。** 架构设计按完整版来想，但实现按最小版来做。等有了10个付费客户和3个月的运行数据，再投入做记忆进化和Skill自动更新。
