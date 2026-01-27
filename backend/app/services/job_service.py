"""
Job Service - Manages async generation jobs
Tracks job status, progress, and results in-memory
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from enum import Enum
from loguru import logger


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    """Represents a generation job"""

    def __init__(self, job_id: str, user_id: str, description: str, request_data: dict):
        self.job_id = job_id
        self.user_id = user_id
        self.description = description
        self.request_data = request_data
        self.status = JobStatus.PENDING
        self.progress = 0
        self.variants: List[Dict[str, Any]] = []
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.detected_features: List[str] = []
        self.template_used: str = ""

    def to_dict(self) -> dict:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "description": self.description[:100] + "...",  # Truncate for response
            "status": self.status.value,
            "progress": self.progress,
            "variants": self.variants,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "detected_features": self.detected_features,
            "template_used": self.template_used
        }


class JobService:
    """Service to manage generation jobs"""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._cleanup_interval = 3600  # Clean up old jobs every hour
        self._max_job_age = 7200  # Keep jobs for 2 hours
        logger.info("JobService initialized with in-memory storage")

    def create_job(self, user_id: str, description: str, request_data: dict) -> str:
        """Create a new job and return job_id"""
        job_id = str(uuid.uuid4())
        job = Job(job_id, user_id, description, request_data)
        self.jobs[job_id] = job

        logger.info(f"Created job {job_id} for user {user_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def update_status(self, job_id: str, status: JobStatus, error: Optional[str] = None):
        """Update job status"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = status
            job.updated_at = datetime.utcnow()
            if error:
                job.error = error
            logger.info(f"Job {job_id} status updated to {status}")

    def update_progress(self, job_id: str, progress: int):
        """Update job progress (0-100)"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.progress = min(100, max(0, progress))
            job.updated_at = datetime.utcnow()
            logger.info(f"Job {job_id} progress: {job.progress}%")

    def add_variant(self, job_id: str, variant: Dict[str, Any]):
        """Add a generated variant to the job"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.variants.append(variant)
            job.updated_at = datetime.utcnow()
            logger.info(f"Added variant {len(job.variants)} to job {job_id}")

    def set_metadata(self, job_id: str, features: List[str], template: str):
        """Set job metadata"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.detected_features = features
            job.template_used = template
            job.updated_at = datetime.utcnow()

    def cleanup_old_jobs(self):
        """Remove old completed/failed jobs"""
        now = datetime.utcnow()
        to_remove = []

        for job_id, job in self.jobs.items():
            age = (now - job.created_at).total_seconds()
            if age > self._max_job_age and job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                to_remove.append(job_id)

        for job_id in to_remove:
            del self.jobs[job_id]
            logger.info(f"Cleaned up old job {job_id}")

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get job status response"""
        job = self.get_job(job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress,
            "variants": job.variants,
            "error": job.error,
            "detected_features": job.detected_features,
            "template_used": job.template_used
        }


# Global job service instance
job_service = JobService()
