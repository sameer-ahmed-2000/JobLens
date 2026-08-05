# JobLens 🎯

> **AI-Powered Real-Time Job Discovery & Skill Gap Analysis System**

JobLens is an intelligent career acceleration platform that aggregates job postings across public ATS boards (Greenhouse, Lever, Ashby) and live job search APIs (Adzuna, Jooble, Remotive, Arbeitnow). It ranks job opportunities against your precomputed resume vector index using cosine similarity and produces explainable skill gap reports with project-backed bridge suggestions.

---

## 🛠️ Technology Stack

* **Backend**: Python 3.10+ managed with [`uv`](https://github.com/astral-sh/uv), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic V2, LangGraph
* **Database & Caching**: PostgreSQL (Aiven/Supabase/local) or SQLite + Redis (Upstash/local Redis 7 for rate limiting & streams)
* **Frontend**: React 19, TypeScript, Vite, TailwindCSS
* **AI / LLM Routing**: FreeModel.dev (OpenAI-compatible), Groq, Google Gemini, Ollama (Local Llama 3), SentenceTransformers, FAISS

---

## 📋 Prerequisites

Ensure you have the following installed before beginning setup:

1. **Python 3.10+** and **`uv`** (Astral's fast Python package installer):
   ```bash
   # Windows (PowerShell)
   powershell -executionpolicy bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Node.js** (v18+) & `npm`
3. **Docker & Docker Compose** (optional, for local Redis/PostgreSQL)

---

## 🔑 Environment Setup (`.env` Configuration)

JobLens requires environment configuration in `backend/.env`. A complete, fully-documented template is provided in [`backend/.env.example`](backend/.env.example).

### Step 1: Create your `backend/.env` file

Navigate to the `backend` directory and copy `.env.example`:

```bash
cd backend
cp .env.example .env
```

### Step 2: Configure Environment Variables

Open `backend/.env` and configure the following key sections:

1. **JWT Secret Key (Required)**:
   Generate a 32+ character random hex string:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Set it in `backend/.env`: `JWT_SECRET_KEY=your_generated_hex_key_here`

2. **LLM Provider Setup**:
   * **FreeModel.dev (Pre-configured Default)**: Set `LLM_PROVIDER_DEFAULT=freemodel` and add `FREEMODEL_API_KEY`.
   * **Local Ollama (Alternative)**: Install [Ollama](https://ollama.ai), run `ollama pull llama3`, and set `LLM_PROVIDER_DEFAULT=ollama`.
   * **Groq / OpenAI / Gemini**: Add your corresponding API keys and set `LLM_PROVIDER_DEFAULT` or role-specific overrides (`LLM_PROVIDER_RATIONALE`, `LLM_PROVIDER_GAP_ANALYSIS`).

3. **Database Configuration**:
   * **PostgreSQL (Recommended)**: Set `DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require`
   * **Local SQLite (Development fallback)**: Set `DATABASE_URL=sqlite:///./joblens.db`

4. **Job Search Aggregators (Optional for live API feeds)**:
   * **Adzuna**: Register at [https://developer.adzuna.com](https://developer.adzuna.com) and set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
   * **Jooble**: Register at [https://jooble.org/api/about](https://jooble.org/api/about) and set `JOOBLE_API_KEY`.
   * **Remotive & Arbeitnow**: Open public APIs enabled out-of-the-box (`REMOTIVE_ENABLED=true`, `ARBEITNOW_ENABLED=true`).

---

## 🚀 How to Reproduce & Run Locally

### Option A: Local Multi-Terminal Execution (Recommended for Development)

#### 1. Start Redis
If using local Redis via Docker:
```bash
docker compose up -d
```
*(If using a remote Redis URL like Upstash in `REDIS_URL`, this step can be skipped).*

#### 2. Initialize Backend & Database
```bash
cd backend

# Sync dependencies using uv
uv sync

# Run database migrations to create all tables
uv run alembic upgrade head

# Start FastAPI dev server (port 8000)
uv run uvicorn app.main:app --reload --port 8000
```
* Backend API: [http://localhost:8000](http://localhost:8000)
* Interactive Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 3. Start Frontend UI
Open a new terminal:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server (port 5173)
npm run dev
```
* Frontend SPA: [http://localhost:5173](http://localhost:5173)

---

### Option B: Quick Start with Docker Compose

Run all services (Redis, Backend APIs with automatic DB migrations, Worker streams, and Frontend SPA) in Docker:

```bash
docker compose up --build
```

---

## 🧪 Running Unit & Integration Tests

Run the test suite inside the `uv`-managed environment:

```bash
cd backend

# Run individual test modules
uv run pytest test_ingestion.py
uv run pytest test_notifier.py
uv run pytest test_dashboard.py
uv run pytest test_jwt_enforcement.py
uv run pytest test_sse.py

# Run all tests
uv run pytest
```

---

## 📡 Key API Routes

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/discover` | `POST` | Triggers live job search across aggregators & ranks top matches |
| `GET /api/matches` | `GET` | Returns scored job matches for the current authenticated user |
| `GET /api/matches/{id}` | `GET` | Returns match details with on-demand LLM fit rationale |
| `POST /api/gap-report` | `POST` | Generates structured skill gap report & project bridge suggestions |
| `GET /api/dashboard` | `GET` | Returns career workspace analytics and success rates |
| `GET /health` | `GET` | System health check (Redis, Database, Scheduler status) |

---

## 📁 Repository Structure

```
JobLens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entrypoint
│   │   ├── config.py             # Settings & Environment variables
│   │   ├── graphs/               # LangGraph discovery & gap analyzer pipelines
│   │   ├── models/               # Pydantic schemas & SQLAlchemy ORM models
│   │   ├── repositories/         # Unit of Work & Repository pattern
│   │   ├── routes/               # API endpoint routers
│   │   └── services/             # Scoring, ingestion, LLM router & skill ontology
│   ├── alembic/                  # Database migration scripts
│   ├── data/                     # Structured resume, postings & skill ontology
│   ├── pyproject.toml            # UV project dependency configuration
│   ├── .env.example              # Full documented environment template
│   └── .env                      # Active backend environment variables
├── frontend/
│   ├── src/                      # React 19 components, pages & API service client
│   └── package.json
├── docker-compose.yml            # Container definition for Redis & app services
├── project.md                    # System architecture design reference
└── README.md                     # Setup, setup reproduction & execution guide
```
