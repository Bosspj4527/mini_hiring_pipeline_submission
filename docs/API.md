# Route Summary

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Pipeline board and search |
| POST | `/candidates` | Add candidate |
| GET | `/candidates/{id}` | Candidate detail + history |
| POST | `/candidates/{id}/advance` | Move exactly one stage forward |
| POST | `/candidates/{id}/reject` | Reject before Hired |
