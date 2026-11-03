from datetime import datetime, timezone
from sqlalchemy import select, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.models import Job
from app.collectors import COLLECTORS

def sync_jobs(db: Session, selected_sources=None):
    """Fetch selected APIs and upsert rows. A unique source/id constraint prevents duplicates."""
    selected_sources = selected_sources or list(COLLECTORS.keys())
    report = {}
    for source_name in selected_sources:
        collector = COLLECTORS.get(source_name)
        if not collector:
            report[source_name] = {"saved": 0, "error": "Unknown source"}
            continue
        try:
            records = collector()
            saved = 0
            for record in records:
                stmt = insert(Job).values(**record, collected_at=datetime.now(timezone.utc))
                update_fields = {
                    key: stmt.excluded[key]
                    for key in (
                        "title", "company", "location", "job_type", "category",
                        "description", "apply_url", "published_at", "collected_at"
                    )
                }
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_job_source_external_id",
                    set_=update_fields,
                )
                db.execute(stmt)
                saved += 1
            db.commit()
            report[source_name] = {"saved": saved, "error": None}
        except Exception as exc:
            db.rollback()
            # Do not expose credentials or raw provider response to the browser.
            report[source_name] = {"saved": 0, "error": f"{type(exc).__name__}: source unavailable"}
    return report

def search_jobs(db: Session, q=None, location=None, source=None, page=1, page_size=25):
    stmt = select(Job)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(Job.title.ilike(term), Job.company.ilike(term), Job.description.ilike(term)))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location.strip()}%"))
    if source:
        stmt = stmt.where(Job.source == source)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    jobs = db.scalars(
        stmt.order_by(Job.published_at.desc().nullslast(), Job.collected_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return jobs, total
