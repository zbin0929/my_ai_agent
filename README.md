<div align="center">

# 🤖 My AI Agent

**基于 CrewAI 的模块化多 Agent 智能协作系统**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-68%20passed-brightgreen.svg)](tests/)

[English](README_EN.md) | 中文

</div>

## 📖 简介

My AI Agent 是一个**企业级多 Agent 智能协作平台**，通过配置化方式定义智能体角色、目标和工作流程。系统提供三种交互模式（命令行、REST API、Web 界面），支持多种主流 LLM，内置丰富的技能工具，帮助团队高效完成复杂任务。

### ✨ 核心亮点

- 🎯 **配置化 Agent 系统** - YAML 定义角色、目标和任务流程
- 🔄 **多模式执行** - 顺序/并行/层级三种任务调度模式
- 🛠️ **15+ 内置技能** - 搜索、绘图、代码执行、文档处理等
- 🌐 **多 LLM 支持** - 智谱AI、OpenAI、DeepSeek、Moonshot、阿里云等
- 🔒 **企业级安全** - Fernet 加密存储、Token 裁剪、访问控制
- 💻 **三种交互方式** - CLI、REST API、现代化 Web 界面
- 📱 **响应式设计** - 支持桌面端和移动端访问
- 🌍 **多语言支持** - 完整的中英文国际化

## 📁 项目结构

```
my_ai_agent/
├── 🎯 入口与脚本
│   ├── main.py                 # 命令行入口
│   ├── start.sh / start.bat    # 一键启动脚本
│   └── stop.sh / stop.bat      # 停止服务脚本
│
├── 🖥️ 前端界面 (Next.js 14 + React 18)
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   ├── components/        # React 组件
│   │   │   ├── chat/         # 聊天界面
│   │   │   ├── office/       # Agent 办公室可视化
│   │   │   └── settings/     # 设置面板
│   │   ├── store/            # Zustand 状态管理
│   │   └── lib/              # API 客户端
│   └── package.json
│
├── ⚙️ 后端 API (FastAPI)
│   ├── main.py               # API 服务入口
│   ├── routes/               # 路由模块
│   │   ├── chat.py          # 流式对话 (SSE)
│   │   ├── sessions.py      # 会话管理
│   │   ├── agents.py        # Agent 配置
│   │   ├── skills.py        # 技能管理
│   │   ├── models.py        # 模型配置
│   │   ├── files.py         # 文件处理
│   │   └── stats.py         # 用量统计
│   └── schemas.py           # Pydantic 模型
│
├── 🧠 核心引擎
│   ├── chat_engine.py       # 主对话引擎
│   ├── worker_executor.py   # Worker 执行器
│   ├── fc_dispatcher.py     # Function Calling 调度器
│   ├── skill_executor.py    # 技能执行器
│   ├── memory.py            # 内存管理 + Token 裁剪
│   ├── security.py          # 安全加密模块
│   ├── llm_factory.py       # LLM 工厂
│   └── model_router.py      # 模型路由
│
├── 🛠️ 技能库 (15+ 内置技能)
│   ├── search_report.py      # 智能搜索报告
│   ├── image_generate.py    # AI 图像生成
│   ├── code_execute.py      # 代码执行
│   ├── doc_summary.py       # 文档摘要
│   ├── doc_generator.py     # 文档生成
│   ├── data_analysis.py     # 数据分析
│   ├── translate.py         # 翻译
│   ├── tts.py               # 文本转语音
│   ├── web_scrape.py        # 网页抓取
│   ├── email_send.py        # 邮件发送
│   ├── reminder.py          # 提醒任务
│   ├── knowledge_base.py    # 知识库
│   ├── media_understand.py  # 媒体理解
│   ├── prompt_optimizer.py  # 提示词优化
│   └── task_manager.py      # 任务管理
│
├── 🔌 插件扩展
│   ├── browser/             # 浏览器自动化
│   ├── code_executor/       # 代码执行器
│   └── bot/                 # 机器人扩展
│
├── ⚙️ 配置与部署
│   ├── config.yaml          # 主配置文件
│   ├── .env.example         # 环境变量模板
│   ├── deploy.sh            # 部署脚本
│   └── deploy/              # 部署配置
│
├── 🧪 测试
│   └── tests/               # 测试套件 (68+ 测试用例)
│
└── 📚 文档
    └── docs/                # 项目文档
```

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18 (前端需要)
- 支持的操作系统：macOS / Linux / Windows

### 1. 克隆项目

