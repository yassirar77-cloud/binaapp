"""
Health Check API Endpoints
"""

from fastapi import APIRouter
from datetime import datetime
import subprocess
import json
import os

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check - quick response"""
    return {
        "status": "ok",
        "service": "binaapp-api",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Run full health check and return JSON results"""
    try:
        # Run health_check.py with JSON output
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        result = subprocess.run(
            ["python", "health_check.py", "--json", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=backend_dir
        )

        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        else:
            return {
                "status": "error",
                "message": "Health check failed",
                "stderr": result.stderr[:200] if result.stderr else None
            }

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Health check timeout"}
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON response"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/health/trigger")
async def trigger_health_check():
    """
    Trigger full health check with Telegram alert if critical.
    Use this endpoint for cron jobs.
    """
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        result = subprocess.run(
            ["python", "health_check.py", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=backend_dir
        )

        status = "healthy" if result.returncode == 0 else "critical"

        return {
            "status": status,
            "exit_code": result.returncode,
            "timestamp": datetime.utcnow().isoformat(),
            "alert_sent": result.returncode != 0,
            "message": "Health check completed"
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Health check timeout after 60s"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/health/auth-config")
async def check_auth_config():
    """
    Diagnostic endpoint to check auth configuration.
    Returns masked values to verify secrets are set without exposing them.
    """
    def mask_secret(secret: str | None) -> str:
        if not secret:
            return "NOT SET ❌"
        if len(secret) < 10:
            return f"SET (too short: {len(secret)} chars) ⚠️"
        return f"SET ✅ (first 10: {secret[:10]}..., length: {len(secret)})"

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "auth_config": {
            "JWT_SECRET_KEY": mask_secret(settings.JWT_SECRET_KEY),
            "SUPABASE_JWT_SECRET": mask_secret(settings.SUPABASE_JWT_SECRET),
            "JWT_ALGORITHM": settings.JWT_ALGORITHM,
            "JWT_EXPIRATION_HOURS": settings.JWT_EXPIRATION_HOURS,
            "SUPABASE_URL": "SET ✅" if settings.SUPABASE_URL else "NOT SET ❌",
            "SUPABASE_ANON_KEY": "SET ✅" if settings.SUPABASE_ANON_KEY else "NOT SET ❌",
            "SUPABASE_SERVICE_ROLE_KEY": "SET ✅" if settings.SUPABASE_SERVICE_ROLE_KEY else "NOT SET ❌",
        },
        "notes": [
            "JWT_SECRET_KEY: Used to sign/verify tokens created by our backend",
            "SUPABASE_JWT_SECRET: Used to verify tokens from Supabase (OAuth/magic links)",
            "If getting 401 errors, check that JWT_SECRET_KEY matches between environments",
            "SUPABASE_JWT_SECRET should match the JWT Secret from Supabase Dashboard > Settings > API"
        ]
    }


@router.get("/health/telegram-test")
async def test_telegram():
    """Test Telegram connection by sending a test message"""
    import requests as req

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        return {
            "status": "error",
            "message": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
        }

    try:
        message = (
            "🧪 *BINAAPP TEST MESSAGE*\n\n"
            "✅ Telegram integration is working!\n"
            f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = req.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)

        if response.status_code == 200:
            return {"status": "ok", "message": "Test message sent to Telegram!"}
        else:
            return {
                "status": "error",
                "message": f"Telegram API error: {response.status_code}",
                "details": response.text[:200]
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}
