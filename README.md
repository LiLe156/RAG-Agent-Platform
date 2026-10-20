🤖 企业级私有化 RAG Agent 智能问答平台
本项目是一个基于 LangGraph + DeepSeek + FastAPI 构建的现代化生产级 AI Agent 应用。针对企业内部知识库场景，实现了多智能体协作、长短记忆持久化、混合检索以及高并发安全防护，并支持 Docker 一键容器化部署。

🚀 核心技术栈
https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white
https://img.shields.io/badge/LangGraph-0.2-orange
https://img.shields.io/badge/FastAPI-0.100-green?logo=fastapi&logoColor=white
https://img.shields.io/badge/Docker-Enabled-blue?logo=docker&logoColor=white
https://img.shields.io/badge/License-MIT-yellow

✨ 核心功能亮点
多智能体协作架构 (Multi-Agent)：拆分 思考专家 -> 撰写专家 -> 审核专家，通过 LangGraph 状态机实现自我反思与纠错，显著降低模型幻觉。

高级 RAG 检索：采用 BM25 (关键词) + FAISS (向量) 双路混合检索，解决专有名词搜索不到的痛点，并引入 Reranker 精排。

长短记忆分层机制：

短期记忆：基于 AsyncSqliteSaver 实现多轮会话上下文持久化。

长期记忆：基于 FAISS 向量库存储用户画像，实现跨会话记忆。

生产级安全护栏：在代码底层实现 Prompt 注入拦截、工具越权校验，并引入 .env 隔离 API 密钥。

全链路可观测性：内置 Trace ID 和 Metrics 监控，精准记录每个节点的耗时与 Token 消耗。

丝滑流式输出：基于 SSE 协议，前端实现真·打字机效果，并带有流式丢包兜底机制。

🏗️ 系统架构与工作流
https://./architecture.png

核心工作流说明：

用户输入后，首先经过 security 模块进行 Prompt 注入检测。

通过后进入 agent_think 节点，自主决定是直接回答还是调用检索工具。

如果需要生成内容，交由 writer 节点起草，随后流转至 critic 节点进行事实性与合规性审核。

若审核不通过（FAIL）且未超最大重试次数，则打回 writer 重写；若通过，则输出给用户，并异步触发 save_memory 节点存入长期记忆。

💻 快速启动指南
准备工作
安装 Docker 和 Docker Desktop。

准备大模型 API Key（本项目默认使用 DeepSeek，兼容 OpenAI 格式）。

在项目根目录创建 .env 文件，并填入密钥：

env
DEEPSEEK_API_KEY=sk-你的密钥
方式一：Docker 一键部署（推荐）
bash
# 构建并启动容器（后台运行）
docker-compose up -d --build
启动后访问 API 文档：http://127.0.0.1:8001/docs
前端测试页面：直接双击打开 test7.html。

方式二：本地开发运行
bash
# 1. 安装依赖 (建议使用虚拟环境)
pip install -r requirements.txt

# 2. 启动后端服务
uvicorn api_server:app --host 127.0.0.1 --port 8001 --loop asyncio

##📁 目录结构说明
```text
RAG-Agent-Platform/
├── app/                  # 核心逻辑目录
│   ├── tools/            # 工具模块 (BM25, RAG, 计算器等)
│   ├── config.py         # 全局配置
│   ├── graph_builder.py  # LangGraph 图结构编排
│   ├── graph_nodes.py    # 核心节点逻辑 (思考、撰写、审核)
│   ├── observability.py  # 全链路日志与监控
│   ├── security.py       # 安全与权限护栏
│   └── state.py          # AgentState 状态定义
├── Dockerfile            # 镜像构建文件
├── docker-compose.yml    # 容器编排配置
├── api_server.py         # FastAPI 后端启动入口
├── test7.html            # 前端聊天测试页面
├── test.pdf              # RAG 测试用知识库文档
└── requirements.txt      # Python 依赖清单
```

🛠️ 踩坑与优化记录 (Engineering Notes)
解决 FastAPI 跨线程死锁：用 await graph.ainvoke 替换了阻塞的 run_in_executor，解决异步数据库连接池冲突。

解决流式清洗难题：在 api_server.py 引入精准截取，过滤大模型输出的 JSON 外壳与内部审核标记 (FAIL/PASS)。

解决多用户并发写冲突：为 FAISS 向量库的写入操作引入 threading.Lock() 互斥锁，防止并发写坏索引。

如果觉得这个项目对你有帮助，欢迎点个 ⭐ Star！
