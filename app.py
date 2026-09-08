"""
Job Marketplace API
====================

A backend API for managing job postings and candidate applications.
No frontend — this is the API only. Data is stored in memory (two plain
Python dictionaries), so nothing to install or configure beyond the
packages in requirements.txt.

HOW TO RUN
----------
    py -m pip install -r requirements.txt
    py -m uvicorn app:app

HOW TO TRY IT
-------------
FastAPI auto-generates an interactive docs page for you — open:
    http://127.0.0.1:8000/docs

There, click on any endpoint below to expand it, click "Try it out",
fill in the fields, and click "Execute" to send a real request to this
API and see the real response. No separate tool (Postman, curl, etc.)
required, though you're welcome to use one if you prefer.

ENDPOINTS
---------
Jobs:
    POST   /jobs                       create a job posting
    GET    /jobs                       list jobs (optional ?status=OPEN/CLOSED)
    GET    /jobs/{job_id}              get one job
    POST   /jobs/{job_id}/close        close a job

Applications:
    POST   /jobs/{job_id}/applications     apply to a job
    GET    /jobs/{job_id}/applications     list applications for a job
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(
    title="Job Marketplace API",
    description="Manage job postings and candidate applications.",
    version="1.0.0",
)

# 1. Data Models

class JobStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class JobCreate(BaseModel):
    """What a client sends when creating a job."""
    title: str = Field(..., min_length=1, max_length=200, examples=["Backend Engineer"])
    description: str = Field(..., min_length=1, examples=["Build and maintain our core APIs."])
    location: str = Field(..., min_length=1, max_length=200, examples=["Remote"])


class Job(JobCreate):
    """What the API returns for a job. Adds server-generated fields on top
    of everything in JobCreate."""
    id: uuid.UUID
    status: JobStatus
    created_at: datetime


class ApplicationCreate(BaseModel):
    """What a client sends when applying to a job."""
    candidate_name: str = Field(..., min_length=1, max_length=200, examples=["Jane Doe"])
    candidate_email: EmailStr = Field(..., examples=["jane.doe@example.com"])


class Application(ApplicationCreate):
    """What the API returns for an application."""
    id: uuid.UUID
    job_id: uuid.UUID
    submitted_at: datetime

# 2. Storage

jobs: dict[uuid.UUID, Job] = {}
applications: dict[uuid.UUID, Application] = {}


def get_job_or_404(job_id: uuid.UUID) -> Job:
    """Shared lookup used by every endpoint that needs an existing job.
    Raises a 404 automatically if the id doesn't exist."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job {job_id} was not found.")
    return job

# 3. Job Endpoints

@app.post("/jobs", response_model=Job, status_code=status.HTTP_201_CREATED, tags=["Jobs"])
def create_job(payload: JobCreate) -> Job:
    """Create a new job posting. New jobs always start as OPEN."""
    job = Job(
        id=uuid.uuid4(),
        status=JobStatus.OPEN,
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    jobs[job.id] = job
    return job


@app.get("/jobs", response_model=list[Job], tags=["Jobs"])
def list_jobs(
    status_filter: Optional[JobStatus] = Query(
        default=None, alias="status", description="Filter by status, e.g. ?status=OPEN"
    )
) -> list[Job]:
    """List all job postings, optionally filtered by status."""
    results = list(jobs.values())
    if status_filter is not None:
        results = [job for job in results if job.status == status_filter]
    return sorted(results, key=lambda job: job.created_at, reverse=True)


@app.get("/jobs/{job_id}", response_model=Job, tags=["Jobs"])
def get_job(job_id: uuid.UUID) -> Job:
    """Get details for a single job posting."""
    return get_job_or_404(job_id)


@app.post("/jobs/{job_id}/close", response_model=Job, tags=["Jobs"])
def close_job(job_id: uuid.UUID) -> Job:
    """Close a job so it no longer accepts new applications. Safe to call
    more than once — closing an already-closed job just returns it as-is."""
    job = get_job_or_404(job_id)
    job.status = JobStatus.CLOSED
    return job

# 4. Application Endpoints

@app.post(
    "/jobs/{job_id}/applications",
    response_model=Application,
    status_code=status.HTTP_201_CREATED,
    tags=["Applications"],
)
def submit_application(job_id: uuid.UUID, payload: ApplicationCreate) -> Application:
    """Submit an application for a job. Rejected with 409 if the job is
    closed, and 404 if the job doesn't exist."""
    job = get_job_or_404(job_id)
    if job.status is JobStatus.CLOSED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Job {job_id} is closed and no longer accepts applications.",
        )

    application = Application(
        id=uuid.uuid4(),
        job_id=job_id,
        submitted_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    applications[application.id] = application
    return application


@app.get(
    "/jobs/{job_id}/applications",
    response_model=list[Application],
    tags=["Applications"],
)
def list_applications(job_id: uuid.UUID) -> list[Application]:
    """List all applications submitted for a given job."""
    get_job_or_404(job_id)  # 404 if the job itself doesn't exist
    matching = [app for app in applications.values() if app.job_id == job_id]
    return sorted(matching, key=lambda app: app.submitted_at)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Basic liveness check — confirms the server is up and responding."""
    return {"status": "ok"}
