# reelmatrix

## Repository Structure

```text
reelmatrix/
├── apps/         # 可运行的应用入口，如 API、编排器、worker、前端
├── core/         # 核心业务逻辑，如 agents、workflows、memory、skills、events
├── mcp_servers/  # 外部工具与平台接入层，如抓取、发布、SEO、知识库等 MCP 服务
├── data/         # 数据相关目录，如 migrations、seed、fixtures、sample data
├── infra/        # 部署与运行环境配置，如 Docker、脚本、云平台配置
├── configs/      # 项目配置文件，如环境变量模板、模型参数、权限与监控配置
├── docs/         # 项目文档，如架构说明、API 文档、runbooks、设计记录
└── tests/        # 测试代码，如单元测试、集成测试、端到端测试
