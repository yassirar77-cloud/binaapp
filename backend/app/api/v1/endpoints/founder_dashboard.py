"""
BinaApp Founder Super Dashboard API Endpoints
Comprehensive business intelligence for founder only.
Protected: Only yassirar77@gmail.com
"""
import httpx
import csv
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from loguru import logger

from app.core.security import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/founder", tags=["Founder Dashboard"])

FOUNDER_EMAIL = "yassirar77@gmail.com"


def verify_founder(current_user: dict):
    """Verify the current user is the founder."""
    email = current_user.get("email", "")
    if email != FOUNDER_EMAIL:
        raise HTTPException(status_code=403, detail="Akses ditolak - hanya pengasas sahaja")
    return current_user


async def _db_count(table: str, filters: dict = None) -> int:
    """Count records in a table."""
    try:
        params = {"select": "id"}
        if filters:
            params.update(filters)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "count=exact"
                },
                params=params
            )

        if response.status_code == 200:
            count_header = response.headers.get("content-range", "")
            if "/" in count_header:
                total = count_header.split("/")[1]
                return int(total) if total != "*" else len(response.json())
            return len(response.json())
        return 0
    except Exception:
        return 0


async def _db_query(table: str, params: dict) -> list:
    """Query records from a table."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                },
                params=params
            )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


@router.get("/overview")
async def get_overview(current_user: dict = Depends(get_current_user)):
    """Complete platform overview with all key metrics."""
    verify_founder(current_user)

    try:
        # Gather metrics
        total_users = await _db_count("profiles")
        total_websites = await _db_count("websites")
        active_websites = await _db_count("websites", {"status": "eq.published"})

        # Subscriptions
        total_subs = await _db_count("subscriptions", {"status": "eq.active"})
        basic_subs = await _db_count("subscriptions", {"status": "eq.active", "tier": "eq.basic"})
        pro_subs = await _db_count("subscriptions", {"status": "eq.active", "tier": "eq.pro"})
        enterprise_subs = await _db_count("subscriptions", {"status": "eq.active", "tier": "eq.enterprise"})

        # MRR estimate (basic=RM29, pro=RM59, enterprise=RM149)
        mrr = (basic_subs * 29) + (pro_subs * 59) + (enterprise_subs * 149)

        # Orders today
        today = datetime.utcnow().strftime("%Y-%m-%d")
        orders_today = await _db_count("delivery_orders", {"created_at": f"gte.{today}T00:00:00"})

        # AI stats
        total_disputes = await _db_count("ai_disputes") if await _db_count("ai_disputes") else 0
        total_health_scans = await _db_count("website_health_scans")

        # Credits
        credits_data = await _db_query("bina_credits", {"select": "balance"})
        total_credits = sum(float(c.get("balance", 0)) for c in credits_data)

        # Trust scores
        trust_data = await _db_query("user_trust_scores", {
            "select": "trust_level",
            "limit": "1000"
        })
        trust_dist = {}
        for t in trust_data:
            level = t.get("trust_level", "new")
            trust_dist[level] = trust_dist.get(level, 0) + 1

        return {
            "status": "success",
            "data": {
                "total_users": total_users,
                "total_websites": total_websites,
                "active_websites": active_websites,
                "mrr": mrr,
                "active_subscriptions": total_subs,
                "subscriptions_by_plan": {
                    "basic": basic_subs,
                    "pro": pro_subs,
                    "enterprise": enterprise_subs
                },
                "orders_today": orders_today,
                "total_disputes": total_disputes,
                "total_health_scans": total_health_scans,
                "total_credits_circulation": total_credits,
                "trust_distribution": trust_dist,
                "generated_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Founder overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue")
async def get_revenue(current_user: dict = Depends(get_current_user)):
    """Revenue breakdown and trends."""
    verify_founder(current_user)

    try:
        subs = await _db_query("subscriptions", {
            "select": "tier,status,created_at",
            "status": "eq.active"
        })

        # Revenue by plan
        plan_prices = {"basic": 29, "pro": 59, "enterprise": 149}
        revenue_by_plan = {}
        for sub in subs:
            tier = sub.get("tier", "free")
            price = plan_prices.get(tier, 0)
            revenue_by_plan[tier] = revenue_by_plan.get(tier, 0) + price

        total_mrr = sum(revenue_by_plan.values())

        return {
            "status": "success",
            "data": {
                "total_mrr": total_mrr,
                "arr": total_mrr * 12,
                "revenue_by_plan": revenue_by_plan,
                "total_subscribers": len(subs)
            }
        }

    except Exception as e:
        logger.error(f"Revenue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """User growth metrics."""
    verify_founder(current_user)

    try:
        profiles = await _db_query("profiles", {
            "select": "id,created_at",
            "order": "created_at.desc",
            "limit": "1000"
        })

        # Group by month
        monthly = {}
        for p in profiles:
            month = p.get("created_at", "")[:7]
            monthly[month] = monthly.get(month, 0) + 1

        return {
            "status": "success",
            "data": {
                "total_users": len(profiles),
                "monthly_signups": monthly,
                "recent_users": profiles[:10]
            }
        }

    except Exception as e:
        logger.error(f"Users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-performance")
async def get_ai_performance(current_user: dict = Depends(get_current_user)):
    """AI system performance statistics."""
    verify_founder(current_user)

    try:
        health_scans = await _db_count("website_health_scans")
        ai_responses = await _db_count("ai_chat_responses")
        verifications = await _db_count("order_verifications")
        rebuilds = await _db_count("website_rebuilds")

        return {
            "status": "success",
            "data": {
                "total_health_scans": health_scans,
                "total_ai_chat_responses": ai_responses,
                "total_order_verifications": verifications,
                "total_website_rebuilds": rebuilds
            }
        }

    except Exception as e:
        logger.error(f"AI performance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credits")
async def get_credits(current_user: dict = Depends(get_current_user)):
    """BinaCredit economy health."""
    verify_founder(current_user)

    try:
        credits = await _db_query("bina_credits", {"select": "user_id,balance"})
        transactions = await _db_query("credit_transactions", {
            "select": "transaction_type,amount,created_at",
            "order": "created_at.desc",
            "limit": "500"
        })

        total_balance = sum(float(c.get("balance", 0)) for c in credits)
        total_earned = sum(float(t.get("amount", 0)) for t in transactions if float(t.get("amount", 0)) > 0)
        total_spent = abs(sum(float(t.get("amount", 0)) for t in transactions if float(t.get("amount", 0)) < 0))

        # By type
        by_type = {}
        for t in transactions:
            tt = t.get("transaction_type", "other")
            by_type[tt] = by_type.get(tt, 0) + float(t.get("amount", 0))

        return {
            "status": "success",
            "data": {
                "total_in_circulation": total_balance,
                "total_wallets": len(credits),
                "total_earned": total_earned,
                "total_spent": total_spent,
                "by_transaction_type": by_type,
                "recent_transactions": transactions[:20]
            }
        }

    except Exception as e:
        logger.error(f"Credits error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{export_type}")
async def export_csv(
    export_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Export data as CSV."""
    verify_founder(current_user)

    valid_types = ["users", "subscriptions", "credits", "penalties", "trust_scores"]
    if export_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Jenis eksport tidak sah. Pilih: {', '.join(valid_types)}")

    table_map = {
        "users": ("profiles", "id,full_name,business_name,created_at"),
        "subscriptions": ("subscriptions", "user_id,tier,status,created_at"),
        "credits": ("bina_credits", "user_id,balance"),
        "penalties": ("restaurant_penalties", "website_id,penalty_type,reason,is_active,created_at"),
        "trust_scores": ("user_trust_scores", "user_id,score,trust_level,credit_multiplier")
    }

    table, columns = table_map[export_type]
    data = await _db_query(table, {"select": columns, "limit": "5000"})

    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=binaapp_{export_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )
