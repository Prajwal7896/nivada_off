import asyncio
import logging
import os
import time

from sqlalchemy import func

from backend.app.db.db import SessionLocal
from backend.app.db.model import (
    Complaint,
    ComplaintAIJob,
    ComplaintCategory,
    Department,
    PredictionLog,
)
from backend.app.db.redis_client import connect_redis, close_redis
from backend.app.db.cache import invalidate_complaint_cache_async
from backend.app.complaint.ai_queue import (
    claim_next_job,
    retry_or_fail_job,
)
from backend.app.complaint.complaints import (
    predict_category,
    get_department_name,
    find_assigned_admin,
)

POLL_INTERVAL_SECONDS = float(os.getenv("AI_WORKER_POLL_SECONDS", "2"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("nivada.ai_worker")


def process_job(job_data: dict) -> bool:
    job_id = job_data["job_id"]
    complaint_id = job_data["complaint_id"]

    try:
        # Read complaint data and release the session before inference.
        with SessionLocal() as db:
            complaint = db.get(Complaint, complaint_id)

            if complaint is None:
                raise RuntimeError(
                    f"Complaint {complaint_id} does not exist"
                )

            complaint_text = complaint.complaint_text
            village_id = complaint.village_id
            taluka_id = complaint.taluka_id
            district_id = complaint.district_id

        # ONNX inference happens without holding a database transaction.
        category_name, confidence = predict_category(complaint_text)

        # Save classification and job completion atomically.
        with SessionLocal() as db:
            job = (
                db.query(ComplaintAIJob)
                .filter(
                    ComplaintAIJob.id == job_id,
                    ComplaintAIJob.status == "processing",
                )
                .with_for_update()
                .first()
            )

            if job is None:
                logger.warning("Job %s is no longer processing", job_id)
                return False

            complaint = (
                db.query(Complaint)
                .filter(Complaint.id == complaint_id)
                .with_for_update()
                .first()
            )

            if complaint is None:
                raise RuntimeError(
                    f"Complaint {complaint_id} disappeared"
                )

            # Protect against duplicate prediction logs.
            if complaint.ai_status == "completed":
                job.status = "completed"
                job.locked_at = None
                job.last_error = None
                db.commit()
                return True

            category = (
                db.query(ComplaintCategory)
                .filter(
                    func.lower(ComplaintCategory.name)
                    == category_name.lower()
                )
                .first()
            )

            if category is None:
                raise RuntimeError(
                    f"Category '{category_name}' does not exist"
                )

            department_name = get_department_name(category.name)

            if not department_name:
                raise RuntimeError(
                    f"No department mapping for '{category.name}'"
                )

            department = (
                db.query(Department)
                .filter(
                    func.lower(Department.name)
                    == department_name.lower()
                )
                .first()
            )

            if department is None:
                raise RuntimeError(
                    f"Department '{department_name}' does not exist"
                )

            assigned_admin = find_assigned_admin(
                db=db,
                department_id=department.id,
                village_id=village_id,
                taluka_id=taluka_id,
                district_id=district_id,
            )

            complaint.category_id = category.id
            complaint.department_id = department.id
            complaint.assigned_admin_id = (
                assigned_admin.id if assigned_admin else None
            )
            complaint.ai_confidence = confidence
            complaint.ai_status = "completed"

            db.add(
                PredictionLog(
                    complaint_id=complaint.id,
                    predicted_category=category.name,
                    confidence=confidence,
                    model_version="2",
                )
            )

            job.status = "completed"
            job.locked_at = None
            job.last_error = None

            db.commit()

        logger.info(
            "Completed AI job %s for complaint %s: category=%s confidence=%.4f",
            job_id,
            complaint_id,
            category_name,
            confidence,
        )
        return True

    except Exception as exc:
        logger.exception(
            "AI processing failed for job %s, complaint %s",
            job_id,
            complaint_id,
        )
        retry_or_fail_job(job_id, str(exc))
        return False


async def run_worker():
    redis_connected = await connect_redis()

    if not redis_connected:
        logger.warning(
            "Redis unavailable; worker will continue without cache invalidation"
        )

    logger.info("NIVADA AI worker started")

    try:
        while True:
            job = claim_next_job()

            if job is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            success = await asyncio.to_thread(process_job, job)

            if success:
                await invalidate_complaint_cache_async()

    except asyncio.CancelledError:
        logger.info("Worker shutdown requested")
        raise

    finally:
        await close_redis()
        logger.info("NIVADA AI worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
