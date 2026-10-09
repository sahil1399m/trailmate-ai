# 🥾 TrailMate AI

> **AI-powered outdoor adventure planner** — built for the [Hacktoberfest Open-Source AI Challenge](https://hacktoberfest.com/) · Week 1: *Touch Grass* 🌿

TrailMate AI takes your available time, preferred activity, intensity level, budget, and location and generates a personalised outdoor mission — all powered by a local open-weight LLM running entirely on your machine with no cloud APIs required.

---

## ✨ Features (Planned)

| Feature | Status |
|---|---|
| FastAPI backend skeleton | ✅ Week 1 |
| Local LLM integration (SmolLM2 via llama.cpp) | 🔜 Week 2 |
| Outdoor plan generation | 🔜 Week 2 |
| Web frontend | 🔜 Week 3 |
| Location / weather enrichment | 🔜 Week 4 |

---

## 🛠 Tech Stack

- **Backend** — [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **LLM runtime** — [llama.cpp](https://github.com/ggerganov/llama.cpp) (local, no cloud)
- **Model** — SmolLM2 1.7B Instruct Q4_K_M (GGUF)
- **Config** — [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- `llama-cli` available on your PATH (llama.cpp installed)
- Model file at `models/smollm2-1.7b-instruct-q4_k_m.gguf`

### 1 · Clone & enter the project

```bash
git clone <repo-url>
cd trailmate-ai
```

### 2 · Create & activate virtual environment

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 3 · Install dependencies

```bash
pip install -r requirements.txt
```

### 4 · Start the backend server

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5 · Verify the health endpoint

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

Interactive API docs are available at **http://localhost:8000/docs**.

---

## 📁 Project Structure

```
trailmate-ai/
├── backend/
│   └── app/
│       ├── __init__.py       # App package
│       ├── main.py           # FastAPI app & routes
│       ├── config.py         # Settings via pydantic-settings
│       └── services/
│           └── __init__.py   # Services package (AI logic goes here)
├── models/                   # GGUF model weights (git-ignored)
├── .env.example              # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

This project is open-source and welcomes Hacktoberfest contributions!  
Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a PR.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
