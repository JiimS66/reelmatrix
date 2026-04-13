# ReelMatrix 技术架构：Workflow vs Agent vs MCP

## 核心原则

**判断标准很简单：这个任务需要"判断力"还是"执行力"？**

- **Workflow（确定性工作流）：** 输入确定 → 步骤确定 → 输出确定。不需要LLM，用代码逻辑跑就行。
- **Agent（AI智能体）：** 输入模糊或多变，需要理解、推理、创造、评估。必须用LLM。
- **MCP（Model Context Protocol）：** Agent访问外部工具和数据源的标准化接口。不是Agent也不是Workflow，而是Agent和外部世界之间的"USB-C接口"。

**一句话总结：Workflow做执行，Agent做判断，MCP做连接。**

---

## 全链路拆解

### 阶段一：战略定位

```
┌─────────────────────────────────────────────────────────┐
│                    战略定位模块                            │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Workflow  │ →  │  Agent   │ →  │ Workflow  │          │
│  │ 数据采集  │    │ 定位分析  │    │ 文档生成  │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│                                                         │
│  MCP连接：网页抓取工具、搜索引擎                           │
└─────────────────────────────────────────────────────────┘
```

| 子任务 | 类型 | 理由 |
|--------|------|------|
| 抓取用户产品官网内容 | **Workflow** | 确定性操作：URL → HTML → 提取文本。用 Playwright/BeautifulSoup，不需要LLM |
| 抓取竞品官网和产品页 | **Workflow** | 同上，爬虫逻辑固定 |
| 搜索竞品信息（G2评价等） | **Workflow + MCP** | 搜索动作本身是确定性的，但通过MCP Server暴露搜索工具给Agent调用 |
| 分析产品定位和差异化机会 | **Agent** | 需要理解产品、竞品、市场，做出创造性判断。这是LLM的核心价值 |
| 生成定位文档（markdown格式） | **Workflow** | Agent输出结构化JSON → 模板引擎填充 → 生成文档。确定性转换 |

**MCP在这里的角色：**
```
定位分析Agent
    ├── MCP Tool: web_scraper    → 抓取指定URL内容
    ├── MCP Tool: search_engine  → 搜索竞品关键词
    └── MCP Tool: review_reader  → 读取G2/Capterra评价数据
```
Agent决定"我需要查一下这个竞品的用户评价"，通过MCP调用review_reader工具，拿到数据后自己做分析。Agent做判断，MCP做连接，Workflow做数据预处理。

---

### 阶段二：客群研究

```
┌─────────────────────────────────────────────────────────┐
│                    客群研究模块                            │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Workflow  │ →  │  Agent   │ →  │ Workflow  │          │
│  │ 数据拉取  │    │ 洞察分析  │    │ 结构化存储 │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│       ↑                                                 │
│  ┌──────────┐                                           │
│  │ Workflow  │  ← 定时任务触发（Celery Beat）              │
│  │ 定时采集  │                                           │
│  └──────────┘                                           │
│                                                         │
│  MCP连接：Reddit API、Twitter API、App Store Scraper      │
└─────────────────────────────────────────────────────────┘
```

| 子任务 | 类型 | 理由 |
|--------|------|------|
| 定时拉取Reddit帖子（按关键词） | **Workflow** | 确定性：关键词列表 → API调用 → 存入数据库。Celery Beat定时触发，不需要LLM |
| 定时拉取Twitter搜索结果 | **Workflow** | 同上 |
| 抓取App Store竞品评价 | **Workflow** | 同上，爬虫脚本定期跑 |
| 对原始数据做清洗和去重 | **Workflow** | 确定性的数据处理：Polars/Pandas管道 |
| 分析用户关切、提取主题、情感分析 | **Agent** | 需要理解自然语言语义，做主题聚类和情感判断。LLM擅长 |
| 生成受众画像和选题建议 | **Agent** | 需要综合所有数据做创造性推理 |
| 将分析结果存入结构化数据库 | **Workflow** | Agent输出JSON → 写入PostgreSQL。确定性操作 |

