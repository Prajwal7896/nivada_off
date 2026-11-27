import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.db.db import SessionLocal
from backend.app.db.model import Complaint, ComplaintAIJob

logger = logging.getLogger(__name__)


def claim_next_job(stale_after_seconds: int = 300):
    """
    Atomically claim one available job.
    PostgreSQL SKIP LOCKED allows multiple workers safely.
    """

    now = datetime.utcnow()
    stale_before = now - timedelta(seconds=stale_after_seconds)

    with SessionLocal() as db:
        # Recover jobs abandoned by crashed workers.
        stale_jobs = (
            db.query(ComplaintAIJob)
            .filter(
                ComplaintAIJob.status == "processing",
                ComplaintAIJob.locked_at <= stale_before
            )
            .with_for_update(skip_locked=True)
            .all()
        )

        for stale_job in stale_jobs:
            stale_job.locked_at = None

            if stale_job.attempts >= stale_job.max_attempts:
                stale_job.status = "failed"

                complaint = db.get(Complaint, stale_job.complaint_id)
                if complaint:
                    complaint.ai_status = "failed"
            else:
                stale_job.status = "queued"
                stale_job.next_retry_at = now

                complaint = db.get(Complaint, stale_job.complaint_id)
                if complaint:
                    complaint.ai_status = "queued"

        # Make recovered jobs visible to the claim query.
        db.flush()

        # Claim one due job.
        job = (
            db.query(ComplaintAIJob)
            .filter(
                ComplaintAIJob.status == "queued",
                ComplaintAIJob.next_retry_at <= now,
                ComplaintAIJob.attempts < ComplaintAIJob.max_attempts
            )
            .order_by(
                ComplaintAIJob.created_at.asc(),
                ComplaintAIJob.id.asc()
            )
            .with_for_update(skip_locked=True)
            .first()
        )

        if job is None:
            db.commit()
            return None

        job.status = "processing"
        job.attempts += 1
        job.locked_at = now

        complaint = db.get(Complaint, job.complaint_id)
        if complaint is None:
            job.status = "failed"
            job.locked_at = None
            job.last_error = "Related complaint does not exist"
            db.commit()
            return None

        complaint.ai_status = "processing"

        complaint_id = job.complaint_id
        job_id = job.id
        attempts = job.attempts
        max_attempts = job.max_attempts

        db.commit()

        return {
            "job_id": job_id,
            "complaint_id": complaint_id,
            "attempts": attempts,
            "max_attempts": max_attempts
        }


def retry_or_fail_job(job_id: int, error: str):
    """
    Retry a failed job with exponential backoff.
    Permanently fail it after max_attempts.
    """

    with SessionLocal() as db:
        job = db.get(ComplaintAIJob, job_id)

        if job is None:
            logger.error("AI job %s was not found during retry", job_id)
            return

        if job.status != "processing":
            logger.warning(
                "Skipping retry for AI job %s because status is %s",
                job_id,
                job.status
            )
            return

        job.last_error = str(error)[:2000]
        job.locked_at = None

        complaint = db.get(Complaint, job.complaint_id)

        if job.attempts >= job.max_attempts:
            job.status = "failed"

            if complaint:
                complaint.ai_status = "failed"

            logger.error(
                "AI job %s permanently failed after %s attempts",
                job_id,
                job.attempts
            )
        else:
            delay_seconds = min(
                300,
                10 * (2 ** max(job.attempts - 1, 0))
            )

            job.status = "queued"
            job.next_retry_at = (
                datetime.utcnow() + timedelta(seconds=delay_seconds)
            )

            if complaint:
                complaint.ai_status = "queued"

            logger.warning(
                "AI job %s scheduled for retry in %s seconds",
                job_id,
                delay_seconds
            )

        db.commit()
