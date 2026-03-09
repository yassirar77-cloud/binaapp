# Test Coverage Analysis - BinaApp

> Last updated: 2026-03-09

## Current State

### Backend (Python/FastAPI) — 124 source files, ~40,276 lines

**Formal tests run by CI (`pytest --cov=app`):**

| File | Tests | What it covers |
|------|-------|---------------|
| `backend/tests/test_health.py` | 4 | Import checks for `app.main`, schemas, delivery schemas |

**Manual/standalone test scripts (NOT run by CI):**

| File | Type | What it covers |
|------|------|---------------|
| `backend/test_delivery_api.py` | Integration (live Supabase) | Supabase connection, zones, menu, order CRUD, tracking |
| `backend/test_email_polling.py` | Integration (live IMAP) | IMAP connection, service status, manual poll, AI service, scheduler |
| `backend/test_email.py` | Integration (live SMTP) | Order confirmation email send |
| `backend/test_gps_api.py` | Integration (live API) | GPS updates, rider movement, location history |
| `backend/test_imap_connection.py` | Integration (live IMAP) | Raw IMAP connection test |

**Summary:** Only **4 trivial import-check tests** run in CI. The 5 standalone scripts require live infrastructure (Supabase, Zoho IMAP, running API server) and are **not part of the automated test suite**.

### Frontend (Next.js/React/TypeScript) — 53 components, 3 hooks, 10 lib modules

- **0 test files** exist
- No test framework (Jest, Vitest, etc.) is configured
- CI only runs type-check, lint, and build

### Admin Dashboard (Next.js) — ~15 source files

- **0 test files** exist
- No test framework configured

---

## Security Note

`backend/test_imap_connection.py` contains a **hardcoded email password** on line 14. This credential should be removed from version control and loaded from environment variables instead.

---

## Coverage Gaps — Ranked by Risk

### 1. CRITICAL: Authentication & Security (`backend/app/core/security.py`, `backend/app/api/v1/endpoints/auth.py`)

**Risk:** Unauthorized access, token forgery, account takeover
**Current coverage:** None
**Lines at risk:** ~304 (security.py) + auth endpoint

The security module handles JWT creation/verification with dual-secret support (custom + Supabase), password hashing, API key validation, and token refresh. None of this has automated tests.

**Recommended tests:**
- `create_access_token` — verify token structure, expiry, claims
- `decode_access_token` — valid token, expired token, tampered token, wrong secret
- `get_current_user` — valid custom JWT, valid Supabase JWT, expired token returns 401, missing `sub` claim, invalid tokens (`"undefined"`, `"null"`, empty string)
- `decode_token_for_refresh` — accepts expired tokens, rejects tampered signatures
- `verify_api_key` — valid key, invalid key, timing-attack resistance, no keys configured
- `verify_password` / `get_password_hash` — round-trip verification
- Auth endpoints: registration validation (weak passwords, duplicate emails), login flow, token refresh

### 2. CRITICAL: Payment Processing (`backend/app/services/payment_service.py`, `toyyibpay_service.py`)

**Risk:** Financial loss, double charges, failed refunds
**Current coverage:** None

**Recommended tests:**
- Stripe checkout session creation (mock `stripe` module)
- Webhook signature verification — valid, invalid, replay attack
- Payment status transitions — success, failure, pending
- ToyyibPay bill creation and callback handling
- Idempotency — duplicate webhook delivery must not double-charge
- Plan pricing accuracy (PLANS dict matches expected values)
- Refund processing and error handling

### 3. CRITICAL: Subscription Guard Middleware (`backend/app/middleware/subscription_guard.py`)

**Risk:** Users bypassing subscription limits, or paying users being incorrectly locked out
**Current coverage:** None
**Lines at risk:** ~1,043 (middleware directory)

**Recommended tests:**
- Locked subscription blocks protected routes, returns correct HTTP status
- Active subscription allows access
- Grace period handling (expired but within grace)
- Feature gating per tier (free vs basic vs pro vs enterprise)
- Edge cases: missing subscription data, database errors

