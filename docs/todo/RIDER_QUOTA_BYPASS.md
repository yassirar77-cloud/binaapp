# TODO: Fix `create_rider` quota-bypass (revenue leak)

**Severity:** High — billing bypass affecting all Starter/Basic merchants
**Discovered during:** Step 3a / Task 5b rider-addon semantic verification (2026-05-21)
**Not fixed in this PR:** This is recorded for a separate PR after polisi v3.0 lands.

## Problem

`backend/app/api/v1/endpoints/delivery.py:1633` — `create_rider` endpoint enforces:

1. JWT (user authenticated)
2. Website ownership (`websites.user_id == current_user.sub`)

…and then inserts the rider row directly. It does **not** call
`subscription_guard.check_limit("add_rider")` before the insert.

The quota machinery exists and is wired correctly:

- `subscription_service.check_limit("add_rider")` (subscription_service.py:560,
  583-606) computes `current < limit + addon_count` using the additive formula.
- `SubscriptionGuard.check_limit("add_rider")` decorator dependency
  (subscription_guard.py:372, 580-598) is the standard wrapper used by
  `create_website`, `generate_ai_hero`, `generate_ai_image`, and `add_zone`.

…but no dependency is attached to `create_rider`, so the check never runs.

## Impact

- **Designed behaviour:** Starter/Basic (`riders_limit=0`) merchant can only add
  riders by purchasing the `rider` addon (RM3 per slot, 365-day expiry). Pro
  (`riders_limit=10`) merchant gets 10 baseline slots and can extend with
  addons. See migration 005/025 + `subscription_service.py:37-62`.
- **Enforced behaviour today:** Any tier — including Starter/Basic on `RM5/29`
  plans — can create unlimited riders without buying the rider addon. The
  RM3-per-slot product is not actually billed when used through the standard
  rider-creation flow.

## Suggested fix

```python
# backend/app/api/v1/endpoints/delivery.py
@router.post("/websites/{website_id}/riders", ...)
async def create_rider(
    website_id: str,
    rider: RiderCreateBusiness,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_rider_admin_client),
    _limit_check: dict = Depends(SubscriptionGuard.check_limit("add_rider")),
):
    ...
```

After the check, on successful insert, increment the rider usage counter:

```python
await subscription_service.increment_usage(user_id, "add_rider")
```

(`SubscriptionGuard.check_limit` already does the usage increment when the
addon block fires; verify the non-addon path also increments — see
subscription_guard.py:597-601.)

## Verification before fix lands

1. Existing merchants on Starter/Basic who have already created riders without
   buying the addon: decide policy. Grandfather them in (leave existing riders
   active), or invoice retroactively (operations call).
2. Pro merchants who have 10+ riders without buying the rider addon: same
   policy decision.
3. Run reconciliation:
   ```sql
   SELECT
     s.user_id,
     s.tier,
     COUNT(r.id) AS rider_count
   FROM public.subscriptions s
   LEFT JOIN public.websites w ON w.user_id = s.user_id
   LEFT JOIN public.riders r ON r.website_id = w.id
   WHERE s.status = 'active'
   GROUP BY s.user_id, s.tier
   HAVING COUNT(r.id) > 0;
   ```
   Cross-reference with `addon_purchases WHERE addon_type='rider' AND status='active'`.

## Related references

- Step 3a Task 5b verdict (rider addon = Option C combined) locked the
  designed semantics
- Step 3 polisi v3.0 Terms s4.4 documents the designed behaviour. When this
  fix lands, the code matches polisi
- Other queued TODO PRs (from Step 3 audit conversation):
  - Quota field naming cleanup (`ai_images_limit` vs `ai_menu_limit`, etc.)
  - Stripe legacy code removal
  - AI consent UI (60-day polisi commitment)
  - Visitor cookie banner + DNT support on generated sites (60-day commitment)
