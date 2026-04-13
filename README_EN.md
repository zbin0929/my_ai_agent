<div align="center">

# 🤖 My AI Agent

**Modular Multi-Agent Intelligent Collaboration System Based on CrewAI**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-68%20passed-brightgreen.svg)](tests/)

[中文](README.md) | English

</div>

## 📖 Introduction

My AI Agent is an **enterprise-grade multi-agent intelligent collaboration platform** that defines agent roles, goals, and workflows through configuration. The system provides three interaction modes (CLI, REST API, Web Interface), supports multiple mainstream LLMs, and includes rich built-in skill tools to help teams efficiently complete complex tasks.

### ✨ Key Highlights

- 🎯 **Configurable Agent System** - Define roles, goals, and task flows via YAML
- 🔄 **Multi-Mode Execution** - Sequential/Parallel/Hierarchical task scheduling
- 🛠️ **15+ Built-in Skills** - Search, image generation, code execution, document processing, and more
- 🌐 **Multi-LLM Support** - Zhipu AI, OpenAI, DeepSeek, Moonshot, Alibaba Cloud, etc.
- 🔒 **Enterprise-Grade Security** - Fernet encryption, token trimming, access control
- 💻 **Three Interaction Methods** - CLI, REST API, modern Web Interface
- 📱 **Responsive Design** - Support for desktop and mobile access
- 🌍 **Multi-Language Support** - Complete Chinese and English internationalization

## 📁 Project Structure

```
my_ai_agent/
├── 🎯 Entry & Scripts
│   ├── main.py                 # CLI entry point
│   ├── start.sh / start.bat    # One-click startup scripts
│   └── stop.sh / stop.bat      # Service stop scripts
│
├── 🖥️ Frontend (Next.js 14 + React 18)
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   ├── components/        # React components
│   │   │   ├── chat/         # Chat interface
│   │   │   ├── office/       # Agent office visualization
│   │   │   └── settings/     # Settings panel
│   │   ├── store/            # Zustand state management
│   │   └── lib/              # API client
│   └── package.json
│
├── ⚙️ Backend API (FastAPI)
│   ├── main.py               # API service entry
│   ├── routes/               # Route modules
│   │   ├── chat.py          # Streaming chat (SSE)
│   │   ├── sessions.py      # Session management
│   │   ├── agents.py        # Agent configuration
│   │   ├── skills.py        # Skill management
│   │   ├── models.py        # Model configuration
│   │   ├── files.py         # File processing
│   │   └── stats.py         # Usage statistics
│   └── schemas.py           # Pydantic models
│
├── 🧠 Core Engine
│   ├── chat_engine.py       # Main conversation engine
│   ├── worker_executor.py   # Worker executor
│   ├── fc_dispatcher.py     # Function Calling dispatcher
│   ├── skill_executor.py    # Skill executor
│   ├── memory.py            # Memory management + token trimming
│   ├── security.py          # Security encryption module
│   ├── llm_factory.py       # LLM factory
│   └── model_router.py      # Model routing
│
├── 🛠️ Skill Library (15+ Built-in Skills)
│   ├── search_report.py      # Intelligent search reports
│   ├── image_generate.py    # AI image generation
│   ├── code_execute.py      # Code execution
│   ├── doc_summary.py       # Document summarization
│   ├── doc_generator.py     # Document generation
│   ├── data_analysis.py     # Data analysis
│   ├── translate.py         # Translation
│   ├── tts.py               # Text-to-speech
│   ├── web_scrape.py        # Web scraping
│   ├── email_send.py        # Email sending
│   ├── reminder.py          # Reminder tasks
│   ├── knowledge_base.py    # Knowledge base
│   ├── media_understand.py  # Media understanding
│   ├── prompt_optimizer.py  # Prompt optimization
│   └── task_manager.py      # Task management
│
├── 🔌 Plugin Extensions
│   ├── browser/             # Browser automation
│   ├── code_executor/       # Code executor
│   └── bot/                 # Bot extensions
│
├── ⚙️ Configuration & Deployment
│   ├── config.yaml          # Main configuration file
│   ├── .env.example         # Environment variable template
│   ├── deploy.sh            # Deployment script
│   └── deploy/              # Deployment configurations
│
├── 🧪 Tests
│   └── tests/               # Test suite (68+ test cases)
│
└── 📚 Documentation
    └── docs/                # Project documentation
```

## 🚀 Quick Start

### Requirements

- Python >= 3.10
- Node.js >= 18 (for frontend)
- Supported OS: macOS / Linux / Windows

### 1. Clone the Project

```bash
git clone https://github.com/zbin0929/my_ai_agent.git
cd my_ai_agent
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies (optional)
cd frontend && npm install && cd ..
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in your API Keys
```

### 4. Start Services

```bash
# Method 1: One-click start all services (recommended)
./start.sh

# Method 2: Start separately
# Start API service
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start frontend (new terminal)
cd frontend && npm run dev
```

Visit http://localhost:3000 to use the Web Interface

## 🎯 Usage Guide

### Command Line Mode

