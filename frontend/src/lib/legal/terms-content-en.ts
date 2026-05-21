/**
 * BinaApp Terms of Service v3.0 — English (translation for convenience only)
 *
 * The Bahasa Malaysia version (`terms-content-bm.ts`) is the
 * authoritative version. In case of any conflict, BM prevails — see
 * section 24 (`prevailingLanguage`).
 *
 * Effective: 21 May 2026. Supersedes v2.0 (31 January 2025) and v1.0.
 *
 * This file reuses the `TermsOfService` type and all sub-types from
 * the BM source-of-truth file rather than redefining them — keeps
 * schema parity strict. Section IDs are intentionally identical to
 * the BM file (cross-document anchor links work in both languages).
 *
 * Word count: 8810 EN words. Estimated reading time: 38 minutes at
 * 230 wpm (English reading speed average).
 */

import type { TermsOfService } from './terms-content-bm';

export const termsEN: TermsOfService = {
  version: '3.0',
  effectiveDate: '21 May 2026',
  lastUpdated: '21 May 2026',
  estimatedReadingMinutes: 38,

  executiveSummary: {
    title: '1-Minute Summary',
    content: `This summary is for quick reference only and **does not** replace the full Terms below. Please read the relevant sections for complete details.

- **What BinaApp is:** A SaaS AI website-builder platform for F&B businesses in Malaysia. **Not** a food delivery platform, **not** a restaurant chain, **not** a rider employer.
- **Subscription plans:** Free (RM 0, watermark & preview mode), Starter (RM 5/month), Basic (RM 29/month), Pro (RM 49/month). Auto-renewal monthly, cancellable anytime, no pro-rata mid-cycle refund.
- **Addons:** Additional slots for specific limits (websites, AI hero, AI images, rider slots, delivery zones). Valid for 365 days. Unused addons refundable within 7 days of purchase.
- **What you are responsible for:** Menu content, price accuracy, food safety, business licensing (SSM, halal, food handling), obligations to riders you engage, and integrity of the customer data you upload.
- **What BinaApp is NOT responsible for:** Food quality, delivery times, customer-merchant disputes, unreviewed AI hallucinations, customer payments that fail to arrive via static QR, and rider actions during delivery.
- **Liability:** Limited to 12 months of subscription fees (or RM 100 for Free Plan users).
- **Disputes:** Subject to the laws of Malaysia. Courts in Kuala Lumpur have exclusive jurisdiction.
- **Privacy:** Collection and processing of personal data is governed by the BinaApp Privacy Policy (\`/polisi-privasi\`).`,
  },

  businessModelCallout: {
    title: "Understanding BinaApp's Business Model",
    content: `**Please read this section first — it forms the foundation for understanding the subsequent terms.**

**What BinaApp is:**

- A SaaS (Software-as-a-Service) platform that provides tools for F&B businesses in Malaysia to build and manage their own websites;
- A technical infrastructure provider for the merchant dashboard, ordering system, menu management, and delivery operations;
- A provider of an AI pipeline for content generation (websites, images, automated replies, complaint analysis).

**What BinaApp is NOT:**

- **NOT** a food delivery platform such as foodpanda, GrabFood, or ShopeeFood;
- **NOT** a restaurant chain, franchise, or inventory holder;
- **NOT** a cloud kitchen or kitchen operator;
- **NOT** a payment processor for customer food orders (we only process **merchant subscription payments** through ToyyibPay);
- **NOT** an employer, employment agency, or legal intermediary for riders — riders are independent contractors engaged by the merchant.

**Important implications you need to understand:**

- **The sale contract is between the customer and the merchant**, not with BinaApp. Customers make purchases from the merchant.
- **Money for food orders does not flow through BinaApp at any time.** COD (Cash on Delivery) payments are paid in cash directly to the rider; static QR payments are transferred directly to the merchant's bank account.
- **Any complaints regarding food quality, order accuracy, delivery times, or customer service must be referred directly to the merchant** — BinaApp does not have the authority to resolve such disputes.
- **Riders who use the BinaApp \`/rider\` Progressive Web App are independent contractors of the merchant** — BinaApp does not provide insurance, EPF (Employees Provident Fund / KWSP), SOCSO (Social Security Organization / PERKESO), or any employee rights to riders.

With this understanding as the foundation, the Terms below describe the rights and responsibilities of each party.`,
  },

  introduction: {
    title: 'Preamble',
    content: `These Terms of Service ("**Terms**") constitute a legal agreement between you ("**you**", "**user**", "**merchant**") and **Ezy Work Asia Solution** (SSM No.: 002944700-D), doing business as "**BinaApp**" ("**we**", "**us**", "**BinaApp**").

These Terms govern your access to and use of the BinaApp platform, including the merchant dashboard, generated websites (hosted on \`*.binaapp.my\` subdomains), the rider Progressive Web App, the ordering system, and all related services provided by BinaApp (the "**Services**").

These Terms take effect on **21 May 2026** and supersede all previous versions, including Version 2.0 (dated 31 January 2025) and Version 1.0 (early 2024). See the Version History section for details of changes between versions.

**By registering an account, using the Services, or clicking the "I agree" button during registration, you acknowledge that you have read, understood, and agreed to be bound by these Terms.** If you do not agree, please stop using the Services.`,
  },

  sections: [
    {
      id: 'penerangan-perkhidmatan',
      title: '1. Service Description',
      content: `BinaApp is a **Software-as-a-Service ("SaaS")** platform owned and operated by **Ezy Work Asia Solution** (SSM No.: 002944700-D), a business registered in Malaysia.

The BinaApp platform provides cloud-based software tools to enable F&B business owners in Malaysia to:

- **Generate restaurant websites** through an AI pipeline (HTML generation, hero images, menu images);
- **Manage digital menus** with a content editor;
- **Provide online ordering systems** with multiple payment methods (COD, static QR);
- **Manage delivery operations** through a dispatcher system and a Progressive Web App for riders, including GPS tracking and photo verification;
- **Interact with customers** through a chat system and AI-assisted complaint resolution;
- **Access visitor analytics** to understand website traffic.

**Important disclosure — what BinaApp is, and what it is not:**

BinaApp is a **technical infrastructure provider only**. BinaApp is **not**:

- A food delivery platform;
- A restaurant chain or franchise holder;
- A food seller, inventory holder, or kitchen operator;
- A payment processor for customer food orders;
- An employer, employment agency, or intermediary for riders.

The contractual relationship for food orders is between **the customer and the merchant**. BinaApp provides the technical infrastructure only to facilitate those operations. Please refer to the "Understanding BinaApp's Business Model" section above for the complete picture.`,
    },

    {
      id: 'definisi',
      title: '2. Definitions',
      content: `In these Terms, unless the context otherwise requires:

- **"Addon"** means a unit of additional quota purchased separately from the base subscription plan — for example, additional website slots, additional AI image credits, or additional rider slots. Addons have a validity period of **365 days** from the date of purchase.

- **"AI" or "Artificial Intelligence"** means the machine-learning systems and models used by BinaApp to generate or analyze content, including those provided by third parties. See **Privacy Policy section 6** for full details of the AI providers used.

- **"BinaApp"**, **"we"**, **"us"** means the BinaApp platform, owned and operated by Ezy Work Asia Solution (SSM No.: 002944700-D).

- **"Customer"** means an individual who browses a restaurant website hosted by BinaApp and/or places an order with a merchant through that website. The Customer is **not** a direct contractual party with BinaApp.

- **"Quota"** means the usage limits enforced for each subscription plan — for example, the number of websites allowed, menu items, AI images per period, rider slots, or delivery zones.

- **"Subscription"** means the recurring service you sign up for with BinaApp, covering the Free, Starter, Basic, or Pro Plan.

- **"Merchant"**, **"you"**, **"user"** means the owner of an F&B business (or an authorized representative of that business) who registers and uses a BinaApp account.

- **"Free Plan"** means the entry-level RM 0 plan with limited features — a watermark on the website, preview mode, and minimum quotas.

- **"AI Provider"** means the third-party companies that provide the AI models used by BinaApp, including **Stability AI**, **DeepSeek**, **Qwen (Alibaba Cloud International)**, and **Anthropic**. See Privacy Policy section 6 for full details.

- **"Privacy Policy"** means the current BinaApp Privacy Policy, accessible at \`/polisi-privasi\`.

- **"Static QR"** means a payment QR code image uploaded by the merchant to their dashboard — for example, a DuitNow QR or bank QR — displayed to the customer to facilitate a payment transfer directly to the merchant's bank account. **BinaApp displays the image only and does not process those payments.**

- **"Rider"** means an individual engaged by the merchant to perform deliveries of customer orders. **The Rider is an independent contractor engaged by the merchant; the Rider is NOT an employee, agent, contractor, or representative of BinaApp.** BinaApp only provides software tools for delivery coordination (the dispatcher dashboard, the rider PWA, GPS tracking).

- **"Subdomain"** means the web address with the format \`[businessname].binaapp.my\` granted to the merchant as a limited license to host their restaurant website.

- **"Terms"** means this Terms of Service document, as updated from time to time.`,
    },

    {
      id: 'kelayakan-akaun',
      title: '3. Eligibility & Account',
      content: `**Eligibility requirements for registration:**

To register and use a BinaApp account, you must:

- Be **at least 18 years old**;
- Have the legal capacity to form a binding contract under the laws of Malaysia;
- Own a legitimate F&B business, or be an authorized representative of that business with authority to form a contract on its behalf;
- Not have been previously suspended or terminated from the BinaApp platform.

**Account registration:**

- You must provide **accurate, complete, and current** information during registration;
- You are responsible for updating your account information if it changes (for example, a change in phone number or business details);
- BinaApp may decline a registration application without giving a reason.

**Account credentials & security:**

- You are responsible for maintaining the **confidentiality of your account password**;
- You **must not share login credentials** with unauthorized parties;
- You are responsible for **all activity** that occurs under your account, whether authorized by you or not;
- You must **notify BinaApp immediately** if you suspect any unauthorized access to your account by sending an email to **admin@binaapp.my**.

**BinaApp's right to decline or terminate:**

BinaApp reserves the right to decline a registration application or terminate an existing account if:

- The information provided is false, misleading, or incomplete;
- The user does not meet the eligibility requirements;
- The user's activity violates these Terms, the Privacy Policy, or applicable Malaysian law.

**Multiple accounts:**

Each business may have one primary account. The use of multiple accounts to circumvent quotas or obscure business identity may result in termination of all related accounts.`,
    },

    {
      id: 'pelan-langganan',
      title: '4. Subscription Plans & Billing',
      content: `**4.1 Available Plans**

BinaApp offers the following subscription plans. Please refer to the plans table below for details of the features in each plan.

The Free Plan allows you to explore the platform without payment commitment, but with minimum quotas and a **"Powered by BinaApp" watermark** on the generated website. Paid plans unlock higher quotas and remove the watermark (unless you explicitly choose to retain it).

**Prices may change:** We reserve the right to amend plan prices from time to time. Any price changes will be notified to you **at least 30 days before the change takes effect** via email to the address registered to your account. You may choose to cancel your subscription before a price change takes effect without penalty.

**4.2 Auto-Renewal**

- Subscriptions are **automatically renewed** every month on the same date as your original registration date;
- The renewal charge is applied via ToyyibPay using the payment method you have configured;
- You may **turn off auto-renewal** at any time through dashboard settings. When turned off, your subscription will end at the end of the current billing period, and the account will be downgraded to the Free Plan (or deleted after the retention period, see section 16).

**4.3 Payment Failure**

If a renewal payment fails (for example, insufficient balance, expired card), the following cycle will occur:

- **Day 1:** Automatic retry;
- **Day 3:** A reminder notification is sent to your registered email;
- **Day 7:** Account suspended — dashboard access is restricted; published websites remain live but with a "Account Suspended" banner;
- **Day 30:** The account is **permanently deleted** and all related data is removed (subject to a 30-day backup period, see Privacy Policy section 14).

To avoid deletion, please update your payment method or contact **support.team@binaapp.my** within 30 days of the first payment failure.

**4.4 Addons**

Addons are units of additional quota you may purchase separately to exceed the limits of the base subscription plan. Please refer to the addons table below for the types available and their pricing.

**Addon validity & refund policy:**

- Addons are valid for **365 days** from the purchase date;
- After the expiry period, **unused addons will lapse and cannot be refunded**;
- **Addons that have been used (consumed) cannot be refunded** under any circumstances;
- **Unused addons may be refunded within 7 days** of purchase by sending an email to **admin@binaapp.my** with the subject \`Refund Request - Addon\` and the transaction details.

**Addon usage:**

- Addons combine with your subscription plan quota **additively** (for example, if your plan allows 10 AI images per month and you purchase 1 ai_image addon, you have 11 images for that month);
- Addons are **not auto-renewed** — you must repurchase when they expire.

**4.5 Quota & Enforcement**

Each plan has specific quota limits. Please refer to the quota table below for details of the limits in each plan.

**Specifically for rider slots — addon semantics:**

The Free, Starter, and Basic Plans have a default rider slot quota of **zero**. To enable riders, you must purchase the \`rider\` addon (RM 3 per slot, valid 365 days). The Pro Plan has **10 base rider slots** and rider addons may be purchased to **extend** beyond 10 slots.

The formula is **additive**: effective rider quota = (base plan limit) + (number of active addon slots).

**Behaviour when quota is reached:**

When the quota reaches the limit, the related feature will be **blocked**. You have three options:

- **(a) Wait until monthly reset** — monthly quotas (AI hero, AI images) reset on your billing cycle date;
- **(b) Purchase an addon** for the specific limit (see section 4.4);
- **(c) Upgrade your subscription** to a higher plan.

**Quota measurement:**

- Monthly quotas (AI hero, AI images) are calculated based on the Malaysia local calendar month (GMT+8);
- Static quotas (websites, menu items, rider slots, zones) are calculated based on the active total at any time.`,
      tierTable: [
        {
          tier: 'Free',
          price: 'RM 0/month',
          features: [
            '"Powered by BinaApp" watermark on the website',
            'Preview mode for platform experimentation',
            '1 website',
            '20 menu items (per website)',
            '3 AI hero images / month',
            '10 AI menu images / month',
            '0 delivery zones (addon required)',
            '0 rider slots (addon required)',
            'Community support only',
          ],
        },
        {
          tier: 'Starter',
          price: 'RM 5/month',
          features: [
            'No watermark',
            '1 website',
            '20 menu items (per website)',
            '1 AI hero image / month',
            '5 AI menu images / month',
            '1 delivery zone',
            '0 rider slots (addon required)',
            'Email support (48-72 hour response during business hours)',
          ],
        },
        {
          tier: 'Basic',
          price: 'RM 29/month',
          features: [
            'No watermark',
            '5 websites',
            'Unlimited menu items (per website)',
            '10 AI hero images / month',
            '30 AI menu images / month',
            '5 delivery zones',
            '0 rider slots (addon required)',
            'Email support (24-48 hour response during business hours)',
          ],
        },
        {
          tier: 'Pro',
          price: 'RM 49/month',
          features: [
            'No watermark',
            'Unlimited websites',
            'Unlimited menu items',
            'Unlimited AI hero images',
            'Unlimited AI menu images',
            'Unlimited delivery zones',
            '10 base rider slots (addon to extend)',
            'Priority support (12-24 hour response during business hours)',
          ],
        },
      ],
      addonTable: [
        {
          addonType: 'ai_image (Additional AI Menu Image)',
          price: 'RM 1 per credit',
          expiry: '365 days from purchase',
          refundPolicy: 'Unused: refund within 7 days • Used: no refund',
        },
        {
          addonType: 'ai_hero (Additional AI Hero Image)',
          price: 'RM 2 per credit',
          expiry: '365 days from purchase',
          refundPolicy: 'Unused: refund within 7 days • Used: no refund',
        },
        {
          addonType: 'website (Additional Website Slot)',
          price: 'RM 5 per slot',
          expiry: '365 days from purchase',
          refundPolicy: 'Unused: refund within 7 days • Used: no refund',
        },
        {
          addonType: 'rider (Additional Rider Slot)',
          price: 'RM 3 per slot',
          expiry: '365 days from purchase',
          refundPolicy: 'Unused: refund within 7 days • Used: no refund',
        },
        {
          addonType: 'zone (Additional Delivery Zone Slot)',
          price: 'RM 2 per slot',
          expiry: '365 days from purchase',
          refundPolicy: 'Unused: refund within 7 days • Used: no refund',
        },
      ],
      quotaTable: [
        {
          limitType: 'Number of websites',
          free: '1',
          starter: '1',
          basic: '5',
          pro: 'Unlimited',
        },
        {
          limitType: 'Menu items (per website)',
          free: '20',
          starter: '20',
          basic: 'Unlimited',
          pro: 'Unlimited',
        },
        {
          limitType: 'AI hero images / month',
          free: '3',
          starter: '1',
          basic: '10',
          pro: 'Unlimited',
        },
        {
          limitType: 'AI menu images / month',
          free: '10',
          starter: '5',
          basic: '30',
          pro: 'Unlimited',
        },
        {
          limitType: 'Delivery zones',
          free: '0 (addon required)',
          starter: '1',
          basic: '5',
          pro: 'Unlimited',
        },
        {
          limitType: 'Rider slots',
          free: '0 (addon required)',
          starter: '0 (addon required)',
          basic: '0 (addon required)',
          pro: '10 (addon to extend)',
        },
      ],
    },

    {
      id: 'pembatalan-refund',
      title: '5. Subscription Cancellation & Refunds',
      content: `**Subscription cancellation:**

You may cancel your subscription at **any time** through dashboard settings ("Account" → "Subscription" → "Cancel Subscription") or by sending an email to **support.team@binaapp.my**.

**Effects of cancellation:**

- The subscription remains active **until the end of the current billing period** that has been paid;
- After that period, your account will be **downgraded to the Free Plan** (or deleted after the retention period if you choose full deletion, see section 16);
- There is **no pro-rata mid-cycle refund** — if you cancel on day 15 of a 30-day cycle, you retain access until day 30 but do not receive a refund for the remaining 15 days;
- Your merchant data remains secured for **30 days after downgrade to the Free Plan** or account deletion (as an emergency backup), then permanently deleted.

**Refunds for subscriptions:**

As a general policy, **no refunds are issued for subscription fees already paid**, except in cases of:

- **Confirmed billing error** — we will return any wrongful charges;
- **Material breach of these Terms by BinaApp** that materially affects your ability to use the Services — a pro-rata refund may be granted at our discretion;
- **Legal obligations** requiring us to issue a refund.

To request a refund, send an email to **admin@binaapp.my** with the subject \`Refund Request - Subscription\` along with the transaction details and the reason for the request within **7 days** of payment.

**Refunds for addons:**

Please refer to section 4.4 for the addon refund policy (summary: unused + within 7 days = refund; used = no refund; expired at 365 days = no refund).

**Refunds for food orders:**

**BinaApp does not process customer payments for food orders** (see the business-model callout above). Therefore:

- **Food order refunds are the merchant's own policy** — BinaApp has no authority to initiate such refunds;
- Customers wishing to request a refund for a food order must **contact the merchant directly**;
- For COD orders: refunds involve the customer and the merchant directly (cash);
- For static QR orders: refunds involve the customer and the merchant through a bank transfer;
- BinaApp may provide **order records and chat logs** as evidence to any relevant party upon request, but cannot issue refunds itself.`,
    },

    {
      id: 'tanggungjawab-pengguna',
      title: '6. User Responsibilities (Prohibited Activities)',
      content: `You agree **not** to, and will not permit any third party to, engage in any of the following activities while using the Services:

**(a) Technical violations:**

- Perform **reverse engineering, decompiling, disassembly**, or attempt to obtain the source code of the Services;
- Run **automated scraping, crawling, or bots** to extract data from the platform without written permission;
- **Obscure or bypass** the quota system, rate limits, or security measures;
- **Upload malware, viruses, worms, trojans, or other harmful code** to the platform.

**(b) Commercial violations:**

- **Resell, sub-license, or rent** access to the Services to third parties without a written agreement with BinaApp;
- **Share account credentials** with unauthorized individuals;
- Use the Services to **provide competing services** that copy or replicate BinaApp's functionality;
- Register **multiple accounts** to circumvent quotas or obscure business identity.

**(c) Content violations:**

- Use the Services to sell or promote **non-halal or haram products** in Malaysia, including: alcohol (to Muslim users), pork products (on halal premises), gambling, illegal drugs, or products that violate Malaysian law;
- Upload **false, misleading, or deceptive** content to customers (for example, false prices, deceptive product images, fake reviews);
- Upload content that **infringes third-party intellectual property rights** (logos, copyrighted images, trademarks);
- Use the Services for **spam, harassment, threats, or abuse** of customers, riders, or other users;
- Upload content that is **obscene, violent, or in violation of Malaysian content regulations**.

**(d) Data violations:**

- Upload customer or third-party data **without appropriate consent** (please see Privacy Policy section 18 for your responsibilities);
- **Misuse customer data** for unauthorized purposes (for example, selling customer lists to advertisers without consent).

**(e) Financial violations:**

- Use the Services for **money laundering**, **fraud**, or financial activities that violate the law;
- Provide **false payment information** or use stolen cards/accounts.

**Consequences of violation:**

Violation of any of the prohibited activities above may result in:

- **Written warning** for minor violations;
- **Account suspension** for moderate violations;
- **Immediate account termination without refund** for serious or repeated violations;
- **Referral to Malaysian authorities** for legal violations;
- **Legal claims** for damages suffered by BinaApp or third parties.`,
    },

    {
      id: 'tanggungjawab-merchant',
      title: '7. Merchant-Specific Responsibilities',
      content: `As a merchant using the Services for your F&B business, you are fully responsible for:

**(a) Menu & price accuracy:**

- Ensuring **menu content, prices, and product descriptions are accurate and up to date**;
- Updating the menu when items are unavailable (out of stock);
- Ensuring the prices displayed to customers are the actual prices that will be charged.

**(b) Food safety & quality:**

- Complying with **Malaysian food safety standards** (Food Act 1983, Food Hygiene Regulations 2009);
- Maintaining **hygiene standards** in your kitchen and preparation areas;
- Storing and delivering food at **appropriate temperatures** to prevent contamination;
- **BinaApp does not conduct hygiene, quality, or food safety inspections of your business** — this is your exclusive responsibility as a merchant.

**(c) Business licensing:**

You are responsible for obtaining and maintaining all licenses, permits, and registrations required for F&B business operations in Malaysia, including but not limited to:

- **SSM business registration** (Companies Commission of Malaysia);
- **Food and beverage licenses** from your local authority (PBT / Pihak Berkuasa Tempatan);
- **JAKIM halal certification** (if you promote products as halal);
- **Food handling certificates** for staff who handle food;
- **Tax registration (SST)** if applicable.

BinaApp will not verify or monitor your license status. We reserve the right to suspend an account if we receive complaints about unlicensed operations.

**(d) Order fulfilment:**

- **Fulfilling customer orders within a reasonable time** as promised on your website;
- **Communicating with customers** about delays, cancellations, or unavailable items;
- **Handling customer complaints** professionally and in a timely manner.

**(e) Customer data integrity:**

- **Ensuring the accuracy of customer data** entered into the platform;
- Obtaining **appropriate consent** from customers before uploading their personal data (please see **Privacy Policy section 18** for details of your obligations as data controller);
- **Responding to PDPA requests from customers** in a timely manner (access, correction, deletion of their personal data).

**The merchant is fully responsible for the integrity of customer data entered into BinaApp.** BinaApp acts as a data processor only.

**(f) Obligations to riders:**

If you engage riders for delivery operations through the BinaApp system:

- You are responsible for the **legal contract with the rider** (as an independent contractor or employee, according to the structure you choose);
- You are responsible for **payments to the rider** (BinaApp does not process rider payments);
- You are responsible for **insurance, safety protection**, and other legal obligations relating to the rider (BinaApp does not provide rider insurance);
- Please see section 9 for further details.`,
    },

    {
      id: 'notis-pengguna-akhir',
      title: '8. Notice to End-Users',
      content: `**This section is an informational notice and is not a binding obligation on customers.**

Customers who browse restaurant websites hosted by BinaApp (for example, \`[businessname].binaapp.my\`) **are not direct contractual parties with BinaApp**.

**Contractual relationship for food orders:**

- When a customer places an order, **the sale contract is between the customer and the merchant**;
- **BinaApp provides the technical infrastructure only** — BinaApp is not a seller, commercial intermediary, or party to the sale transaction;
- **Any claim, complaint, or refund request for a food order must be referred directly to the merchant**, not BinaApp.

**Collection of customer data:**

When a customer enters their personal data through the website (for example, name, phone number, delivery address), that data is collected **on behalf of the merchant**. **The merchant is the primary data controller** for their customer data, and BinaApp acts as a data processor.

Please see **Privacy Policy section 12** for full details of the collection of visitor data and customer privacy rights.

**Customer rights:**

- For access, correction, or deletion of their personal data, customers should contact **the merchant directly**;
- If the merchant does not respond, customers may contact BinaApp at **admin@binaapp.my** and we will facilitate the request to the merchant;
- Customers also have the right to file a complaint with the **Personal Data Protection Department of Malaysia** (1-300-88-2400, www.pdp.gov.my).

**Purpose of this notice:**

This notice is provided to clarify BinaApp's business model to customers. It **does not constitute a contractual obligation** enforceable by BinaApp against customers. Customers **do not need to accept these Terms** to place a food order, because the sale contract is with the merchant, not BinaApp.`,
    },

    {
      id: 'disclaimer-penghantaran',
      title: '9. Delivery Operations Disclaimer',
      content: `**Important disclosure about rider status:**

Riders who use the BinaApp \`/rider\` Progressive Web App to perform deliveries are **independent contractors engaged by the merchant**, and **NOT**:

- BinaApp employees;
- BinaApp contractors;
- BinaApp agents or representatives;
- Intermediaries between BinaApp and the merchant.

**What BinaApp provides to riders:**

BinaApp only provides **technical software tools** to riders for delivery coordination, namely:

- A Progressive Web App (\`/rider\`) to accept delivery assignments;
- GPS tracking during active deliveries (to be displayed to the merchant and customer);
- An interface for uploading proof-of-delivery photos;
- Communication channels with the merchant's dispatcher.

**What BinaApp does NOT provide to riders:**

- **Accident insurance, medical insurance, or financial guarantees** for riders;
- **EPF (Employees Provident Fund / KWSP), SOCSO (Social Security Organization / PERKESO), or EIS (Employment Insurance System) contributions**;
- **Wages, commissions, bonuses, or any payments** to riders;
- **Road safety training** or rider certification;
- **Employee legal protections** as enshrined under the Employment Act 1955.

**Legal status of the rider:**

The rider's legal relationship is **exclusively with the merchant who engages them**, and is subject to the agreement between them (oral or written). The merchant is responsible for:

- Making a **valid contract** with the rider (independent contractor or employee);
- Paying the **agreed compensation** to the rider;
- Providing **appropriate insurance** for the rider (accident, third-party liability, etc.);
- Complying with the **Malaysian legal obligations** relating to the employment structure chosen (EPF/SOCSO if an employee, proper independent-contractor status if applicable).

**Responsibility for rider actions:**

BinaApp is **not responsible** for:

- Accidents, injuries, or death of riders during delivery;
- Damage to vehicles, property, or third parties as a result of rider actions;
- Traffic law violations by riders;
- Theft, accidents, or delays in orders caused by the rider;
- Unprofessional or unlawful acts by the rider.

**Full liability for all of the above rests with the merchant who engaged the rider, and/or the rider themselves as an independent contractor, according to their agreement.**`,
    },

    {
      id: 'disclaimer-qr-statik',
      title: '10. Static QR Disclaimer',
      content: `**Important disclosure about Static QR:**

If a merchant chooses to enable payment via **Static QR** (a payment QR code such as DuitNow QR or a bank QR), the merchant uploads the QR image to their dashboard. This QR image is then displayed to the customer at the time of order or on the order screen.

**What BinaApp does with the Static QR:**

- **Displays the QR image** to the customer at order time;
- Stores the QR image in the merchant's dashboard for ease of access.

**What BinaApp does NOT do with the Static QR:**

- **Does NOT verify the authenticity** of the QR code (we do not scan or verify that the QR actually points to the merchant's account);
- **Does NOT guarantee** that the payment reaches the merchant's bank account;
- **Does NOT process, receive, or hold** the customer's payment money;
- **Does NOT record** payment transaction details (BinaApp only records the order status: paid / unpaid);
- **Does NOT issue receipts** for customer payments (receipts are issued by the customer's bank or payment app).

**Merchant responsibilities:**

- **Ensuring the QR image uploaded is a valid QR** owned by you or your business;
- **Verifying customer payment receipts** (for example, through bank notifications or payment apps) before confirming the order status as "paid";
- **Resolving any payment disputes** with the customer directly.

**Full disclaimer:**

BinaApp is **not responsible** for:

- A customer transferring to the **wrong account** (for example, due to the QR being swapped or compromised);
- A customer **claiming to have paid** but the transfer not being received by the merchant;
- **QR fraud** by third parties (for example, fake QR codes pasted over valid QRs);
- **Overdraft charges, transaction fees**, or other financial costs incurred by the customer or merchant.

Any Static QR payment dispute is **between the customer and the merchant** and is resolved directly between them, or through the customer's bank/payment provider. BinaApp may assist by providing **order records and chat logs** as evidence, but cannot make dispute decisions or initiate refunds.`,
    },

    {
      id: 'disclaimer-ai',
      title: '11. AI Content Disclaimer',
      content: `BinaApp uses generative AI and analytical AI to deliver features such as:

- HTML website generation;
- Menu and hero image generation;
- Reply text generation in customer-merchant chat;
- Complaint analysis and refund action recommendations;
- Delivery photo verification.

**Full disclaimer regarding AI content:**

Content generated by AI is provided **"as-is"** without warranty of accuracy, suitability, or fitness for a particular purpose. AI **may produce**:

- **Hallucinations (false facts)** — for example, inaccurate business details in generated HTML;
- **Culturally inappropriate content** — for example, images or text that do not respect Malaysian local values;
- **Inaccurate language** — for example, incorrect BM grammar, inappropriate dialect use;
- **Inaccurate refund recommendations** — AI complaint analysis is only a recommendation; the final decision rests with the merchant;
- **Wrongly verified delivery proof photos** — AI may incorrectly verify blurry or invalid photos as valid, or vice versa.

**Merchant responsibilities:**

The merchant is **fully responsible for reviewing and approving all AI content before:**

- Publishing a website to customers;
- Sending reply messages to customers;
- Making refund decisions based on AI recommendations;
- Confirming deliveries based on AI photo verification results.

**Intellectual property rights of AI content:**

- BinaApp **does not warrant** that AI-generated content is **free from third-party copyright infringement** — particularly for generated images, which may resemble existing copyrighted works;
- **The merchant is responsible** for copyright infringements arising from the use of AI-generated content;
- For AI content ownership rights, please see section 14.3.

**Data transfer to AI providers:**

Use of AI features involves data transfer to third-party AI providers (Stability AI, DeepSeek, Qwen, Anthropic). See **Privacy Policy sections 6 and 16** for details of providers, processing regions, and PII risks.

**Right to refuse AI use:**

If you are uncomfortable with AI processing for a particular feature, you may:

- **Avoid that feature** (for example, handling complaints manually without AI analysis);
- **Contact us** at admin@binaapp.my to discuss alternative options.`,
    },

    {
      id: 'pdpa-link',
      title: '12. Personal Data Protection',
      content: `The collection, use, disclosure, retention, and processing of your personal data (as a merchant) and customer data that you upload to the BinaApp platform is governed by the **BinaApp Privacy Policy**, accessible at **\`/polisi-privasi\`**.

By using the Services, **you agree to the terms of that Privacy Policy**, including:

- Disclosure of data to third-party AI providers (Stability AI, DeepSeek, Qwen, Anthropic);
- Cross-border data transfers to Singapore, the United States, and the People's Republic of China;
- Collection of first-party analytics data on generated websites;
- Subscription payment processing via ToyyibPay.

**Your data subject rights under PDPA 2010:**

You have rights of access, correction, withdrawal of consent, deletion, portability, and restriction of processing over your personal data. These rights may be exercised through the methods set out in **Privacy Policy section 15**.

**For privacy inquiries or PDPA requests**, please send an email to **admin@binaapp.my** in the format specified in the Privacy Policy.

**Future commitment:**

BinaApp is committed to improving privacy practices through the implementation of explicit consent UI for AI features handling PII, a cookie banner on restaurant websites, and support for the HTTP Do-Not-Track header within **60 days** of the effective date of the Privacy Policy (see **Privacy Policy section 20**).`,
    },

    {
      id: 'alat-perisian',
      title: '13. Software Tools & Features',
      content: `The BinaApp Services include the following software tools and features:

**(a) Merchant dashboard:**
The primary interface for managing accounts, subscriptions, websites, menus, and operations.

**(b) AI content generation pipeline:**
Automatic generation of websites, images, and text using four primary AI providers. See **Privacy Policy section 6** for details of each provider.

**(c) Menu editor (\`/menu-designer\`):**
A tool to design and manage digital menus, including categories, items, prices, and images.

**(d) Delivery dispatcher system (\`/delivery\`):**
The interface for merchants to manage delivery assignments to riders, view real-time delivery status, and resolve issues.

**(e) Rider Progressive Web App (\`/rider\`):**
A PWA installed on rider devices to receive assignments, update status, upload delivery proof photos, and communicate with the dispatcher.

**(f) GPS tracking:**
A rider location tracking system during active deliveries. See **Privacy Policy section 5** for details of GPS data collection.

**(g) Customer-merchant chat system:**
A direct communication channel between customers and merchants through a chat interface on the restaurant website.

**(h) AI-assisted complaint resolution system:**
A workflow for resolving customer complaints, with action recommendations (full refund, partial refund, or reject) generated by AI for merchant consideration.

**(i) Addon system:**
Purchase of additional quota units for websites, AI images, rider slots, and delivery zones.

**(j) First-party visitor analytics:**
Restaurant website traffic tracking for the merchant's analytics dashboard. See **Privacy Policy section 11**.

**(k) BinaBot:**
An in-dashboard support chatbot to assist merchants with questions about the platform.

**Feature updates:**

BinaApp may add, modify, or remove features from time to time. Material new features or removals will be notified to you in accordance with section 22 (Amendments to Terms).`,
    },

    {
      id: 'harta-intelek',
      title: '14. Intellectual Property Rights',
      content: `**14.1 Platform Ownership by BinaApp**

All intellectual property rights related to the BinaApp platform, including:

- **Source code** (frontend, backend, infrastructure);
- **User interface design (UI/UX)**;
- **"BinaApp" trademark** and BinaApp logo;
- **Technical documentation** and training materials;
- **Algorithms and business logic**;
- **Website template database** provided by BinaApp;

are the exclusive property of **Ezy Work Asia Solution** (the operator of BinaApp) or licensed to us by third parties. No rights are granted to you except as explicitly stated in these Terms.

You **may not**:
- Copy, modify, or distribute the platform's source code or materials;
- Use the "BinaApp" trademark without written permission;
- Claim ownership of any platform component.

**14.2 Content Ownership by Merchant**

You **retain full ownership** of the content you upload or create using the platform, including:

- **Menus, prices, and product descriptions** that you enter;
- **Business logos** that you upload;
- **Original product photos** that you upload;
- **Business information** (name, address, hours of operation, etc.);
- **Merchant's own policies** (terms of sale, refund policy, etc.).

**License you grant to BinaApp:**

To enable BinaApp to provide the Services, you grant BinaApp a **royalty-free, worldwide, non-exclusive, sub-licensable license** to:

- Display your content on the generated website;
- Process the content for platform functions (for example, AI generation);
- Make backups and replication for operational purposes.

This license terminates when you terminate the account, subject to the retention period for backups (see Privacy Policy section 14).

**14.3 AI-Generated Content**

For content generated through the BinaApp AI pipeline (HTML websites, menu images, hero images, reply texts):

- **Ownership transfers to the merchant** — BinaApp **does not claim copyright** to AI output;
- You are free to use, modify, or publish the AI-generated content for your business;
- **BinaApp retains a limited, royalty-free background license** to display and process such AI content as part of platform operations.

**Important exceptions:**

- **BinaApp does not warrant** that AI-generated content is **free from third-party copyright infringement**. AI-generated images may resemble existing copyrighted works (see section 11);
- **You are responsible** for copyright infringements arising from the use of AI-generated content.

**14.4 Subdomain License**

BinaApp grants you a **limited, non-exclusive, revocable license** to use the subdomain \`[businessname].binaapp.my\` to host your restaurant website.

**Subdomain license conditions:**

- The subdomain must be **grammatically valid** and not misleading (for example, not resembling another brand);
- The subdomain must be **related to your legitimate F&B business**;
- It may not be used to **squat on third-party trademarks** or identities (trademark squatting).

**BinaApp's right to revoke a subdomain:**

BinaApp reserves the right to **revoke a subdomain without prior notice** if the subdomain is used for:

- **Illegal activities or activities that violate Malaysian law**;
- **Violations of these Terms** (for example, prohibited content);
- **Violations of third-party rights** (trademark, copyright);
- **Content containing hate speech, obscenity, or violence**.

**License termination:**

The subdomain license **automatically terminates** when:

- You terminate your BinaApp account;
- BinaApp terminates your account for Terms violations;
- The subdomain is revoked for the reasons stated above.

After termination, BinaApp may **reclaim and reassign** the subdomain to another user.`,
    },

    {
      id: 'ketersediaan-perkhidmatan',
      title: '15. Service Availability',
      content: `**Uptime target:**

BinaApp sets a target of **99.9% service availability** for the main platform components (dashboard, ordering system, published websites). However, **we do not guarantee** this uptime as an enforceable contractual commitment.

**Scheduled maintenance:**

From time to time, we need to perform scheduled maintenance to update software, improve security, or enhance performance. For maintenance that will cause **significant service disruption**, we will:

- **Give at least 24 hours notice** in advance via email and a dashboard banner;
- **Schedule maintenance during low-traffic hours** when possible (for example, 2 AM - 4 AM Malaysia time);
- **Notify of restoration status** when maintenance is complete.

**Emergency maintenance:**

For **critical security issues or unexpected outages**, we may perform maintenance without prior notice. We will notify you as soon as possible after the issue is resolved.

**Force majeure:**

BinaApp is **not responsible** for service disruptions caused by events beyond our control, including but not limited to:

- Natural disasters (earthquakes, floods, typhoons);
- Government action (sanctions, orders, export controls);
- **Third-party provider infrastructure** disruptions (Supabase, Render, Vercel, ToyyibPay, AI providers);
- Large-scale cyber attacks (unusual DDoS, ransomware);
- Utility network disruptions (electricity, ISP internet);
- War, riots, or civil unrest.

**Support tiers by plan:**

Support inquiry response (business hours Monday-Friday, 9 AM - 6 PM Malaysia time):

- **Free Plan:** Community support only (no SLA);
- **Starter Plan:** Email response within **48-72 hours** of business hours;
- **Basic Plan:** Email response within **24-48 hours** of business hours;
- **Pro Plan:** Priority response within **12-24 hours** of business hours.

For critical issues (complete service outage, data breach), we strive to respond as quickly as possible regardless of subscription tier.

**Compensation for disruption:**

We **do not provide automatic compensation or subscription extensions** for service disruption, except in cases of:

- A **disruption lasting more than 24 hours** caused by our technical fault;
- A compensation request **approved at our discretion**.

To request compensation, send an email to **support.team@binaapp.my** with details of the disruption.`,
    },

    {
      id: 'penamatan-akaun',
      title: '16. Account Termination',
      content: `**Termination by you:**

You may terminate your BinaApp account at **any time** by:

- Cancelling the subscription through dashboard settings (account downgraded to the Free Plan at the end of the billing period);
- Sending an email to **admin@binaapp.my** with the subject \`Account Termination Request\` for full account deletion.

**Effects of termination:**

- Access to the dashboard is terminated on the effective termination date;
- **Published websites** will be **deleted** from BinaApp hosting;
- **Merchant data** (account, menus, orders, etc.) is **deleted** in accordance with the retention policy (see **Privacy Policy section 14**), including:
  - **30 days** of emergency backup for recovery;
  - **7 years** for order records and payment transactions (legal accounting and tax requirements);
  - After the backup/retention period, data is permanently deleted.

**No refunds:**

Account termination **does not entitle you to a refund** of subscription fees paid for the current billing period. Please see section 5 for the refund policy.

**Termination by BinaApp:**

BinaApp may terminate your account with or without notice in the following circumstances:

- **Material breach of these Terms** or the Privacy Policy (for example, the prohibited activities in section 6);
- **Continued payment failure** exceeding 30 days (see section 4.3);
- **Activity violating Malaysian law** or that compromises platform security;
- **Account abandonment** (no login activity for 180 days on the Free Plan);
- **Court order** or legal obligation.

**Notice of termination:**

- For **non-material violations**, we will give a **written warning** and a **14-day remediation period** before termination;
- For **material violations or unlawful activities**, we may terminate **immediately without notice**.

**Data export before termination:**

Before terminating an account, you have the right to **export your data** in a structured format. Contact us at **admin@binaapp.my** to request a data export, in accordance with the right to portability in Privacy Policy section 15.

**Survival clause:**

The following clauses will **continue in force** after account termination:

- Intellectual property rights (section 14);
- Limitation of liability (section 18);
- Indemnification (section 19);
- Governing law and disputes (section 21);
- Legal retention obligations (see Privacy Policy section 14).`,
    },

    {
      id: 'perkhidmatan-pihak-ketiga',
      title: '17. Third-Party Services',
      content: `BinaApp relies on several third-party providers to deliver the Services. Please refer to the third-party services table below for details of each provider and links to their privacy policies.

**Contractual relationships:**

- BinaApp has **commercial agreements** with each of the third-party providers above;
- Your use of the Services **consents to the necessary data transfers** to these providers, in accordance with Privacy Policy sections 6 and 16.

**Liability for third-party disruption:**

If a service disruption is caused by a **third-party provider failure**, BinaApp is **not responsible** for losses, but we will:

- **Find alternative solutions** as quickly as possible;
- **Notify status** to users via email and a dashboard banner;
- **Communicate with the provider** to expedite recovery.

**Right to change providers:**

BinaApp reserves the right to **change or add third-party providers** from time to time to improve service quality, cost, or privacy compliance. Material provider changes will be notified to you in accordance with section 22 (Amendments to Terms) and the Privacy Policy.

**Provider privacy policies:**

You are encouraged to read each third-party provider's privacy policy to understand their privacy practices. BinaApp does not control those policies and **is not responsible** for changes in provider privacy practices.`,
      thirdPartyTable: [
        {
          service: 'ToyyibPay',
          region: 'Malaysia',
          purpose: 'Processing of merchant subscription payments',
          policyUrl: 'https://toyyibpay.com/privacy-policy',
        },
        {
          service: 'Supabase',
          region: 'Singapore / Southeast Asia',
          purpose: 'Database and storage (primary data retention)',
          policyUrl: 'https://supabase.com/privacy',
        },
        {
          service: 'Render',
          region: 'Singapore / Global',
          purpose: 'Backend application hosting',
          policyUrl: 'https://render.com/privacy',
        },
        {
          service: 'Vercel',
          region: 'United States / Global',
          purpose: 'Frontend hosting and content delivery network (CDN)',
          policyUrl: 'https://vercel.com/legal/privacy-policy',
        },
        {
          service: 'Stability AI',
          region: 'United States',
          purpose: 'AI image generation (hero, menu items)',
          policyUrl: 'https://stability.ai/privacy-policy',
        },
        {
          service: 'DeepSeek',
          region: "People's Republic of China",
          purpose: 'AI website generation, complaint analysis, AI chat replies, BinaBot',
          policyUrl: 'https://www.deepseek.com/privacy',
        },
        {
          service: 'Qwen / Alibaba Cloud International',
          region: 'Singapore',
          purpose: 'Delivery photo verification, content improvements',
          policyUrl: 'https://www.alibabacloud.com/help/en/legal/privacy-policy',
        },
        {
          service: 'Anthropic Claude',
          region: 'United States',
          purpose: 'Support email analysis (with sanitization)',
          policyUrl: 'https://www.anthropic.com/privacy',
        },
      ],
    },

    {
      id: 'had-liabiliti',
      title: '18. Limitation of Liability',
      content: `**(a) Maximum Liability Cap**

To the extent permitted by Malaysian law, **BinaApp's maximum aggregate liability** to you for all claims arising out of or relating to these Terms or the Services, whether in contract, tort (including negligence), breach of statutory duty, or otherwise, shall be **limited to the higher of:**

- **The total subscription fees you have paid to BinaApp in the 12 months immediately preceding** the event giving rise to the claim; or
- **RM 100** (for Free Plan users or users who have not paid any fees).

**(b) Exclusion of Liability**

To the extent permitted by law, BinaApp **is not liable** for any of the following losses or damages:

- **Indirect damages**;
- **Consequential damages**;
- **Special damages**;
- **Punitive damages** or exemplary damages;
- **Loss of profit**, whether direct or indirect;
- **Loss of revenue, business, or business opportunity**;
- **Loss of data or business goodwill**;
- **Losses caused by AI hallucinations or errors** that were not reviewed by the merchant;
- **Losses caused by food poisoning, food-related illness**, or any food safety issues;
- **Losses caused by delivery accidents, rider injuries**, or property damage during delivery;
- **Losses caused by rider negligence**, theft, or unprofessional rider actions;
- **Customer-merchant disputes** including refunds, wrong orders, delivery times;
- **Static QR payment disputes** or any customer-merchant payment issues;
- **Third-party provider service disruptions** (ToyyibPay, Vercel, Render, Supabase, AI providers);
- **Delays or failures due to force majeure** (see section 15).

**(c) Carve-Outs That Cannot Be Limited (Malaysian Law Carve-Outs)**

Nothing in these Terms shall exclude or limit BinaApp's liability for:

- **Fraud or fraudulent misrepresentation**;
- **Willful misconduct**;
- **Death or personal injury** caused by BinaApp's negligence;
- **Any liability that cannot be excluded or limited under Malaysian law**.

**(d) Basis of Exclusion**

You acknowledge that:

- BinaApp's subscription fees are set **based on the liability limit** stated in these Terms;
- If BinaApp were required to bear higher liability, the subscription fees **would be significantly higher** to cover the cost of the risk;
- This allocation of risk is **fair and reasonable** in the context of B2B SaaS in Malaysia.

**(e) Time Limit for Claims**

Any claim against BinaApp must be made within **1 year** of the date of the event giving rise to the claim. Claims made after this period will be deemed **waived**.`,
    },

    {
      id: 'indemniti',
      title: '19. Indemnification',
      content: `**Indemnification by Merchant to BinaApp:**

You agree to **indemnify, defend, and hold harmless** BinaApp, its parent and subsidiary companies, directors, officers, agents, contractors, and representatives ("**Indemnified Parties**") from and against **any and all claims, damages, losses, costs, expenses (including reasonable attorneys' fees), penalties, fines, and liabilities** arising out of or in connection with:

**(a) Merchant business operations:**

- Your F&B business operations generally;
- The quality, safety, or authenticity of the food you sell;
- Delivery delays, failures, or wrong orders;
- Customer complaints about your service.

**(b) Merchant content:**

- Content you display on the website or dashboard, including **AI-generated content** that you publish;
- **Third-party intellectual property infringement** caused by your content;
- **False, misleading, or deceptive information** in your content;
- **Content that violates Malaysian law** (obscenity, hate speech, halal/haram).

**(c) Third-party data:**

- Uploading personal data of customers or third parties **without appropriate consent** (see Privacy Policy section 18);
- **Violation of PDPA 2010** or related data protection laws;
- Access, correction, or deletion requests from data subjects that you fail to handle;
- **Fines or penalties** imposed by the PDP Department or other authorities as a result of your actions as data controller.

**(d) Breach of these Terms:**

- Any breach of these Terms by you;
- Prohibited activities in section 6;
- Use of the Services for unauthorized purposes;
- Unauthorized sharing of account credentials.

**(e) Breach of law:**

- **Violations of Malaysian law** relating to F&B business operations (Food Act 1983, local authority regulations, SSM business licensing, JAKIM halal certification);
- **Class employee claims** from riders you engage (claiming BinaApp as employer when the relationship is merchant-rider);
- **Tax law violations** (SST, income tax);
- **Intellectual property claims** from third parties as a result of your content or brand.

**Indemnification process:**

If BinaApp receives a claim subject to this indemnification, we will:

- **Notify you in writing** as soon as possible of the claim;
- Allow you to **assume the defence** of the claim, with reasonable counsel of your choice (BinaApp may remain involved as an observer at our own cost);
- **Cooperate reasonably** with you in the defence.

You **may not settle a claim** involving an admission of liability or financial obligation of BinaApp without our prior written consent.

**Survival:**

This indemnification obligation **continues in force** after account termination for claims relating to the period of your use of the Services.`,
    },

    {
      id: 'pemecahan',
      title: '20. Severability',
      content: `If any **provision, clause, or word** in these Terms is found to be:

- **Invalid**;
- **Unenforceable**;
- **Unlawful**; or
- **Contrary to public policy**;

by a court of competent jurisdiction in Malaysia or by a regulatory authority, then:

- That provision, clause, or word **shall be severed** from these Terms;
- The **remainder of these Terms** shall **remain valid, in force, and fully enforceable**;
- The severed provision shall be **replaced, if possible, with a valid provision** that reflects the original intent of the parties as closely as possible.

**Proportional interpretation:**

If only part of a provision is found invalid, only the invalid part shall be severed, and the valid part shall be enforced.

**No implicit waiver:**

Our failure to enforce any provision of these Terms at any time **does not constitute a waiver** of our right to enforce that provision in the future.`,
    },

    {
      id: 'undang-undang',
      title: '21. Governing Law & Disputes',
      content: `**Governing law:**

These Terms are governed by and construed in accordance with the **laws of Malaysia**, without regard to conflict-of-laws principles.

**Exclusive jurisdiction:**

Any dispute, controversy, or claim arising out of or in connection with these Terms, including disputes regarding the existence, validity, or termination thereof, shall be subject to the **exclusive jurisdiction of the Malaysian Courts in Kuala Lumpur**.

**Dispute resolution process — informal resolution first:**

Before initiating formal legal proceedings, both parties agree to:

- **Contact the other party in writing** (email to admin@binaapp.my for BinaApp) with details of the dispute and the proposed resolution;
- **Negotiate in good faith** to reach a resolution within **30 days** of the written notice;
- If no resolution is reached within 30 days, either party may proceed with legal action.

**Malaysian Consumer Claims Tribunal:**

For **small consumer claims (under RM 50,000)**, you may be eligible to file a claim with the **Malaysian Consumer Claims Tribunal (TTPM / Tribunal Tuntutan Pengguna Malaysia)** separately. Further information at [www.kpdn.gov.my](https://www.kpdn.gov.my).

**PDPA complaints:**

For privacy or data protection-related complaints, you may apply to the **Personal Data Protection Department (JPDP) of Malaysia**. See **Privacy Policy section 22** and the Contact Us section (23) for details.

**Exclusion of arbitration:**

These Terms **do not designate arbitration** as a mandatory dispute resolution mechanism. You retain the right to file a claim in the Malaysian Courts with jurisdiction.

**Legal costs:**

Each party shall bear **its own legal costs**, unless ordered by the court or agreed in writing.

**Time limit for claims:**

Please see section 18(e) for the applicable 1-year claim period.`,
    },

    {
      id: 'pindaan-terma',
      title: '22. Amendments to Terms',
      content: `BinaApp reserves the right to **amend these Terms from time to time** to reflect changes in:

- Services, features, or subscription plans;
- Third-party providers or business model;
- Legal and regulatory requirements;
- User feedback and industry best practices.

**Classification of changes:**

**(a) Material changes:**

**Material** changes include (but are not limited to):

- **Subscription price changes** or introduction of new charges;
- **Reduction of features** or significant feature discontinuation;
- **Third-party provider changes** that affect privacy or data location;
- **Modification of liability, indemnification**, or jurisdiction terms;
- **Addition of new or significant user obligations**.

For material changes:

- We will give **at least 30 days notice** before the change takes effect;
- The notice is sent via **email to the address registered to your account** and via a **dashboard banner**;
- You will be given the option to **accept the amended Terms** or **cancel the subscription without penalty** before the effective date.

**(b) Minor changes:**

**Minor** changes include:

- **Grammar, spelling, or text clarifications**;
- **Update of cross-references or URL links**;
- **Clarification of existing terms** without changing material meaning;
- **Addition of details to existing disclosures**.

For minor changes:

- We will update the Terms **without direct notification** to you;
- The changes will be **recorded in the Version History section** with a brief description.

**Continued use = acceptance:**

Continued use of the Services after the amended Terms take effect **constitutes your acceptance** of the new Terms. If you do not agree with the material changes, you must:

- **Stop using the Services** immediately; and
- **Cancel your subscription** within 30 days of the notice.

**Current version:**

The latest version of the Terms will **state the effective date** at the top of the document. See the Version History section for details of changes between versions.`,
    },

    {
      id: 'hubungi-kami',
      title: '23. Contact Us',
      content: `**For general and business inquiries:**

Email: **info@binaapp.my**

**For technical support:**

Email: **support.team@binaapp.my**

Support tier depends on your subscription plan (see section 15).

**For privacy inquiries and PDPA requests:**

Email: **admin@binaapp.my**

Please see **Privacy Policy section 22** for details of the PDPA request format.

**For payment or refund issues:**

Email: **admin@binaapp.my** with the subject \`Billing Inquiry - [Detail]\`.

**Company information:**

**Ezy Work Asia Solution**
SSM Registration No.: **002944700-D**

(A correspondence address will be provided in a future update.)

**To file a complaint with regulatory authorities:**

If you are not satisfied with our response or if you believe we have violated Malaysian law:

**(a) Personal data protection complaints:**

**Personal Data Protection Department (JPDP) of Malaysia**
- Hotline: **1-300-88-2400**
- Website: **www.pdp.gov.my**

**(b) General consumer complaints:**

**Ministry of Domestic Trade and Cost of Living (KPDN)**
- Website: **www.kpdn.gov.my**
- Malaysian Consumer Claims Tribunal (for claims < RM 50,000)

**Support response times:**

- **Privacy/PDPA inquiries:** 21 days (per Privacy Policy section 22);
- **Technical support inquiries:** As per your subscription plan (see section 15).`,
    },

    {
      id: 'bahasa-muktamad',
      title: '24. Prevailing Language',
      content: `These Terms are provided in two languages: **Bahasa Malaysia (BM)** and **English (EN)**.

**The Bahasa Malaysia version of these Terms is the authoritative and prevailing version.**

In the event of any **discrepancy, difference in interpretation, or inconsistency** between the Bahasa Malaysia version and the English translation, **the Bahasa Malaysia version shall prevail and supersede the English version**.

The English version is provided as a **translation for convenience only**, to help users more comfortable with English understand the terms. It **does not constitute a separate legal document**.

Any other translation versions (if launched in the future, for example Chinese or Tamil) are also provided **for convenience only**, and the Bahasa Malaysia version still prevails.

**Consistency with the Privacy Policy:**

This clause is consistent with **Privacy Policy section 23**, which also designates BM as the prevailing version.`,
    },

    {
      id: 'pengakuan',
      title: '25. Acknowledgment & Acceptance',
      content: `By:

- **Clicking the "I agree" button** during registration;
- **Making a subscription payment** for the Starter, Basic, or Pro Plan;
- **Logging in and using** the BinaApp dashboard;
- **Publishing a website** using the platform; or
- **Interacting with the Services** in any way,

**you acknowledge that:**

1. You have **read and understood** these Terms of Service in their entirety, including the disclaimer sections (8, 9, 10, 11) and the limitation of liability (18) and indemnification (19) sections;

2. You have **read and accepted the BinaApp Privacy Policy** (\`/polisi-privasi\`);

3. You are **at least 18 years old** and have **full legal capacity** to form a contract that is enforceable under Malaysian law;

4. You **have authority to form this contract** on behalf of your F&B business (if you represent a business);

5. You **agree to be bound** by these Terms and any subsequent amendments, in accordance with section 22;

6. You **understand BinaApp's business model** (see "Understanding BinaApp's Business Model" callout above) — particularly that BinaApp is not a food delivery platform, not a restaurant chain, not a customer payment processor, and not a rider employer;

7. You **consent to cross-border data transfers** to AI providers in Singapore, the United States, and the People's Republic of China, as described in the Privacy Policy;

8. You **acknowledge your responsibilities as data controller** for customer data and other third-party data that you upload (see Privacy Policy section 18);

9. You **agree to the indemnification clause** in section 19, including your obligation to indemnify BinaApp against third-party claims arising out of your business operations or data you upload;

10. You **understand the limitation of liability** in section 18 and agree to that allocation of risk as fair and reasonable in the context of B2B SaaS in Malaysia.

**If you DO NOT agree to any term:**

- **Stop using the Services** immediately;
- **Do not register** a new account;
- **Cancel any existing subscription**;
- Contact **admin@binaapp.my** to begin the process of deleting your account and related data.

**Permanent acceptance:**

This acceptance remains in force until your account is terminated or the Terms are amended (in accordance with section 22).`,
    },

    {
      id: 'riwayat-perubahan',
      title: '26. Version History',
      content: `Below is the version history of the BinaApp Terms of Service. See the changelog list below for details of changes between versions.

**How to read the changelog:**

Each version update is listed with version number, date, and a summary of material changes. Minor changes such as grammar corrections or text clarifications are not listed individually.

**Current version:** v3.0 (21 May 2026)

**Previous versions can be requested** by contacting admin@binaapp.my if you wish to review earlier versions.`,
    },
  ],

  changelog: [
    {
      version: '3.0',
      date: '21 May 2026',
      changes: [
        'Addition of an "Understanding BinaApp\\\'s Business Model" callout at the start of the document as the foundation for understanding;',
        'Correction of Section 1 — BinaApp clarified as a SaaS platform, NOT a food delivery platform (per audit Conflict #4);',
        'Addition of new definitions in Section 2: Addon, Quota, AI Provider, Static QR, and clarification of Rider status as merchant\\\'s independent contractor;',
        'Restructuring of Section 4 (Subscription Plans & Billing) with 5 sub-sections: available plans (including Free), auto-renewal, payment failure, addons, and quotas;',
        'Free Plan RM 0 formally included with features and quota details (per audit Finding 1);',
        'Addition of addons table (5 types: ai_image, ai_hero, website, rider, zone) with prices, 365-day validity, and 7-day refund policy;',
        'Addition of detailed quota table for all 4 tiers (Free, Starter, Basic, Pro);',
        'Addition of rider addon semantic clarification — additive on top of base plan limits (per audit Task 5b verdict);',
        'Replacement of Section 5 (Refunds) to remove ambiguity and add addon refund policy;',
        'Expansion of Section 6 (Prohibited Activities) following the foodpanda s3.1 model — 5 categories of prohibition (technical, commercial, content, data, financial);',
        'Addition of Section 7 (Merchant-Specific Responsibilities) — menu accuracy, food safety, licensing (SSM/halal/PBT), customer data integrity, rider obligations;',
        'Replacement of the previous "Customer Responsibilities" with "Notice to End-Users" (Section 8) — informational, not binding obligations (per audit Conflict #6);',
        'Reinforcement of Section 9 (Delivery Disclaimer) — rider as merchant\\\'s independent contractor, BinaApp does not provide insurance/EPF/SOCSO (per audit T12);',
        'Addition of Section 10 (Static QR Disclaimer) — BinaApp only displays the image, does not process payment (per audit T13);',
        'Addition of Section 11 (AI Content Disclaimer) — AI content as-is, hallucinations may occur, merchant responsible for review (foodpanda s6.11 model);',
        'Replacement of Section 12 (PDPA) with a single paragraph + link-out to the Privacy Policy (per audit Conflict #2);',
        'Update of Section 13 (Software Tools & Features) to reflect the current platform (/delivery, /rider, /menu-designer, addon system, GPS, chat, AI dispute);',
        'Restructuring of Section 14 (Intellectual Property) with 4 sub-sections, including AI content ownership (14.3) and subdomain revocation (14.4);',
        'Addition of Section 15 with explicit support tiers per plan (Starter 48-72h, Basic 24-48h, Pro 12-24h);',
        'Expansion of Section 17 (Third-Party Services) with a table of 8 providers: ToyyibPay, Supabase, Render, Vercel, Stability, DeepSeek, Qwen/Alibaba Cloud, Anthropic;',
        'Restructuring of Section 18 (Limitation of Liability) following the foodpanda model — (a) cap, (b) explicit exclusions, (c) Malaysian law carve-outs;',
        'Addition of Section 19 (Indemnification) — merchant obligation to indemnify BinaApp against third-party claims (foodpanda s13 model);',
        'Addition of Section 20 (Severability) — foodpanda s17 model;',
        'Reinforcement of Section 21 (Governing Law) — KL Courts jurisdiction, 30-day informal resolution, references to TTPM and KPDN;',
        'Consolidation of Section 22 (Amendments to Terms) — material vs minor change distinction, 30-day notice for material;',
        'Update of Section 23 (Contact Us) with 3 official emails: info@, support.team@, admin@;',
        'Addition of Section 24 (Prevailing Language) — consistent with Privacy Policy s23;',
        'Addition of Section 25 (Acknowledgment & Acceptance) — 10-point acknowledgment;',
        'Removal of references to obsolete AI providers (GLM removed) and obsolete payment processors (FPX placeholder removed).',
      ],
    },
    {
      version: '2.0',
      date: '31 January 2025',
      changes: [
        'Addition of clauses related to generative AI features;',
        'Update of the subscription plan list and prices;',
        'Addition of basic delivery system details;',
        'Update of intellectual property clauses.',
      ],
    },
    {
      version: '1.0',
      date: 'Early 2024',
      changes: ['Initial version of the Terms of Service at the launch of BinaApp.'],
    },
  ],

  contact: {
    company: 'Ezy Work Asia Solution',
    ssm: '002944700-D',
    dpoEmail: 'admin@binaapp.my',
    supportEmail: 'support.team@binaapp.my',
    generalEmail: 'info@binaapp.my',
    pdpDeptPhone: '1-300-88-2400',
    pdpDeptWebsite: 'www.pdp.gov.my',
  },

  prevailingLanguage: {
    title: 'Prevailing Language',
    content: `The Bahasa Malaysia version of these Terms is the authoritative version. In the event of any discrepancy between the Bahasa Malaysia version and the English translation, the Bahasa Malaysia version shall prevail.`,
  },
};
