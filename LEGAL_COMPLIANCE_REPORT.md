# BinaApp Malaysian Legal Compliance Report

**Generated:** 2026-01-27
**Analysis Version:** 1.0
**Codebase Commit:** 5ca4340 (main branch)

---

## Executive Summary

This report analyzes BinaApp's compliance with Malaysian laws including the **Personal Data Protection Act 2010 (PDPA)**, **Consumer Protection (Electronic Trade) Regulations 2024**, **Communications and Multimedia Act 1998**, **Road Transport Act 1987**, and relevant **Service Tax regulations**.

### Overall Compliance Status

| Category | Status | Risk Level |
|----------|--------|------------|
| PDPA Compliance | ⚠️ **PARTIAL** | HIGH |
| Consumer Protection | ⚠️ **PARTIAL** | MEDIUM |
| Payment Compliance | ✅ **ADEQUATE** | LOW |
| GPS/Location Privacy | ⚠️ **PARTIAL** | MEDIUM |
| AI Transparency | ❌ **MISSING** | MEDIUM |
| Rider/Transport Laws | ⚠️ **PARTIAL** | HIGH |
| Data Security | ❌ **INADEQUATE** | CRITICAL |

---

## 1. Data Collection Inventory

### 1.1 Personal Data Categories Collected

| Data Type | Source Location | Database Table | Purpose | Legal Basis |
|-----------|-----------------|----------------|---------|-------------|
| **Email Address** | `/frontend/src/app/register/page.tsx:95` | `auth.users` | Account authentication | Consent (registration) |
| **Password** | `/frontend/src/app/register/page.tsx:104` | `auth.users` (hashed) | Authentication | Consent (registration) |
| **Full Name** | `/frontend/src/app/profile/page.tsx:1065` | `profiles.full_name` | User identification | Consent |
| **Phone Number** | `/frontend/src/app/profile/page.tsx:1086` | `profiles.phone` | Contact, WhatsApp | Consent |
| **Business Name** | `/frontend/src/app/create/page.tsx` | `websites.business_name` | Website generation | Contract performance |
| **Business Address** | `/frontend/src/app/create/page.tsx` | `websites.location_address` | Maps integration | Consent |
| **Customer Name** | `/frontend/public/widgets/delivery-widget.js` | `delivery_orders.customer_name` | Order fulfillment | Contract |
| **Customer Phone** | `/frontend/public/widgets/delivery-widget.js` | `delivery_orders.customer_phone` | Delivery coordination | Contract |
| **Delivery Address** | `/frontend/public/widgets/delivery-widget.js` | `delivery_orders.delivery_address` | Delivery | Contract |
| **GPS Coordinates (Delivery)** | `/frontend/public/widgets/delivery-widget.js` | `delivery_orders.delivery_latitude/longitude` | Location services | Consent |
| **GPS Coordinates (Rider)** | `/frontend/src/app/rider/page.tsx:518` | `rider_locations` table | Real-time tracking | Consent (implicit) |
| **Chat Messages** | `/backend/app/api/v1/endpoints/chat.py:680` | `chat_messages.content` | Customer communication | Contract |
| **Payment References** | `/backend/app/api/v1/endpoints/payments.py` | `transactions.toyyibpay_bill_code` | Payment processing | Contract |
| **Rider Information** | `/frontend/src/app/profile/page.tsx:771` | `riders` table | Delivery services | Contract |

### 1.2 Special Category Data

| Data Type | Table | Sensitivity | PDPA Section |
|-----------|-------|-------------|--------------|
| **Vehicle Registration Number** | `riders.vehicle_plate` | Medium | Section 40 |
| **Real-time GPS Location** | `rider_locations` | High | Section 40 |
| **Payment Transaction IDs** | `transactions` | High | Section 9 |
| **Chat Communication Content** | `chat_messages` | Medium | Section 40 |

### 1.3 Data Flow Diagram

