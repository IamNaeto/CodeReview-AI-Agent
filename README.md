# Agentic AI Code Review System

A production-grade multi-agent code review system that coordinates specialist AI sub-agents to analyze code changes, identify defects, and produce actionable review reports.

## Features

- **Supervisor / Sub-Agent Architecture**: Intelligent delegation to 6 specialist agents
- **Specialist Agents**: Correctness, Security, Architecture, Performance, Quality, Testing
- **Smart Agent Selection**: Supervisor only invokes relevant agents per change set
- **Cross-Validation**: High-severity findings are validated by secondary agents
- **Multiple Input Sources**: Git diffs, commits, PRs, local repositories
- **GitHub Integration**: List PRs, post inline review comments, create PR reviews
- **Modern React UI**: Real-time agent activity, filtering by severity/category
- **CLI Tool**: Run reviews directly from terminal
- **Review History**: Persistent SQLite storage with comparison support
- **Custom Rules**: Support for repository-specific coding standards

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React UI      │────▶│  FastAPI Backend │────▶│  SQLite DB      │
│   / CLI         │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            ┌──────────────┐    ┌──────────────┐
            │   Supervisor  │    │   Git Service │
            │    Agent      │    │  (clone/parse)│
            └──────┬───────┘    └──────────────┘
                   │
     ┌─────┬──────┼──────┬─────┬──────┐
     ▼     ▼      ▼      ▼     ▼      ▼
  [Security] [Correctness] [Architecture] [Performance] [Quality] [Testing]
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- OpenRouter API key

### 1. Clone & Configure

```bash
git clone <repository-url>
cd code-review-agent
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY and optional GITHUB_TOKEN and move it into the backend directory
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run build
```

### 4. Run the Application

**Backend:**
```bash
cd backend
# Ensure that .env is present in this directory with the needed variables
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (development):**
```bash
cd frontend
npm run dev
```

**Production (served from backend):**
The FastAPI app automatically serves the built frontend from `frontend/dist/` at `/`.

### 5. CLI Usage

```bash
cd cli
pip install -r requirements.txt

# Review a GitHub PR
python review_cli.py start --repo https://github.com/owner/repo.git --pr 42

# Review local changes
python review_cli.py start --local /path/to/repo --branch main

# Show a completed review
python review_cli.py show 123

# List recent reviews
python review_cli.py list
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `MODEL_NAME` | No | LLM model (default: `openai/gpt-4o-mini`) |
| `GITHUB_TOKEN` | No | For GitHub PR integration |
| `GITLAB_TOKEN` | No | For GitLab MR integration |
| `APP_HOST` | No | Backend host (default: `0.0.0.0`) |
| `APP_PORT` | No | Backend port (default: `8000`) |
| `DATABASE_URL` | No | SQLite path (default: `sqlite:///./code_review.db`) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reviews/start` | Start a review |
| GET | `/api/v1/reviews/{id}` | Get review with findings |
| GET | `/api/v1/reviews/{id}/status` | Get review progress |
| GET | `/api/v1/reviews` | List reviews |
| POST | `/api/v1/reviews/github-pr` | Review GitHub PR |
| POST | `/api/v1/reviews/{id}/post-github-comments` | Post findings to PR |
| GET | `/api/v1/github/repos/{owner}/{repo}/prs` | List PRs |

## Evaluation

Five evaluation scenarios are provided in `evaluation/scenarios/`:

1. **SQL Injection** - Security vulnerability
2. **N+1 Query & O(n²)** - Performance issues
3. **Race Condition & Swallowed Exceptions** - Correctness issues
4. **Missing Tests** - Testing gaps
5. **God Class & Tight Coupling** - Architecture issues

Run them by pasting the scenario content as a raw diff in the UI.

## Docker Deployment

```bash
docker-compose up --build
```

Access the UI at `http://localhost` and API at `http://localhost:8000`.

## License

MIT