**关键设计：数据采集和分析解耦。**

数据采集是Workflow，每天/每周定时跑，把原始数据攒在数据库里。分析Agent按需被触发（比如每周一次），读取积累的数据做分析。这样即使Agent出问题，数据也不会丢。

**MCP在这里的角色：**

MCP Server封装各个数据源的访问接口：

```python
# 示例：Reddit MCP Server 暴露的工具
class RedditMCPServer:
    tools = [
        Tool(
            name="search_subreddit",
            description="搜索指定subreddit中的帖子",
            params={"subreddit": str, "query": str, "limit": int}
        ),
        Tool(
            name="get_post_comments",
            description="获取指定帖子的所有评论",
            params={"post_id": str}
        ),
    ]
```

但注意：**日常数据采集不走MCP，走Workflow直接调API。** MCP是给Agent在需要"临时查一下某个具体帖子"时用的。批量数据采集走确定性管道效率更高。

---

### 阶段三：内容智能

```
┌─────────────────────────────────────────────────────────┐
│                    内容智能模块                            │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Workflow  │ →  │  Agent   │ →  │  Agent   │          │
│  │ Brief组装 │    │ 内容生成  │    │ 质量评审  │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│                       │               │                 │
│                       ↓               ↓                 │
│                  ┌──────────┐    ┌──────────┐          │
│                  │ Workflow  │    │ Workflow  │          │
│                  │ 格式转换  │    │ 评分记录  │          │
│                  └──────────┘    └──────────┘          │
│                                                         │
│  MCP连接：SEO工具、品牌知识库                              │
└─────────────────────────────────────────────────────────┘
```

| 子任务 | 类型 | 理由 |
|--------|------|------|
| 组装内容brief（从选题库、品牌调性、SEO关键词拼装） | **Workflow** | 确定性：从数据库取数据 → 填入brief模板 → 生成结构化prompt |
| 内容创作（写博客/推文串/LinkedIn帖子） | **Agent** | 核心创造性任务，必须用LLM |
| SEO关键词研究和推荐 | **Workflow + 轻量LLM** | 关键词数据拉取是Workflow；判断哪些关键词值得写是轻量LLM任务（分类，不是生成） |
| 一鱼多吃（长文 → 多渠道适配版本） | **Agent** | 需要理解内容核心并为不同渠道重写，不是简单截断 |
| 质量评审（品牌一致性、事实准确性） | **Agent** | 需要判断力：内容是否on-brand？有没有不当表述？ |
| 质量评分记录 | **Workflow** | Agent输出评分JSON → 写入数据库。确定性 |
| 格式转换（Markdown → 各平台格式） | **Workflow** | 确定性模板转换，不需要LLM |

**这个模块是Agent密度最高的地方——因为内容创作本质上就是判断+创造。**

但要注意的是：**brief组装是Workflow，不是Agent。** 很多人的错误是让Agent自己决定"今天写什么"，但其实选题应该由阶段二的分析结果驱动，brief应该是结构化的——Agent只负责在brief约束内创作。这就是harness engineering的思路。

**MCP在这里的角色：**

```
内容生成Agent
    ├── MCP Tool: seo_analyzer    → 查询目标关键词的搜索量和竞争度
    ├── MCP Tool: brand_kb        → 读取品牌调性文档和历史优质内容（作为few-shot示例）
    └── MCP Tool: fact_checker    → 验证内容中的事实性声明（联网搜索确认）

质量评审Agent
    ├── MCP Tool: brand_kb        → 读取品牌规范进行一致性检查
    └── MCP Tool: compliance_rules → 读取行业合规规则（如FTC health claims）
```

---

### 阶段四：投放分发

