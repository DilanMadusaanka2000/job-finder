"""Permitted API adapters. All adapters normalize records to the same shape."""
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import re
import requests
from urllib.parse import urlencode
from app.config import settings

SOFTWARE_TERMS = (
    "software engineer", "software developer", "developer", "programmer",
    "backend", "back-end", "frontend", "front-end", "full stack", "full-stack",
    "python", ".net", "java", "flutter", "devops", "qa engineer", "test engineer",
    "mobile engineer", "web engineer", "data engineer", "engineering manager",
)

def _clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return unescape(re.sub(r"\s+", " ", value)).strip()

def _date(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def _is_software_job(title: str, description: str = "") -> bool:
    haystack = f"{title} {description}".lower()
    return any(term in haystack for term in SOFTWARE_TERMS)

class _TopJobsListingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.heading = None
        self.heading_text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "tr" and attributes.get("onclick", "").startswith("createAlert("):
            match = re.fullmatch(
                r"createAlert\('([^']*)','([^']*)','([^']*)','([^']*)','([^']*)'\)",
                attributes["onclick"],
            )
            self.row = {
                "click_args": match.groups() if match else None,
                "cells": [],
                "title": "",
                "company": "",
            }
        elif self.row is not None:
            if tag == "td":
                self.cell = []
            if tag in ("h1", "h2"):
                self.heading = tag
                self.heading_text = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        if self.heading is not None:
            self.heading_text.append(data)

    def handle_endtag(self, tag):
        if self.row is None:
            return
        if tag == self.heading:
            value = " ".join(" ".join(self.heading_text).split())
            self.row["title" if tag == "h2" else "company"] = value
            self.heading = None
            self.heading_text = []
        if tag == "td" and self.cell is not None:
            self.row["cells"].append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if tag == "tr":
            self.rows.append(self.row)
            self.row = None

def _topjobs_date(value):
    try:
        return datetime.strptime(value.strip(), "%a %b %d %Y").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def fetch_topjobs():
    """Fetch software vacancy metadata from the public TopJobs functional-area listing."""
    response = requests.get(
        "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp",
        params={"FA": "SDQ"},
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": "PersonalJobAggregator/1.0"},
    )
    response.raise_for_status()

    parser = _TopJobsListingParser()
    parser.feed(response.text)
    if not parser.rows:
        raise ValueError("TopJobs listing returned no recognizable vacancy rows")

    output = []
    for row in parser.rows:
        cells = row["cells"]
        click_args = row["click_args"]
        title = row["title"]
        if not click_args or len(cells) < 7 or not title or not _is_software_job(title):
            continue

        row_id, agent_code, job_code, employer_code, _ = click_args
        detail_url = "https://www.topjobs.lk/employer/JobAdvertismentServlet?" + urlencode({
            "rid": row_id,
            "ac": agent_code,
            "jc": job_code,
            "ec": employer_code,
            "pg": "applicant/vacancybyfunctionalarea.jsp",
        })
        output.append({
            "source": "TopJobs",
            "external_id": cells[1] or job_code,
            "title": title[:500],
            "company": (row["company"] or "Unknown")[:300],
            "location": (cells[6] or "Not specified")[:500],
            "job_type": "Not specified",
            "category": "Software / IT",
            "description": "",
            "apply_url": detail_url,
            "published_at": _topjobs_date(cells[4]),
        })
    return output

def fetch_remotive():
    """Public API; terms require attribution and linking back to the Remotive listing.
    Remotive advises no more than four fetches/day; schedule accordingly.
    """
    response = requests.get(
        "https://remotive.com/api/remote-jobs",
        params={"category": "software-dev"},
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": "PersonalJobAggregator/1.0"},
    )
    response.raise_for_status()
    output = []
    for item in response.json().get("jobs", []):
        title = item.get("title") or ""
        description = _clean_html(item.get("description") or "")
        url = item.get("url") or ""
        if not url or not _is_software_job(title, description):
            continue
        output.append({
            "source": "Remotive",
            "external_id": str(item.get("id") or url),
            "title": title[:500],
            "company": (item.get("company_name") or "Unknown")[:300],
            "location": (item.get("candidate_required_location") or "Remote / see listing")[:500],
            "job_type": (item.get("job_type") or "Not specified")[:100],
            "category": "Software / IT",
            "description": description,
            "apply_url": url,
            "published_at": _date(item.get("publication_date")),
        })
    return output

def fetch_arbeitnow():
    """Public job-board API. Check its current documentation/terms before production use."""
    response = requests.get(
        "https://www.arbeitnow.com/api/job-board-api",
        params={"page": 1},
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": "PersonalJobAggregator/1.0"},
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data", []) if isinstance(payload, dict) else []
    output = []
    for item in items:
        title = item.get("title") or ""
        description = _clean_html(item.get("description") or "")
        url = item.get("url") or ""
        if not url or not _is_software_job(title, description):
            continue
        output.append({
            "source": "Arbeitnow",
            "external_id": str(item.get("slug") or url),
            "title": title[:500],
            "company": (item.get("company_name") or "Unknown")[:300],
            "location": (item.get("location") or ("Remote" if item.get("remote") else "Not specified"))[:500],
            "job_type": "Not specified",
            "category": "Software / IT",
            "description": description,
            "apply_url": url,
            "published_at": _date(item.get("created_at")),
        })
    return output

def fetch_adzuna():
    """Optional authenticated source. Country coverage depends on Adzuna's supported markets."""
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []
    country = settings.adzuna_country.lower()
    response = requests.get(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
        params={
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "results_per_page": 50,
            "what": "software engineer developer",
            "content-type": "application/json",
            "sort_by": "date",
        },
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": "PersonalJobAggregator/1.0"},
    )
    response.raise_for_status()
    output = []
    for item in response.json().get("results", []):
        title = item.get("title") or ""
        description = _clean_html(item.get("description") or "")
        url = item.get("redirect_url") or ""
        if not url or not _is_software_job(title, description):
            continue
        loc = item.get("location") or {}
        output.append({
            "source": "Adzuna",
            "external_id": str(item.get("id") or url),
            "title": title[:500],
            "company": ((item.get("company") or {}).get("display_name") or "Unknown")[:300],
            "location": (loc.get("display_name") or "Not specified")[:500],
            "job_type": "Not specified",
            "category": "Software / IT",
            "description": description,
            "apply_url": url,
            "published_at": _date(item.get("created")),
        })
    return output

COLLECTORS = {
    "remotive": fetch_remotive,
    "arbeitnow": fetch_arbeitnow,
    "adzuna": fetch_adzuna,
    "topjobs": fetch_topjobs,
}
