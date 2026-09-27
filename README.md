# Mini Hiring Pipeline

A small recruiter-facing web app for managing one job's candidate pipeline.

## Features
- Candidate creation starts at **Applied**.
- Forward movement is exactly one stage at a time: Applied → Screening → Interview → Offer → Hired.
- Rejection is allowed before Hired and is terminal.
- Final outcomes cannot be reversed.
- Candidate detail page shows full, append-only stage history and time in current stage.
- Natural-language search supports candidate names (including typo-tolerant matching), stage filters, time-in-stage filters, "since Monday" movement, offer-not-hired, and excluding rejected candidates.
- Search errors explain what the parser understood and what is missing.

## Architecture
- **FastAPI**: HTTP routes and form handling.
- **SQLAlchemy + SQLite**: persistence and relationships.
- **Jinja2**: server-rendered HTML for a small, dependency-light UI.
- **Search parser**: deterministic intent extraction in `app/search.py`; candidate name ranking uses Python's standard-library `difflib`.
- **Audit model**: `StageHistory` stores every transition. The model rejects updates/deletes at the ORM event layer, and application routes never expose edit/delete operations for history.

### Data model
`Candidate(id, name, email, current_stage, stage_entered_at, created_at)`

`StageHistory(id, candidate_id, from_stage, to_stage, changed_at)`

One candidate has many history records. A new history record is written in the same transaction as each stage change.

## Why these decisions
1. **Server-rendered UI** keeps the app small and easy to run for a take-home exercise.
2. **SQLite** avoids requiring a separate database service.
3. **Deterministic search** is easier to test and explain than an LLM-driven query layer.
4. **Standard-library fuzzy matching** avoids an extra fuzzy-search dependency while still handling common typos such as `sharam` → `Sharma`.
5. **Append-only history** makes the audit trail explicit rather than reconstructing history from mutable candidate state.

## Run locally
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000`.

## Example searches
- `Find Priya Sharam`
- `Who's in Interview right now?`
- `Screening more than a week`
- `Who moved to Interview since Monday?`
- `Who reached the Offer stage but didn't get hired?`
- `Everyone except rejected`

Filters can be combined, for example: `Priya in Interview` or `Sharam Interview since Monday`.

## Testing
```bash
pytest
```

## AI-assisted development log
See `docs/AI_CHAT_LOG.md`. It records the prompts/decisions used while designing the assignment and one explicit disagreement with an AI suggestion.

## What I would do with more time
- Add authentication and recruiter accounts.
- Add CSRF protection and production security headers.
- Add PostgreSQL for deployment and database-level append-only audit guarantees.
- Add richer date parsing (specific dates, relative ranges, timezone-aware interpretation).
- Add pagination and database indexes for larger candidate sets.
- Expand the search grammar and expose parsed filters in the UI.
- Add API endpoints and a stronger automated integration-test suite.
- Add deployment configuration and observability.