```bash
git clone https://github.com/zbin0929/my_ai_agent.git
cd my_ai_agent
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或: venv\Scripts\activate  # Windows

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖（可选）
cd frontend && npm install && cd ..
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Keys
```

### 4. 启动服务

```bash
# 方式一：一键启动所有服务（推荐）
./start.sh

# 方式二：单独启动
# 启动 API 服务
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 启动前端（新终端）
cd frontend && npm run dev
```

访问 http://localhost:3000 使用 Web 界面

## 🎯 使用指南

### 命令行模式

```bash
# 基础用法
python main.py

# 指定研究主题
python main.py --topic "量子计算最新进展"

# 自定义参数
python main.py \
  --topic "AI智能体技术" \
  --num-points 5 \
  --word-count 500 \
  --output-file "report.txt"

# 仅验证配置
python main.py --validate

# 启用详细日志
python main.py --verbose

# 指定执行模式
python main.py --mode hierarchical
```

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 流式对话 (SSE) |
| `/api/health` | GET | 健康检查 |
| `/api/sessions` | GET | 会话列表 |
| `/api/sessions/{id}` | GET/DELETE | 获取/删除会话 |
| `/api/sessions/{id}/export` | GET | 导出 Markdown |
| `/api/agents` | GET/POST | Agent 列表/配置 |
| `/api/skills` | GET | 技能列表 |
| `/api/models` | GET | 可用模型列表 |
| `/api/stats` | GET | 用量统计 |

### Web 界面功能

- 💬 **智能对话** - 流式输出、思考过程可视化
- 📁 **会话管理** - 置顶、重命名、导出 Markdown
- ⚙️ **Agent 配置** - 可视化配置角色和目标
- 🛠️ **技能管理** - 启用/禁用技能、参数配置
- 🤖 **模型设置** - 多 LLM 切换、参数调优
- 📊 **用量统计** - Token 消耗、API 调用统计
- 🎮 **Agent 办公室** - 像素风格的可视化工作场景
- 🌓 **深色模式** - 自动跟随系统或手动切换

## ⚙️ 配置说明

### Agent 配置示例 (`config.yaml`)

```yaml
agents:
  - name: "researcher"
    role: "研究员"
    goal: "搜索并总结关于 {topic} 的最新信息"
    backstory: "你擅长使用搜索引擎查找最新资料，并提炼要点"
    tools: ["search"]
    verbose: true

  - name: "writer"
    role: "报告撰写员"
    goal: "根据资料写出简洁的报告"
    backstory: "你擅长把复杂内容变成易读的文字"

  - name: "executor"
    role: "执行员"
    goal: "将最终报告保存到本地文件"
    backstory: "你负责把报告写入文件，确保内容完整"
    tools: ["file_writer"]

tasks:
  - name: "research"
    description: "搜索关于 {topic} 的最新信息，总结出{num_points}个要点"
    agent: "researcher"
    expected_output: "要点总结"
    context: []

  - name: "write"
    description: "根据研究资料，写一段{word_count}字左右的总结报告"
    agent: "writer"
    expected_output: "完整报告"
    context: ["research"]

  - name: "save"
    description: "将最终报告保存到文件 '{output_file}' 中"
    agent: "executor"
    expected_output: "保存确认"
    context: ["write"]
```

### 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `ZHIPU_API_KEY` | 智谱 AI API Key | ✅ 推荐 |
| `OPENAI_API_KEY` | OpenAI API Key | ❌ 可选 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ❌ 可选 |
| `MOONSHOT_API_KEY` | Moonshot API Key | ❌ 可选 |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key | ❌ 可选 |
| `ENCRYPTION_KEY` | API Key 加密密钥 (Fernet) | ✅ 推荐 |
| `ADMIN_TOKEN` | 管理接口认证令牌 | ✅ 生产环境 |
| `LOG_LEVEL` | 日志级别 | ❌ 默认 INFO |

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行核心功能测试
pytest tests/test_p0_features.py -v

# 生成覆盖率报告
pytest tests/ --cov=core --cov-report=html
```

## 📸 界面预览

> Web 界面截图将在这里展示

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的改动 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

### 贡献者

感谢所有为项目做出贡献的开发者！

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

## 👤 作者

**zbin0929**

- GitHub: [@zbin0929](https://github.com/zbin0929)
- 项目主页: [https://github.com/zbin0929/my_ai_agent](https://github.com/zbin0929/my_ai_agent)

---

<div align="center">

⭐ 如果这个项目对你有帮助，请给它一个 Star！

**[⬆ 返回顶部](#-my-ai-agent)**

</div>