```
┌─────────────────────────────────────────────────────────┐
│                    投放分发模块                            │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Workflow  │ →  │ Workflow  │ →  │ Workflow  │          │
│  │ 排期计算  │    │ 格式适配  │    │ API发布   │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│                                       │                 │
│                                  ┌────┴─────┐          │
│                                  │ Workflow  │          │
│                                  │ 状态追踪  │          │
│                                  └──────────┘          │
│                                                         │
│  MCP连接：Twitter API、WordPress API、LinkedIn API        │
└─────────────────────────────────────────────────────────┘
```

| 子任务 | 类型 | 理由 |
|--------|------|------|
| 计算最佳发布时间 | **Workflow** | 基于历史数据的统计计算，确定性算法 |
| 内容格式适配（字数裁剪、图片规格调整） | **Workflow** | 确定性规则：Twitter ≤ 280字符、LinkedIn ≤ 3000字符 |
| 调用平台API发布 | **Workflow** | 确定性：POST请求 → 检查响应 → 记录状态 |
| 发布失败重试 | **Workflow** | 确定性：指数退避重试逻辑 |
| 发布状态追踪和日志 | **Workflow** | 写数据库，确定性 |

**这个模块几乎不需要Agent。** 分发是纯执行——内容已经确定了，渠道已经确定了，时间已经确定了，剩下的就是调API发出去。

**MCP在这里的核心作用——标准化平台接入：**

```python
# 每个社媒平台封装为一个MCP Server
class TwitterMCPServer:
    tools = [
        Tool(name="post_tweet", params={"text": str, "media_ids": list}),
        Tool(name="post_thread", params={"tweets": list}),
        Tool(name="get_tweet_metrics", params={"tweet_id": str}),
    ]

class WordPressMCPServer:
    tools = [
        Tool(name="create_post", params={"title": str, "content": str, "status": str}),
        Tool(name="upload_media", params={"file_path": str}),
    ]

class LinkedInMCPServer:
    tools = [
        Tool(name="create_share", params={"text": str, "visibility": str}),
    ]
```

**MCP在这里的价值是解耦。** 分发Workflow不直接写Twitter API调用代码，而是通过MCP统一接口调用。这样加新平台只需要写一个新的MCP Server，Workflow代码不用改。这也是为什么MCP被比喻成"USB-C"。

---

### 阶段五：A/B测试

```
┌─────────────────────────────────────────────────────────┐
│                    A/B测试模块                            │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Workflow  │ →  │ Workflow  │ →  │  Agent   │          │
│  │ 变体分配  │    │ 数据收集  │    │ 结果解读  │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│       ↑                                                 │
│  ┌──────────┐                                           │
│  │  Agent   │  ← 决定测试什么（标题？格式？时间？）         │
│  │ 实验设计  │                                           │
│  └──────────┘                                           │
│                                                         │
│  MCP连接：各平台数据拉取工具                               │
└─────────────────────────────────────────────────────────┘
```

| 子任务 | 类型 | 理由 |
|--------|------|------|
| 决定测试什么变量 | **Agent** | 需要判断：当前最有价值的测试是什么？标题风格？发布时间？内容长度？ |
| 生成变体内容（如两个不同标题） | **Agent** | 创造性任务 |
| 变体分配和发布调度 | **Workflow** | 确定性：A组周一发，B组周三发 |
| 从各平台拉取互动数据 | **Workflow** | 定时任务：API拉数据 → 写入数据库 |
| 统计计算（贝叶斯置信度等） | **Workflow** | 纯数学计算，不需要LLM |
| 解读测试结果并生成建议 | **Agent** | 需要把统计数据翻译成actionable insight："列表体标题在工程师受众中表现更好" |

**Agent只出现在两头（设计实验 + 解读结果），中间全是Workflow。**

---

### 阶段六：学习优化

```
┌─────────────────────────────────────────────────────────┐
│                    学习优化模块                            │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Workflow  │ →  │  Agent   │ →  │ Workflow  │          │
│  │ 数据汇总  │    │ 模式识别  │    │ 参数更新  │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│                                                         │
│  MCP连接：客户知识库（读写）                               │
└─────────────────────────────────────────────────────────┘
```