```
User Input → Frontend Forms → API Endpoints → Supabase PostgreSQL
                ↓                    ↓
         localStorage          External Services:
         (auth tokens)         - ToyyibPay (payments)
                               - Stability AI (images)
                               - DeepSeek AI (content)
                               - Cloudinary (storage)
```

---

## 2. Feature-to-Law Mapping

### 2.1 User Registration & Authentication

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| User Registration | Collect email, password, name | PDPA Section 7(1) | ⚠️ **PARTIAL** | No privacy notice at point of collection |
| Session Management | JWT tokens, 24-hour expiry | PDPA Section 9(1)(e) | ✅ **COMPLIANT** | N/A |
| Password Storage | Bcrypt hashing | PDPA Section 9(1)(d) | ✅ **COMPLIANT** | N/A |
| Cookie Usage | Auth token in cookies | PDPA, CMA 1998 | ⚠️ **PARTIAL** | No cookie consent mechanism |

**Files:**
- `/frontend/src/lib/supabase.ts` (auth token storage)
- `/backend/app/core/security.py` (password hashing)
- `/backend/app/api/v1/endpoints/auth.py` (registration endpoint)

### 2.2 GPS Location Tracking

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| Rider GPS Tracking | Continuous location updates | PDPA Section 7 | ⚠️ **PARTIAL** | No explicit consent form |
| Location History | 30-day retention | PDPA Section 7(1)(e) | ⚠️ **PARTIAL** | Retention policy not disclosed |
| Customer Location | Delivery coordinates | PDPA Section 7 | ⚠️ **PARTIAL** | No privacy notice |
| Map Display | Leaflet + OpenStreetMap | N/A | ✅ **COMPLIANT** | N/A |

**Files:**
- `/frontend/src/app/rider/page.tsx:504-580` (GPS watchPosition)
- `/backend/app/api/v1/endpoints/delivery.py:2435-2529` (location update API)
- `/DATABASE_SCHEMA.sql:580-590` (rider_locations table)

**PDPA Requirements:**
- Section 7(1)(a): Must inform data subject of purpose - **❌ NOT MET**
- Section 7(1)(b): Must obtain consent - **⚠️ PARTIAL** (browser prompt only)
- Section 7(1)(e): Must inform retention period - **❌ NOT MET**

### 2.3 Payment Processing

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| ToyyibPay Integration | FPX online banking | BNM Guidelines | ✅ **COMPLIANT** | N/A |
| No Card Storage | Delegated to payment gateway | PCI-DSS | ✅ **COMPLIANT** | N/A |
| Subscription Billing | Recurring payments | Consumer Protection Act | ⚠️ **PARTIAL** | No auto-renewal disclosure |
| Transaction Records | Bill codes, reference IDs | PDPA Section 9(1)(d) | ⚠️ **PARTIAL** | Payment refs unencrypted |

**Files:**
- `/backend/app/services/toyyibpay_service.py` (payment gateway)
- `/backend/app/api/v1/endpoints/payments.py` (payment endpoints)
- `/backend/migrations/005_subscription_management.sql` (transactions schema)

**Compliance Notes:**
- No sensitive card data stored locally ✅
- Payment processing fully delegated to licensed provider (ToyyibPay) ✅
- Webhook signature verification missing ⚠️

### 2.4 AI-Powered Features

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| Website Generation | DeepSeek/Qwen AI | PDPA, Consumer Protection | ❌ **MISSING** | No AI disclosure |
| Image Generation | Stability AI | PDPA, Copyright Act | ❌ **MISSING** | No AI-generated label |
| Content Moderation | Keyword blocking | CMA 1998 Section 211 | ✅ **COMPLIANT** | N/A |
| Data to AI Services | Business descriptions | PDPA Section 129 (cross-border) | ⚠️ **PARTIAL** | No cross-border transfer notice |

