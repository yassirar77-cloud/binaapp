# Phase 2 — remaining sync Supabase `.execute()` call sites

Perf audit follow-up. The Supabase Python client is synchronous: every
`.execute()` called directly inside an `async def` blocks the uvicorn event
loop for the full DB round trip, serialising all concurrent requests.

**Phase 1 (done)** wrapped the hottest public paths in
`fastapi.concurrency.run_in_threadpool`:

- `app/api/v1/endpoints/delivery.py` — via the `_db()` helper (31 call sites):
  public menu (`GET /menu/{id}`, `GET /menu/{id}/item/{id}`), widget config
  (`GET /config/{id}`), ring coverage (`GET /zones/{id}/cover`), order create
  (`POST /orders` incl. its customer/conversation/notification helpers),
  order tracking (`GET /orders/{n}/track`), order status (`GET /orders/{n}/status`).
- `app/middleware/subdomain.py` — the per-pageview website lookup and the
  auto-recovery insert.

**Phase 2 (todo)** — remaining direct `.execute()` calls per file, counted on
2026-07-03. Wrap with the same `_db()` pattern (or move the module to the
async client). Suggested order = traffic × count:

| File | Remaining calls | Notes |
|---|---|---|
| `app/api/v1/endpoints/delivery.py` | 76 | rider PWA endpoints, owner order management, admin rider CRUD, settings. `_db()` helper already available in this file. |
| `app/api/v1/endpoints/admin_dashboard.py` | 59 | admin-only; the `/dashboard` endpoint alone fires 10 sequential queries — batch + wrap. |
| `app/api/v1/endpoints/disputes.py` | 51 | dispute flows; medium traffic. |
| `app/main.py` | 43 | generation status polling (`GET /api/generate/status`) is polled frequently — wrap that first. |
| `app/api/v1/endpoints/chat.py` | 34 | chat polling endpoints — high frequency. |
| `app/services/ai_chatbot_service.py` | 30 | called from chat endpoints. |
| `app/services/ai_proactive_monitor.py` | 25 | scheduler context (blocking less harmful, still worth it). |
| `app/api/v1/endpoints/menu_delivery.py` | 25 | merchant menu CRUD. |
| `app/services/ai_website_doctor.py` | 20 | health scans. |
| `app/api/v1/endpoints/websites.py` | 12 | website CRUD. |
| `app/api/v1/endpoints/delivery_zones.py` | 11 | owner zone editor. |
| `app/api/v1/endpoints/penghantar_live.py` | 5 | live rider map. |
| `app/api/v1/endpoints/website_health.py` | 4 | |
| `app/api/v1/endpoints/customers.py` | 4 | |
| `app/api/v1/endpoints/monitor.py` | 1 | |
| `app/api/simple/generate.py` | 1 | |
| `app/core/supabase.py` | 1 | connection self-test at client creation. |

Regenerate this table with:

```bash
grep -rn "\.execute()" app/ --include="*.py" | grep -v "await _db(" \
  | awk -F: '{print $1}' | sort | uniq -c | sort -rn
```

## Explicitly out of scope (per owner decision, 2026-07-03)

- **Stripe** (`app/services/payment_service.py`) and **ToyyibPay**
  (`app/services/toyyibpay_service.py`, blocking `requests.post`) — payments
  stay untouched until a separately planned round.
