# Contributing to SpendOS

First off, thank you for considering contributing to SpendOS! We welcome contributions to both the FastAPI backend and the React frontend.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone the repository** to your local machine: `git clone <your-fork-url>`
3. **Set up the backend**
   ```bash
   cd SpendOS_Backend/smart-procurement
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r ../../requirements-dev.txt
   alembic upgrade head
   ```
4. **Set up the frontend**
   ```bash
   cd SpendOS_Frontend
   npm install
   ```

## Development Workflow

1. **Create a new branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes**
3. **Run tests**
   - Backend: `pytest`
   - Frontend: `npm run test`
4. **Format and lint your code**
   - Ensure you use `ruff`/`black` for Python and `eslint` for JavaScript.
5. **Commit your changes**: `git commit -m "Add descriptive message"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Submit a Pull Request** using our provided template.

## Code Standards

- We strongly enforce types via Pydantic on the backend.
- We enforce strong Prop validation (or TypeScript when applicable) on the frontend.
- New features MUST be accompanied by corresponding test coverage.