**Files:**
- `/frontend/src/app/api/generate/route.ts` (AI generation)
- `/backend/app/services/stability_service.py` (Stability AI)
- `/backend/app/utils/content_moderation.py` (moderation)

**Missing Disclosures (Required by Consumer Protection Regulations 2024):**
- AI-generated content must be labeled
- Users must be informed data is sent to external AI services
- Cross-border data transfer to China (DeepSeek) and Singapore (Stability AI) requires notice

### 2.5 User-Generated Content

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| Menu Item Upload | Images and descriptions | CMA 1998 Section 233 | ⚠️ **PARTIAL** | No DMCA takedown |
| Chat Messages | Customer communication | CMA 1998, PDPA | ✅ **ADEQUATE** | N/A |
| Review/Ratings | Not implemented | N/A | N/A | N/A |
| Content Moderation | Illegal content blocking | CMA 1998 Section 211 | ✅ **COMPLIANT** | N/A |

**Files:**
- `/backend/app/api/upload.py` (file uploads)
- `/backend/app/api/v1/endpoints/chat.py:759-859` (chat image uploads)
- `/backend/app/utils/content_moderation.py` (moderation)

**Content Moderation Coverage:**
- Illegal activities (drugs, weapons, gambling) ✅
- Scam/fraud patterns ✅
- Adult content ✅
- Fake documents ✅
- No user reporting mechanism ❌
- No content takedown procedure ❌

### 2.6 Rider/Delivery Services

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| Rider Registration | Name, phone, vehicle info | Road Transport Act 1987 | ⚠️ **PARTIAL** | No license verification |
| GPS Tracking | Real-time location | PDPA Section 7 | ⚠️ **PARTIAL** | No explicit consent |
| Delivery Assignment | Order allocation | N/A | ✅ **COMPLIANT** | N/A |
| Vehicle Information | Plate, model, type | Road Transport Act | ⚠️ **PARTIAL** | No insurance verification |
| Employment Status | Independent contractor | Employment Act 1955 | ❌ **MISSING** | No classification |

**Files:**
- `/frontend/src/app/rider/page.tsx` (rider app)
- `/backend/app/api/v1/endpoints/delivery.py:1268-1332` (rider creation)
- `/DATABASE_SCHEMA.sql:394-430` (riders table)

**Road Transport Act 1987 Compliance Gaps:**
- No driving license number field ❌
- No license verification system ❌
- No insurance information storage ❌
- No background check mechanism ❌
- No road safety training records ❌

### 2.7 Merchant Features

| Feature | Description | Malaysian Law | Status | Gap |
|---------|-------------|---------------|--------|-----|
| Website Builder | AI-generated websites | Companies Act, LHDN | ⚠️ **PARTIAL** | No SSM registration |
| Multi-tenant Hosting | Subdomain architecture | MCMC Registration | ⚠️ **PARTIAL** | No content liability policy |
| Business Data | Company information | PDPA | ✅ **COMPLIANT** | N/A |
| E-commerce | Shopping cart, checkout | Consumer Protection | ⚠️ **PARTIAL** | No refund policy |

**Files:**
- `/backend/app/middleware/subdomain.py` (multi-tenant)
- `/backend/app/api/v1/endpoints/websites.py` (website generation)
- `/DATABASE_SCHEMA.sql:82-117` (websites table)

---

## 3. Critical Compliance Gaps

### 3.1 HIGH PRIORITY (Could Cause Shutdown/Fines)

