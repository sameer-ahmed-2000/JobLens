# JobLens 🎯

> **AI-Powered Real-Time Job Discovery & Skill Gap Analysis System**

JobLens is an intelligent career acceleration platform that aggregates job postings across multiple job boards (Greenhouse, Lever, Ashby) and live search engines (Adzuna, Jooble, Remotive, Arbeitnow). It ranks job opportunities against your precomputed resume index using a weighted multi-factor scoring formula and produces explainable skill gap reports with tailored bridge suggestions.

---

## 🛠️ Technology Stack

* **Backend**: Python 3.10+ managed with [`uv`](https://github.com/astral-sh/uv), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic V2, LangGraph
* **Database**: Local SQLite (or PostgreSQL/Supabase) + Redis 7 (Stream Queue & Caching)
* **Frontend**: React 19, TypeScript, Vite, TailwindCSS
* **AI / LLM Routing**: FreeModel.dev (OpenAI-compatible), Ollama (Local Llama 3), SentenceTransformers, FAISS

---

## 📋 Prerequisites

Before starting, ensure you have the following installed on your system:

1. **Python 3.10+** and **`uv`** (Astral's fast Python package installer):
   ```bash
   # Install uv (Windows PowerShell)
   powershell -executionpolicy bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Install uv (macOS / Linux)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Node.js** (v18+) & `npm`
3. **Docker & Docker Compose** (for running Redis)

---

## 🔑 API Keys & Configuration Guide

JobLens uses several external services. Here is how to obtain and configure all required and optional API keys.

### 1. LLM Provider (Required for Rationale & Gap Analysis)
JobLens supports multiple LLM providers via `llm_router.py`:
* **FreeModel.dev (Pre-configured Default)**:
  * Uses an OpenAI-compatible API endpoint.
  * An active free key is already included in `backend/.env`: `FREEMODEL_API_KEY=fe_oa_5eb8b36f6c825a98e3787a6d7e`
* **Local Ollama (Alternative)**:
  * Install [Ollama](https://ollama.ai) and pull Llama 3: `ollama pull llama3`
  * Set `LLM_PROVIDER=ollama` in `backend/.env`.

---

### 2. Live Job Search Aggregators

#### 🌐 **Adzuna API** (Recommended)
* **What it does**: Powers real-time, keyword-driven search across worldwide job markets.
* **How to get free keys**:
  1. Register for a free developer account at [https://developer.adzuna.com](https://developer.adzuna.com).
  2. Copy your **App ID** and **App Key** from your dashboard.
  3. Set them in `backend/.env`:
     ```env
     ADZUNA_APP_ID=your_app_id_here
     ADZUNA_APP_KEY=your_app_key_here
     ADZUNA_COUNTRY=in     # Country code: in, us, gb, ca, etc.
     ADZUNA_ENABLED=true
     ```

#### 🌐 **Jooble API** (Recommended)
* **What it does**: Aggregates job postings from LinkedIn, Indeed, ZipRecruiter, and thousands of regional job boards.
* **How to get free key**:
  1. Register for a free developer key at [https://jooble.org/api/about](https://jooble.org/api/about) (no credit card required).
  2. Set your key in `backend/.env`:
     ```env
     JOOBLE_API_KEY=your_jooble_key_here
     JOOBLE_ENABLED=true
     ```

#### 🌐 **Remotive & Arbeitnow**
* **What they do**: Provide remote tech and startup job feeds.
* **API Key required?**: **No!** Both services provide open public APIs. They are enabled out of the box (`REMOTIVE_ENABLED=true`, `ARBEITNOW_ENABLED=true`).

---

### 3. Direct ATS Connectors (Greenhouse, Lever, Ashby)
* **API Key required?**: **No!** JobLens directly parses public board feeds (e.g. Anthropic, Stripe, Netflix, Vercel, Linear) defined in `data/job_sources.json`.

---

## 🚀 Local Execution Guide

### Step 1: Environment Setup

1. **Root Environment File** (used by Docker Compose):
   Create a `.env` file in the root directory:
   ```env
   REDIS_PASSWORD=334ffewdsd
   ```

2. **Backend Environment File**:
   Create or verify `backend/.env`:
   ```env
   # FastAPI Configuration
   HOST=0.0.0.0
   PORT=8000
   ENVIRONMENT=development

   # Database Configuration (Local SQLite)
   DATABASE_URL=sqlite:///./joblens.db

   # LLM Configuration
   LLM_PROVIDER=freemodel
   FREEMODEL_API_KEY=fe_oa_510612b45665b370d3a2c35eb8b36f6c825a98e3787a6d7e
   FREEMODEL_BASE_URL=https://api.freemodel.dev/v1
   FREEMODEL_MODEL=auto

   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=334ffewdsd

   # Aggregators
   ADZUNA_APP_ID=your_adzuna_app_id
   ADZUNA_APP_KEY=your_adzuna_app_key
   ADZUNA_COUNTRY=in
   ADZUNA_ENABLED=true

   JOOBLE_API_KEY=your_jooble_key
   JOOBLE_ENABLED=true

   REMOTIVE_ENABLED=true
   ARBEITNOW_ENABLED=true
   ```

---

### Step 2: Start Redis

Start the Redis 7 container using Docker Compose:
```bash
docker-compose up -d
```
*To verify Redis is running:*
```bash
docker ps
```

---

### Step 3: Setup & Start the Backend

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Lock and install all dependencies into `.venv` using `uv`:
   ```bash
   uv sync
   ```
3. Run Alembic database migrations to create local SQLite tables:
   ```bash
   uv run alembic upgrade head
   ```
4. Start the FastAPI development server:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```
*Backend API will be available at [http://localhost:8000](http://localhost:8000).*  
*Interactive Swagger API Docs available at [http://localhost:8000/docs](http://localhost:8000/docs).*

---

### Step 4: Setup & Start the Frontend

1. Open a new terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
*Frontend application will be accessible at [http://localhost:5173](http://localhost:5173).*

---

## 🧪 Running Unit Tests

Run unit tests inside the `uv`-managed environment:

```bash
cd backend

# Run individual test suites
uv run pytest test_ingestion.py
uv run pytest test_notifier.py
uv run pytest test_dashboard.py
uv run pytest test_sse.py
```

---

## 📡 Key API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/discover` | `POST` | Triggers live search against aggregators & ranks top matches |
| `GET /api/matches` | `GET` | Returns scored job matches for the current user |
| `POST /api/gap-report` | `POST` | Generates a structured skill gap report for a job posting |
| `GET /api/dashboard` | `GET` | Returns career workspace analytics and success rates |
| `GET /health` | `GET` | System health check (Redis, scheduler, DB status) |

---

## 📁 Repository Structure

```
JobLens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entrypoint
│   │   ├── config.py             # Environment configuration & Settings
│   │   ├── graphs/               # LangGraph state graph definitions
│   │   ├── models/               # Pydantic schemas & SQLAlchemy ORM models
│   │   ├── repositories/         # Unit of Work & Repository pattern
│   │   ├── routes/               # API endpoint routers
│   │   └── services/             # Ingestion connectors, scoring, LLM router
│   ├── alembic/                  # Database migration scripts
│   ├── data/                     # Resume JSON, job sources & skill ontology
│   ├── pyproject.toml            # UV project dependency configuration
│   └── .env                      # Active backend environment variables
├── frontend/
│   ├── src/                      # React components, pages & API services
│   └── package.json
├── docker-compose.yml            # Redis 7 service definition
├── project.md                    # Project context & architecture reference
└── README.md                     # Local setup & operational guide
```
