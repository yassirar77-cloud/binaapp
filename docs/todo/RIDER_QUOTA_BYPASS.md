# RESOLVED: `create_rider` quota-bypass (revenue leak)

**Severity:** High — billing bypass affecting all Starter/Basic merchants
**Discovered during:** Step 3a / Task 5b rider-addon semantic verification (2026-05-21)
**Status:** FIXED — `create_rider` now depends on
`SubscriptionGuard.check_limit("add_rider")` and consumes a `rider` addon credit
on the addon-backed slot (commit "Enforce rider quota + consume rider addon
credit on create_rider"). The notes below are kept for history; a couple of the
original claims about the surrounding machinery were wrong and are corrected
inline so the record is accurate.

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
  (subscription_guard.py:371-443) exists and is the correct wrapper to attach.

…but no dependency was attached to `create_rider`, so the check never ran.

**Correction (original claim was wrong):** the guard dependency was NOT "the
standard wrapper used by create_website, generate_ai_hero, generate_ai_image,
and add_zone." In reality only `create_website` (websites.py:39) used the guard
dependency; `generate_ai_hero`/`generate_ai_image` call bare
`subscription_service.check_limit(...)` (read-only) and `add_zone` had no check
at all. So zones share the same class of bypass — see the separate zone audit.

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

On successful insert, consume the addon credit when the slot came from one:

```python
if _limit_check and _limit_check.get("using_addon"):
    await subscription_service.use_addon_credit(user_id, "rider")
```

**Correction (original claim was wrong):** do NOT call
`increment_usage(user_id, "add_rider")` — rider counts are read live from the
`riders` table (`get_actual_resource_counts`), `"add_rider"` is not mapped in
`increment_usage`'s `field_mapping`, and the call is a silent no-op. The INSERT
itself is the count increment.

Also: the original note claimed "`SubscriptionGuard.check_limit` already does
the usage increment when the addon block fires (subscription_guard.py:597-601)."
That is wrong. The guard *dependency* (subscription_guard.py:371-443) only
blocks; it neither increments usage nor consumes credits. Lines 597-601 live in
the separate `check_and_increment_usage` helper, which no endpoint calls. Credit
consumption therefore has to be wired explicitly at the call site (as above).

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
