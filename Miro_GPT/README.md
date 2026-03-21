# Miro_GPT

Mini MiroFish built locally in `Miro_GPT`, with a new codebase and a simpler architecture:

- `backend/`: Flask API, SQLite tasks, project artifacts, Zep graph integration, simulation engine, subagents
- `frontend/`: Vue 3 wizard for upload, graph, simulation, and report

## Local run

Backend:

```powershell
cd backend
Copy-Item .env.example .env
uv sync
uv run python -m backend
```

Frontend:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

## Required keys

- `LLM_API_KEY`: ontology generation, simulation rounds, report writer/critic
- `ZEP_API_KEY`: graph creation, graph search, research brief generation

## Verified commands

```powershell
cd backend
uv run pytest
uv run python -m compileall src
uv run python -c "from backend import create_app; app=create_app(); print(app.url_map)"

cd ..\frontend
npm run build
```
