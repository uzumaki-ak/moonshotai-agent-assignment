# this file runs scrape and analysis pipeline from cli
import argparse

from app.db.session import SessionLocal
from app.models import PipelineJob
from app.services.jobs.pipeline import run_analyze_job, run_scrape_job


def create_job(job_type: str, params: dict) -> str:
    # this function creates a pipeline job row and returns id
    with SessionLocal() as db:
        job = PipelineJob(job_type=job_type, status="pending", params=params)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id


def main() -> None:
    # this function starts requested pipeline operation
    parser = argparse.ArgumentParser(description="run moonshot pipeline")
    parser.add_argument("mode", choices=["scrape", "analyze", "all"])
    parser.add_argument("--brands", nargs="*", default=["Safari", "Skybags", "American Tourister", "VIP"])
    parser.add_argument("--products-per-brand", type=int, default=10)
    parser.add_argument("--reviews-per-product", type=int, default=50)
    args = parser.parse_args()

    if args.mode in {"scrape", "all"}:
        scrape_id = create_job(
            "scrape",
            {
                "brands": args.brands,
                "products_per_brand": args.products_per_brand,
                "reviews_per_product": args.reviews_per_product,
            },
        )
        run_scrape_job(scrape_id)

    if args.mode in {"analyze", "all"}:
        analyze_id = create_job("analyze", {"force_recompute": True})
        run_analyze_job(analyze_id)


if __name__ == "__main__":
    main()
