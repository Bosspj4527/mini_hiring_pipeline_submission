from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Candidate, StageHistory, STAGES, ACTIVE_STAGES
from .search import search_candidates

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Mini Hiring Pipeline")
templates = Jinja2Templates(directory="app/templates")

def utcnow(): return datetime.now(timezone.utc)

def normalize_dt(dt): return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

def days_in_stage(c): return max(0, (utcnow() - normalize_dt(c.stage_entered_at)).days)

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db), q: str = ""):
    candidates, error = search_candidates(db, q) if q else (db.scalars(select(Candidate)).all(), None)
    grouped = {s: [c for c in candidates if c.current_stage == s] for s in STAGES}
    return templates.TemplateResponse("index.html", {"request":request,"grouped":grouped,"stages":STAGES,"q":q,"error":error,"days_in_stage":days_in_stage})

@app.post("/candidates")
def add_candidate(name: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    if db.scalar(select(Candidate).where(Candidate.email == email.strip().lower())):
        raise HTTPException(400, "A candidate with this email already exists.")
    now=utcnow(); c=Candidate(name=name.strip(), email=email.strip().lower(), current_stage="Applied", stage_entered_at=now, created_at=now)
    db.add(c); db.flush(); db.add(StageHistory(candidate_id=c.id, from_stage=None, to_stage="Applied", changed_at=now)); db.commit()
    return RedirectResponse(f"/candidates/{c.id}", status_code=303)

@app.get("/candidates/{candidate_id}")
def candidate_detail(candidate_id: int, request: Request, db: Session = Depends(get_db)):
    c=db.get(Candidate,candidate_id)
    if not c: raise HTTPException(404,"Candidate not found")
    return templates.TemplateResponse("detail.html", {"request":request,"candidate":c,"stages":STAGES,"days_in_stage":days_in_stage})

@app.post("/candidates/{candidate_id}/advance")
def advance(candidate_id:int, db:Session=Depends(get_db)):
    c=db.get(Candidate,candidate_id)
    if not c: raise HTTPException(404,"Candidate not found")
    if c.current_stage in ("Hired","Rejected"): raise HTTPException(400,"Final outcomes cannot be changed.")
    idx=ACTIVE_STAGES.index(c.current_stage)
    next_stage=ACTIVE_STAGES[idx+1]
    now=utcnow(); old=c.current_stage; c.current_stage=next_stage; c.stage_entered_at=now
    db.add(StageHistory(candidate_id=c.id, from_stage=old, to_stage=next_stage, changed_at=now)); db.commit()
    return RedirectResponse(f"/candidates/{c.id}",status_code=303)

@app.post("/candidates/{candidate_id}/reject")
def reject(candidate_id:int, db:Session=Depends(get_db)):
    c=db.get(Candidate,candidate_id)
    if not c: raise HTTPException(404,"Candidate not found")
    if c.current_stage in ("Hired","Rejected"): raise HTTPException(400,"This candidate is already at a final outcome.")
    now=utcnow(); old=c.current_stage; c.current_stage="Rejected"; c.stage_entered_at=now
    db.add(StageHistory(candidate_id=c.id, from_stage=old, to_stage="Rejected", changed_at=now)); db.commit()
    return RedirectResponse(f"/candidates/{c.id}",status_code=303)
