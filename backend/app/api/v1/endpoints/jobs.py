# this file manages scrape and analysis job endpoints
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import PipelineJob
from app.schemas.job import AnalyzeJobCreate, JobRead, ScrapeJobCreate
from app.services.jobs.pipeline import run_analyze_job_async, run_scrape_job_async

router = APIRouter()


@router.post("/scrape", response_model=JobRead)
def create_scrape_job(payload: ScrapeJobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> PipelineJob:
    # this endpoint queues a scrape job
    job = PipelineJob(
        job_type="scrape",
        status="pending",
        params={
            "brands": payload.brands,
            "products_per_brand": payload.products_per_brand,
            "reviews_per_product": payload.reviews_per_product,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_scrape_job_async, job.id)
    return job


@router.post("/analyze", response_model=JobRead)
def create_analyze_job(payload: AnalyzeJobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> PipelineJob:
    # this endpoint queues an analysis job
    job = PipelineJob(
        job_type="analyze",
        status="pending",
        params={"force_recompute": payload.force_recompute},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_analyze_job_async, job.id)
    return job


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)) -> PipelineJob:
    # this endpoint returns one job status
    job = db.get(PipelineJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[PipelineJob]:
    # this endpoint lists latest jobs for pipeline page
    return db.execute(select(PipelineJob).order_by(PipelineJob.started_at.desc()).limit(100)).scalars().all()
