#!/usr/bin/env python3
"""
BinaApp Health Check System
Monitors services and sends Telegram alerts on critical issues.
"""

import os
import sys
import json
import logging
import argparse
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not installed. Run: pip install requests")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Configuration from environment variables."""

    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY: str = os.getenv('SUPABASE_KEY', '')

    FRONTEND_URL: str = os.getenv('BINAAPP_FRONTEND_URL', 'https://binaapp.my')
    BACKEND_URL: str = os.getenv('BINAAPP_BACKEND_URL', 'https://api.binaapp.my')

    TIMEOUT: int = int(os.getenv('HEALTH_CHECK_TIMEOUT', '10'))
    RESPONSE_WARNING_MS: int = 2000
    RESPONSE_CRITICAL_MS: int = 5000
    DISK_WARNING_PERCENT: int = int(os.getenv('DISK_WARNING_THRESHOLD', '80'))
    DISK_CRITICAL_PERCENT: int = int(os.getenv('DISK_CRITICAL_THRESHOLD', '95'))


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class Status(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    response_time_ms: Optional[float] = None
    details: Dict = field(default_factory=dict)


@dataclass
class HealthReport:
    overall_status: Status
    timestamp: datetime
    checks: List[CheckResult]
    server_info: Dict = field(default_factory=dict)

    def get_failed_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status != Status.HEALTHY]

    def get_critical_checks(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status == Status.CRITICAL]


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger('binaapp_health')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

def check_http_endpoint(name: str, url: str, expected_status: int = 200) -> CheckResult:
    """Check if HTTP endpoint is responding."""
    try:
        start_time = datetime.now()
        response = requests.get(url, timeout=Config.TIMEOUT)
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        if response.status_code != expected_status:
            return CheckResult(
                name=name,
                status=Status.CRITICAL,
                message=f"Status {response.status_code} (expected {expected_status})",
                response_time_ms=elapsed_ms,
                details={'status_code': response.status_code, 'url': url}
            )

        if elapsed_ms > Config.RESPONSE_CRITICAL_MS:
            return CheckResult(
                name=name,
                status=Status.CRITICAL,
                message=f"Very slow: {elapsed_ms:.0f}ms",
                response_time_ms=elapsed_ms,
                details={'url': url}
            )
        elif elapsed_ms > Config.RESPONSE_WARNING_MS:
            return CheckResult(
                name=name,
                status=Status.WARNING,
                message=f"Slow: {elapsed_ms:.0f}ms",
                response_time_ms=elapsed_ms,
                details={'url': url}
            )

        return CheckResult(
            name=name,
            status=Status.HEALTHY,
            message=f"OK ({elapsed_ms:.0f}ms)",
            response_time_ms=elapsed_ms,
            details={'url': url}
        )

    except requests.exceptions.Timeout:
        return CheckResult(
            name=name,
            status=Status.CRITICAL,
            message=f"Timeout after {Config.TIMEOUT}s",
            details={'url': url}
        )
    except requests.exceptions.ConnectionError as e:
        return CheckResult(
            name=name,
            status=Status.CRITICAL,
            message=f"Connection failed",
            details={'url': url, 'error': str(e)[:100]}
        )
    except Exception as e:
        return CheckResult(
            name=name,
            status=Status.CRITICAL,
            message=f"Error: {str(e)[:50]}",
            details={'url': url, 'error': str(e)}
        )


def check_supabase_connection() -> CheckResult:
    """Check Supabase database connectivity."""
    name = "Database (Supabase)"

    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        return CheckResult(
            name=name,
            status=Status.WARNING,
            message="Supabase not configured",
            details={'configured': False}
        )

    try:
        url = f"{Config.SUPABASE_URL}/rest/v1/"
        headers = {
            'apikey': Config.SUPABASE_KEY,
            'Authorization': f'Bearer {Config.SUPABASE_KEY}'
        }

        start_time = datetime.now()
        response = requests.get(url, headers=headers, timeout=Config.TIMEOUT)
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        if response.status_code in [200, 401, 406]:
            return CheckResult(
                name=name,
                status=Status.HEALTHY,
                message=f"Connected ({elapsed_ms:.0f}ms)",
                response_time_ms=elapsed_ms
            )
        else:
            return CheckResult(
                name=name,
                status=Status.CRITICAL,
                message=f"Error: {response.status_code}",
                response_time_ms=elapsed_ms
            )

    except requests.exceptions.Timeout:
        return CheckResult(
            name=name,
            status=Status.CRITICAL,
            message=f"Timeout after {Config.TIMEOUT}s"
        )
    except Exception as e:
        return CheckResult(
            name=name,
            status=Status.CRITICAL,
            message=f"Error: {str(e)[:50]}",
            details={'error': str(e)}
        )


def check_disk_space() -> CheckResult:
    """Check available disk space."""
    name = "Disk Space"

    try:
        total, used, free = shutil.disk_usage("/")
        percent_used = (used / total) * 100
        free_gb = free / (1024 ** 3)

        details = {
            'total_gb': round(total / (1024 ** 3), 2),
            'used_gb': round(used / (1024 ** 3), 2),
            'free_gb': round(free_gb, 2),
            'percent_used': round(percent_used, 1)
        }

        if percent_used >= Config.DISK_CRITICAL_PERCENT:
            return CheckResult(
                name=name,
                status=Status.CRITICAL,
                message=f"Disk {percent_used:.1f}% full!",
                details=details
            )
        elif percent_used >= Config.DISK_WARNING_PERCENT:
            return CheckResult(
                name=name,
                status=Status.WARNING,
                message=f"Disk {percent_used:.1f}% full",
                details=details
            )
        else:
            return CheckResult(
                name=name,
                status=Status.HEALTHY,
                message=f"{free_gb:.1f}GB free",
                details=details
            )

    except Exception as e:
        return CheckResult(
            name=name,
            status=Status.WARNING,
            message=f"Could not check: {str(e)[:30]}"
        )


