# My AI Agent - 多Agent智能体系统

一个基于 **CrewAI** 的模块化多 Agent 协作系统，支持配置化定义智能体与工作流，提供命令行、API 和 Web 界面三种交互方式。

---

## 📁 项目结构

```
my_ai_agent/
├── main.py                 # 命令行入口
├── api/                    # FastAPI 后端服务
│   ├── main.py            # API 入口
│   └── routes/            # API 路由
├── frontend/              # Next.js 前端界面
│   ├── src/               # React 组件
│   └── package.json
├── core/                  # 核心模块
│   ├── agent_factory.py   # Agent 工厂
│   ├── task_orchestrator.py # 任务编排器
│   ├── llm_factory.py     # LLM 管理
│   ├── chat_engine.py     # 对话引擎
│   ├── memory.py          # 内存管理
│   └── ...
├── plugins/               # 插件目录
├── skills/                # 技能定义
├── config/                # 配置文件
├── requirements.txt       # Python 依赖
└── deploy.sh              # 部署脚本
```

---

## ⚡ 快速开始

### 1. 安装依赖

```bash
# Python 环境
pip install -r requirements.txt

# 前端依赖（可选）
cd frontend && npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 3. 运行

```bash
# 方式一：命令行模式
python main.py --topic "AI技术趋势"

# 方式二：启动 API 服务
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 方式三：启动前端界面（需先启动 API）
cd frontend && npm run dev
```

---

## 🎯 核心特性

### 配置化 Agent 系统
通过 `config.yaml` 定义 Agent 角色、目标和任务流程：

```yaml
agents:
  - name: "researcher"
    role: "研究员"
    goal: "搜索关于 {topic} 的最新信息"
    backstory: "你擅长使用搜索引擎查找最新资料"

tasks:
  - name: "research"
    description: "搜索关于 {topic} 的最新信息"
    agent: "researcher"
    context: []                    # 无依赖
  
  - name: "write"
    description: "撰写总结报告"
    agent: "writer"
    context: ["research"]          # 依赖 research 任务
```

### 多模式执行
- **顺序模式**：任务按依赖关系依次执行
- **并行模式**：无依赖任务同时执行
- **层级模式**：支持层级化的 Agent 管理

### 多 LLM 支持
- 智谱 AI (GLM-4)
- OpenAI (GPT-4/GPT-3.5)
- DeepSeek
- 支持扩展其他提供商

### 内置工具
- 文件读写
- 网络搜索（智谱原生）
- 文档处理 (PDF/Word/Excel)
- 代码执行

---

## 🛠️ 命令行用法

```bash
# 基础用法
python main.py

# 指定主题
python main.py --topic "量子计算最新进展"

# 自定义参数
python main.py \
  --topic "AI智能体" \
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

---

## 📡 API 服务

启动 API：
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

主要接口：
- `POST /api/chat` - 对话接口
- `GET /api/health` - 健康检查
- `GET /api/agents` - Agent 列表
- `GET /api/models` - 可用模型列表

---

## 🎨 前端界面

基于 **Next.js + React + Tailwind CSS** 的现代化 Web 界面：

```bash
cd frontend
npm install
npm run dev          # 开发模式 http://localhost:3000
npm run build        # 生产构建
```

---

## 📚 项目模块

| 模块 | 说明 |
|------|------|
| `core/` | 核心引擎（Agent、任务编排、LLM、内存） |
| `api/` | FastAPI 服务端 |
| `frontend/` | Next.js 前端 |
| `plugins/` | 插件扩展目录 |
| `skills/` | 技能定义目录 |
| `deploy/` | 部署配置 |

---

## 📦 依赖环境

- Python >= 3.10
- Node.js >= 18（前端）
- API Keys: 智谱 AI / OpenAI / DeepSeek

---

## 🔒 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `ZHIPU_API_KEY` | 智谱 AI API Key | 是 |
| `OPENAI_API_KEY` | OpenAI API Key | 可选 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 可选 |
| `ENCRYPTION_KEY` | 数据加密密钥 | 是 |
| `LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARNING/ERROR) | 否 |

---

## 📄 许可证

MIT License

---

## 👤 作者

**zxs-0312**

Gitee: https://gitee.com/zxs-0312/my_ai_agent.git