| # | Gap | Malaysian Law | Risk | Recommendation |
|---|-----|---------------|------|----------------|
| 1 | **No Privacy Policy** | PDPA Section 7(1)(a) | Fines up to RM300,000 | Create and display privacy policy |
| 2 | **No Consent Mechanism** | PDPA Section 6 | Fines up to RM300,000 | Add consent checkboxes |
| 3 | **Unencrypted PII** | PDPA Section 9(1)(d) | Data breach liability | Implement encryption |
| 4 | **No Data Breach Procedure** | PDPA Amendment 2024 | Mandatory notification | Create incident response plan |
| 5 | **Cross-border Transfer (AI)** | PDPA Section 129 | Fines up to RM300,000 | Add transfer notice |
| 6 | **No Rider Insurance Verification** | Road Transport Act | Liability issues | Add insurance fields |
| 7 | **Auth Tokens in Plaintext** | PDPA Section 9(1)(d) | Security breach risk | Encrypt/hash tokens |

### 3.2 MEDIUM PRIORITY (Should Fix Before Public Launch)

| # | Gap | Malaysian Law | Risk | Recommendation |
|---|-----|---------------|------|----------------|
| 8 | **No Cookie Consent** | PDPA + Best Practice | User complaints | Add cookie banner |
| 9 | **No AI Content Disclosure** | Consumer Protection 2024 | Consumer complaints | Label AI content |
| 10 | **No Refund Policy** | Consumer Protection Act | Chargebacks | Create refund terms |
| 11 | **No Terms of Service** | Contract Law | Disputes | Draft ToS |
| 12 | **No Data Retention Policy** | PDPA Section 7(1)(e) | Compliance audit failure | Define retention periods |
| 13 | **No Data Export Function** | PDPA Section 12 | Access request failure | Build data export |
| 14 | **No Data Deletion Function** | PDPA Section 7(1)(d) | Deletion request failure | Build data deletion |
| 15 | **No Rider Contractor Agreement** | Employment Act | Misclassification | Draft contractor terms |

### 3.3 LOW PRIORITY (Best Practices)

| # | Gap | Best Practice | Recommendation |
|---|-----|---------------|----------------|
| 16 | No rate limiting (active) | OWASP | Register RateLimitMiddleware |
| 17 | No security headers (active) | OWASP | Register SecurityHeadersMiddleware |
| 18 | No audit logging | ISO 27001 | Add comprehensive logging |
| 19 | Permissive CORS | Security | Restrict to specific domains |
| 20 | No 2FA option | Security | Add optional 2FA |

---

## 4. Code Changes Needed

### 4.1 Privacy Policy Integration

**Create Privacy Policy Page:**
```
Location: /frontend/src/app/privacy/page.tsx (NEW FILE)
Content: Comprehensive privacy policy per PDPA requirements
Link from: Footer on all pages, registration form
```

**Update Registration Form:**
```typescript
// File: /frontend/src/app/register/page.tsx
// Add around line 85:
<div className="flex items-start">
  <input
    type="checkbox"
    id="privacy-consent"
    required
    onChange={(e) => setPrivacyConsent(e.target.checked)}
  />
  <label htmlFor="privacy-consent">
    Saya telah membaca dan bersetuju dengan
    <Link href="/privacy">Polisi Privasi</Link> dan
    <Link href="/terms">Terma Perkhidmatan</Link>
  </label>
</div>
```

### 4.2 Consent Mechanism for GPS Tracking

**Update Rider App:**
```typescript
// File: /frontend/src/app/rider/page.tsx
// Add before line 505 (GPS initialization):

const [gpsConsent, setGpsConsent] = useState(false);

// Show consent modal BEFORE requesting location
const requestGPSConsent = () => {
  setShowConsentModal(true);
  // Modal content:
  // - Purpose: Real-time delivery tracking
  // - Data collected: Latitude, longitude, accuracy
  // - Retention: 30 days
  // - Third parties: Merchant view only
  // - Withdrawal: Can disable in settings
};

if (!gpsConsent) {
  requestGPSConsent();
  return;
}
```

### 4.3 Database Encryption

