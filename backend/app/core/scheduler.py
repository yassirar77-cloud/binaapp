"""
Background Task Scheduler for BinaApp
Uses APScheduler to run periodic tasks like email polling
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("apscheduler package not installed. Background scheduling will be disabled.")

from app.core.config import settings


class EmailPollingScheduler:
    """Scheduler for email polling background tasks"""

    JOB_ID = "email_polling_job"

    def __init__(self):
        """Initialize the scheduler"""
        self.scheduler: Optional[Any] = None
        self._is_running = False
        self._started_at: Optional[datetime] = None
        self._last_job_run: Optional[datetime] = None
        self._job_run_count = 0

        if APSCHEDULER_AVAILABLE:
            # Configure scheduler with job stores and executors
            jobstores = {
                'default': MemoryJobStore()
            }
            executors = {
                'default': AsyncIOExecutor()
            }
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions into one
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 60  # Allow 60 seconds grace time for missed jobs
            }

            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='UTC'
            )
            logger.info("APScheduler initialized successfully")
        else:
            logger.warning("APScheduler not available - scheduling disabled")

    def is_available(self) -> bool:
        """Check if scheduler is available"""
        return APSCHEDULER_AVAILABLE and self.scheduler is not None

    @property
    def is_running(self) -> bool:
        """Check if scheduler is currently running"""
        return self._is_running and self.scheduler is not None and self.scheduler.running

    async def _poll_job(self):
        """The actual polling job that runs periodically"""
        from app.services.email_polling_service import email_polling_service

        self._last_job_run = datetime.utcnow()
        self._job_run_count += 1

        logger.info(f"Email polling job #{self._job_run_count} starting...")

        try:
            # Update service running state
            email_polling_service.is_running = True

            # Run the polling
            result = await email_polling_service.poll_inbox()

            if result.get("success"):
                logger.info(
                    f"Polling job #{self._job_run_count} completed: "
                    f"{result.get('emails_processed', 0)} emails processed"
                )
            else:
                logger.error(f"Polling job #{self._job_run_count} failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error in polling job #{self._job_run_count}: {e}")
        finally:
            from app.services.email_polling_service import email_polling_service
            email_polling_service.is_running = False

    def start(self) -> bool:
        """Start the email polling scheduler"""
        if not self.is_available():
            logger.error("Cannot start scheduler - APScheduler not available")
            return False

        if self.is_running:
            logger.warning("Scheduler is already running")
            return True

        try:
            # Add the polling job
            interval_seconds = settings.EMAIL_POLLING_INTERVAL_SECONDS

            self.scheduler.add_job(
                self._poll_job,
                trigger=IntervalTrigger(seconds=interval_seconds),
                id=self.JOB_ID,
                name="Email Polling Job",
                replace_existing=True
            )

            # Start the scheduler
            self.scheduler.start()
            self._is_running = True
            self._started_at = datetime.utcnow()

            logger.info(f"Email polling scheduler started (interval: {interval_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False

    def stop(self) -> bool:
        """Stop the email polling scheduler"""
        if not self.is_available():
            return False

        if not self.is_running:
            logger.warning("Scheduler is not running")
            return True

        try:
            # Remove the job first
            try:
                self.scheduler.remove_job(self.JOB_ID)
            except Exception:
                pass

            # Shutdown the scheduler
            self.scheduler.shutdown(wait=True)
            self._is_running = False

            logger.info("Email polling scheduler stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False

    def restart(self) -> bool:
        """Restart the email polling scheduler"""
        self.stop()
        return self.start()

    def pause(self) -> bool:
        """Pause the polling job without stopping the scheduler"""
        if not self.is_running:
            return False

        try:
            self.scheduler.pause_job(self.JOB_ID)
            logger.info("Email polling job paused")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job: {e}")
            return False

    def resume(self) -> bool:
        """Resume the paused polling job"""
        if not self.is_available():
            return False

        try:
            self.scheduler.resume_job(self.JOB_ID)
            logger.info("Email polling job resumed")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job: {e}")
            return False

    async def trigger_now(self) -> Dict[str, Any]:
        """Manually trigger an immediate poll"""
        from app.services.email_polling_service import email_polling_service

        logger.info("Manual email polling triggered")

        try:
            result = await email_polling_service.poll_inbox()
            return {
                "success": True,
                "message": "Manual poll completed",
                "result": result
            }
        except Exception as e:
            logger.error(f"Manual poll failed: {e}")
            return {
                "success": False,
                "message": f"Manual poll failed: {str(e)}",
                "error": str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        job_info = None
        next_run_time = None

        if self.is_available() and self.scheduler.running:
            job = self.scheduler.get_job(self.JOB_ID)
            if job:
                job_info = {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "pending": job.pending
                }
                next_run_time = job.next_run_time.isoformat() if job.next_run_time else None

        return {
            "scheduler_available": self.is_available(),
            "is_running": self.is_running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "last_job_run": self._last_job_run.isoformat() if self._last_job_run else None,
            "job_run_count": self._job_run_count,
            "next_run_time": next_run_time,
            "polling_interval_seconds": settings.EMAIL_POLLING_INTERVAL_SECONDS,
            "job_info": job_info
        }

    def shutdown(self):
        """Gracefully shutdown the scheduler"""
        if self.scheduler and self.scheduler.running:
            try:
                self.scheduler.shutdown(wait=True)
                logger.info("Scheduler shutdown complete")
            except Exception as e:
                logger.error(f"Error during scheduler shutdown: {e}")
        self._is_running = False


# Create singleton instance
email_polling_scheduler = EmailPollingScheduler()


async def start_email_polling():
    """Helper function to start email polling on application startup"""
    from app.services.email_polling_service import email_polling_service

    if not settings.EMAIL_POLLING_ENABLED:
        logger.info("Email polling is disabled in settings")
        return False

    if not email_polling_service.is_available():
        logger.warning("Email polling service not available (check configuration)")
        return False

    # Test connection first
    test_result = await email_polling_service.test_connection()
    if not test_result.get("success"):
        logger.error(f"Email polling connection test failed: {test_result.get('message')}")
        return False

    logger.info(
        f"Email polling connection test successful. "
        f"Inbox: {test_result.get('inbox_messages', 0)} messages, "
        f"{test_result.get('inbox_unseen', 0)} unseen"
    )

    # Start the scheduler
    return email_polling_scheduler.start()


def stop_email_polling():
    """Helper function to stop email polling on application shutdown"""
    email_polling_scheduler.shutdown()
