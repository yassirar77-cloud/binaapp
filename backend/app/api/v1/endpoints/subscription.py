"""
Subscription Management Endpoints
Handles subscription status, usage tracking, limits, transactions, and addons
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from app.services.subscription_service import subscription_service
from app.services.supabase_client import supabase_service
from app.services.toyyibpay_service import toyyibpay_service
from app.core.security import get_current_user
from app.core.config import settings

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class CheckLimitRequest(BaseModel):
    action: str  # 'create_website', 'add_menu_item', 'generate_ai_hero', etc.


class UpgradeRequest(BaseModel):
    new_plan: str  # 'basic' or 'pro'
    prorate: bool = False


class AddonPurchaseRequest(BaseModel):
    addon_type: str  # 'ai_image', 'ai_hero', 'website', 'rider', 'zone'
    quantity: int = 1


class UseAddonRequest(BaseModel):
    addon_type: str
    quantity: int = 1


# =============================================================================
# Subscription Status Endpoints
# =============================================================================

@router.get("/status")
async def get_subscription_status(current_user: dict = Depends(get_current_user)):
    """
    Get current subscription status
    Returns plan name, status, dates, and days remaining
    """
    try:
        user_id = current_user.get("sub")
        status_data = await subscription_service.get_subscription_status(user_id)
        return status_data
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan status langganan"
        )


@router.get("/usage")
async def get_usage_with_limits(current_user: dict = Depends(get_current_user)):
    """
    Get current usage vs limits
    Returns usage data for all tracked resources with percentages
    """
    try:
        user_id = current_user.get("sub")
        usage_data = await subscription_service.get_usage_with_limits(user_id)
        return usage_data
    except Exception as e:
        logger.error(f"Error getting usage with limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan data penggunaan"
        )


@router.post("/check-limit")
async def check_limit(
    request: CheckLimitRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if user can perform a specific action
    Returns whether action is allowed and relevant limit info
    """
    try:
        user_id = current_user.get("sub")
        result = await subscription_service.check_limit(user_id, request.action)
        return result
    except Exception as e:
        logger.error(f"Error checking limit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyemak had"
        )


# =============================================================================
# Subscription Plans Endpoints
# =============================================================================

@router.get("/plans")
async def get_subscription_plans():
    """
    Get all available subscription plans with pricing and features
    """
    try:
        plans = await subscription_service.get_subscription_plans()

        # Add feature descriptions
        feature_descriptions = {
            "starter": [
                "1 laman web",
                "20 item menu",
                "1 penjanaan AI hero",
                "5 imej AI",
                "1 zon penghantaran",
                "Subdomain",
                "Semua integrasi",
                "Sokongan e-mel"
            ],
            "basic": [
                "5 laman web",
                "Item menu tanpa had",
                "10 penjanaan AI hero/bulan",
                "30 imej AI/bulan",
                "5 zon penghantaran",
                "Subdomain tersuai",
                "AI keutamaan",
                "Analitik",
                "Pembayaran QR",
                "Borang hubungi",
                "Sokongan keutamaan"
            ],
            "pro": [
                "Laman web tanpa had",
                "Item menu tanpa had",
                "Penjanaan AI tanpa had",
                "Imej AI tanpa had",
                "Zon penghantaran tanpa had",
                "10 rider (GPS tracking)",
                "AI lanjutan",
                "Subdomain tersuai"
            ]
        }

        # Enhance plans with features
        enhanced_plans = []
        for plan in plans:
            plan_name = plan.get("plan_name", "starter")
            enhanced_plans.append({
                **plan,
                "feature_list": feature_descriptions.get(plan_name, [])
            })

        return {"plans": enhanced_plans}
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan pelan langganan"
        )


