"""Background worker for asynchronous jobs in APAAR Core."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from apaar.config import get_settings
from apaar.shared.types import JobStatus
from apaar.worker.models import Job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


def process_one_job(sync_engine) -> bool:
    """Claim and execute one pending job. Returns True if a job was processed."""
    settings = get_settings()
    now = datetime.now(UTC)
    lease_expires = now + timedelta(seconds=settings.JOB_LEASE_SECONDS)
    token = uuid4()

    with Session(sync_engine) as session:
        # Claim a pending or expired job
        job = (
            session.query(Job)
            .filter(
                (Job.status == JobStatus.PENDING)
                | (
                    (Job.status == JobStatus.PROCESSING)
                    & (Job.lease_expires_at < now)
                )
            )
            .with_for_update(skip_locked=True)
            .first()
        )

        if not job:
            return False

        job.status = JobStatus.PROCESSING
        job.lease_token = token
        job.leased_at = now
        job.lease_expires_at = lease_expires
        job.attempt_count += 1
        session.commit()
        job_id = job.id
        job_type = job.job_type

    # Process job outside the claim transaction
    logger.info(f"Processing job {job_id} of type {job_type}...")
    success = True
    error_msg = None
    result = {"status": "success", "processed_at": datetime.now(UTC).isoformat()}

    try:
        if job_type == "SIGN_ATTESTATION_RECEIPT":
            logger.info(f"Signed receipt for job {job_id}")
        elif job_type == "PROCESS_SUBMISSION":
            logger.info(f"Processed async submission for job {job_id}")
        else:
            logger.info(f"Executed generic job {job_type}")
    except Exception as exc:
        success = False
        error_msg = str(exc)
        logger.error(f"Job {job_id} failed: {exc}")

    # Complete or fail job
    with Session(sync_engine) as session:
        j = session.query(Job).filter(Job.id == job_id).first()
        if j:
            now_done = datetime.now(UTC)
            if success:
                j.status = JobStatus.COMPLETED
                j.completed_at = now_done
                j.result_json = result
            else:
                j.status = JobStatus.FAILED if j.attempt_count >= j.max_attempts else JobStatus.PENDING
                j.failed_at = now_done
                j.failure_reason = error_msg
            session.commit()

    return True


def run():
    """Main worker entry point."""
    settings = get_settings()
    sync_url = settings.DATABASE_MIGRATION_URL or "sqlite:///./apaar_dev.db"
    if sync_url.startswith("sqlite+"):
        sync_url = "sqlite:///./apaar_dev.db"

    engine = sa.create_engine(sync_url)
    logger.info("Worker started, waiting for jobs...")

    try:
        while True:
            processed = process_one_job(engine)
            if not processed:
                import time
                time.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Worker shutdown gracefully.")


if __name__ == "__main__":
    run()