def run_all_checks() -> HealthReport:
    """Run all health checks."""
    logger.info("Starting health checks...")
    timestamp = datetime.now()
    checks: List[CheckResult] = []

    # Check Frontend
    logger.debug(f"Checking frontend: {Config.FRONTEND_URL}")
    checks.append(check_http_endpoint("Frontend", Config.FRONTEND_URL))

    # Check Backend API
    backend_health_url = f"{Config.BACKEND_URL}/health"
    logger.debug(f"Checking backend: {backend_health_url}")
    checks.append(check_http_endpoint("Backend API", backend_health_url))

    # Check Supabase
    logger.debug("Checking Supabase connection")
    checks.append(check_supabase_connection())

    # Check Disk Space
    logger.debug("Checking disk space")
    checks.append(check_disk_space())

    # Determine overall status
    statuses = [c.status for c in checks]
    if Status.CRITICAL in statuses:
        overall_status = Status.CRITICAL
    elif Status.WARNING in statuses:
        overall_status = Status.WARNING
    else:
        overall_status = Status.HEALTHY

    server_info = {
        'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        'python_version': sys.version.split()[0],
        'check_count': len(checks)
    }

    report = HealthReport(
        overall_status=overall_status,
        timestamp=timestamp,
        checks=checks,
        server_info=server_info
    )

    logger.info(f"Health check complete: {overall_status.value.upper()}")
    return report


# =============================================================================
# TELEGRAM FUNCTIONS
# =============================================================================

def is_telegram_configured() -> bool:
    return bool(Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID)


def format_telegram_message(report: HealthReport) -> str:
    """Format report as Telegram message."""
    status_emoji = {
        Status.HEALTHY: "✅",
        Status.WARNING: "⚠️",
        Status.CRITICAL: "🚨"
    }

    emoji = status_emoji.get(report.overall_status, "❓")
    timestamp_str = report.timestamp.strftime("%Y-%m-%d %H:%M:%S MYT")

    lines = [
        f"{emoji} *BINAAPP HEALTH ALERT*",
        "",
        f"*Status:* {report.overall_status.value.upper()}",
        f"*Time:* {timestamp_str}",
        "",
    ]

    failed_checks = report.get_failed_checks()
    if failed_checks:
        lines.append("*Issues Detected:*")
        for check in failed_checks:
            check_emoji = "🚨" if check.status == Status.CRITICAL else "⚠️"
            lines.append(f"{check_emoji} {check.name}: {check.message}")
        lines.append("")

    lines.append("*All Checks:*")
    for check in report.checks:
        check_emoji = status_emoji.get(check.status, "❓")
        time_str = f" ({check.response_time_ms:.0f}ms)" if check.response_time_ms else ""
        lines.append(f"{check_emoji} {check.name}{time_str}")

    lines.extend([
        "",
        f"🖥️ Server: {report.server_info.get('hostname', 'unknown')}",
        "",
        "_Please investigate if critical._"
    ])

    return "\n".join(lines)


def send_telegram_alert(report: HealthReport, dry_run: bool = False) -> bool:
    """Send alert to Telegram."""
    if not is_telegram_configured():
        logger.warning("Telegram not configured")
        return False

    message = format_telegram_message(report)

    if dry_run:
        logger.info("DRY RUN - Would send:")
        print("\n" + "=" * 50)
        print(message)
        print("=" * 50 + "\n")
        return True

    try:
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': Config.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            logger.info("✅ Telegram alert sent!")
            return True
        else:
            logger.error(f"Telegram error: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Failed to send Telegram: {e}")
        return False


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def print_report(report: HealthReport, verbose: bool = False) -> None:
    """Print report to console."""
    status_emoji = {
        Status.HEALTHY: "✅",
        Status.WARNING: "⚠️",
        Status.CRITICAL: "🚨"
    }

    emoji = status_emoji.get(report.overall_status, "")

    print("\n" + "=" * 60)
    print(f"  BINAAPP HEALTH CHECK REPORT")
    print("=" * 60)
    print(f"  Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Overall:   {emoji} {report.overall_status.value.upper()}")
    print("-" * 60)

    for check in report.checks:
        e = status_emoji.get(check.status, "")
        time_str = f" ({check.response_time_ms:.0f}ms)" if check.response_time_ms else ""
        print(f"  {e} {check.name}: {check.message}{time_str}")

    print("=" * 60 + "\n")


def get_exit_code(status: Status) -> int:
    """Get cron-compatible exit code."""
    return 1 if status == Status.CRITICAL else 0


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='BinaApp Health Check')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Do not send alerts')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')

    args = parser.parse_args()

    global logger
    logger = setup_logging(verbose=args.verbose)

    try:
        report = run_all_checks()

        if args.json:
            output = {
                'status': report.overall_status.value,
                'timestamp': report.timestamp.isoformat(),
                'checks': [
                    {
                        'name': c.name,
                        'status': c.status.value,
                        'message': c.message,
                        'response_time_ms': c.response_time_ms
                    }
                    for c in report.checks
                ]
            }
            print(json.dumps(output, indent=2))
        elif not args.quiet:
            print_report(report, verbose=args.verbose)

        # Send Telegram ONLY if CRITICAL
        if report.overall_status == Status.CRITICAL:
            logger.warning("🚨 CRITICAL - Sending Telegram alert")
            send_telegram_alert(report, dry_run=args.dry_run)

        return get_exit_code(report.overall_status)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