**Enable pgcrypto:**
```sql
-- File: /backend/migrations/NEW_encryption_migration.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt phone numbers
ALTER TABLE public.profiles ADD COLUMN phone_encrypted BYTEA;
ALTER TABLE public.riders ADD COLUMN phone_encrypted BYTEA;
ALTER TABLE public.delivery_orders ADD COLUMN customer_phone_encrypted BYTEA;

-- Function to encrypt
CREATE OR REPLACE FUNCTION encrypt_phone(phone TEXT) RETURNS BYTEA AS $$
  SELECT pgp_sym_encrypt(phone, current_setting('app.encryption_key'));
$$ LANGUAGE SQL;

-- Function to decrypt
CREATE OR REPLACE FUNCTION decrypt_phone(encrypted BYTEA) RETURNS TEXT AS $$
  SELECT pgp_sym_decrypt(encrypted, current_setting('app.encryption_key'));
$$ LANGUAGE SQL;
```

### 4.4 AI Disclosure Banner

**Add to AI-Generated Websites:**
```typescript
// File: /backend/app/services/ai_service.py
// After generating HTML, inject disclosure:

const AI_DISCLOSURE = `
<div class="ai-disclosure" style="background:#f0f0f0;padding:10px;text-align:center;font-size:12px;">
  Laman web ini dijana dengan bantuan AI. Kandungan mungkin memerlukan semakan.
  (This website was generated with AI assistance. Content may require review.)
</div>
`;

// Inject after opening <body> tag
generated_html = generated_html.replace('<body>', f'<body>{AI_DISCLOSURE}');
```

### 4.5 Data Retention Implementation

**Add retention cleanup job:**
```python
# File: /backend/app/services/data_retention_service.py (NEW FILE)

from datetime import datetime, timedelta
from app.services.supabase_client import get_supabase_client

RETENTION_POLICIES = {
    'rider_locations': 30,      # 30 days
    'chat_messages': 365,       # 1 year
    'delivery_orders': 730,     # 2 years
    'order_status_history': 730 # 2 years
}

async def cleanup_expired_data():
    supabase = get_supabase_client()

    for table, days in RETENTION_POLICIES.items():
        cutoff = datetime.now() - timedelta(days=days)

        # Archive before delete
        await supabase.from_(table).select("*")\
            .lt('created_at', cutoff.isoformat())\
            .execute()  # Archive to cold storage

        # Delete expired
        await supabase.from_(table)\
            .delete()\
            .lt('created_at', cutoff.isoformat())\
            .execute()
```

### 4.6 Cross-Border Data Transfer Notice

**Add to website creation:**
```typescript
// File: /frontend/src/app/create/page.tsx
// Add before AI generation:

<div className="border border-yellow-400 bg-yellow-50 p-4 rounded">
  <h4 className="font-bold">Notis Pemindahan Data</h4>
  <p>Untuk menjana laman web anda, maklumat perniagaan akan dihantar kepada:</p>
  <ul>
    - DeepSeek AI (China) - penjanaan kandungan
    - Stability AI (Singapore) - penjanaan imej
  </ul>
  <p>Data ini tertakluk kepada polisi privasi penyedia tersebut.</p>
  <label>
    <input type="checkbox" required />
    Saya bersetuju dengan pemindahan data rentas sempadan ini
  </label>
</div>
```

---

## 5. Database Schema Review

### 5.1 All Supabase Tables