### 4. HIGH: Order & Delivery Logic (`backend/app/api/v1/endpoints/delivery.py`, `menu_delivery.py`)

**Risk:** Incorrect orders, wrong pricing, delivery failures
**Current coverage:** Manual scripts only (not in CI)

**Recommended tests:**
- Order creation — valid data, missing required fields, invalid zone
- Price calculation — subtotal, delivery fee, discounts, rounding
- Order status state machine (pending → confirmed → preparing → delivering → delivered)
- Invalid status transitions rejected (e.g., delivered → pending)
- Delivery zone boundary validation (coordinates in/out of zone)
- Menu item availability checks and out-of-stock handling

### 5. HIGH: AI Services (7 files, ~3,500+ lines)

**Risk:** Bad AI responses to customers, incorrect content generation, prompt injection
**Current coverage:** None

Files: `ai_chatbot_service.py`, `ai_chat_responder.py`, `ai_email_support.py`, `ai_order_verifier.py`, `ai_website_rebuilder.py`, `ai_website_doctor.py`, `ai_service.py`, `ai_sla_service.py`, `ai_proactive_monitor.py`

**Recommended tests:**
- Prompt construction correctness (no API call needed — just verify the built string)
- Input sanitization before sending to LLM (prevent prompt injection)
- Response parsing — valid JSON, malformed output, empty response
- Fallback behavior when AI service is unavailable or returns errors
- Rate limiting / token budget enforcement
- Order verification logic (mock AI response, test the business decision)
- SLA monitoring thresholds and alert triggering

### 6. HIGH: Subscription & Billing (`backend/app/services/subscription_service.py`, `subscription_reminder_service.py`)

**Risk:** Users losing access, billing errors, missed reminders
**Current coverage:** None

**Recommended tests:**
- Subscription creation and activation
- Plan upgrade/downgrade logic and proration
- Expiry detection and grace period handling
- Feature limits per tier (max websites, etc.)
- Reminder email scheduling at correct intervals

### 7. MEDIUM: Chat System (`backend/app/api/v1/endpoints/chat.py`, `ai_chat.py`)

**Risk:** Lost messages, broken real-time communication
**Current coverage:** None

**Recommended tests:**
- Message creation and retrieval
- Conversation threading
- AI chat response integration (mock AI)
- Chat settings CRUD (`ai_chat_settings.py`)

### 8. MEDIUM: Email Service (`backend/app/services/email_service.py`, `email_polling_service.py`)

**Risk:** Missed customer emails, broken notifications
**Current coverage:** Manual scripts only

**Recommended tests:**
- Email template rendering with different order data (edge cases: empty items, long names)
- SMTP connection error handling (mock `aiosmtplib`)
- Email polling — parsing incoming emails (mock `imap_tools`)
- Thread matching for reply emails
- Escalation logic when AI confidence is below threshold

### 9. MEDIUM: Trust Score & Dispute Systems

**Risk:** Incorrect trust scores, unfair dispute outcomes
**Current coverage:** None

Files: `trust_score_service.py`, `dispute_service.py`, `restaurant_penalty_service.py`

**Recommended tests:**
- Trust score calculation formula with various inputs
- Score update on order completion/cancellation/dispute
- Dispute creation, evidence submission, resolution flow
- Penalty calculation, application, and automatic removal
- Escalated dispute routing

### 10. MEDIUM: Pydantic Schemas (`backend/app/models/schemas.py`, `delivery_schemas.py`, `dispute_schemas.py`)

**Risk:** Invalid data accepted, valid data rejected
**Current coverage:** Import-only checks

**Recommended tests:**
- Schema validation with valid data
- Rejection of invalid data (missing required fields, wrong types, out-of-range values)
- Field validators (e.g., `WebsiteGenerationRequest.description` min_length=10)
- Enum completeness (all status values handled)

### 11. MEDIUM: Frontend Utility Functions (`frontend/src/lib/`)

**Risk:** Silent data corruption, broken UI behavior
**Current coverage:** None