| 子任务 | 类型 | 理由 |
|--------|------|------|
| 汇总过去N周的表现数据 | **Workflow** | SQL聚合查询，确定性 |
| 识别表现模式和趋势 | **Agent** | 需要理解"为什么某类内容突然不行了"——这是判断，不是计算 |
| 生成策略调整建议 | **Agent** | 创造性推理："建议增加案例研究类内容，减少纯干货列表" |
| 更新客户知识库中的偏好参数 | **Workflow** | Agent输出JSON → 写入数据库。确定性 |
| 更新内容brief模板中的权重 | **Workflow** | 调整参数，确定性 |

---

## 汇总：各模块的Workflow/Agent/MCP比例

| 模块 | Workflow占比 | Agent占比 | MCP工具数 |
|------|-------------|----------|----------|
| 战略定位 | 40% | 60% | 3（网页抓取、搜索、评价读取） |
| 客群研究 | 70% | 30% | 4（Reddit、Twitter、App Store、Google Trends） |
| 内容智能 | 30% | 70% | 3（SEO分析、品牌知识库、事实核查） |
| 投放分发 | **95%** | **5%** | 3+（每个平台一个MCP Server） |
| A/B测试 | 60% | 40% | 复用分发模块的MCP |
| 学习优化 | 50% | 50% | 1（客户知识库） |

**整个系统大约60% Workflow + 40% Agent。** 如果你把所有东西都做成Agent，成本会翻3-5倍（LLM调用），而且不可靠。

---

## MCP架构总览

### MCP Server清单

```
ReelMatrix MCP Servers
│
├── 数据源类
│   ├── reddit-mcp-server        → Reddit API封装
│   ├── twitter-mcp-server       → Twitter/X API封装
│   ├── appstore-mcp-server      → App Store评价抓取
│   └── web-scraper-mcp-server   → 通用网页抓取
│
├── 平台发布类
│   ├── twitter-publisher-mcp    → Twitter发帖/发串
│   ├── wordpress-mcp-server     → WordPress文章发布
│   ├── linkedin-mcp-server      → LinkedIn帖子发布
│   └── medium-mcp-server        → Medium文章发布
│
├── 工具类
│   ├── seo-analyzer-mcp         → 关键词分析和SEO评分
│   └── search-engine-mcp        → 联网搜索（用于事实核查和竞品研究）
│
└── 知识库类
    ├── brand-kb-mcp-server      → 品牌调性、历史内容、风格指南
    └── client-kb-mcp-server     → 客户专属知识库（表现数据、偏好、策略）
```

### MCP vs 直接API调用的决策规则

| 场景 | 用MCP | 直接调API |
|------|-------|----------|
| Agent在推理过程中需要**按需**获取外部信息 | ✅ | |
| Workflow做**批量**定时数据采集 | | ✅ |
| 新增一个平台/数据源 | ✅（只写MCP Server） | ❌（要改Workflow代码） |
| 高频调用（每秒100+次） | | ✅（MCP有协议开销） |
| Agent需要**动态发现**可用工具 | ✅ | |

**简单记：Agent访问外部世界用MCP，Workflow批量处理用直接API。**

---

## Harness层设计

在Workflow和Agent之上，Harness层负责治理整个系统：

```
┌─────────────────────────────────────────────────────────────┐
│                        Harness Layer                         │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ 权限控制     │ │ 限速与配额   │ │ 质量Gate    │          │
│  │ 哪个Agent能  │ │ API调用频率  │ │ 内容必须过   │          │
│  │ 用哪些工具   │ │ LLM token限额│ │ 评分才能发布  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ 重试与降级   │ │ 可观测性     │ │ 人工审核节点  │          │
│  │ 失败自动重试  │ │ 全链路日志   │ │ 高风险内容   │          │
│  │ 连续失败告警  │ │ Agent决策追踪│ │ 需人工approve │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 具体规则

**权限控制：**
- 内容生成Agent：可读品牌知识库、可读SEO数据，不可直接发布
- 分发Workflow：可调用发布API，但只能发布状态为"approved"的内容
- A/B测试Agent：可读所有数据，可写实验配置，不可改已发布内容

**质量Gate：**
```
内容生成 → 质量评审Agent打分 → 分数 ≥ 7/10 → 进入发布队列
                              → 分数 < 7/10 → 回退重新生成（最多3次）
                              → 3次仍不过 → 标记为需人工介入