```bash
# Basic usage
python main.py

# Specify research topic
python main.py --topic "Latest Quantum Computing Advances"

# Custom parameters
python main.py \
  --topic "AI Agent Technology" \
  --num-points 5 \
  --word-count 500 \
  --output-file "report.txt"

# Validate configuration only
python main.py --validate

# Enable verbose logging
python main.py --verbose

# Specify execution mode
python main.py --mode hierarchical
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Streaming chat (SSE) |
| `/api/health` | GET | Health check |
| `/api/sessions` | GET | Session list |
| `/api/sessions/{id}` | GET/DELETE | Get/Delete session |
| `/api/sessions/{id}/export` | GET | Export to Markdown |
| `/api/agents` | GET/POST | Agent list/configuration |
| `/api/skills` | GET | Skill list |
| `/api/models` | GET | Available model list |
| `/api/stats` | GET | Usage statistics |

### Web Interface Features

- 💬 **Smart Chat** - Streaming output, thinking process visualization
- 📁 **Session Management** - Pin, rename, export to Markdown
- ⚙️ **Agent Configuration** - Visual configuration of roles and goals
- 🛠️ **Skill Management** - Enable/disable skills, parameter configuration
- 🤖 **Model Settings** - Multi-LLM switching, parameter tuning
- 📊 **Usage Statistics** - Token consumption, API call statistics
- 🎮 **Agent Office** - Pixel-style visualization of working agents
- 🌓 **Dark Mode** - Auto-follow system or manual toggle

## ⚙️ Configuration

### Agent Configuration Example (`config.yaml`)

```yaml
agents:
  - name: "researcher"
    role: "Researcher"
    goal: "Search and summarize latest information about {topic}"
    backstory: "You excel at using search engines to find the latest information and extract key points"
    tools: ["search"]
    verbose: true

  - name: "writer"
    role: "Report Writer"
    goal: "Write concise reports based on research materials"
    backstory: "You are skilled at transforming complex content into readable text"

  - name: "executor"
    role: "Executor"
    goal: "Save the final report to local file"
    backstory: "You are responsible for writing reports to files, ensuring content completeness"
    tools: ["file_writer"]

tasks:
  - name: "research"
    description: "Search for latest information about {topic}, summarize {num_points} key points"
    agent: "researcher"
    expected_output: "Key points summary"
    context: []

  - name: "write"
    description: "Based on research materials, write a summary report of about {word_count} words"
    agent: "writer"
    expected_output: "Complete report"
    context: ["research"]

  - name: "save"
    description: "Save the final report to file '{output_file}'"
    agent: "executor"
    expected_output: "Save confirmation"
    context: ["write"]
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ZHIPU_API_KEY` | Zhipu AI API Key | ✅ Recommended |
| `OPENAI_API_KEY` | OpenAI API Key | ❌ Optional |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ❌ Optional |
| `MOONSHOT_API_KEY` | Moonshot API Key | ❌ Optional |
| `DASHSCOPE_API_KEY` | Alibaba Cloud Bailian API Key | ❌ Optional |
| `ENCRYPTION_KEY` | API Key encryption key (Fernet) | ✅ Recommended |
| `ADMIN_TOKEN` | Admin interface auth token | ✅ Production |
| `LOG_LEVEL` | Log level | ❌ Default INFO |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run core feature tests
pytest tests/test_p0_features.py -v

# Generate coverage report
pytest tests/ --cov=core --cov-report=html
```

## 📸 Interface Preview

> Web interface screenshots will be displayed here

## 🤝 Join the Community, Build Together

**We warmly welcome you to join!** Regardless of your technical level, you can contribute to this project. This is an open and friendly community that welcomes all forms of participation.

### 🌟 Ways to Participate

| Participation | For Whom | How to Start |
|--------------|----------|--------------|
| 🐛 **Report Bugs** | All users | [Submit an Issue](https://github.com/zbin0929/my_ai_agent/issues) when you find problems |
| 💡 **Suggest Features** | All users | Have new ideas? [Tell us](https://github.com/zbin0929/my_ai_agent/issues/new?template=feature_request.md) |
| 📝 **Improve Docs** | Tech writers | Improve README, add tutorials, translate content |
| 🔧 **Contribute Code** | Developers | Fork → Develop → Submit Pull Request |
| 🧪 **Test & Feedback** | Testers | Try new features, share your experience |
| 🌍 **Translations** | Multilingual users | Help translate to more languages |
| 💬 **Help Others** | Experienced users | Help other users in Issues |
| ⭐ **Spread the Word** | Everyone | Star the project, share with friends |

### 🚀 Quick Start Contributing

1. **Fork this repository** to your GitHub account
2. **Create a feature branch** `git checkout -b feature/amazing-feature`
3. **Commit your changes** `git commit -m 'Add some amazing feature'`
4. **Push to the branch** `git push origin feature/amazing-feature`
5. **Open a Pull Request** - we'll review it soon

### 📋 Contribution Guidelines

- Follow [PEP 8](https://pep8.org/) code style
- Run tests before submitting: `pytest tests/`
- Add corresponding test cases for new features
- Keep documentation updated with code changes

### 💬 Communication Channels

- 💻 [GitHub Issues](https://github.com/zbin0929/my_ai_agent/issues) - Bug reports and discussions
- 📧 Email the author: Contact via GitHub profile

### 🙏 Contributors

Thanks to all developers who have contributed to this project! Every effort makes this project better.

<a href="https://github.com/zbin0929/my_ai_agent/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zbin0929/my_ai_agent" alt="Contributors" />
</a>

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).

## 👤 Author

**zbin0929**

- GitHub: [@zbin0929](https://github.com/zbin0929)
- Project Homepage: [https://github.com/zbin0929/my_ai_agent](https://github.com/zbin0929/my_ai_agent)

---

<div align="center">

⭐ If this project helps you, please give it a Star!

**[⬆ Back to Top](#-my-ai-agent)**

</div>