@router.post("/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create payment for subscription upgrade
    Returns ToyyibPay payment URL
    """
    try:
        user_id = current_user.get("sub")
        email = current_user.get("email")
        new_plan = request.new_plan.lower()

        # Validate plan
        valid_plans = ["starter", "basic", "pro"]
        if new_plan not in valid_plans:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pelan tidak sah: {new_plan}"
            )

        # Get current subscription
        current_sub = await subscription_service.get_subscription_status(user_id)
        current_plan = current_sub.get("plan_name", "starter")

        # Check if upgrade is valid
        plan_order = {"starter": 1, "basic": 2, "pro": 3}
        if plan_order.get(new_plan, 0) <= plan_order.get(current_plan, 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda hanya boleh naik taraf ke pelan yang lebih tinggi"
            )

        price = subscription_service.TIER_PRICES.get(new_plan, 29.00)

        # Get user details
        user_data = await supabase_service.get_user_by_id(user_id)
        user_phone = user_data.get("phone", "0123456789") if user_data else "0123456789"
        customer_name = user_data.get("full_name", email.split("@")[0]) if user_data else "Customer"

        # Create ToyyibPay bill
        external_ref = f"UPGRADE_{new_plan}_{user_id[:16]}"

        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp {new_plan.upper()} Plan Upgrade",
            bill_description=f"Naik taraf ke pelan {new_plan.upper()}",
            bill_amount=price,
            bill_email=email,
            bill_phone=user_phone,
            bill_name_customer=customer_name,
            bill_external_reference_no=external_ref
        )

        if result.get("success"):
            bill_code = result.get("bill_code")

            # Store transaction record
            try:
                invoice_number = await subscription_service.generate_invoice_number()
                await supabase_service.insert_record("transactions", {
                    "user_id": user_id,
                    "transaction_type": "subscription",
                    "item_description": f"Upgrade to {new_plan.upper()} Plan",
                    "amount": price,
                    "toyyibpay_bill_code": bill_code,
                    "payment_status": "pending",
                    "invoice_number": invoice_number,
                    "metadata": {"plan": new_plan, "previous_plan": current_plan}
                })
            except Exception as db_error:
                logger.warning(f"Could not store transaction: {db_error}")

            return {
                "success": True,
                "payment_url": result.get("payment_url"),
                "bill_code": bill_code,
                "new_plan": new_plan,
                "amount": price
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Gagal mencipta pembayaran")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memproses naik taraf"
        )


@router.post("/renew")
async def renew_subscription(current_user: dict = Depends(get_current_user)):
    """
    Create payment for subscription renewal.
    Returns ToyyibPay payment URL for paid plans.
    Auto-confirms immediately for free plans (RM 0.00).
    """
    try:
        user_id = current_user.get("sub")
        email = current_user.get("email")

        # Get current subscription
        sub_status = await subscription_service.get_subscription_status(user_id)
        plan_name = sub_status.get("plan_name", "starter")
        price = subscription_service.TIER_PRICES.get(plan_name, 5.00)

        # Normalize legacy "free" tier to "starter" for display,
        # but keep price as 0.00 for auto-confirmation
        display_plan = plan_name if plan_name != "free" else "starter"

        # FREE plan renewal: auto-confirm without ToyyibPay
        if price <= 0:
            logger.info(f"Free plan renewal for user {user_id}, auto-confirming...")

            # Renew subscription directly
            renewal_result = await subscription_service.renew_subscription(user_id)

            # Record the transaction as immediately successful
            try:
                invoice_number = await subscription_service.generate_invoice_number()
                await supabase_service.insert_record("transactions", {
                    "user_id": user_id,
                    "transaction_type": "renewal",
                    "item_description": f"{display_plan.upper()} Plan Renewal (Percuma)",
                    "amount": 0,
                    "payment_status": "success",
                    "payment_date": datetime.utcnow().isoformat(),
                    "invoice_number": invoice_number,
                    "metadata": {"plan": plan_name, "auto_confirmed": True}
                })
            except Exception as db_error:
                logger.warning(f"Could not store free renewal transaction: {db_error}")

            return {
                "success": True,
                "payment_url": None,
                "auto_confirmed": True,
                "amount": 0,
                "plan": display_plan,
                "message": "Pembaharuan percuma berjaya!"
            }

        # PAID plan renewal: create ToyyibPay bill
        # Get user details
        user_data = await supabase_service.get_user_by_id(user_id)
        user_phone = user_data.get("phone", "0123456789") if user_data else "0123456789"
        customer_name = user_data.get("full_name", email.split("@")[0]) if user_data else "Customer"

        # Create ToyyibPay bill
        external_ref = f"RENEW_{plan_name}_{user_id[:16]}"

        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp {display_plan.upper()} Renewal",
            bill_description=f"Perbaharui langganan {display_plan.upper()}",
            bill_amount=price,
            bill_email=email,
            bill_phone=user_phone,
            bill_name_customer=customer_name,
            bill_external_reference_no=external_ref
        )

        if result.get("success"):
            bill_code = result.get("bill_code")

            # Store transaction record
            try:
                invoice_number = await subscription_service.generate_invoice_number()
                await supabase_service.insert_record("transactions", {
                    "user_id": user_id,
                    "transaction_type": "renewal",
                    "item_description": f"{display_plan.upper()} Plan Renewal",
                    "amount": price,
                    "toyyibpay_bill_code": bill_code,
                    "payment_status": "pending",
                    "invoice_number": invoice_number,
                    "metadata": {"plan": plan_name}
                })
            except Exception as db_error:
                logger.warning(f"Could not store transaction: {db_error}")

            return {
                "success": True,
                "payment_url": result.get("payment_url"),
                "bill_code": bill_code,
                "amount": price,
                "plan": display_plan
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Gagal mencipta pembayaran")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renewing subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memproses pembaharuan"
        )


# =============================================================================
# Addon Endpoints
# =============================================================================

@router.get("/addons/available")
async def get_available_addons():
    """
    Get available addons with pricing
    """
    try:
        addons = [
            {
                "type": "ai_image",
                "name": "Imej AI",
                "description": "Jana 1 imej AI untuk menu",
                "price": 1.00
            },
            {
                "type": "ai_hero",
                "name": "Penjanaan AI Hero",
                "description": "Jana 1 bahagian hero AI",
                "price": 2.00
            },
            {
                "type": "website",
                "name": "Laman Web Tambahan",
                "description": "Tambah 1 slot laman web",
                "price": 5.00
            },
            {
                "type": "rider",
                "name": "Rider Tambahan",
                "description": "Tambah 1 slot rider",
                "price": 3.00
            },
            {
                "type": "zone",
                "name": "Zon Penghantaran Tambahan",
                "description": "Tambah 1 zon penghantaran",
                "price": 2.00
            }
        ]

        return {"addons": addons}
    except Exception as e:
        logger.error(f"Error getting addons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan senarai addon"
        )


@router.get("/addons/credits")
async def get_addon_credits(current_user: dict = Depends(get_current_user)):
    """
    Get user's available addon credits
    """
    try:
        user_id = current_user.get("sub")
        credits = await subscription_service.get_available_addon_credits(user_id)
        return {"credits": credits}
    except Exception as e:
        logger.error(f"Error getting addon credits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan kredit addon"
        )


@router.post("/addons/purchase")
async def purchase_addon(
    request: AddonPurchaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Purchase addon credits
    Returns ToyyibPay payment URL
    """
    try:
        user_id = current_user.get("sub")
        email = current_user.get("email")
        addon_type = request.addon_type
        quantity = max(1, request.quantity)

        # Validate addon type
        if addon_type not in subscription_service.ADDON_PRICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Jenis addon tidak sah: {addon_type}"
            )

        unit_price = subscription_service.ADDON_PRICES[addon_type]
        total_price = unit_price * quantity

        # Get user details
        user_data = await supabase_service.get_user_by_id(user_id)
        user_phone = user_data.get("phone", "0123456789") if user_data else "0123456789"
        customer_name = user_data.get("full_name", email.split("@")[0]) if user_data else "Customer"

        # Addon names in Malay
        addon_names = {
            "ai_image": "Imej AI",
            "ai_hero": "Penjanaan AI Hero",
            "website": "Laman Web Tambahan",
            "rider": "Rider Tambahan",
            "zone": "Zon Penghantaran"
        }

        addon_name = addon_names.get(addon_type, addon_type)

        # Create ToyyibPay bill
        external_ref = f"ADDON_{addon_type}_{user_id[:12]}"

        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp {addon_name} x{quantity}",
            bill_description=f"Pembelian {quantity}x {addon_name}",
            bill_amount=total_price,
            bill_email=email,
            bill_phone=user_phone,
            bill_name_customer=customer_name,
            bill_external_reference_no=external_ref
        )

        if result.get("success"):
            bill_code = result.get("bill_code")

            # Store transaction record
            try:
                invoice_number = await subscription_service.generate_invoice_number()
                transaction_record = await supabase_service.insert_record("transactions", {
                    "user_id": user_id,
                    "transaction_type": "addon",
                    "item_description": f"{addon_name} x{quantity}",
                    "amount": total_price,
                    "toyyibpay_bill_code": bill_code,
                    "payment_status": "pending",
                    "invoice_number": invoice_number,
                    "metadata": {
                        "addon_type": addon_type,
                        "quantity": quantity,
                        "unit_price": unit_price
                    }
                })

                transaction_id = transaction_record.get("transaction_id") if transaction_record else None
            except Exception as db_error:
                logger.warning(f"Could not store transaction: {db_error}")
                transaction_id = None

            return {
                "success": True,
                "payment_url": result.get("payment_url"),
                "bill_code": bill_code,
                "transaction_id": transaction_id,
                "addon_type": addon_type,
                "quantity": quantity,
                "total_amount": total_price
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Gagal mencipta pembayaran")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing addon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memproses pembelian addon"
        )


