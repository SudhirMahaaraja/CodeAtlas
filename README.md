# CodeAtlas — Interactive Codebase Visualizer & Doc Generator

CodeAtlas is a web application that statically analyzes a codebase (supporting Python, JavaScript, JSX, HTML, and CSS) from a uploaded ZIP file or a public GitHub repository. It generates two comprehensive markdown documents—a structured `README.md` (overview, stack, folder structure, run instructions) and a detailed `DEVELOPER.md` (cross-file import graphs, Mermaid diagrams, file references, method arguments, return types)—using parsing and rule-based heuristics. **No AI/LLM calls are made at runtime.**

---

## ✨ Features
- **Zero-LLM Engine:** Fast, deterministic, and free codebase analysis using native AST parsing.
- **Cross-File Import Resolution:** Resolves imports and renders dependency relationships dynamically using **Mermaid** diagrams.
- **AST Parsing (Python):** Gathers module docstrings, classes, methods, arguments, type hints, decorators, and function calls.
- **Regex Parsing (JS/JSX/HTML/CSS):** Identifies custom React hooks, component exports, linked resources, and selectors.
- **Premium Developer Dashboard:** A 3-pane responsive IDE workbench layout featuring:
  - Theme toggler supporting customized **Light** and **Dark** modes.
  - Interactive sidebar for ZIP uploads, public GitHub links, and localStorage-persisted recent runs.
  - Visual inspector panel detailing LOC, files count, detected framework badges, and dependency tables.
  - Markdown text rendering with dynamic Mermaid graph compilation.

---

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python 3.10+), Pydantic v2 schemas, Jinja2 templating, PyMongo
- **Frontend:** Vite, React, Lucide React icons, Marked.js (Markdown), Mermaid (Diagrams), SlotText (Tactile rolling text animations)
- **Database:** MongoDB (with an automatic in-memory fallback if no local MongoDB instance is running)

---

## 📁 Repository Structure
```text
CodeAtlas/
├── backend/
│   ├── app/
│   │   ├── api/             # Routes for analyze (/zip, /github) and jobs status
│   │   ├── core/            # Workspace management, database setups, and app configs
│   │   ├── generators/      # Jinja2 documentation template generators
│   │   ├── ingestion/       # Unzip handler and Git cloning utilities
│   │   ├── models/          # Shared Pydantic data schemas
│   │   ├── parsers/         # AST and Regex file parsing engines
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest suite verifying parsers and endpoints
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── assets/          # Static logos and icons
│   │   ├── App.jsx          # React dashboard source code
│   │   ├── index.css        # Vanilla CSS custom design system tokens
│   │   └── main.jsx         # React application entrypoint
│   ├── index.html           # Frontend entry page
│   └── package.json         # Node.js frontend dependencies
├── DEVELOPER.md             # CodeAtlas developer documentation
└── README.md                # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git (configured in system path)
- *Optional:* MongoDB running locally on `mongodb://localhost:27017`

### 1. Backend Setup & Run
1. Navigate to the root directory and activate the virtual environment:
   ```bash
   # Windows:
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run the FastAPI development server:
   ```bash
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The backend will be available at [http://localhost:8000](http://localhost:8000). The interactive API docs can be viewed at `/docs`.*

### 2. Frontend Setup & Run
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   *The frontend dashboard will be available at [http://localhost:5173](http://localhost:5173).*

---

## 🧪 Running Tests
You can run backend unit and integration tests using `pytest` from the workspace root:
```bash
.venv\Scripts\python -m pytest
```

---

*Documentation compiled automatically by CodeAtlas.*