# Automated Research Agent

An AI-powered research assistant with a Discord-style chat UI. Enter any research topic and the agent will search the web, filter credible sources, extract content, summarize findings, and synthesize a comprehensive briefing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Chat UI    │  │  Markdown   │  │  SSE Stream Handler     │  │
│  │  (Discord)  │  │  Renderer   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + SSE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Research Agent                           ││
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  ││
│  │  │  Search   │ │Credibility│ │  Content  │ │ Summarizer  │  ││
│  │  │   Tool    │ │  Filter   │ │ Extractor │ │   Chain     │  ││
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────────┘  ││
│  │                                             ┌─────────────┐  ││
│  │                                             │ Synthesizer │  ││
│  │                                             │   Chain     │  ││
│  │                                             └─────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ LangChain
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM Provider (Ollama / vLLM)                   │
│                         LLaMA 3 (8B / 70B)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Web Search**: Google Custom Search Engine search for relevant sources
- **Credibility Filtering**: Domain-based reputation scoring
- **Content Extraction**: Clean text extraction from web pages
- **AI Summarization**: Per-source summaries via LangChain + LLaMA 3
- **Research Synthesis**: Comprehensive briefing generation
- **Streaming UI**: Real-time progress updates via SSE

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- **LLaMA 3** via one of:
  - [Ollama](https://ollama.ai) (local, recommended for dev)
  - [vLLM](https://github.com/vllm-project/vllm) (hosted, recommended for prod)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull LLaMA 3 model (if using Ollama)
ollama pull llama3:8b

# Configure environment
cat > .env << EOF
LLM_PROVIDER=ollama
LLM_MODEL=llama3:8b
EOF

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## LLM Configuration

### Option 1: Ollama (Local Inference)

Best for development and privacy-sensitive deployments.

**Setup:**

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve

# Pull LLaMA 3 model
ollama pull llama3:8b      # 8B model (~4.7GB)
ollama pull llama3:70b     # 70B model (~40GB, requires 48GB+ RAM)
```

**Environment Variables:**

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3:8b
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
```

**Supported Ollama Models:**
| Model | Size | RAM Required | Use Case |
|-------|------|--------------|----------|
| `llama3:8b` | 4.7GB | 8GB+ | Development, quick responses |
| `llama3:8b-instruct-q8_0` | 8.5GB | 16GB+ | Better quality, still fast |
| `llama3:70b` | 40GB | 48GB+ | Production quality |
| `llama3:70b-instruct-q4_0` | 40GB | 48GB+ | Quantized, faster |

### Option 2: vLLM (Hosted Inference)

Best for production deployments with dedicated GPU servers.

**Start vLLM server:**

```bash
# Install vLLM
pip install vllm

# Start server with LLaMA 3
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Meta-Llama-3-8B-Instruct \
  --port 8080
```

**Environment Variables:**

```env
LLM_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8080/v1
VLLM_API_KEY=EMPTY
LLM_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
```

**Supported vLLM Models:**
| Model | HuggingFace ID | GPU VRAM |
|-------|----------------|----------|
| LLaMA 3 8B | `meta-llama/Meta-Llama-3-8B-Instruct` | 16GB+ |
| LLaMA 3 70B | `meta-llama/Meta-Llama-3-70B-Instruct` | 80GB+ (or multi-GPU) |

### Option 3: Cloud-Hosted vLLM

For cloud deployments (Together AI, Anyscale, etc.):

```env
LLM_PROVIDER=vllm
VLLM_BASE_URL=https://api.together.xyz/v1
VLLM_API_KEY=your_api_key_here
LLM_MODEL=meta-llama/Llama-3-8b-chat-hf
```

---

## Environment Variables Reference

| Variable                 | Default                    | Description                     |
| ------------------------ | -------------------------- | ------------------------------- |
| `LLM_PROVIDER`           | `ollama`                   | LLM backend: `ollama` or `vllm` |
| `OLLAMA_BASE_URL`        | `http://localhost:11434`   | Ollama server URL               |
| `VLLM_BASE_URL`          | `http://localhost:8080/v1` | vLLM OpenAI-compatible API URL  |
| `VLLM_API_KEY`           | `EMPTY`                    | API key for hosted vLLM         |
| `LLM_MODEL`              | `llama3:8b`                | Model name/ID                   |
| `LLM_TEMPERATURE`        | `0.1`                      | Sampling temperature            |
| `LLM_MAX_TOKENS`         | `4096`                     | Max output tokens               |
| `MAX_SEARCH_RESULTS`     | `10`                       | CSE results to fetch            |
| `MAX_SOURCES_TO_PROCESS` | `5`                        | Sources to summarize            |
| `API_HOST`               | `0.0.0.0`                  | Backend bind address            |
| `API_PORT`               | `8000`                     | Backend port                    |
| `CORS_ORIGINS`           | `http://localhost:3000`    | Allowed CORS origins            |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/           # Research orchestration
│   │   │   └── research_agent.py
│   │   ├── chains/           # LangChain chains
│   │   │   ├── summarizer.py
│   │   │   └── synthesizer.py
│   │   ├── tools/            # Agent tools
│   │   │   ├── web_search.py
│   │   │   ├── content_extractor.py
│   │   │   └── credibility_filter.py
│   │   ├── models/           # Pydantic schemas
│   │   ├── api/              # FastAPI routes
│   │   ├── config.py         # Settings management
│   │   ├── llm.py            # LLaMA provider factory
│   │   └── main.py           # Application entry
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   ├── components/
│   │   │   ├── chat/         # Chat UI components
│   │   │   └── ui/           # Base UI components
│   │   ├── hooks/            # React hooks
│   │   ├── lib/              # Utilities & API client
│   │   └── types/            # TypeScript types
│   ├── package.json
│   └── tailwind.config.ts
│
└── README.md
```

## API Reference

### POST `/api/research`

Start a research task with streaming progress.

**Request:**

```json
{
  "topic": "Latest advancements in quantum computing",
  "depth": "standard"
}
```

**Response:** Server-Sent Events stream

```
event: progress
data: {"status": "searching", "message": "...", "progress": 0.2, ...}

event: progress
data: {"status": "summarizing", "message": "...", "progress": 0.6, ...}

event: result
data: {"topic": "...", "briefing": "...", "sources": [...], ...}
```

### GET `/api/health`

Health check endpoint.

### GET `/api/health/llm`

Check LLM provider connectivity and model availability.

### GET `/api/config`

Get current configuration (non-sensitive).

---

## Development

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm run dev
```

### Verify LLM Connection

```bash
curl http://localhost:8000/api/health/llm
```

---

## Customization

### Adding New Tools

Create a new tool in `backend/app/tools/`:

```python
from langchain_core.tools import BaseTool

class MyCustomTool(BaseTool):
    name: str = "my_tool"
    description: str = "Description for the LLM"

    async def _arun(self, input: str) -> str:
        # Implement tool logic
        return result
```

### Modifying Prompts

Edit prompt templates in:

- `backend/app/chains/summarizer.py` - Source summarization
- `backend/app/chains/synthesizer.py` - Briefing synthesis

### Adjusting Credibility Scores

Edit `backend/app/tools/credibility_filter.py` to add/modify domain scores.

---

## Features (v1.1)

### ✅ Implemented

- **Citation Linking** - Inline citations [1], [2] with clickable references
- **Conversation History** - Persistent storage with SQLite database
- **PDF Export** - Download briefings as formatted PDF documents
- **Academic Search** - arXiv and Semantic Scholar integration
- **Rate Limiting** - 10 requests/minute, 100 requests/hour per IP
- **Response Caching** - 24-hour TTL cache for repeated queries

### API Endpoints

| Endpoint                  | Method         | Description                 |
| ------------------------- | -------------- | --------------------------- |
| `/api/research`           | POST           | Start research (SSE stream) |
| `/api/conversations`      | GET            | List all conversations      |
| `/api/conversations`      | POST           | Create conversation         |
| `/api/conversations/{id}` | GET/PUT/DELETE | Manage conversation         |
| `/api/export/pdf`         | POST           | Export briefing as PDF      |
| `/api/cache/stats`        | GET            | Cache statistics            |
| `/api/cache/clear`        | POST           | Clear cache                 |
| `/api/health`             | GET            | Health check                |
| `/api/health/llm`         | GET            | LLM connectivity check      |

### Research Request Options

```json
{
  "topic": "Your research topic",
  "depth": "standard",
  "include_academic": true
}
```

- `depth`: "quick" (3 sources), "standard" (5), "deep" (8)
- `include_academic`: Enable arXiv + Semantic Scholar search

---

## TODO

- [ ] User authentication and saved research
- [ ] Citation export (BibTeX, RIS)
- [ ] Multi-language support
- [ ] Custom source filters

## License

MIT
