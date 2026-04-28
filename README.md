<div align="center">
  <img src="SpendOS_Frontend/public/logo.png" alt="SpendOS Logo" width="150" height="150" style="border-radius: 50%" />
  
  # SpendOS
  
  **A high-performance, AI-native procurement platform for intelligent vendor discovery and risk analysis.**
  
  [![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
  [![Throughput](https://img.shields.io/badge/Capacity-94k_TPM-blueviolet?style=for-the-badge)](https://groq.com/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

</div>

---

## 🚀 Overview

**SpendOS** is a next-generation procurement engine designed to automate the heavy lifting of supplier vetting. By leveraging a high-throughput **multi-model LLM strategy (94,000 TPM)** and **LangGraph** orchestration, it transforms raw web search results into structured, risk-scored, and ranked vendor portfolios in seconds.

### Why SpendOS?
- **Extreme Speed**: Powered by Groq-accelerated inference and **parallel LangGraph nodes**, achieving a 5x workflow speedup.
- **Deep Insights**: Beyond basic search, it performs multi-dimensional risk and reliability scoring.
- **Production Grade**: Built with an asynchronous task queue (ARQ), robust sanitization, centralized prompt management, and enterprise-level auth logic.

---

## 🏗 Architecture

SpendOS follows a decoupled **Service-Worker architecture**:

1.  **FastAPI Web Server**: Handles authentication, session management, and task entry.
2.  **ARQ Background Worker**: Executes long-running LangGraph AI pipelines outside the request cycle.
3.  **LangGraph Orchestrator**: Manages state across 5 specialized AI nodes:
    - *Vendor Discovery (SerpAPI)*
    - *Data Enrichment*
    - *Risk Analysis (Parallel)*
    - *Reliability Scoring (Parallel)*
    - *Final Recommendation*
4.  **React 19 Frontend**: Real-time progress tracking via Server-Sent Events (SSE).

> [!NOTE]
> For a deep dive into the system design, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 🛠 Tech Stack

- **Backend**: FastAPI, LangGraph, SQLAlchemy 2.0 (Async), ARQ.
- **Frontend**: React 19, Vite, Tailwind-ready Vanilla CSS.
- **Infrastructure**: Redis (Broker), PostgreSQL (Storage), SerpAPI (Search).
- **Inference**: Groq (Llama 3.3, Qwen 32B, Llama 3.1).

---

## 🚦 Getting Started

### Prerequisites
- Python 3.10+ & Node.js 18+
- PostgreSQL & Redis (Local or Docker)
- API Keys: [Groq](https://console.groq.com/), [SerpAPI](https://serpapi.com/)

### 1. Backend Setup
```bash
cd SpendOS_Backend/smart-procurement
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r ../../requirements.txt
cp .env.example .env  # Add your API keys here
```

### 2. Frontend Setup
```bash
cd SpendOS_Frontend
npm install
npm run dev
```

### 3. Run with Docker (Recommended)
```bash
docker-compose up --build
```

---

## ⚙️ Configuration

Key environment variables required in `SpendOS_Backend/smart-procurement/.env`:

| Variable | Description |
| :--- | :--- |
| `GROQ_API_KEY` | High-speed LLM inference key. |
| `SERP_API_KEY` | Web search tool key for vendor discovery. |
| `SECRET_KEY` | Secure string for JWT/CSRF signing. |
| `DATABASE_URL` | Asyncpg connection string for PostgreSQL (e.g. Neon). |
| `REDIS_URL` | Redis DSN for task queue and pub/sub. |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins (optional — has defaults). |

---

## 📖 API & Documentation

Once the app is running, access the interactive docs at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

See [API.md](./API.md) for detailed payload examples.

---

## ☁️ Deployment

SpendOS is production-ready on **Render** (backend) + **Vercel** (frontend) + **Neon** (PostgreSQL).

> For the full step-by-step deployment guide, see **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

### Quick Start (Render Blueprint)
1. Link your repo to Render.
2. It will automatically detect `render.yaml`.
3. Fill in your Secrets and click **Apply**.
4. Run `alembic upgrade head` from Render's Shell tab.

---

## 🔒 Security

SpendOS implements enterprise-grade security including:
- **JWT authentication** with HttpOnly cookies and CSRF double-submit protection
- **Rate limiting** (30 req/min per user) via SlowAPI
- **Security headers** (HSTS, X-Frame-Options, X-XSS-Protection, etc.)
- **Password hashing** with bcrypt + salt
- **User-scoped authorization** on all data queries

For details, see the Security Architecture section in [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 📄 License
This project is licensed under the MIT License.

