<div align="center">
  <img src="SpendOS_Frontend/public/logo.png" alt="SpendOS Logo" width="150" height="150" style="border-radius: 50%" />
  
  # SpendOS
  
  **A modern, intelligent procurement platform powered by AI-driven insights and real-time analytics.**
  
  [![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
  [![Vite](https://img.shields.io/badge/Vite-7.3-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
  [![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

</div>

<br/>

## 📋 Table of Contents

- [Overview](#-overview)
- [Tech Stack](#-tech-stack)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation setup](#-installation-setup)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Development & Contributing](#-development--contributing)
- [Troubleshooting](#-troubleshooting)
- [License & Support](#-license--support)

---

## 🔎 Overview

**SpendOS** is an AI-powered smart procurement platform designed to modernize and automate the supply chain vetting process. By combining low-latency LLM inference (powered by **Groq**) with complex verification workflows (**LangGraph/LangChain**), it generates dynamic executive summaries, structured vendor metrics, and critical supply chain risk analyses.

Whether you are seeking robust cost optimization or a complete audit trail of potential vendors, SpendOS delivers real-time analytics through a visually stunning, glassmorphism-styled React dashboard.

---

## 🛠 Tech Stack

### Backend

- **Framework:** FastAPI
- **Workflow Orchestration:** LangGraph & LangChain
- **AI/LLM Provider:** Groq
- **Database (Auth):** SQLAlchemy with PostgreSQL/SQLite support
- **Testing:** `pytest`, `pytest-asyncio`
- **Language:** Python 3.9+

### Frontend

- **Framework:** React 19 (via Vite)
- **Styling:** Tailwind CSS (Modern, Responsive, Glassmorphism UI)
- **Routing:** React Router v7
- **HTTP Client:** Axios
- **Linting:** ESLint & PostCSS

---

## ✨ Key Features

1. **Intelligent Procurement Automation:** Leverages AI/ML (LangGraph flows) to automatically analyze, score, and rank vendors.
2. **Real-time Analytics Dashboard:** Dynamic interface for visualizing supplier metrics, costs, and project risks.
3. **Supplier Management System:** Keep track of extensive vendor information seamlessly over time.
4. **Cost Optimization Capabilities:** Compare bids and uncover hidden cost anomalies using analytical reasoning.
5. **Complete Audit Trail:** Traceable interactions for all LLM-driven decisions and state transitions.
6. **RESTful API:** Completely documented backend services out-of-the-box (powered by Swagger UI/Redoc).
7. **Responsive UI:** State-of-the-art frontend ready to adapt across mobile, tablet, and desktop interfaces.

---

## 📂 Project Structure

This repository operates as a monorepo containing both the FastAPI Backend and the React Frontend.

```text
SpendOS/
├── .github/                 # GitHub workflows (CI/CD)
├── .gitignore               # Global git exclusions
├── README.md                # This project documentation
├── requirements.txt         # Root-level Python dependencies
├── venv/                    # Python virtual environment (ignored from repo)
│
├── SpendOS_Backend/         # FastAPI Backend Application
│   └── smart-procurement/
│       ├── app/             # Main application codebase (API, Agents, DB)
│       ├── tests/           # Dedicated pytest test suite
│       ├── .env.example     # Template for backend environment variables
│       ├── pyproject.toml   # Python project settings (pytest config, etc.)
│       └── README.md        # Detailed backend documentation
│
└── SpendOS_Frontend/        # React + Vite Frontend Client
    ├── public/              # Static external assets (e.g. logo)
    ├── src/                 # Main frontend source code (components, styles)
    ├── .env.example         # Template for frontend environment variables
    ├── eslint.config.js     # Global ESLint configuration
    ├── package.json         # NPM dependencies and scripts
    ├── tailwind.config.js   # Tailwind style customization
    ├── vite.config.js       # Vite build configurations
    └── README.md            # Detailed frontend documentation
```

---

## 🔧 Prerequisites

Before starting, ensure your operating system has the following installed:

- **Python 3.9+**: For the backend environment.
- **Node.js 18+ & NPM**: For frontend dependency management and the Vite server.
- **Git**: For version control.
- _(Optional)_ **Docker**: If you intend to containerize the database or services later.

---

## 🚀 Installation setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/SpendOS.git
cd SpendOS
```

### 2. Backend Setup

Create an isolated virtual environment and install dependencies.

**Unix/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> [!NOTE]
> No manual migrations are needed. Tables are auto-created when the backend starts.

### 3. Frontend Setup

Install the Node modules for the React client.

**All platforms:**

```bash
cd SpendOS_Frontend
npm install
```

---

## ⚙️ Configuration

Environment variables drive different configurations for both applications. Reference the `.env.example` file in the respective directories.

### Backend Configurations

Create a `.env` file inside `SpendOS_Backend/smart-procurement/`:

```env
# Required AI integration key
GROQ_API_KEY=your_actual_api_key_here

# Required for Google Search Tools/Agens
SERPAPI_API_KEY=your_actual_serp_key

# Database url (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/smart_procurement
```

### Frontend Configurations

Create a `.env` file inside `SpendOS_Frontend/`:

```env
# Point the frontend to the development backend
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 🏃 Running the Application

To run SpendOS locally, you should keep two separate terminal tabs open.

### Start the Backend (Terminal 1)

> [!TIP]
> Ensure your virtual environment is activated before running the backend.

**Unix/macOS:**

```bash
source venv/bin/activate
cd SpendOS_Backend/smart-procurement
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
cd SpendOS_Backend/smart-procurement
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start the Frontend (Terminal 2)

**All platforms:**

```bash
cd SpendOS_Frontend
npm run dev
```

The frontend will start a local preview, typically accessible at: **[http://localhost:5173](http://localhost:5173)**

---

## 📖 API Documentation

The RESTful API is powered by FastAPI, meaning OpenAPI specs are generated automatically.

Once the backend is running, you can interact directly with the Swagger UI documentation:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

| Example Core Endpoints     | Method | Description                                           |
| -------------------------- | ------ | ----------------------------------------------------- |
| `/api/auth/token`          | `POST` | Exchanges credentials for a JWT (via HTTPOnly cookie) |
| `/api/procurement/analyze` | `POST` | Kicks off the AI vendor search/evaluation graph       |

---

## 💻 Development & Contributing

### Code Quality

SpendOS emphasizes rigorous code quality via linting and unit testing.

- **Frontend Linting**: Pre-configured via ESLint and Prettier.
  ```bash
  npm run lint
  ```
- **Backend Testing**: Pytest handles API coverage. Ensure your `venv` is activated.
  ```bash
  cd SpendOS_Backend/smart-procurement
  pytest tests/ -v
  ```

### Contributing Workflow

1. **Fork the repository** on GitHub.
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Commit changes:** `git commit -m 'Add amazing feature'`
4. **Push the branch:** `git push origin feature/amazing-feature`
5. **Open a Pull Request** summarizing your architecture implementations.

> [!IMPORTANT]
> All Pull Requests require passing status checks (frontend linting and backend pytests) before they can be successfully merged into `main`.

---

## 🔧 Troubleshooting

| Issue                                           | Potential Cause                              | Solution                                                                                                                             |
| :---------------------------------------------- | :------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| **Port 8000 occupied**                          | Another service/container is running on 8000 | Kill the existing process (`kill -9 $(lsof -t -i:8000)` on Unix, or `Stop-Process` on Windows), or start the app with `--port 8001`. |
| **"groq_client.py" missing key**                | Missing `.env` variables                     | Ensure that a root-level `.env` with a valid `GROQ_API_KEY` exists inside `SpendOS_Backend/smart-procurement/`                       |
| **React API calls return `Network Error`**      | CORS issues or Vite base URL mismatch        | Verify you’re using the proxy setup or `.env` specifically contains `VITE_API_BASE_URL=http://localhost:8000/api`                    |
| **`npm install` fails with native deps errors** | Old version of Node                          | Ensure you are on Node 18+. Use `nvm` to upgrade.                                                                                    |

---

## 📄 License & Support

This project is licensed under the MIT License - see the LICENSE file for details.

**Support**  
If you run into issues, please [open an issue](https://github.com/your-username/SpendOS/issues) in this repository. For direct contact, you may reach out to the open-source maintenance team at `support@example.com`.
