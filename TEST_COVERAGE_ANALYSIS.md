# Test Coverage Analysis - BinaApp

## Current State

### Backend (Python/FastAPI)

**Formal tests run by CI (`pytest --cov=app`):**

| File | Tests | What it covers |
|------|-------|---------------|
| `backend/tests/test_health.py` | 4 | Import checks for `app.main`, schemas, delivery schemas |

**Manual/standalone test scripts (NOT run by CI):**

| File | Tests | What it covers |
|------|-------|---------------|
| `backend/test_delivery_api.py` | 5 | Supabase connection, delivery zones, menu, order creation, order tracking |
| `backend/test_email_polling.py` | 6 | IMAP connection, service status, manual poll, AI service, scheduler |
| `backend/test_email.py` | 1 | Order confirmation email |
| `backend/test_gps_api.py` | 5 | GPS updates, rider movement, location history |
| `backend/test_imap_connection.py` | 1 | IMAP connection test |

**Summary:** Only 4 trivial import-check tests run in CI. The standalone scripts require live infrastructure (Supabase, IMAP servers) and are not part of the automated test suite.

### Frontend (Next.js/React/TypeScript)

- **0 test files** exist
- No test framework (Jest, Vitest, etc.) is configured
- CI only runs type-check, lint, and build
- 53 component files, 3 custom hooks, 10 lib/util modules — all untested

### Admin Dashboard (Next.js)

- **0 test files** exist
- No test framework configured

---

## Coverage Gaps — Ranked by Risk

### 1. CRITICAL: Authentication & Authorization (`backend/app/api/v1/endpoints/auth.py`)

**Risk:** Security vulnerabilities, unauthorized access
**Current coverage:** None

Recommended tests:
- User registration validation (email format, password strength)
- Login with correct/incorrect credentials
- Token generation, expiry, and refresh
- Protected endpoint access without/with invalid token
- Role-based access control (admin vs regular user)

### 2. CRITICAL: Payment Processing (`backend/app/services/payment_service.py`, `toyyibpay_service.py`)

**Risk:** Financial loss, double charges, failed refunds
**Current coverage:** None

Recommended tests:
- Stripe checkout session creation (mock Stripe API)
- Payment webhook signature verification
- Successful/failed payment status transitions
- ToyyibPay bill creation and callback handling
- Idempotency — duplicate webhook delivery
- Refund processing

### 3. HIGH: Order & Delivery Logic (`backend/app/api/v1/endpoints/delivery.py`, `menu_delivery.py`)

**Risk:** Incorrect orders, wrong pricing, delivery failures
**Current coverage:** Manual scripts only (not in CI)

Recommended tests:
- Order creation with valid/invalid data
- Price calculation (subtotal, delivery fee, discounts)
- Order status transitions (pending → confirmed → preparing → delivering → delivered)
- Delivery zone validation (coordinates within zone boundaries)
- Menu item availability checks

### 4. HIGH: AI Services (7 service files, ~3,500 lines)

**Risk:** Bad AI responses to customers, incorrect content generation
**Current coverage:** None (AI email test is manual and requires live API keys)

Files: `ai_chatbot_service.py`, `ai_chat_responder.py`, `ai_email_support.py`, `ai_order_verifier.py`, `ai_website_rebuilder.py`, `ai_website_doctor.py`, `ai_service.py`

Recommended tests:
- Prompt construction and template rendering (no API call needed)
- Input sanitization before sending to AI
- Response parsing and error handling for malformed AI output
- Fallback behavior when AI service is unavailable
- Rate limiting / token budget enforcement
- Order verification logic (mock AI response, test decision-making)

### 5. HIGH: Subscription & Billing (`backend/app/services/subscription_service.py`)

**Risk:** Users losing access, billing errors
**Current coverage:** None

Recommended tests:
- Subscription creation and activation
- Plan upgrade/downgrade logic
- Expiry and grace period handling
- Feature gating based on subscription tier
- Reminder scheduling (`subscription_reminder_service.py`)