| Table | Records PII | Has RLS | Encryption | Status |
|-------|-------------|---------|------------|--------|
| `profiles` | ✅ Yes | ✅ Yes | ❌ No | ⚠️ |
| `subscriptions` | Stripe IDs | ✅ Yes | ❌ No | ⚠️ |
| `websites` | Contact info | ✅ Yes | ❌ No | ⚠️ |
| `analytics` | No | ✅ Yes | N/A | ✅ |
| `templates` | No | ✅ Yes | N/A | ✅ |
| `menu_categories` | No | ✅ Yes | N/A | ✅ |
| `menu_items` | No | ✅ Yes | N/A | ✅ |
| `menu_item_options` | No | ✅ Yes | N/A | ✅ |
| `delivery_zones` | No | ✅ Yes | N/A | ✅ |
| `riders` | ✅ Yes | ✅ Yes | ❌ No | ❌ CRITICAL |
| `delivery_orders` | ✅ Yes | ⚠️ Partial | ❌ No | ❌ CRITICAL |
| `order_items` | No | ✅ Yes | N/A | ✅ |
| `rider_locations` | GPS data | ✅ Yes | ❌ No | ⚠️ |
| `order_status_history` | No | ✅ Yes | N/A | ✅ |
| `delivery_settings` | WhatsApp # | ✅ Yes | ❌ No | ⚠️ |
| `chat_conversations` | ✅ Yes | ⚠️ Partial | ❌ No | ⚠️ |
| `chat_messages` | Content | ⚠️ Partial | ❌ No | ⚠️ |
| `chat_participants` | User info | ✅ Yes | ❌ No | ⚠️ |
| `transactions` | Payment refs | ✅ Yes | ❌ No | ⚠️ |
| `payments` | Bill codes | ✅ Yes | ❌ No | ⚠️ |

### 5.2 Sensitive Fields Requiring Encryption

**CRITICAL - Encrypt Immediately:**
- `riders.password_hash` - Currently TEXT, should be properly hashed
- `riders.auth_token` - Plaintext token storage
- `riders.phone` - PII exposed
- `delivery_orders.customer_phone` - PII exposed
- `delivery_orders.delivery_address` - PII exposed
- `subscriptions.stripe_customer_id` - Payment credential
- `transactions.toyyibpay_bill_code` - Payment reference

**HIGH - Encrypt Before Production:**
- `profiles.phone`
- `chat_messages.content` (contains PII in messages)
- `websites.contact_email`
- `delivery_settings.whatsapp_number`

### 5.3 RLS Policy Audit

**Properly Protected (Owner-Only Access):**
- `profiles` - `auth.uid() = id`
- `subscriptions` - `auth.uid() = user_id`
- `websites` - `user_id = auth.uid()`

**Overly Permissive (Requires App-Layer Filtering):**
```sql
-- File: /database/migrations/003_fix_rls_security.sql
-- These allow any SELECT/INSERT:
delivery_orders: USING (true)
chat_conversations: USING (true)
chat_messages: USING (true)
```

**Recommendation:** Implement phone-based customer filtering at database level.

### 5.4 Access Control Recommendations

| Data | Current Access | Recommended | Action |
|------|----------------|-------------|--------|
| Customer phone | App filtering | DB-level RLS | Add phone verification |
| Rider location | Any website owner | Only assigned orders | Restrict RLS |
| Chat messages | Any participant | Verified participants | Add verification |
| Payment records | Authenticated users | Owner only | Tighten RLS |

---

## 6. Malaysian Law Reference

### 6.1 Personal Data Protection Act 2010 (PDPA)

**Key Requirements:**
- **Section 6**: Consent required before processing personal data
- **Section 7**: Data Protection Principles (notice, consent, disclosure, retention, integrity, access, security)
- **Section 9**: Security safeguards for personal data
- **Section 12**: Data subject's right to access
- **Section 129**: Cross-border data transfer restrictions

**2024 Amendment Additions:**
- Mandatory data breach notification within 72 hours
- Data Protection Officers required for large processors
- Increased penalties up to RM1,000,000

### 6.2 Consumer Protection (Electronic Trade) Regulations 2024

**Key Requirements:**
- Clear disclosure of AI-generated content
- Transparent pricing and refund policies
- Authentication of merchant identity
- Clear terms and conditions

### 6.3 Communications and Multimedia Act 1998

**Key Sections:**
- **Section 211**: Prohibition on offensive content
- **Section 233**: Improper use of network facilities

### 6.4 Road Transport Act 1987

**Requirements for Delivery Riders:**
- Valid driving license for vehicle class
- Vehicle registration and insurance
- Periodic vehicle inspections (for motorcycles >5 years)

