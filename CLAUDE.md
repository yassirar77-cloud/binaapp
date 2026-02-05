# CLAUDE.md - AI Assistant Guide for BinaApp

This document provides context and conventions for AI assistants working on the BinaApp codebase.

## Project Overview

**BinaApp** is an AI-powered, no-code website builder for Malaysian SMEs. Users describe their website in Bahasa Malaysia or English, and the AI generates a fully functional website with integrated features (WhatsApp ordering, shopping cart, Google Maps, etc.) published to a custom subdomain (`yourname.binaapp.my`).

**Key Features:**
- AI-powered website generation from natural language descriptions
- Real-time delivery tracking system with rider PWA
- WhatsApp Business integration for orders
- Subscription-based pricing (free, basic, pro, enterprise tiers)
- Support for Bahasa Malaysia and English

## Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript (strict mode disabled)
- **Styling:** Tailwind CSS 3.4
- **State:** Zustand
- **UI:** Lucide icons, Framer Motion, React Hook Form
- **Maps:** Leaflet + React Leaflet
- **Charts:** Recharts
- **Auth:** Supabase Auth Helpers
- **Node:** >= 20.0.0

### Backend
- **Framework:** FastAPI (Python 3.11)
- **Server:** Uvicorn
- **Database:** PostgreSQL via Supabase
- **Validation:** Pydantic v2
- **Auth:** JWT (python-jose) + Passlib + bcrypt
- **AI:** DeepSeek V3 (primary), Qwen, Claude 3.5 Sonnet (email support)
- **Email:** Zoho SMTP (aiosmtplib) + IMAP polling
- **Payments:** Stripe, ToyyibPay (Malaysia)
- **Storage:** Cloudinary, Supabase Storage
- **Background Jobs:** APScheduler

### Infrastructure
- **Database:** Supabase (PostgreSQL with RLS)
- **Hosting:** Render.com (backend), Vercel (frontend)
- **Cache:** Redis (optional)
- **Storage:** Cloudflare R2, Supabase Storage

## Directory Structure

```
binaapp/
├── frontend/                    # Next.js 14 SPA
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   │   ├── auth/           # Login, register, daftar
│   │   │   ├── create/         # Website creation wizard
│   │   │   ├── dashboard/      # User dashboard
│   │   │   ├── delivery/       # Delivery management
│   │   │   ├── editor/         # Visual HTML editor
│   │   │   ├── my-projects/    # User's websites
│   │   │   ├── rider/          # Rider PWA app
│   │   │   └── subscription/   # Subscription management
│   │   ├── components/         # Reusable React components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # Utilities (api.ts, supabase.ts)
│   │   └── types/              # TypeScript interfaces
│   ├── public/                 # Static assets
│   └── package.json
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py             # FastAPI entry point (~3600 lines)
│   │   ├── api/v1/
│   │   │   ├── endpoints/      # API route handlers
│   │   │   │   ├── auth.py
│   │   │   │   ├── websites.py
│   │   │   │   ├── delivery.py # Largest file (~114KB)
│   │   │   │   ├── chat.py
│   │   │   │   ├── payments.py
│   │   │   │   └── subscription.py
│   │   │   └── router.py
│   │   ├── services/           # Business logic
│   │   │   ├── ai_service.py   # AI generation (~3250 lines)
│   │   │   ├── supabase_client.py
│   │   │   ├── templates.py    # Website templates (~3300 lines)
│   │   │   └── payment_service.py
│   │   ├── models/schemas.py   # Pydantic schemas
│   │   ├── core/
│   │   │   ├── config.py       # Settings from env
│   │   │   ├── security.py     # JWT & auth utilities
│   │   │   └── scheduler.py    # APScheduler
│   │   └── middleware/         # Request middleware
│   ├── migrations/             # SQL migration files (17+)
│   ├── tests/
│   └── requirements.txt
│
├── database/                    # Database setup scripts
├── templates/                   # HTML website templates
├── docker-compose.yml           # Local development
├── render.yaml                  # Render.com deployment
├── DATABASE_SCHEMA.sql          # Complete schema backup
└── .env.example                 # Environment template
```

## Development Commands

