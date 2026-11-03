# Software Engineer Job Aggregator

A learning project that collects software-development vacancies from permitted job APIs, stores normalized records in PostgreSQL, de-duplicates records per source, and displays them in a FastAPI/Jinja dashboard.

## Features

- FastAPI dashboard and JSON endpoint (`/api/jobs`)
- PostgreSQL via SQLAlchemy 2
- Remotive, Arbeitnow, TopJobs public vacancy listings, and optional Adzuna API adapter
- Search by title/company/description, location, and source
- Duplicate protection using a database unique constraint on `(source, external_id)`
- Manual source sync from the dashboard
- Basic tests and Docker Compose for PostgreSQL

## Requirements

- Python 3.11+
- Docker Desktop (or a local PostgreSQL 16+ server)
- Internet access for enabled source APIs

## Run locally (Windows PowerShell)

```powershell
cd software_job_aggregator
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Click **Sync sources** to fetch listings.
Docker Compose exposes PostgreSQL on host port `5434` to avoid conflicts with other PostgreSQL servers on the default port `5432`.

Linux/macOS virtual environment activation:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d db
uvicorn app.main:app --reload
```

## Optional Adzuna source

Create an application at https://developer.adzuna.com/ and add your credentials to `.env`:

```dotenv
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
ADZUNA_COUNTRY=gb
```

Restart the application. Adzuna's supported country coverage and API access depend on its current offering. The example defaults to Great Britain; it does not guarantee Sri Lankan listings. Review Adzuna's API terms and any attribution/licensing obligations before publishing the dashboard or using the API commercially.

## API and dashboard

- `GET /` — dashboard
- `POST /sync` — fetch selected providers and upsert records
- `GET /api/jobs?q=python&location=remote&source=Remotive&page=1` — JSON listings
- `GET /health` — process health check

## Sources and limits

1. **Remotive** — `https://remotive.com/api/remote-jobs`. Public remote-work API. Remotive says listings are delayed by 24 hours, advises no more than four fetches per day, and requires mentioning Remotive and linking to the original listing. Its terms restrict some redistribution contexts; review the live terms before deployment.
2. **Arbeitnow** — `https://www.arbeitnow.com/api/job-board-api`. The adapter uses the publicly documented job-board endpoint. Arbeitnow's terms require a backlink and reserve the right to revoke API permission. Verify the current API documentation and terms before production use.
3. **Adzuna** — authenticated API; requires app ID/key. Country coverage varies. Follow current Adzuna API terms, display/attribution requirements, rate limits, and licensing restrictions.
4. **TopJobs** — reads software-related vacancy metadata (title, employer, location, and listing date) from the public [Software Development listings](https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ). Each result links to its original TopJobs vacancy; descriptions are not copied. Check TopJobs' current terms before deploying or increasing sync frequency.

This project uses public APIs and the TopJobs public vacancy listing; it does not bypass website protections. It does not guarantee complete coverage of Sri Lankan, international, or remote jobs. A source may be unavailable, omit a country, change its schema, remove expired listings, or require an agreement. “International” does not mean every job is open to applicants in every country. Always check the original posting and work-authorization requirements.

## De-duplication

Each provider supplies an external ID or URL. PostgreSQL enforces uniqueness for `(source, external_id)` and the sync uses an upsert. The same job may still appear twice if two providers list it with different IDs. Cross-provider matching can be added using normalized title/company/location fingerprints, but should not delete records automatically without review.

## Run tests

```bash
pytest -q
```

## Production notes

- Do not commit `.env` or API keys.
- Add authentication and CSRF protection before exposing `/sync` publicly.
- Add rate limiting, structured logs, provider-specific retries, pagination, scheduled sync, database migrations (Alembic), and monitoring before production.
- Use a background worker for sync instead of keeping a browser request open.
- Add provider attribution exactly as each source requires.