High-value targets for unit testing:
- `lib/utils.ts` — general utility functions
- `lib/mapUtils.ts` — coordinate/distance calculations (haversine, boundary checks)
- `lib/businessConfig.ts` — business rule configuration
- `lib/chatApi.ts` — API request construction and error handling
- `lib/api.ts` — main API client, auth header injection
- `hooks/useSubscription.ts` — subscription state derivation

### 12. LOW-MEDIUM: Image Moderation (`backend/app/services/image_moderation_service.py`)

**Risk:** Inappropriate content displayed on customer sites
**Current coverage:** None

**Recommended tests:**
- Moderation decision logic (mock external API)
- Handling of various image formats and sizes
- Fallback when moderation service is unavailable

### 13. LOW: Webhook, Notification, Storage Services

**Risk:** Missed events, data inconsistency
**Current coverage:** None

**Recommended tests:**
- Webhook signature validation and payload parsing
- Notification service — correct notification type routing
- Storage service — upload, download, delete with mocked Supabase storage

---

## Recommended Action Plan

### Phase 1 — Testing Infrastructure (1-2 days)

1. **Backend: Create `conftest.py` with core fixtures**
   - Mock Supabase client (intercept all `.table()` calls)
   - FastAPI `TestClient` fixture
   - Fake JWT tokens for authenticated requests
   - Mock environment variables via `monkeypatch`

2. **Frontend: Set up Vitest + React Testing Library**
   - Add to `frontend/package.json`: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`
   - Create `vitest.config.ts`
   - Add `npm test` to CI pipeline

3. **Clean up standalone test scripts**
   - Remove hardcoded credentials from `test_imap_connection.py`
   - Move reusable test logic into `backend/tests/` as proper pytest tests with mocks

### Phase 2 — Cover Critical Paths (3-5 days)

4. **Auth & security tests** (`backend/tests/test_security.py`, `backend/tests/test_auth.py`)
   - JWT lifecycle, dual-secret verification, edge cases
   - Registration, login, protected endpoints via TestClient

5. **Payment service tests** (`backend/tests/test_payments.py`)
   - Mock Stripe/ToyyibPay, test all payment flows
   - Webhook handling with signature verification

6. **Subscription guard tests** (`backend/tests/test_subscription_guard.py`)
   - Middleware blocks/allows based on subscription state
   - Feature tier gating

7. **Order lifecycle tests** (`backend/tests/test_orders.py`)
   - Full CRUD, price calculations, status transitions

### Phase 3 — Broaden Coverage (5-7 days)

8. **Schema validation tests** — Ensure all Pydantic models reject bad input
9. **AI service unit tests** — Prompt building, response parsing, fallback logic (mocked LLM)
10. **Frontend lib tests** — `mapUtils`, `utils`, `businessConfig`, `chatApi`
11. **Chat system tests** — Message flow, AI integration
12. **Email service tests** — Template rendering, SMTP/IMAP error handling

### Phase 4 — Integration & E2E (ongoing)

13. **API workflow tests** — Sign up → create website → add menu → receive order → complete delivery
14. **Admin dashboard tests** — API route handlers, data aggregation logic
15. **Coverage threshold enforcement** — Add `--cov-fail-under=50` to CI, increase over time

---

## Metrics

| Area | Source Files | Lines of Code | Test Files | Estimated Coverage |
|------|-------------|---------------|------------|-------------------|
| Backend services | 36 files | ~22,755 | 0 | 0% |
| Backend endpoints | 33 files | ~15,479 | 0 | 0% |
| Backend core | 7 files | ~999 | 0 | 0% |
| Backend middleware | 3 files | ~1,043 | 0 | 0% |
| Backend models | 4 files | — | 1 (import-only) | <1% |
| Frontend components | 53 files | — | 0 | 0% |
| Frontend hooks/lib | 13 files | — | 0 | 0% |
| Admin dashboard | ~15 files | — | 0 | 0% |

**Overall estimated automated test coverage: <1%**

The CI pipeline reports coverage (`pytest --cov=app --cov-report=xml`) but currently only covers 4 import checks across `test_health.py`. The 5 standalone test scripts cover real functionality but require live infrastructure and are excluded from CI.