```

**人工审核节点（V0阶段必须保留）：**
- 所有内容首次发布前
- 涉及health/medical话题的内容（如果客户是health类产品）
- A/B测试中任何涉及品牌定位变更的实验

**限速：**
- 单客户每日LLM调用上限：100K tokens（约$3 Sonnet成本）
- 平台API调用严格遵守各平台限速
- 超限自动降级：停止新内容生成，只维持已排期的发布

---

## 技术实现路径

### V0用什么框架

| 组件 | 推荐 | 理由 |
|------|------|------|
| Agent框架 | **LangGraph** | 支持有状态的multi-step Agent，比CrewAI更灵活，图式编排适合复杂条件分支 |
| MCP SDK | **官方Python SDK** | Anthropic官方维护，社区活跃，文档完善 |
| Workflow引擎 | **Celery + Redis** | 成熟稳定，定时任务、异步执行、重试都内置 |
| Harness实现 | **自己写（先别用框架）** | V0阶段Harness逻辑不复杂，用Python装饰器和中间件模式就够 |

### V0的MCP Server优先级

| 优先级 | MCP Server | 理由 |
|--------|-----------|------|
| P0（必须有） | twitter-publisher-mcp | V0核心发布渠道 |
| P0（必须有） | brand-kb-mcp | 内容生成的基础上下文 |
| P0（必须有） | web-scraper-mcp | 定位分析和竞品研究的基础 |
| P1（尽快有） | reddit-mcp-server | 客群研究主要数据源 |
| P1（尽快有） | seo-analyzer-mcp | 内容选题的数据依据 |
| P2（V1再做） | wordpress-mcp | 博客自动发布 |
| P2（V1再做） | linkedin-mcp-server | 第二发布渠道 |
| P3（V2再做） | client-kb-mcp | 跨客户学习需要 |

### 一个完整的内容生产流程示例

```
1. [Workflow] Celery Beat 触发"周一内容生产"任务
       ↓
2. [Workflow] 从数据库读取本周选题列表（阶段二的输出）
       ↓
3. [Workflow] 为每个选题组装content brief（模板填充）
       ↓
4. [Agent] 内容生成Agent收到brief
       ├── [MCP] 调用 brand-kb-mcp 读取品牌调性和历史优质内容
       ├── [MCP] 调用 seo-analyzer-mcp 确认目标关键词
       └── 生成博客文章草稿
       ↓
5. [Agent] 质量评审Agent收到草稿
       ├── [MCP] 调用 brand-kb-mcp 对比品牌规范
       └── 输出评分 + 修改建议
       ↓
6. [Workflow] 检查评分
       ├── ≥ 7分 → 标记为 "ready_to_publish"
       └── < 7分 → 回到步骤4重新生成（附带修改建议）
       ↓
7. [Workflow] 人工审核队列（V0必须，V2+可选）
       ↓
8. [Agent] 渠道适配Agent
       └── 博客文章 → Twitter推文串 + LinkedIn帖子
       ↓
9. [Workflow] 格式转换（Markdown → 各平台格式）
       ↓
10. [Workflow] 写入发布排期队列
       ↓
11. [Workflow] Celery Worker 按排期时间调用 MCP 发布
       ├── [MCP] twitter-publisher-mcp.post_thread()
       └── [MCP] linkedin-mcp-server.create_share()
       ↓
12. [Workflow] 记录发布状态，启动数据追踪任务
```

**10个步骤中，只有3个用到Agent（步骤4、5、8），其余全是Workflow。** 这就是正确的比例。
