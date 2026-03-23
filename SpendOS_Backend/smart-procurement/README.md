# 🧠 Smart Procurement & Vendor Intelligence Platform

An **AI-powered procurement intelligence system** that leverages **LangGraph** for multi-agent reasoning, **ARQ** for asynchronous task execution, and **FastAPI** for a clean service-oriented API.

---

## 🏗 Architecture

```
FastAPI (API Layer)  ←→  Service Layer (Auth/Proc)  ←→  ARQ Worker (LangGraph)
                                ↓                          ↓
                       PostgreSQL (persistence)      Redis (task queue)
```

### Core Components

1.  **Service Layer**: All business logic is encapsulated in `app/services`, isolating the API routes from data access logic.
2.  ** LangGraph Pipeline**: A deterministic workflow that orchestrates LLM nodes (Groq) for discovery, enrichment, and analysis.
3.  **ARQ Worker**: A dedicated background process that handles long-running AI tasks, ensuring high availability of the main API.

---

## 📁 Project Structure

```
smart-procurement/
├── app/
│   ├── api/               # Lightweight FastAPI routes
│   ├── services/          # Centralized business logic (AuthService, ProcurementService)
│   ├── agents/            # LangGraph workflow nodes
│   ├── models/            # SQLAlchemy Database models
│   ├── graph/             # Workflow definitions & state management
│   ├── llm/               # LLM clients & routing
│   └── worker.py          # ARQ background task definitions
├── alembic/               # Database migration scripts
├── tests/                 # Comprehensive test suite
├── scripts/               # Utility scripts (run_worker, verify_sse)
└── .env.example
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd smart-procurement
```

### 2. Install Dependencies

```bash
# For Production
pip install -r ../../requirements.txt

# For Local Development (includes pytest, formatting tooling)
pip install -r ../../requirements-dev.txt
```

### 3. Database Setup

This project automatically manages the database schema. Ensure your PostgreSQL instance is running, and the tables will be created when you start the API.

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env:
# - Set GROQ_API_KEY (from https://console.groq.com)
# - Set SERP_API_KEY (from https://serpapi.com)
# - Set DATABASE_URL (PostgreSQL for user management)
# - Set a strong SECRET_KEY
```

### 3. Start PostgreSQL

```bash
docker run -d \
  --name procurement-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=root \
  -e POSTGRES_DB=smart_procurement \
  -p 5432:5432 \
  postgres:15
```

### 4. Start API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The database tables are auto-created on startup. Visit: http://localhost:8000/docs

---

## 📡 API Endpoints

### Auth

```bash
# Register
POST /api/auth/register
{ "email": "user@co.com", "password": "secret123", "full_name": "Jane" }

# Get Token (form data)
POST /api/auth/token
username=user@co.com&password=secret123
```

### Procurement Analysis

```bash
POST /api/procurement/analyze
# Authentication is handled automatically via HttpOnly cookie.
# Ensure you have logged in and that withCredentials is enabled.

{
  "product_name": "Industrial Pressure Sensors",
  "product_category": "electronics",
  "quantity": 500,
  "budget_usd": 50000,
  "required_certifications": ["ISO 9001"],
  "delivery_deadline_days": 30,
  "scoring_weights": {
    "cost_weight": 0.35,
    "reliability_weight": 0.40,
    "risk_weight": 0.25
  }
}
```

### Other

```bash
GET  /health    # Health check
GET  /          # Service info
GET  /docs      # Swagger UI
```

---

## 📊 Scoring Model

```
Final Score = (cost_weight × cost_score)
            + (reliability_weight × reliability_score)
            − (risk_weight × risk_score)
```

- **Risk Score (0–100)**: Lower = safer. Based on financial stability, news sentiment, compliance issues.
- **Reliability Score (0–100)**: Higher = more reliable. Based on years in business, certifications, ratings, delivery performance.
- **Cost Score (0–100)**: Higher = cheaper. `100 − normalized_price_percentile`.

All weights are **configurable per request** and must sum to 1.0.

---

## 🧪 Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/test_scoring.py -v

# Integration tests
pytest tests/test_graph.py -v

# API tests
pytest tests/test_api.py -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## 🔐 Security

- JWT Bearer token authentication on protected endpoints
- Bcrypt password hashing (direct, no passlib)
- Pydantic input validation with strict schemas
- API rate limiting via `slowapi`
- Environment variable–based secrets

---

## 🔄 CI/CD

GitHub Actions pipeline in `.github/workflows/ci.yml`:

**CI** (every push):

1. Install dependencies
2. Unit tests (scoring logic)
3. Integration tests (graph workflow)
4. API tests
5. API startup verification

**CD** (merge to `main`):

1. Install dependencies
2. Start FastAPI service
3. Health check

---

## ⚙️ Configuration Reference

All configurable in `.env`:

| Variable                      | Default                | Description                            |
| ----------------------------- | ---------------------- | -------------------------------------- |
| `GROQ_API_KEY`                | required               | Groq API key                           |
| `SERP_API_KEY`                | required               | SerpAPI key for vendor search          |
| `DATABASE_URL`                | required               | PostgreSQL async URL (user management) |
| `SECRET_KEY`                  | required               | JWT signing key                        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60                     | JWT expiry                             |
| `RATE_LIMIT_PER_MINUTE`       | 30                     | API rate limit                         |
| `LLM_VENDOR_DISCOVERY`        | `llama-3.1-8b-instant` | Discovery model                        |
| `LLM_VENDOR_ENRICHMENT`       | `llama-3.1-8b-instant` | Enrichment model                       |
| `LLM_RISK_ANALYSIS`           | `llama-3.1-8b-instant` | Risk model                             |
| `LLM_RELIABILITY_ANALYSIS`    | `llama-3.1-8b-instant` | Reliability model                      |
| `LLM_EXPLANATION`             | `llama-3.1-8b-instant` | Explanation model                      |
