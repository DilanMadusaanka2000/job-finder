from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base, engine, get_db
from app.services import search_jobs, sync_jobs
from app.collectors import COLLECTORS

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str | None = Query(default=None, max_length=150),
    location: str | None = Query(default=None, max_length=150),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    page_size = 25
    jobs, total = search_jobs(db, q=q, location=location, source=source, page=page, page_size=page_size)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request, "jobs": jobs, "q": q or "", "location": location or "",
            "source": source or "", "sources": ["Remotive", "Arbeitnow", "Adzuna", "TopJobs"],
            "page": page, "total": total, "pages": max(1, (total + page_size - 1) // page_size),
        },
    )

@app.post("/sync")
def sync(
    sources: list[str] = Form(default=["remotive", "arbeitnow", "adzuna"]),
    db: Session = Depends(get_db),
):
    sync_jobs(db, sources)
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/jobs")
def api_jobs(
    q: str | None = None,
    location: str | None = None,
    source: str | None = None,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    jobs, total = search_jobs(db, q=q, location=location, source=source, page=page)
    return {
        "total": total,
        "page": page,
        "jobs": [{
            "id": job.id, "source": job.source, "title": job.title,
            "company": job.company, "location": job.location, "job_type": job.job_type,
            "apply_url": job.apply_url, "published_at": job.published_at,
        } for job in jobs],
    }

@app.get("/health")
def health():
    return {"status": "ok", "sources": list(COLLECTORS.keys())}