---

## 7. Implementation Priority Matrix

### Phase 1: Critical (Week 1-2)

| Task | Effort | Impact |
|------|--------|--------|
| Create Privacy Policy | 2 days | HIGH |
| Add Consent Checkboxes | 1 day | HIGH |
| Enable Database Encryption | 3 days | HIGH |
| Create Terms of Service | 2 days | HIGH |
| Register Security Middleware | 1 day | MEDIUM |

### Phase 2: High Priority (Week 3-4)

| Task | Effort | Impact |
|------|--------|--------|
| Implement Data Retention | 3 days | HIGH |
| Add Cross-border Transfer Notice | 1 day | MEDIUM |
| Create AI Content Disclosure | 2 days | MEDIUM |
| Build Data Export Function | 3 days | MEDIUM |
| Add Rider Document Fields | 2 days | HIGH |

### Phase 3: Medium Priority (Month 2)

| Task | Effort | Impact |
|------|--------|--------|
| Implement Content Reporting | 5 days | MEDIUM |
| Add Cookie Consent Banner | 2 days | LOW |
| Create Refund Policy | 2 days | MEDIUM |
| Build Data Deletion Function | 3 days | MEDIUM |
| Add Audit Logging | 5 days | MEDIUM |

---

## 8. Compliance Checklist

### PDPA Compliance

- [ ] Privacy Policy published and accessible
- [ ] Consent mechanism at registration
- [ ] GPS tracking consent for riders
- [ ] Data retention periods disclosed
- [ ] Cross-border transfer notice for AI
- [ ] Data export function available
- [ ] Data deletion function available
- [ ] Security measures documented
- [ ] Data breach procedure established
- [ ] Encryption for sensitive data

### Consumer Protection

- [ ] AI-generated content labeled
- [ ] Pricing clearly displayed
- [ ] Refund policy published
- [ ] Merchant terms and conditions
- [ ] Payment security disclosure

### Rider/Transport Compliance

- [ ] License verification field
- [ ] Insurance verification field
- [ ] Contractor agreement
- [ ] Safety acknowledgment form
- [ ] Vehicle documentation

---

## 9. Appendices

### A. Files Analyzed

```
Authentication:
- /frontend/src/lib/supabase.ts
- /backend/app/api/v1/endpoints/auth.py
- /backend/app/core/security.py

Data Collection:
- /frontend/src/app/register/page.tsx
- /frontend/src/app/profile/page.tsx
- /frontend/public/widgets/delivery-widget.js

GPS Tracking:
- /frontend/src/app/rider/page.tsx
- /backend/app/api/v1/endpoints/delivery.py

AI Features:
- /frontend/src/app/api/generate/route.ts
- /backend/app/services/stability_service.py
- /backend/app/utils/content_moderation.py

Payment:
- /backend/app/services/toyyibpay_service.py
- /backend/app/api/v1/endpoints/payments.py

Database:
- /DATABASE_SCHEMA.sql
- /backend/migrations/*.sql
- /database/migrations/003_fix_rls_security.sql
```

### B. External Services Data Flows

| Service | Location | Data Sent | Purpose |
|---------|----------|-----------|---------|
| Supabase | Singapore | All user data | Database & Auth |
| ToyyibPay | Malaysia | User ID, email, phone, amount | Payments |
| DeepSeek AI | China | Business descriptions | Content generation |
| Stability AI | Singapore | Business descriptions | Image generation |
| Qwen AI | Singapore | Image URLs, descriptions | Image analysis |
| Cloudinary | Global CDN | Images | Storage |

### C. Compliance Monitoring

**Regular Reviews Required:**
- Monthly: Data retention policy enforcement
- Quarterly: Security audit and penetration testing
- Annually: Full PDPA compliance review
- On-demand: Incident response testing

---

*Report prepared for internal use. Consult legal counsel before implementation.*
