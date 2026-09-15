#!/usr/bin/env python3
"""
BinaApp Subscription Cron Runner
================================

Script to run via Render Cron Job or any external scheduler.

Schedule: Daily at 00:00 Malaysia Time (UTC+8)
Which equals 16:00 UTC the previous day

RENDER CRON SETUP:
------------------
1. Go to Render Dashboard
2. Create a new "Cron Job" service
3. Connect to this repository
4. Set:
   - Name: binaapp-subscription-cron
   - Schedule: 0 16 * * *  (16:00 UTC = 00:00 MYT)
   - Command: python cron_runner.py
   - Environment: Copy from main backend service

MANUAL TESTING:
---------------
    cd /backend
    python cron_runner.py

Or with specific Python:
    python3 cron_runner.py

ENVIRONMENT VARIABLES REQUIRED:
-------------------------------
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_KEY / SUPABASE_KEY -- the
  same aliases app/main.py accepts; whichever is set is normalised into
  SUPABASE_SERVICE_ROLE_KEY for the rest of the app)
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD
- FRONTEND_URL (or BASE_URL)
- SUPPORT_EMAIL
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger


def setup_logging():
    """Configure logging for cron job"""
    # Remove default handler
    logger.remove()

    # Add console handler with timestamp
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # Add file handler for persistent logs (if running on server)
    log_dir = os.environ.get("LOG_DIR", "/tmp")
    log_file = os.path.join(log_dir, "subscription_cron.log")

    try:
        logger.add(
            log_file,
            rotation="1 day",
            retention="7 days",
            level="DEBUG"
        )
        logger.info(f"Logging to file: {log_file}")
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")


#: The service key may arrive under any of these names -- app/main.py and
#: app/services/design_plan_store.py already accept all three. The cron used
#: to demand SUPABASE_SERVICE_ROLE_KEY exactly and exited 1 when only an
#: alias was set.
SERVICE_KEY_VARS = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_KEY",
)


def resolve_service_key():
    """Return the Supabase service key under any accepted alias.

    The winning value is written back to SUPABASE_SERVICE_ROLE_KEY so
    ``app.config.settings`` -- which only reads that name -- sees it too.
    """
    for var in SERVICE_KEY_VARS:
        value = (os.environ.get(var) or "").strip()
        if value:
            if var != "SUPABASE_SERVICE_ROLE_KEY":
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = value
                logger.info(f"Using {var} as SUPABASE_SERVICE_ROLE_KEY")
            return value
    return None


def verify_environment():
    """Verify required environment variables are set"""
    optional_vars = [
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "FRONTEND_URL",
        "BASE_URL",
        "SUPPORT_EMAIL",
    ]

    missing = []
    if not (os.environ.get("SUPABASE_URL") or "").strip():
        missing.append("SUPABASE_URL")
    if not resolve_service_key():
        missing.append(" or ".join(SERVICE_KEY_VARS))

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error(
            "On Render these are per-service values: a `sync: false` key in "
            "render.yaml is created empty and must be filled in on THAT "
            "service (Dashboard -> the cron service -> Environment), or "
            "inherited from binaapp-backend via `fromService` in render.yaml. "
            "Setting it on the web service alone does not reach the cron."
        )
        return False

    # Log optional vars status
    for var in optional_vars:
        if os.environ.get(var):
            logger.debug(f"Optional var {var}: SET")
        else:
            logger.warning(f"Optional var {var}: NOT SET")

    return True


def main():
    """Main entry point for cron runner"""
    setup_logging()

    logger.info("=" * 70)
    logger.info("BINAAPP SUBSCRIPTION CRON JOB")
    logger.info(f"Started at: {datetime.utcnow().isoformat()} UTC")
    logger.info("=" * 70)

    # Verify environment
    if not verify_environment():
        logger.error("Environment verification failed. Exiting.")
        sys.exit(1)

    try:
        # Which job: `python cron_runner.py` (default) runs the subscription
        # cron; `python cron_runner.py design-stats` runs the weekly
        # direction-stats report (docs/design/direction-stats.md).
        job = (sys.argv[1] if len(sys.argv) > 1 else "subscription").strip().lower()
        if job in ("design-stats", "design_stats", "direction-stats"):
            from app.cron.design_stats_cron import run_design_stats_sync

            result = run_design_stats_sync()
        else:
            from app.cron.subscription_cron import run_subscription_cron_sync

            result = run_subscription_cron_sync()

        # Log results summary
        logger.info("=" * 70)
        logger.info("CRON JOB RESULTS SUMMARY")
        logger.info("=" * 70)

        if result.get("success"):
            logger.info("Status: SUCCESS")
        else:
            logger.error(f"Status: FAILED - {result.get('error', 'Unknown error')}")

        logger.info(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")

        # Log step results
        steps = result.get("steps", {})
        for step_name, step_result in steps.items():
            logger.info(f"\n{step_name}:")
            for key, value in step_result.items():
                logger.info(f"  {key}: {value}")

        # Pretty print full results
        logger.debug(f"Full results: {json.dumps(result, indent=2, default=str)}")

        # Exit with appropriate code
        if result.get("success"):
            logger.info("Cron job completed successfully!")
            sys.exit(0)
        else:
            logger.error("Cron job completed with errors")
            sys.exit(1)

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you're running from the backend directory")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Cron job failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