@router.post("/addons/use")
async def use_addon(
    request: UseAddonRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Use addon credits
    Called when user performs an action that exceeds their plan limit
    """
    try:
        user_id = current_user.get("sub")
        addon_type = request.addon_type
        quantity = max(1, request.quantity)

        # Check available credits
        credits = await subscription_service.get_available_addon_credits(user_id, addon_type)
        available = credits.get(addon_type, 0)

        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kredit tidak mencukupi. Baki: {available}"
            )

        # Use credits
        success_count = 0
        for _ in range(quantity):
            if await subscription_service.use_addon_credit(user_id, addon_type):
                success_count += 1

        if success_count == quantity:
            return {
                "success": True,
                "used": success_count,
                "remaining": available - success_count
            }
        else:
            return {
                "success": False,
                "used": success_count,
                "remaining": available - success_count,
                "message": f"Hanya {success_count} daripada {quantity} kredit berjaya digunakan"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error using addon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menggunakan kredit addon"
        )


# =============================================================================
# Transaction History Endpoints
# =============================================================================

@router.get("/transactions")
async def get_transactions(
    current_user: dict = Depends(get_current_user),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's transaction history
    """
    try:
        user_id = current_user.get("sub")

        url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
        params = {
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset)
        }

        if from_date:
            params["created_at"] = f"gte.{from_date}"
        if to_date:
            params["created_at"] = f"lte.{to_date}"
        if transaction_type and transaction_type != "all":
            params["transaction_type"] = f"eq.{transaction_type}"

        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code == 200:
            transactions = response.json()

            # Calculate total spent
            total_spent = sum(
                t.get("amount", 0) for t in transactions
                if t.get("payment_status") == "success"
            )

            return {
                "transactions": transactions,
                "total_spent": total_spent,
                "count": len(transactions)
            }

        return {"transactions": [], "total_spent": 0, "count": 0}

    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan sejarah transaksi"
        )


