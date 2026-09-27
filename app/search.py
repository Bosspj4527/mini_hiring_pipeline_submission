import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher, get_close_matches
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from .models import Candidate, StageHistory, STAGES

STAGE_ALIASES = {"applied":"Applied", "screening":"Screening", "screen":"Screening", "interview":"Interview", "offer":"Offer", "hired":"Hired", "rejected":"Rejected", "reject":"Rejected"}
STOP = {"find","show","me","who","is","are","in","right","now","has","been","stuck","for","more","than","a","week","weeks","days","day","moved","to","since","on","everyone","except","candidates","candidate","reached","stage","but","didn't","didnt","get","all","that","have","had","the","current","everyone","except","reached","right"}

def _norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()

def parse_query(q: str):
    raw = q.strip()
    if not raw: return {"error":"Type a search, for example: 'Priya Sharma' or 'in Interview'."}
    n = _norm(raw)
    stage = None
    for key, value in STAGE_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", n): stage = value; break
    exclude_rejected = bool(re.search(r"\b(except|excluding|without)\b.*\breject", n)) or "everyone except rejected" in n
    offer_not_hired = bool(re.search(r"offer.*(didn.?t|get|not).*(hired|hire)", n)) or "reached offer" in n and "hired" in n
    since = None
    if "since monday" in n:
        now = datetime.now(timezone.utc); days_since_monday = now.weekday(); since = (now - timedelta(days=days_since_monday)).replace(hour=0,minute=0,second=0,microsecond=0)
    m = re.search(r"since\s+(\d+)\s+days?", n)
    if m: since = datetime.now(timezone.utc) - timedelta(days=int(m.group(1)))
    stuck_days = None
    m = re.search(r"more than\s+(\d+)\s+days?", n)
    if m: stuck_days = int(m.group(1))
    elif "more than a week" in n or "over a week" in n: stuck_days = 7
    tokens = [t for t in n.split() if t not in STOP and t not in STAGE_ALIASES and not t.isdigit()]
    name_query = " ".join(tokens).strip()
    # Remove residual date/time words from name query.
    name_query = re.sub(r"\b(since|monday|week|weeks|days|day|more|than)\b", " ", name_query).strip()
    return {"raw":raw,"stage":stage,"exclude_rejected":exclude_rejected,"offer_not_hired":offer_not_hired,"since":since,"stuck_days":stuck_days,"name_query":name_query}

def _name_score(query, name):
    if not query: return 0.0
    q = query.lower(); n = name.lower()
    if q in n: return 1.0
    parts = q.split(); name_parts=n.split()
    best = max((SequenceMatcher(None, p, np).ratio() for p in parts for np in name_parts), default=0)
    whole = SequenceMatcher(None,q,n).ratio()
    return max(best, whole)

def search_candidates(db: Session, q: str):
    parsed = parse_query(q)
    if parsed.get("error"): return [], parsed["error"]
    candidates = db.scalars(select(Candidate)).all()
    if parsed["stage"]: candidates = [c for c in candidates if c.current_stage == parsed["stage"]]
    if parsed["exclude_rejected"]: candidates = [c for c in candidates if c.current_stage != "Rejected"]
    if parsed["offer_not_hired"]:
        candidates = [c for c in candidates if c.current_stage != "Hired" and any(h.to_stage == "Offer" for h in c.history)]
    if parsed["since"]:
        candidates = [c for c in candidates if any(h.to_stage == (parsed["stage"] or c.current_stage) and h.changed_at >= parsed["since"] for h in c.history)]
    if parsed["stuck_days"] is not None:
        if not parsed["stage"]:
            return [], "I understood the time filter, but not which stage you mean. Try: 'Screening more than a week'."
        cutoff = datetime.now(timezone.utc) - timedelta(days=parsed["stuck_days"])
        candidates = [c for c in candidates if c.current_stage == parsed["stage"] and c.stage_entered_at <= cutoff]
    if parsed["name_query"]:
        scored=[(c,_name_score(parsed["name_query"],c.name)) for c in candidates]
        if not scored:
            return [], f"No candidates match the other filters. I understood the name as '{parsed['name_query']}'."
        if max(s for _,s in scored) < 0.55 and not parsed["stage"] and not parsed["since"] and not parsed["stuck_days"] and not parsed["offer_not_hired"] and not parsed["exclude_rejected"]:
            suggestions = get_close_matches(parsed["name_query"], [c.name for c in db.scalars(select(Candidate)).all()], n=3, cutoff=0.45)
            hint = ", ".join(suggestions) if suggestions else "Try a candidate name or a stage such as Interview."
            return [], f"I couldn't make sense of '{parsed['name_query']}'. Did you mean: {hint}?"
        candidates = [c for c, _score in sorted(scored, key=lambda x:x[1], reverse=True)]
    else:
        candidates = sorted(candidates, key=lambda c: (c.current_stage != parsed.get("stage"), c.name.lower()))
    return candidates, None