### Frontend (from `/frontend`)
```bash
npm run dev          # Start dev server (localhost:3000)
npm run build        # Production build
npm run lint         # ESLint check
npm run type-check   # TypeScript check (tsc --noEmit)
```

### Backend (from `/backend`)
```bash
uvicorn app.main:app --reload              # Start dev server (localhost:8000)
pytest                                      # Run tests
pytest -v --cov=app                        # Tests with coverage
ruff check .                               # Linting (PEP 8)
black .                                    # Code formatting
```

### Docker
```bash
docker-compose up -d                       # Start all services
docker-compose down                        # Stop services
docker-compose logs -f backend             # View backend logs
```

## Code Conventions

### Python (Backend)

1. **Type hints required** for function parameters and return values:
```python
async def example_function(param: str) -> dict:
    """Brief description."""
    pass
```

2. **Use loguru** for logging with emoji prefixes:
```python
from loguru import logger
logger.info(f"✅ User registered: {email}")
logger.error(f"❌ Registration error: {e}")
```

3. **HTTPException** for API errors with proper status codes:
```python
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Clear error message"
)
```

4. **Async/await** for all database and external API calls.

5. **Pydantic models** for request/response validation in `models/schemas.py`.

### TypeScript (Frontend)

1. **Interface-first** - Define types in `src/types/index.ts`:
```typescript
interface Props {
  title: string
  onClick: () => void
}

export function Component({ title, onClick }: Props) {
  // ...
}
```

2. **Use path alias** `@/` for imports:
```typescript
import { apiFetch } from '@/lib/api'
import type { Website } from '@/types'
```

3. **Functional components** with hooks (no class components).

4. **Use `apiFetch`** from `@/lib/api.ts` for all API calls - handles auth tokens and 401 refresh automatically.

5. **Toast notifications** via `react-hot-toast`:
```typescript
import toast from 'react-hot-toast'
toast.success('Saved!')
toast.error('Failed to save')
```

### Commit Message Format
```
Add: new feature description
Fix: bug description
Update: enhancement description
Refactor: what was refactored
Docs: documentation changes
```

## Key Architecture Patterns

### Authentication Flow
1. Custom JWT tokens generated by backend (`core/security.py`)
2. Tokens stored in localStorage (mobile browser cookie issues)
3. `apiFetch()` automatically adds Authorization header
4. Token refresh on 401 with automatic retry
5. Fallback to Supabase session for OAuth flows

### Database Access
- All database operations go through `services/supabase_client.py`
- Use service role key for admin operations (bypasses RLS)
- Use anon key for user-scoped operations (respects RLS)
- UUID primary keys everywhere
- Timestamps: `created_at`, `updated_at` (TIMESTAMPTZ)

### API Structure
- Base URL: `http://localhost:8000` (dev), `https://api.binaapp.my` (prod)
- All endpoints prefixed with `/api/v1/`
- Swagger docs at `/docs`, ReDoc at `/redoc`
- Health check at `/health`

### Subscription System
- Tiers: `free`, `basic`, `pro`, `enterprise`
- Usage limits enforced via `middleware/subscription_guard.py`
- Limits tracked in `subscriptions` table
- `useSubscription` hook for frontend subscription state

### Real-time Features
- Supabase Realtime for live updates (orders, rider location)
- WebSocket endpoints in `chat.py` for messaging
- Fallback polling for unreliable connections

## Database Schema (Key Tables)

| Table | Purpose |
|-------|---------|
| `profiles` | User profile extending auth.users |
| `subscriptions` | Subscription tier and status |
| `websites` | Generated websites and metadata |
| `orders` | Delivery orders |
| `order_items` | Items in orders |
| `riders` | Delivery rider info |
| `rider_locations` | Real-time GPS tracking |
| `delivery_zones` | Service area zones |
| `chat_conversations` | Chat conversation records |
| `chat_messages` | Chat messages with media |
| `menu_categories` | Restaurant menu categories |
| `menu_items` | Individual menu items |

All tables have RLS policies. Migrations in `backend/migrations/`.

## Environment Variables

Key variables (see `.env.example` for full list):

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx

# AI
DEEPSEEK_API_KEY=xxx
QWEN_API_KEY=xxx

