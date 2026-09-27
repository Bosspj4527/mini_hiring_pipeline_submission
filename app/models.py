from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, event, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

STAGES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected"]
ACTIVE_STAGES = STAGES[:5]

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    current_stage: Mapped[str] = mapped_column(String(30), index=True)
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    history: Mapped[list["StageHistory"]] = relationship(back_populates="candidate", order_by="StageHistory.changed_at", cascade="all, delete-orphan")

class StageHistory(Base):
    __tablename__ = "stage_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    from_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(30))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    candidate: Mapped[Candidate] = relationship(back_populates="history")

@event.listens_for(StageHistory, "before_update")
def prevent_history_update(mapper, connection, target):
    raise ValueError("Audit history is immutable and cannot be updated.")

@event.listens_for(StageHistory, "before_delete")
def prevent_history_delete(mapper, connection, target):
    raise ValueError("Audit history is immutable and cannot be deleted.")