### 6. MEDIUM: Email Service (`backend/app/services/email_service.py`, `email_polling_service.py`)

**Risk:** Missed customer emails, broken notifications
**Current coverage:** Manual scripts only

Recommended tests:
- Email template rendering with different data
- SMTP connection error handling (mock SMTP)
- Email polling — parsing incoming emails (mock IMAP)
- Thread matching for reply emails
- Escalation logic when AI confidence is low

### 7. MEDIUM: Trust Score & Dispute Systems

**Risk:** Incorrect trust scores, unfair dispute outcomes
**Current coverage:** None

Files: `trust_score_service.py`, `dispute_service.py`, `restaurant_penalty_service.py`

Recommended tests:
- Trust score calculation given various inputs
- Score update on order completion/cancellation
- Dispute creation and resolution flow
- Penalty application and removal

### 8. MEDIUM: Frontend Utility Functions (`frontend/src/lib/`)

**Risk:** Silent data corruption, broken UI behavior
**Current coverage:** None

High-value targets for unit testing:
- `lib/utils.ts` — general utility functions
- `lib/mapUtils.ts` — coordinate/distance calculations
- `lib/businessConfig.ts` — business rule configuration
- `lib/chatApi.ts` — API request construction
- `hooks/useSubscription.ts` — subscription state logic

### 9. LOW-MEDIUM: Image Moderation (`backend/app/services/image_moderation_service.py`)

**Risk:** Inappropriate content displayed on customer sites
**Current coverage:** None

Recommended tests:
- Moderation decision logic (mock external API)
- Handling of various image formats and sizes
- Fallback when moderation service is unavailable

### 10. LOW: Webhook Handling (`backend/app/services/webhook_service.py`)

**Risk:** Missed events, data inconsistency
**Current coverage:** None

Recommended tests:
- Webhook signature validation
- Payload parsing for different event types
- Retry/idempotency behavior

---

## Recommended Action Plan

### Phase 1 — Quick Wins (establish testing infrastructure)

1. **Set up frontend testing framework** — Add Vitest + React Testing Library to `frontend/package.json`, configure, and add a sample test. Update CI to run `npm test`.

2. **Move standalone backend tests into pytest** — Refactor `test_delivery_api.py`, etc. to use pytest fixtures and mocks instead of live services. Move them into `backend/tests/`.

3. **Add pytest fixtures and mocks** — Create `backend/tests/conftest.py` with:
   - A mock Supabase client
   - A FastAPI `TestClient` fixture
   - Mock environment variables

### Phase 2 — Cover Critical Paths

4. **Auth endpoint tests** — Test registration, login, token validation, and role checks using FastAPI TestClient with mocked Supabase.

5. **Payment service tests** — Mock Stripe/ToyyibPay APIs, test payment flows end-to-end.

6. **Order lifecycle tests** — Test the full order creation → status update → completion flow.

### Phase 3 — Broaden Coverage

7. **AI service unit tests** — Test prompt building, response parsing, and fallback logic with mocked LLM responses.

8. **Frontend utility tests** — Unit test `lib/` and `hooks/` modules.

9. **Subscription logic tests** — Test plan management, expiry, and feature gating.

10. **Integration tests** — API-level tests for key workflows (sign up → create site → add menu → receive order).

---

## Metrics

| Area | Source Files | Test Files | Estimated Coverage |
|------|-------------|------------|-------------------|
| Backend services | 37 files (~22,755 lines) | 1 (health only) | <1% |
| Backend endpoints | 33 files | 0 | 0% |
| Frontend components | 53 files | 0 | 0% |
| Frontend hooks/utils | 13 files | 0 | 0% |
| Admin dashboard | ~15 files | 0 | 0% |

**Overall estimated test coverage: <1%**

The CI pipeline is configured to report coverage (`pytest --cov=app --cov-report=xml`) but currently only covers import checks. The five standalone test scripts test real functionality but require live infrastructure and are not part of CI.