@router.get("/transactions/{transaction_id}")
async def get_transaction_detail(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get transaction detail
    """
    try:
        user_id = current_user.get("sub")

        url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
        params = {
            "transaction_id": f"eq.{transaction_id}",
            "user_id": f"eq.{user_id}"
        }

        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code == 200:
            records = response.json()
            if records:
                return records[0]

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaksi tidak dijumpai"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mendapatkan butiran transaksi"
        )


# =============================================================================
# Payment Verification Endpoint
# =============================================================================

class VerifyPaymentRequest(BaseModel):
    bill_code: str
    status_id: Optional[str] = None


@router.post("/verify-payment")
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify payment status from ToyyibPay and process if successful.
    Called by frontend after returning from payment gateway.

    1. Get bill status from ToyyibPay API
    2. Find transaction in database by bill_code
    3. If paid (status_id = 1), update transaction to 'completed'
    4. Apply subscription upgrade or addon credits
    5. Return success
    """
    try:
        user_id = current_user.get("sub")
        bill_code = request.bill_code
        status_id = request.status_id

        logger.info(f"Verifying payment for user {user_id}, bill_code: {bill_code}, status_id: {status_id}")

        # Step 1: Get bill status from ToyyibPay API
        toyyibpay_result = toyyibpay_service.get_bill_transactions(bill_code)

        payment_status = "unknown"
        toyyibpay_status = None

        if toyyibpay_result.get("success"):
            transactions = toyyibpay_result.get("transactions", [])
            if isinstance(transactions, list) and len(transactions) > 0:
                # Get the latest transaction
                latest_txn = transactions[0]
                toyyibpay_status = latest_txn.get("billpaymentStatus")

                # ToyyibPay status: 1 = Paid, 2 = Pending, 3 = Failed
                if toyyibpay_status == "1":
                    payment_status = "paid"
                elif toyyibpay_status == "2":
                    payment_status = "pending"
                elif toyyibpay_status == "3":
                    payment_status = "failed"

                logger.info(f"ToyyibPay transaction status: {toyyibpay_status} -> {payment_status}")
        else:
            # Fallback to URL status_id if ToyyibPay API fails
            if status_id == "1":
                payment_status = "paid"
            elif status_id == "2":
                payment_status = "pending"
            elif status_id == "3":
                payment_status = "failed"
            logger.warning(f"ToyyibPay API failed, using URL status_id: {status_id}")

        # Step 2: Find transaction in database by bill_code
        import httpx

        url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
        params = {
            "toyyibpay_bill_code": f"eq.{bill_code}",
            "select": "*"
        }
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

        transaction = None
        if response.status_code == 200:
            records = response.json()
            if records:
                transaction = records[0]
                logger.info(f"Found transaction: {transaction.get('transaction_id')}")

        if not transaction:
            logger.warning(f"No transaction found for bill_code: {bill_code}")
            return {
                "success": False,
                "payment_status": payment_status,
                "message": "Transaksi tidak dijumpai"
            }

        # Verify transaction belongs to current user
        if transaction.get("user_id") != user_id:
            logger.warning(f"Transaction user mismatch: {transaction.get('user_id')} != {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaksi tidak sah"
            )

        # Step 3: If paid, update transaction and apply benefits
        if payment_status == "paid" and transaction.get("payment_status") != "success":
            logger.info(f"Processing successful payment for transaction {transaction.get('transaction_id')}")

            # Update transaction status to success
            transaction_id = transaction.get("transaction_id")
            update_url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
            update_params = {"transaction_id": f"eq.{transaction_id}"}
            update_data = {
                "payment_status": "success",
                "payment_date": datetime.utcnow().isoformat()
            }

            async with httpx.AsyncClient() as client:
                patch_resp = await client.patch(
                    update_url,
                    headers={**headers, "Prefer": "return=minimal"},
                    params=update_params,
                    json=update_data
                )

            if patch_resp.status_code not in [200, 204]:
                logger.error(f"Failed to update transaction {transaction_id}: {patch_resp.status_code} {patch_resp.text}")
            else:
                logger.info(f"Transaction {transaction_id} marked as success")

            # Step 4: Apply subscription upgrade or addon credits
            transaction_type = transaction.get("transaction_type")
            metadata = transaction.get("metadata", {})

            if transaction_type == "subscription":
                # Apply subscription upgrade
                plan = metadata.get("plan", "basic")
                await _apply_subscription_upgrade(user_id, plan, headers)
                logger.info(f"Applied subscription upgrade to {plan} for user {user_id}")

            elif transaction_type == "renewal":
                # Apply subscription renewal
                plan = metadata.get("plan", "starter")
                await _apply_subscription_renewal(user_id, plan, headers)
                logger.info(f"Applied subscription renewal for {plan} for user {user_id}")

            elif transaction_type == "addon":
                # Apply addon credits
                addon_type = metadata.get("addon_type")
                quantity = metadata.get("quantity", 1)
                success = await _apply_addon_credits(user_id, addon_type, quantity, headers, transaction_id, bill_code)
                if success:
                    logger.info(f"Applied {quantity}x {addon_type} addon for user {user_id}")
                else:
                    logger.error(f"Failed to apply addon credits for user {user_id}")
                    # Don't fail the whole response - transaction is already marked as success

            return {
                "success": True,
                "payment_status": "paid",
                "transaction_type": transaction_type,
                "message": "Pembayaran berjaya disahkan"
            }

        elif payment_status == "paid":
            # Transaction already marked as success — but addon credits may
            # not have been applied if the callback marked the transaction as
            # success before _process_addon_payment ran (race condition).
            # Verify addon_purchases actually exist; create them if missing.
            transaction_type = transaction.get("transaction_type")
            if transaction_type == "addon":
                metadata = transaction.get("metadata", {})
                addon_type = metadata.get("addon_type")
                quantity = metadata.get("quantity", 1)
                transaction_id = transaction.get("transaction_id")

                if addon_type:
                    # Check if addon_purchases record exists for this transaction
                    existing = await _check_addon_purchases_exist(
                        user_id, transaction_id, headers
                    )
                    if not existing:
                        logger.warning(
                            f"⚠️ Transaction {transaction_id} is 'success' but no addon_purchases found. "
                            f"Applying addon credits now (race condition recovery)."
                        )
                        await _apply_addon_credits(
                            user_id, addon_type, quantity, headers, transaction_id, bill_code
                        )

            return {
                "success": True,
                "payment_status": "paid",
                "message": "Pembayaran sudah diproses"
            }

        else:
            return {
                "success": False,
                "payment_status": payment_status,
                "message": "Pembayaran belum selesai" if payment_status == "pending" else "Pembayaran gagal"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying payment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengesahkan pembayaran"
        )


async def _apply_subscription_upgrade(user_id: str, plan: str, headers: dict):
    """Apply subscription upgrade for user"""
    import httpx
    from datetime import timedelta

    # Calculate new end date (30 days from now)
    end_date = (datetime.utcnow() + timedelta(days=30)).isoformat()

    # Check if subscription exists
    url = f"{settings.SUPABASE_URL}/rest/v1/subscriptions"
    params = {"user_id": f"eq.{user_id}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code == 200 and response.json():
            # Update existing subscription
            resp = await client.patch(
                url,
                headers={**headers, "Prefer": "return=minimal"},
                params=params,
                json={
                    "tier": plan,
                    "status": "active",
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": end_date,
                    "auto_renew": True
                }
            )
            if resp.status_code not in [200, 204]:
                logger.error(f"Failed to update subscription for {user_id}: {resp.status_code} {resp.text}")
        else:
            # Create new subscription
            resp = await client.post(
                url,
                headers={**headers, "Prefer": "return=minimal"},
                json={
                    "user_id": user_id,
                    "tier": plan,
                    "status": "active",
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": end_date,
                    "auto_renew": True
                }
            )
            if resp.status_code not in [200, 201, 204]:
                logger.error(f"Failed to create subscription for {user_id}: {resp.status_code} {resp.text}")


async def _apply_subscription_renewal(user_id: str, plan: str, headers: dict):
    """Apply subscription renewal for user"""
    import httpx
    from datetime import timedelta

    # Calculate new end date (30 days from now)
    end_date = (datetime.utcnow() + timedelta(days=30)).isoformat()

    url = f"{settings.SUPABASE_URL}/rest/v1/subscriptions"
    params = {"user_id": f"eq.{user_id}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code == 200 and response.json():
            # Update existing subscription - extend end date
            existing = response.json()[0]
            current_end = existing.get("end_date")

            # If current subscription hasn't expired, extend from current end date
            if current_end:
                try:
                    current_end_dt = datetime.fromisoformat(current_end.replace("Z", "+00:00"))
                    if current_end_dt > datetime.utcnow().replace(tzinfo=current_end_dt.tzinfo):
                        end_date = (current_end_dt + timedelta(days=30)).isoformat()
                except:
                    pass

            resp = await client.patch(
                url,
                headers={**headers, "Prefer": "return=minimal"},
                params=params,
                json={
                    "status": "active",
                    "end_date": end_date,
                    "auto_renew": True
                }
            )
            if resp.status_code not in [200, 204]:
                logger.error(f"Failed to renew subscription for {user_id}: {resp.status_code} {resp.text}")
        else:
            # Create new subscription if doesn't exist
            resp = await client.post(
                url,
                headers={**headers, "Prefer": "return=minimal"},
                json={
                    "user_id": user_id,
                    "tier": plan,
                    "status": "active",
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": end_date,
                    "auto_renew": True
                }
            )
            if resp.status_code not in [200, 201, 204]:
                logger.error(f"Failed to create subscription for {user_id}: {resp.status_code} {resp.text}")


async def _apply_addon_credits(user_id: str, addon_type: str, quantity: int, headers: dict, transaction_id: str = None, bill_code: str = None):
    """
    Apply addon credits for user.
    Creates a record in addon_purchases table with status 'active'.

    Schema (production table - migration 015 + 024):
    id (PK), user_id, toyyibpay_bill_code, addon_type, quantity, status,
    transaction_id, reference_no, created_at, updated_at,
    quantity_used, unit_price, total_price, expires_at

    Status values: 'active', 'depleted', 'expired'
    """
    import httpx
    from datetime import datetime, timedelta

    # Addon prices - must match subscription_service.ADDON_PRICES
    ADDON_PRICES = {
        "ai_image": 1.00,
        "ai_hero": 2.00,
        "website": 5.00,
        "rider": 3.00,
        "zone": 2.00
    }

    unit_price = ADDON_PRICES.get(addon_type, 1.00)
    total_price = unit_price * quantity
    expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()

    url = f"{settings.SUPABASE_URL}/rest/v1/addon_purchases"

    logger.info(f"📝 Applying addon credits for user {user_id}: {addon_type} x{quantity}")
    logger.info(f"   Unit price: RM{unit_price}, Total: RM{total_price}")

    try:
        # Idempotency check: skip if addon_purchases record already exists
        # for this transaction to prevent duplicates from callback + verify-payment race
        if transaction_id:
            async with httpx.AsyncClient() as client:
                check_resp = await client.get(
                    url,
                    headers=headers,
                    params={
                        "transaction_id": f"eq.{transaction_id}",
                        "select": "id"
                    }
                )
            if check_resp.status_code == 200 and check_resp.json():
                logger.info(f"⏭️ Addon purchase already exists for transaction {transaction_id}, skipping duplicate creation")
                return True

        insert_data = {
            "user_id": user_id,
            "addon_type": addon_type,
            "quantity": quantity,
            "quantity_used": 0,
            "unit_price": float(unit_price),
            "total_price": float(total_price),
            "status": "active",
            "expires_at": expires_at
        }

        # Link to transaction record if we have a valid UUID transaction_id
        if transaction_id:
            insert_data["transaction_id"] = transaction_id
        # Include toyyibpay_bill_code if available (migration 015 column)
        if bill_code:
            insert_data["toyyibpay_bill_code"] = bill_code

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={**headers, "Prefer": "return=representation"},
                json=insert_data
            )

        if response.status_code in [200, 201]:
            result = response.json()
            record_id = result[0].get("id") if result else "N/A"
            logger.info(f"✅ Addon credits applied successfully for user {user_id}")
            logger.info(f"   Record ID: {record_id}, Type: {addon_type}, Qty: {quantity}")
            return True
        else:
            logger.error(f"❌ Failed to apply addon credits for user {user_id}")
            logger.error(f"   Status: {response.status_code}")
            logger.error(f"   Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Error applying addon credits for user {user_id}: {e}", exc_info=True)
        return False


async def _check_addon_purchases_exist(user_id: str, transaction_id: str, headers: dict) -> bool:
    """
    Check if addon_purchases record(s) exist for a given transaction.
    Used to detect the race condition where the callback marked a transaction
    as 'success' but failed to create the addon_purchases record.
    """
    import httpx

    if not transaction_id:
        return False

    url = f"{settings.SUPABASE_URL}/rest/v1/addon_purchases"
    params = {
        "user_id": f"eq.{user_id}",
        "transaction_id": f"eq.{transaction_id}",
        "select": "id"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code == 200:
            records = response.json()
            return len(records) > 0

        return False
    except Exception as e:
        logger.error(f"Error checking addon_purchases: {e}")
        return False