# Auth
JWT_SECRET_KEY=xxx
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Payments
STRIPE_SECRET_KEY=xxx
STRIPE_WEBHOOK_SECRET=xxx

# Frontend env (NEXT_PUBLIC_ prefix)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=xxx
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
```

## Common Tasks for AI Assistants

### Adding a New API Endpoint
1. Create/edit file in `backend/app/api/v1/endpoints/`
2. Add Pydantic models in `models/schemas.py` if needed
3. Register route in `api/v1/router.py`
4. Add business logic in `services/` if complex
5. Update frontend `lib/api.ts` or create dedicated API helper

### Adding a New Frontend Page
1. Create folder in `frontend/src/app/[route]/`
2. Add `page.tsx` for the route
3. Add types to `src/types/index.ts`
4. Use existing components from `src/components/`
5. Protect with auth check in middleware if needed

### Modifying Database Schema
1. Add migration SQL in `backend/migrations/`
2. Run migration in Supabase SQL editor
3. Update `DATABASE_SCHEMA.sql` backup
4. Update Pydantic models in `models/schemas.py`
5. Update TypeScript types in `frontend/src/types/`

### Debugging Common Issues
- **401 errors**: Check token in localStorage, verify JWT_SECRET_KEY matches
- **CORS errors**: Check `CORS_ORIGINS` in backend config
- **Mobile auth issues**: Tokens must be in Authorization header (not cookies)
- **RLS errors**: Check Supabase policies or use service role key
- **Realtime not working**: Check Supabase subscription limits

## Important Files to Know

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app setup, middleware, startup events |
| `backend/app/services/ai_service.py` | AI website generation logic |
| `backend/app/services/supabase_client.py` | All database operations |
| `backend/app/core/security.py` | JWT creation/validation |
| `backend/app/api/v1/endpoints/delivery.py` | Complex delivery system |
| `frontend/src/lib/api.ts` | API client with auth handling |
| `frontend/src/lib/supabase.ts` | Supabase client & token management |
| `frontend/src/app/create/page.tsx` | Website creation wizard |
| `frontend/src/app/delivery/page.tsx` | Delivery management UI |

## Testing

### Backend
```bash
cd backend
pytest                           # All tests
pytest tests/test_auth.py -v     # Specific test file
pytest --cov=app --cov-report=html  # Coverage report
```

### Frontend
```bash
cd frontend
npm run type-check               # TypeScript validation
npm run lint                     # ESLint
npm run build                    # Full build test
```

## Deployment

### Backend (Render.com)
- Auto-deploys from main branch
- Config in `render.yaml`
- Health check: `/health`
- Logs: Render dashboard or `render logs`

### Frontend (Vercel)
- Auto-deploys from main branch
- Build command: `npm run build`
- Environment vars in Vercel dashboard

### Database Migrations
1. Write SQL migration file
2. Test in Supabase staging
3. Run in production via SQL editor
4. Keep `DATABASE_SCHEMA.sql` updated

## Language Support

BinaApp supports Bahasa Malaysia and English:
- URL aliases: `/register` = `/daftar`
- AI prompts handle both languages
- UI text should consider Malaysian SME context
- WhatsApp integration uses local format (+60)

## Recent Development Patterns

Based on recent commits:
- Bug fixes often involve realtime/polling reliability
- Order status transitions require careful timestamp handling
- Mobile compatibility is critical (token-based auth, not cookies)
- Subscription limits need careful validation
- Large HTML content requires higher token limits for AI APIs

## Quick Reference

| Action | Location |
|--------|----------|
| Add API endpoint | `backend/app/api/v1/endpoints/` |
| Add React component | `frontend/src/components/` |
| Add TypeScript type | `frontend/src/types/index.ts` |
| Add Pydantic schema | `backend/app/models/schemas.py` |
| Modify DB schema | `backend/migrations/` + SQL editor |
| Add environment var | `.env.example` + `backend/app/core/config.py` |
| Add frontend route | `frontend/src/app/[route]/page.tsx` |

---

*Last updated: 2026-02-05*
*Repository: https://github.com/yassirar77-cloud/binaapp*
