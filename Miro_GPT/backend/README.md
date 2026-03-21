# Mini MiroFish Backend

## Run

```powershell
uv sync
uv run python -m backend
```

The API starts on `http://127.0.0.1:5001`.

## Notes

- Tasks are persisted in `backend/data/app.db`.
- Project artifacts are stored in `backend/data/projects`.
- `LLM_API_KEY` is required for ontology, simulation, and report generation.
- `ZEP_API_KEY` is required for graph build and graph-backed research.
