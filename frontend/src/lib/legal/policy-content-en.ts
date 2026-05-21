/**
 * BinaApp Privacy Policy v3.0 — English (translation for convenience only)
 *
 * The Bahasa Malaysia version (`policy-content-bm.ts`) is the
 * authoritative version. In case of any conflict, BM prevails — see
 * section 23 (`prevailingLanguage`).
 *
 * Effective: 21 May 2026. Supersedes v2.0 (31 January 2025) and v1.0.
 *
 * This file reuses the `PrivacyPolicy` type and all sub-types from the
 * BM source-of-truth file rather than redefining them — keeps schema
 * parity strict. Section IDs are intentionally identical to the BM
 * file (cross-document anchor links work in both languages).
 *
 * Word count: 6665 EN words. Estimated reading time: 29 minutes at
 * 230 wpm (English reading speed average).
 */

import type { PrivacyPolicy } from './policy-content-bm';

export const privacyPolicyEN: PrivacyPolicy = {
  version: '3.0',
  effectiveDate: '21 May 2026',
  lastUpdated: '21 May 2026',
  estimatedReadingMinutes: 29,

  executiveSummary: {
    title: '1-Minute Summary',
    content: `This summary is for quick reference only and **does not** replace the full Policy below. Please read the relevant sections for complete details.

- **Who we are:** BinaApp is an AI website-builder platform for food and beverage (F&B) businesses in Malaysia, owned and operated by **Ezy Work Asia Solution** (SSM No.: 002944700-D).
- **What data we collect:** Your account data (email, business name, phone number), dashboard usage data, customer order data you input, rider GPS location data during active deliveries, and subscription transaction records.
- **For what purpose:** To provide your platform services — generating websites, processing orders, supporting deliveries, issuing subscription invoices, and providing customer support.
- **To whom we disclose:** Infrastructure providers (Supabase, Render), the subscription payment processor (ToyyibPay), and AI providers (Stability AI, DeepSeek, Qwen/Alibaba Cloud, Anthropic Claude). We **do not sell** your data to anyone.
- **What we do NOT process:** We **do not process customer payments for food orders** (COD = cash directly to the rider; static QR = direct bank transfer to the merchant). We also **do not access your WhatsApp messages** — WhatsApp links are deep-links only.
- **Your rights:** You have rights of access, correction, withdrawal of consent, deletion, portability, and restriction of processing under PDPA 2010. Contact admin@binaapp.my.
- **Future commitments:** Within 60 days of the effective date, we will launch (a) per-feature explicit consent UI for AI functions handling customer PII, (b) a cookie banner on generated restaurant websites, and (c) support for the HTTP Do-Not-Track header.`,
  },

  introduction: {
    title: '1. Introduction',
    content: `Welcome to the BinaApp Privacy Policy ("**Policy**"). BinaApp ("**we**", "**us**", "**BinaApp**") is an artificial-intelligence ("**AI**")-powered website-builder platform for food and beverage ("**F&B**") businesses in Malaysia. The platform is owned and operated by **Ezy Work Asia Solution** (SSM No.: 002944700-D), a business registered in Malaysia.

This Policy explains how we collect, use, disclose, retain, and protect your personal data when you:

- Register and use a BinaApp merchant account;
- Use the BinaApp dashboard to manage your F&B business;
- Use the AI features to generate websites, images, or analysis;
- Interact with BinaBot or our support team;
- Browse restaurant websites hosted by BinaApp on behalf of merchants (for example, [businessname].binaapp.my).

We are committed to complying with the **Personal Data Protection Act 2010** ("**PDPA 2010**") of Malaysia and the seven principles enshrined within it:

1. The General Principle;
2. The Notice and Choice Principle;
3. The Disclosure Principle;
4. The Security Principle;
5. The Retention Principle;
6. The Data Integrity Principle;
7. The Access Principle.

This Policy takes effect on **21 May 2026** and supersedes all previous versions, including Version 2.0 (dated 31 January 2025) and Version 1.0 (early 2024). See the Version History section at the end of this Policy for details of changes between versions.

**Please read this Policy carefully.** By registering a BinaApp account, using our services, or browsing websites hosted by BinaApp, you acknowledge that you have read, understood, and agreed to the terms of this Policy. If you do not agree, please stop using our services.`,
  },

  sections: [
    {
      id: 'pendaftaran-akaun',
      title: '2. When You Register a BinaApp Account (Merchant)',
      content: `When you register a BinaApp merchant account, we collect the following information:

**Data collected:**
- Email address
- Password (stored in a hashed form using industry-standard security algorithms — we **cannot** see your original plaintext password)
- Full name
- Business name
- Phone number
- SSM registration number (optional, if entered)
- Business logo (optional, if uploaded)

**Purpose of collection:**
- To identify you as the account owner;
- To enable secure login;
- To communicate with you regarding the account, subscription, and service updates;
- To restore access if you forget your password;
- To issue subscription invoices and receipts.

**Legal basis (PDPA 2010):**
- Your explicit consent given during registration;
- Processing necessary for performance of the service contract with you.

**Where the data is stored:**
- Supabase database (cloud-based PostgreSQL infrastructure provider) in the Southeast Asia (Singapore) region and/or Malaysia region, depending on platform configuration.
- Encrypted backups retained for the same period.

**How long it is retained:**
- For the duration of your active account;
- For 30 days after account termination (for emergency recovery), then permanently deleted.

You can update your account information at any time through the BinaApp dashboard. For full account deletion, see the Your Rights section below.`,
    },

    {
      id: 'penggunaan-dashboard',
      title: '3. When You Use the BinaApp Dashboard',
      content: `When you log in and use the BinaApp dashboard, we collect certain usage data to ensure the platform functions, measure quota usage, and detect technical issues.

**Data collected:**
- IP address (for session authentication and security)
- Browser type and operating system
- Device type (mobile, tablet, desktop)
- Login date and time
- Dashboard pages visited
- Actions performed (e.g., generating a website, updating a menu, uploading a photo)
- Quota usage counters (number of websites generated, AI images, riders added, and so on)

**Purpose of collection:**
- To ensure your session is secure and not compromised;
- To measure usage against your subscription limits;
- To detect and investigate technical errors;
- To improve the overall platform user experience.

**Important disclosure — we do NOT use third-party analytics SDKs:**

BinaApp **does not** use Google Analytics, PostHog, Plausible, Mixpanel, Amplitude, Sentry (for analytics), Hotjar, FullStory, or any other third-party behavioral analytics SDK on our merchant dashboard. All usage telemetry is collected and stored within our Supabase infrastructure only.

**Legal basis:**
- Legitimate interest in secure and functional platform operations;
- Processing necessary for performance of the service contract.

**Retention period:** 90 days for detailed usage logs; aggregated (de-identified) data may be retained longer for internal statistical purposes.`,
    },

    {
      id: 'pesanan-customer',
      title: '4. When the Merchant Receives Orders',
      content: `When a customer places an order on your restaurant website or you record an order manually in the dashboard, BinaApp stores that order data on your behalf. **You, as the merchant, are the data controller for your customer data.** BinaApp acts as a data processor for you.

**Data stored for each order:**
- Customer name
- Customer phone number
- Delivery address (if applicable)
- Items ordered
- Order total
- Special instructions (if any)
- Order notes
- Order status (new, being prepared, in delivery, completed)
- Order date and time

**Purpose of collection:**
- To enable you to manage customer orders;
- To enable riders to contact customers during delivery;
- To maintain your transaction records;
- To enable customers to check the status of their orders.

**"Personal data of other individuals" clause:**

When you enter or upload customer data into the BinaApp platform, **you confirm that you have obtained appropriate consent from those customers** to collect and process their personal data under PDPA 2010. You are fully responsible for:

- Informing customers about the collection of their data;
- Providing your own privacy policy (if applicable, e.g., for chain businesses);
- Ensuring customers have rights of access and correction of their data;
- Handling customer data deletion requests.

BinaApp provides the technical infrastructure for you to manage this data but does not act as the primary data controller for your customer data.

**Where it is stored:** Supabase database (Singapore/Malaysia).

**Retention period:** Up to 7 years from the order date, in accordance with Malaysian accounting record requirements. You may request deletion of specific customer data at any time through the dashboard.`,
    },

    {
      id: 'rider-penghantaran',
      title: '5. When the Rider Performs Deliveries',
      content: `BinaApp provides an optional delivery system that you can enable for your business. When your delivery rider uses this system, the following data is collected:

**Rider data managed by the merchant:**
- Rider name
- Phone number
- Vehicle plate number (if entered)
- Profile photo (optional)

Riders are **registered and managed by you as the merchant** in the BinaApp dashboard. The contractual relationship between you and the rider is outside the scope of BinaApp's services.

**Rider status — important disclosure:**

The riders you register are **independent contractors engaged by you as the merchant**, and **not** employees, agents, or representatives of BinaApp. BinaApp provides software tools for you to manage delivery operations only; all employment responsibilities, insurance, wages, and legal obligations relating to riders are your responsibility as the merchant.

**Rider GPS data:**
- Location coordinates (latitude and longitude) are collected **only during active deliveries** (from when the rider accepts an assignment until the delivery is marked complete);
- Location data is updated every few seconds to allow customers and merchants to track delivery status;
- GPS tracking is **stopped** as soon as the delivery is completed or cancelled.

**Delivery photo verifier:**
- When the rider uploads a photo as proof of completed delivery, the photo is sent to the Qwen AI model (in Singapore, via Alibaba Cloud International) for automated verification (e.g., detecting the package or front door);
- ⚠️ **PII risk:** Photos may contain customer faces, vehicle license plates, or other identifying elements. See the AI section below for further details.

**Purpose of collection:**
- To enable real-time delivery coordination;
- To enable customers to track their orders;
- To provide proof of delivery to the merchant.

**Retention period:**
- GPS data: 30 days after delivery completion;
- Delivery proof photos: 30 days after delivery completion.`,
    },

    {
      id: 'ai-features',
      title: "6. When You Interact with BinaApp's AI Features",
      content: `BinaApp uses several third-party AI providers to deliver features such as website generation, image generation, complaint analysis, automated replies, and photo verification. When you use these features, the related data is sent to those AI providers for processing.

The table below lists each AI feature, the provider used, the processing region, the type of data sent, the PII risk (Personal Identifiable Information / personal data), and the current consent status.

**Note on consent status:** Several AI features that handle customer PII currently operate on a notice-only basis (you are informed via this Policy that data is sent to the AI). Within 60 days of the effective date of this Policy (see the 60-Day Commitments section), we will launch a per-feature explicit consent UI for these functions.

**Note on Anthropic Claude (support email analysis):** Before the email content is sent to Anthropic, the sender's email address is hashed (one-way hashed) so that the original email address cannot be recovered. In addition, under standard commercial contracts, **Anthropic does not use customer data to train the Claude models**.

**Note on AI providers outside Malaysia:** Use of these AI features involves cross-border data transfers to the United States, the People's Republic of China, and Singapore. See the Cross-Border Data Transfers section for details of the safeguards applied.

If you are uncomfortable with AI processing for any particular feature, you may:
- Avoid using that feature (for example, not using AI complaint analysis and handling complaints manually);
- Contact us at admin@binaapp.my to discuss alternative options.`,
      aiVendorTable: [
        {
          feature: 'Website Generation',
          vendor: 'DeepSeek',
          region: "People's Republic of China",
          dataSent: 'Business description, name, location, cuisine type that you enter',
          piiRisk: 'warning',
          piiNote: 'Risky if you include customer PII in the description',
          consentStatus: 'Implicit consent when initiating generation',
        },
        {
          feature: 'Menu / Hero Image Generation',
          vendor: 'Stability AI',
          region: 'United States',
          dataSent: 'Visual text prompt only (e.g., "nasi lemak with sambal")',
          piiRisk: 'safe',
          piiNote: 'No PII sent — only visual description',
          consentStatus: 'Implicit consent when requesting an image',
        },
        {
          feature: 'Complaint / Dispute Analysis',
          vendor: 'DeepSeek',
          region: "People's Republic of China",
          dataSent: 'Customer complaint text, related order history, transaction details',
          piiRisk: 'warning',
          piiNote: 'May contain customer PII (name, phone number within complaint text)',
          consentStatus: 'Notice only — explicit consent UI to launch within 60 days',
        },
        {
          feature: 'AI Replies in Chat',
          vendor: 'DeepSeek',
          region: "People's Republic of China",
          dataSent: 'Customer-merchant conversation context, latest customer message',
          piiRisk: 'warning',
          piiNote: 'Contains customer PII within conversation context',
          consentStatus: 'Notice only — explicit consent UI to launch within 60 days',
        },
        {
          feature: 'BinaBot (Merchant Support Chatbot)',
          vendor: 'DeepSeek',
          region: "People's Republic of China",
          dataSent: 'Your questions and merchant account context',
          piiRisk: 'warning',
          piiNote: 'May contain PII if you include customer details in questions',
          consentStatus: 'Implicit consent when interacting with BinaBot',
        },
        {
          feature: 'Delivery Photo Verification',
          vendor: 'Qwen (Alibaba Cloud International)',
          region: 'Singapore',
          dataSent: 'Delivery proof photo uploaded by the rider',
          piiRisk: 'warning',
          piiNote: 'May contain customer faces, license plates, or other identifying elements',
          consentStatus: 'Notice only — explicit consent UI to launch within 60 days',
        },
        {
          feature: 'Support Email Analysis',
          vendor: 'Anthropic Claude',
          region: 'United States',
          dataSent: 'Email text content; sender email address is hashed (sanitized) before sending',
          piiRisk: 'safe',
          piiNote: 'Email address is hashed; Anthropic does not train models on customer data per standard commercial contract',
          consentStatus: 'Notice (used for internal support operations)',
        },
        {
          feature: 'Merchant Chatbot (served to customers on the website)',
          vendor: 'DeepSeek',
          region: "People's Republic of China",
          dataSent: 'Customer questions to the merchant, merchant account context',
          piiRisk: 'warning',
          piiNote: 'May contain customer PII in their questions',
          consentStatus: 'Notice only — explicit consent UI to launch within 60 days',
        },
      ],
    },

    {
      id: 'sokongan',
      title: '7. When You Contact Our Support',
      content: `When you contact the BinaApp support team or interact with BinaBot, we collect and process that communication data to help resolve your inquiry.

**Support channels and data collected:**

**(a) BinaBot (in-dashboard chatbot):**
- Your messages, merchant account context, and conversation history;
- Sent to DeepSeek (in the People's Republic of China) to generate AI replies;
- See the table in section 6 for details of PII risk and consent status.

**(b) Support email (support.team@binaapp.my, admin@binaapp.my):**
- Email content, sender's email address, and any attachments;
- Email content is analyzed using Anthropic Claude to accelerate classification and response;
- **Before being sent to Claude, the sender's email address is hashed**, so the original address cannot be recovered from the data sent.

**(c) Live chat (if available):**
- Conversation content and interaction times.

**Purpose of collection:**
- To resolve your inquiry or complaint;
- To improve support quality;
- To train internal support staff (de-identified data).

**Retention period:**
- BinaBot conversation history: 90 days;
- Support email: up to 2 years for audit trail and reference purposes;
- Live chat logs: 90 days.

**Important disclosure:** Anthropic maintains standard commercial contracts with enterprise customers that **prohibit the use of customer input data to train the Claude models**. This means the email content you send that is processed by Claude **is not used to train their AI models**.`,
    },

    {
      id: 'pembayaran-langganan',
      title: '8. When You Make Subscription Payments',
      content: `BinaApp charges monthly subscription fees for access to the platform (for example, Starter plan RM 5/month, Basic RM 29/month, Pro RM 49/month, or equivalent). These subscription payments are processed via **ToyyibPay**, a payment processor approved by Bank Negara Malaysia.

**Data processed for subscription payments:**
- Your name and email address (sent to ToyyibPay for receipt issuance);
- Transaction amount and subscription details;
- Transaction ID returned by ToyyibPay.

**What BinaApp does NOT store:**
- Your **credit / debit card number**;
- **CVV / CVC number**;
- **Card expiry date**;
- **Bank account information** used for the transfer.

All sensitive payment details are handled and stored by ToyyibPay (a PCI-DSS-compliant payment processor) and are never stored in BinaApp systems.

**What BinaApp stores:**
- Transaction ID (for reference);
- Payment date;
- Amount paid;
- Subscription status (active, expired, cancelled);
- Electronic receipt (PDF/HTML).

**Purpose of collection:**
- To activate and maintain your subscription;
- To issue receipts and invoices;
- To comply with Malaysian accounting and tax record requirements.

**Retention period:** 7 years (per Malaysian accounting and tax record law).

**Legal basis:** Processing necessary for performance of the subscription contract with you; compliance with legal obligations (tax records).`,
    },

    {
      id: 'non-processing-makanan',
      title: '9. Important Disclosure — BinaApp Does NOT Process Customer Food Order Payments',
      content: `**This is an important disclosure that we want to make explicit:**

BinaApp processes **merchant subscription payments** only (see section 8). BinaApp **does not process, receive, or store** any customer payment details for food orders placed through your restaurant website.

**How customers pay for food orders:**

**(a) COD (Cash on Delivery):**
- The customer pays **cash directly to the rider** when the order arrives;
- No money flows through BinaApp systems;
- BinaApp does not store records of these cash payment details (only the order status: paid / unpaid).

**(b) Static QR Transfer:**
- The merchant uploads an image of their own payment QR code (e.g., DuitNow QR or bank QR) to the dashboard;
- The customer scans this QR and transfers **directly to the merchant's bank account**;
- The money does not flow through BinaApp systems at any point;
- BinaApp has no access to the merchant's bank account or records of those transfers;
- The merchant is responsible for verifying payment (for example, by checking the customer's bank receipt or transfer notification).

**What BinaApp stores for food orders:**
- Order status (new, paid, in delivery, completed);
- Order amount;
- Payment method chosen by the customer (COD or QR);
- Not the actual payment details.

**Important implications:**
- Any payment disputes between customer and merchant (e.g., customer not paying, or transferring to the wrong account) are **between the customer and the merchant**, not BinaApp;
- BinaApp cannot initiate refunds for food orders because we never held that money;
- For food order refunds, the customer must discuss directly with the merchant.`,
    },

    {
      id: 'whatsapp-deeplink',
      title: '10. Important Disclosure — WhatsApp Links Are Deep-Links Only',
      content: `Restaurant websites generated by BinaApp may contain "Contact via WhatsApp" buttons or links that allow customers to contact the merchant via WhatsApp.

**How it works:**

The button is a **deep-link** to the WhatsApp application (for example, \`https://wa.me/60123456789\`). When a customer clicks this button:

1. The WhatsApp app opens on the customer's device (if installed);
2. A new conversation with the merchant's phone number opens;
3. The customer can type and send a message.

**What BinaApp does NOT do:**
- BinaApp **does not access, store, or read** your WhatsApp messages;
- BinaApp **does not integrate with the WhatsApp Business API** or any other WhatsApp messaging API;
- BinaApp **does not receive notifications** when messages are sent or read;
- BinaApp **does not store conversation content** between customers and merchants on WhatsApp.

The deep-link is simply a way to make it easy for customers to contact the merchant. Once the conversation moves to WhatsApp, it is a private communication between the customer and the merchant, governed by the WhatsApp privacy policy (Meta Platforms, Inc.), not by BinaApp.

**What BinaApp stores:**
- Your (merchant's) WhatsApp phone number that you enter in the website settings — this is needed to generate the deep-link.

**Non-Malaysian users using the website:** If a customer outside Malaysia clicks the WhatsApp button, the resulting communication transfer is governed by WhatsApp's privacy policy and does not involve BinaApp.`,
    },

    {
      id: 'visitor-tracker',
      title: '11. When Visitors Browse Your Restaurant Website',
      content: `When a visitor browses a restaurant website hosted by BinaApp (for example, \`businessname.binaapp.my\`), we collect first-party analytics data to provide an analytics dashboard to you as the merchant.

**Data collected:**
- Visitor IP address (truncated for privacy);
- Browser User-Agent string;
- Device type (mobile, tablet, desktop);
- Browser family and operating system;
- Referrer URL — the website the visitor came from;
- Page path visited (\`/menu\`, \`/about\`, etc.);
- Visit date and time;
- Anonymous visitor ID generated locally (hash of IP + User-Agent, or \`bina_visitor\` localStorage ID).

**Purpose of collection:**
- To provide website traffic statistics to the merchant;
- To measure the popularity of specific pages;
- To understand visitor device and browser patterns;
- To help the merchant improve website content and design.

**What is NOT collected:**
- Visitor name, email, or phone number (unless the visitor chooses to enter them via an order form);
- Precise GPS location;
- Browsing activity on other websites;
- Advertising or marketing profile data.

**Where the data is stored:**
- Supabase database (Singapore/Malaysia), within the BinaApp account for the relevant merchant;
- Analytics data is displayed to the merchant via their dashboard only;
- The data is **not sold, shared, or transferred** to advertisers or any other third party.

**Important disclosure — visitors are not given direct notice today:**

Currently, the generated restaurant websites **do not display a cookie banner or tracking notice** to visitors. Visitors may not be aware that data about their visits is being collected. We are **committed to launching a visitor notice banner and HTTP Do-Not-Track support within 60 days** of the effective date of this Policy (see the 60-Day Commitments section).

**Merchant opt-out option:**

As a merchant, you may **disable visitor analytics tracking** for your website at any time through the dashboard settings ("Edit Website" → "Enable visitor analytics" toggle). When disabled:

- The tracking script is removed from the website's HTML code on the next publish;
- Existing analytics requests from previously published websites are rejected by our servers;
- No new visit data will be recorded for your website.

**Retention period:** For the duration of the active merchant account (the data is the merchant's business analytics asset). When the account terminates, the data is deleted in accordance with the account retention policy.`,
    },

    {
      id: 'notis-pengguna-akhir',
      title: '12. Notice to End-Users (Website Visitors)',
      content: `**This section is addressed to you if you are a visitor (customer) browsing a website like \`[businessname].binaapp.my\` — not a merchant who owns a BinaApp account.**

**Hosting explanation:**

The website you are visiting is a website **hosted by BinaApp on behalf of the merchant** (the F&B business you are transacting with). Although the website ends in \`.binaapp.my\`, it is the merchant's business website, not BinaApp's.

**Contractual relationship:**

When you place an order through this website:

- **The sale contract is between you and the merchant**, not BinaApp;
- BinaApp provides the technical platform to enable the merchant to run their operations, but BinaApp **is not a party to the sale transaction** between you and the merchant;
- Any issues regarding food quality, delivery time, refunds, or service complaints must be referred **directly to the merchant**.

**Your personal data:**

When you place an order or contact the merchant through this website, your personal data (name, phone number, address, order details) is collected by BinaApp **on behalf of the merchant**. The merchant is the primary data controller for your data. BinaApp acts as the data processor for the merchant.

**Your rights:**

- To access, correct, or delete personal data held by the merchant, please contact the merchant directly;
- If the merchant does not respond, you may contact BinaApp at admin@binaapp.my and we will facilitate the request to the merchant;
- You also have the right to file a complaint with the Personal Data Protection Department of Malaysia (see the Contact Us / Complaints section).

**Merchant privacy policy:**

The merchant may have their own privacy policy governing the collection and use of your data. If the merchant does not provide one, this Policy applies as the baseline privacy policy for platform operations.

**Visit analytics:**

Your visit to this website is tracked for the merchant's business analytics purposes. See section 11 for details of the data collected. There is currently no direct notice banner displayed; we will launch a notice banner and Do-Not-Track support within 60 days.`,
    },

    {
      id: 'cookies',
      title: '13. Cookies and Tracking Technology',
      content: `BinaApp uses cookies and limited local storage (localStorage) technology for the platform to function. We classify these technologies into three categories:

**(a) Strictly Necessary Cookies:**

These cookies are required for basic platform operation and cannot be disabled without affecting platform functionality.

- **Supabase Auth session cookies:** Maintain your merchant login session. Expire when you log out or after a configured period of inactivity;
- **CSRF security cookies:** Protect against cross-site request forgery attacks.

**(b) Preference Cookies:**

These cookies store your preferences for a better experience.

- **Theme preference:** Light / dark mode;
- **Language preference:** BM / EN;
- **Dashboard display preferences:** Card layout, table ordering.

**(c) First-Party Analytics Local Storage:**

- **\`bina_visitor\` (localStorage):** An anonymous visitor ID generated locally on the device of a restaurant website visitor. Used to distinguish returning visitors from new visitors in the merchant's analytics. Can be cleared at any time by clearing the browser cache.

**Important disclosure — NO third-party analytics SDKs:**

We **do not use** any third-party behavioral analytics service, including but not limited to:

- Google Analytics
- Google Tag Manager
- Facebook Pixel
- PostHog
- Plausible
- Mixpanel
- Amplitude
- Hotjar
- FullStory
- Microsoft Clarity
- Sentry (for user analytics)

All telemetry data is collected and stored solely within our Supabase infrastructure as first-party data.

**Managing cookies:**

You may manage or delete cookies through your browser settings. Please note that disabling essential cookies will affect your ability to log in and use the platform.

For restaurant website visitors: a cookie management banner is currently not shown. We will launch a banner with cookie choices within 60 days (see the 60-Day Commitments section).`,
    },

    {
      id: 'tempoh-penyimpanan',
      title: '14. Data Retention Periods',
      content: `We retain your personal data only for as long as necessary for the original purpose of collection, or as required by Malaysian law (for example, the 7-year accounting record requirement).

The table below summarizes the retention periods for various data types:

(See the data retention table below.)

**After the retention period:**
- Data is permanently deleted from active databases;
- Encrypted backups containing the data remain for the backup cycle period (30 days) before being overwritten;
- Deleted data cannot be recovered after the backup period ends.

**Exceptions:**
- Data related to ongoing legal disputes, investigations, or audits may be retained longer as required by law;
- Aggregated and de-identified data (for example, overall platform usage statistics) may be retained indefinitely for internal analytical purposes.`,
      retentionTable: [
        {
          dataType: 'Merchant account (active)',
          period: 'For the duration of active subscription + 30 days after termination',
        },
        {
          dataType: 'Customer order records',
          period: '7 years (Malaysian accounting record requirements)',
        },
        {
          dataType: 'Merchant-customer chat messages',
          period: '90 days',
        },
        {
          dataType: 'Rider GPS data',
          period: '30 days after delivery completion',
        },
        {
          dataType: 'Subscription payment transaction records',
          period: '7 years (Malaysian tax record requirements)',
        },
        {
          dataType: 'Backup of deleted data',
          period: '30 days after account deletion',
        },
        {
          dataType: 'AI request logs (input and output)',
          period: '90 days',
        },
        {
          dataType: 'Delivery verification photos',
          period: '30 days after delivery completion',
        },
        {
          dataType: 'Merchant payment QR images',
          period: 'For the duration of the active account',
        },
        {
          dataType: 'Quota usage records',
          period: '90 days',
        },
        {
          dataType: 'Addon purchase records',
          period: '7 years',
        },
        {
          dataType: 'Visitor localStorage ID (`bina_visitor`)',
          period: 'Until the visitor clears their browser cache',
        },
      ],
    },

    {
      id: 'hak-pdpa',
      title: '15. Your Rights Under PDPA 2010',
      content: `Under the Personal Data Protection Act 2010 (PDPA 2010), you have the following rights regarding your personal data held by BinaApp:

**(a) Right of Access**

You have the right to request a copy of your personal data that we hold, and to be informed of the purposes of processing and the classes of third parties who may receive the data.

**(b) Right of Correction**

If your personal data that we hold is inaccurate, incomplete, or out of date, you have the right to request correction or update.

**(c) Right to Withdraw Consent**

You may withdraw your consent to the processing of your personal data at any time. Please note that withdrawal of consent may affect our ability to provide services to you.

**(d) Right to Deletion**

You may request that your personal data be deleted, subject to legal retention requirements (for example, tax records must be retained for 7 years).

**(e) Right to Data Portability**

You may request to receive your personal data in a structured, commonly used, machine-readable format (for example, JSON or CSV), and to transfer it to another data controller.

**(f) Right to Restrict Processing**

You may request that processing of your personal data be restricted in certain circumstances — for example, while we investigate complaints about the accuracy of your data.

**How to make a request:**

Send an email to **admin@binaapp.my** in the following format:

- **Subject:** \`PDPA Request - [Request Type]\` (e.g.: \`PDPA Request - Access\`, \`PDPA Request - Deletion\`)
- **Include:** Your full name, the email address registered to the account, and specific details of your request.

**Response period:**

We will respond to your request within **21 days** of receipt of the complete request (in accordance with Section 7 of PDPA 2010). If the request is complex or requires additional verification, we may need additional time and will inform you.

**Identity verification:**

To protect your data, we may request additional identity verification before processing the request (for example, confirming a recent order ID or other account details).

**Fees:**

The first access request within a 12-month period is **free**. Subsequent requests within the same period may incur a reasonable processing fee, as permitted by PDPA 2010.

**Complaints:**

If you are not satisfied with our response, you may file a complaint with the Personal Data Protection Department of Malaysia (see the Contact Us / Complaints section).`,
    },

    {
      id: 'pemindahan-merentas-sempadan',
      title: '16. Cross-Border Data Transfers',
      content: `Some of your personal data may be transferred outside Malaysia for processing by our infrastructure and AI providers. These transfers are carried out in accordance with **Section 129 of PDPA 2010** and the relevant Notices from the Personal Data Protection (PDP) Commissioner.

**Processing regions and providers:**

**(a) Malaysia:**
- BinaApp's primary infrastructure;
- Certain data backups;
- Subscription payment processing by ToyyibPay.

**(b) Singapore:**
- Supabase (database and storage) — Southeast Asia region;
- Render (backend application server) — Southeast Asia region;
- Qwen (Alibaba Cloud International) — AI delivery photo verification.

**(c) United States:**
- Stability AI — AI image generation;
- Anthropic Claude — support email analysis;
- Vercel / Render (if used for global frontend hosting).

**(d) People's Republic of China:**
- DeepSeek — AI website generation, complaint analysis, AI chat replies, BinaBot.

**Safeguards applied:**

For each cross-border transfer, we ensure that at least one of the following applies:

- **Your consent:** You provide explicit consent for the transfer (e.g., when using certain AI features);
- **Performance of contract:** The transfer is necessary for performance of the service contract with you;
- **Standard Contractual Clauses:** Our providers are bound by contracts containing data protection provisions equivalent to PDPA 2010;
- **Vendor compliance:** Our providers maintain relevant industry compliance certifications or attestations (for example, ISO 27001, SOC 2, GDPR).

**Risks of cross-border transfers:**

You should be aware that data protection laws in the recipient region may differ from PDPA 2010. For example:

- Data processed in the United States is subject to US law, including potential access by US enforcement agencies;
- Data processed in the People's Republic of China is subject to Chinese cyber laws, including the Cybersecurity Law and the Personal Information Protection Law (PIPL).

By using the BinaApp AI features that involve these third-party providers, you acknowledge and consent to these cross-border transfers.

**Right to object:**

If you have specific concerns about cross-border transfers, please contact us at admin@binaapp.my. We will endeavour to provide alternatives where possible (for example, avoiding the use of certain AI features).`,
    },

    {
      id: 'kanak-kanak',
      title: '17. Children',
      content: `**BinaApp users (merchants) must be at least 18 years old.**

The BinaApp platform is a business-to-business (B2B) service aimed at legally established F&B business owners. We **do not** accept registrations from individuals under 18 as merchants.

If we discover that a merchant account has been registered by an individual under 18, we will terminate that account and delete all data associated with it.

**Data of customers under 18:**

As a merchant, if you upload or record data of customers who are under 18 (for example, young customers placing orders), **you are responsible for obtaining the consent of a parent or legal guardian** before collecting or processing such data, as required by PDPA 2010 and relevant Malaysian child protection laws.

BinaApp provides the technical infrastructure but cannot determine the age of your customers. The responsibility for compliance with the child consent requirement lies with you as the data controller.

**Visitors under 18 on restaurant websites:**

Visitors under 18 may browse restaurant websites generated by BinaApp. We do not collect direct identifying data about visitors through first-party analytics (see section 11). However, if a visitor under 18 chooses to enter their personal data (for example, through an order form), that data is held by the merchant and subject to the merchant's responsibility for compliance with the child consent requirement.

If you become aware that your child has provided personal data through a website hosted by BinaApp, please contact the merchant directly to request deletion, or contact us at admin@binaapp.my and we will facilitate the request.`,
    },

    {
      id: 'data-pihak-ketiga',
      title: '18. Third-Party Data Uploaded by Merchants',
      content: `As a merchant, you may upload or enter personal data about other individuals into the BinaApp platform in various contexts, including:

- **Customer data:** Customer names, phone numbers, addresses that you record for orders;
- **Rider data:** Names, phone numbers, vehicle details of riders you register;
- **Staff data:** If you add additional users (branches, staff) to your merchant account.

**Your acknowledgment as data controller:**

When you enter personal data of other individuals into BinaApp, **you confirm and warrant that:**

1. You have a lawful basis (e.g., consent, contract, or legal obligation) to process that personal data;
2. You have informed the affected individuals about the collection of their data, the purposes of processing, and the classes of third parties that may receive the data (including BinaApp as data processor and the AI providers listed in section 6);
3. You have provided your own privacy policy (if applicable) to those individuals;
4. You will respond to access, correction, or deletion requests from those individuals in a timely manner.

**BinaApp's role:**

BinaApp acts as the **data processor** for the personal data you upload. We:

- Store and process the data on your behalf in accordance with your instructions;
- Do not use that data for our own purposes (except for required platform operations, such as quota and usage analytics);
- Will facilitate PDPA requests from those individuals, but the final decision on requests is your responsibility as data controller.

**Indemnity:**

You agree to indemnify and hold BinaApp harmless from any claims, fines, or losses arising from breach of your obligations under PDPA 2010 or other data protection laws relating to third-party data that you upload. Further details on indemnity are in the Terms of Service.

**Deletion after account termination:**

Upon termination of your merchant account, we will delete all customer data and other third-party data that you uploaded in accordance with our retention policy (see section 14), subject to legal retention requirements for certain records.`,
    },

    {
      id: 'algorithmic-decision',
      title: '19. Algorithmic Decision-Making (AI)',
      content: `BinaApp uses AI to assist in certain decision-making, particularly in customer complaint and dispute workflows. This section describes your rights regarding decisions made by our AI systems.

**What AI decisions affect you:**

**(a) Complaint analysis and recommendation:**
- When a customer submits a complaint through the chat system or complaint form, AI (DeepSeek) analyzes the complaint and recommends an action: full refund, partial refund, or reject;
- This recommendation is displayed to you as the merchant for review and approval;
- **You as the merchant make the final decision** on whether to accept the AI's recommendation or make a manual decision.

**(b) Support email classification:**
- Incoming support emails are classified by AI (Anthropic Claude) for routing to the appropriate team;
- No automated decisions directly affect you — only administrative routing.

**(c) Delivery photo verification:**
- AI (Qwen) analyzes delivery proof photos to verify certain elements (e.g., visible package, front door);
- Verification failure does not prevent a delivery being marked complete — it only flags it for merchant review.

**Your right to manual review:**

You have the right to request a manual human review of any decision influenced by our AI systems. To request manual review:

- Send an email to **admin@binaapp.my** with the subject \`AI Decision Review - [Brief Detail]\`;
- Include specific details of the decision you want reviewed and the reasons for your request.

**Response time:**

We will respond to review requests within a **reasonable period** based on the complexity of the case. We do not promise a specific SLA for manual review.

**Transparent about AI limitations:**

Please be aware that AI systems are not perfect and can make mistakes. We encourage you to:
- Always review AI recommendations before accepting them;
- Flag AI errors to us so we can improve the system;
- Use your own professional judgment as a business owner.`,
    },

    {
      id: 'komitmen-60-hari',
      title: '20. 60-Day Commitments',
      content: `We are committed to continuously improving our privacy practices. Within **60 days** of the effective date of this Policy (i.e., on or before **20 July 2026**), we will launch the following changes:

**(a) Explicit Consent UI for AI Features Handling PII**

Several AI features currently operate on a notice-only basis (you are informed via this Policy that data is sent to AI providers). We will launch a per-feature explicit consent dialog for:

- Complaint / dispute analysis (DeepSeek);
- AI replies in customer-merchant chat (DeepSeek);
- Delivery photo verification (Qwen);
- Merchant chatbot served to customers (DeepSeek).

You will be asked to provide explicit consent once per feature, with the option to withdraw consent at any time through dashboard settings.

**(b) Cookie Notice Banner on Generated Restaurant Websites**

Visitors of restaurant websites hosted by BinaApp will be given a clear notice of first-party analytics tracking (\`bina_visitor\`), with the option to accept or reject tracking.

**(c) Support for the HTTP Do-Not-Track (DNT) Header**

Our analytics server will honour the \`DNT: 1\` HTTP header sent by visitor browsers. When this header is present, analytics requests will be rejected without recording.

**Status updates:**

The implementation status of these commitments will be updated in the Version History section as each is launched. If we encounter delays, we will update this Policy to clarify the new status.

**Why we are making this a formal commitment:**

We believe user privacy is a long-term priority. Rather than launching these features without time clarity, we are publicly committing to a deadline so that you can hold us accountable. If you do not see these features launch within the promised period, please contact us at admin@binaapp.my.`,
    },

    {
      id: 'perubahan-polisi',
      title: '21. Changes to This Policy',
      content: `BinaApp reserves the right to update this Policy from time to time to reflect changes in:

- Our data collection practices;
- New features or third-party providers;
- Legal and regulatory requirements;
- User feedback and industry best practices.

**Notification of changes:**

When we make **material** changes to the Policy (for example, changes in AI providers, collection of new data types, or changes in retention periods), we will notify you through:

- Email to the email address registered to your account; and/or
- A notice in the BinaApp dashboard; and/or
- An in-app notification on the next login.

For minor changes (for example, grammar corrections, clarification of text), we will update the Policy without direct notification but will record the change in the Version History section.

**Effective date:**

The latest version of the Policy will state the effective date at the top of the document. Any changes will take effect on that date, unless stated otherwise.

**Continued consent:**

Continued use of the BinaApp service after a change to this Policy takes effect constitutes your consent to the new terms. If you do not agree with the changes, please stop using our service and contact us to begin the account deletion process.

**Version history:**

See the Version History section at the end of this Policy for details of changes between versions.`,
    },

    {
      id: 'hubungi-kami',
      title: '22. Contact Us / Complaints',
      content: `**For privacy inquiries or PDPA requests:**

**BinaApp Data Protection Officer (DPO)**
Email: **admin@binaapp.my**

Please use this email for:
- Requests for access, correction, deletion, portability, or restriction of processing;
- Withdrawal of consent;
- Inquiries about our privacy practices;
- Complaints about the handling of your data.

**For general technical support:**

Email: **support.team@binaapp.my**

**Company information:**

Ezy Work Asia Solution
SSM No.: 002944700-D
(A correspondence address will be provided in a future update.)

**To file a complaint with regulatory authorities:**

If you are not satisfied with our response to your privacy complaint, or if you believe we have violated PDPA 2010, you have the right to file a complaint with:

**Personal Data Protection Department (JPDP) of Malaysia**
- Complaints Hotline: **1-300-88-2400**
- Website: **www.pdp.gov.my**
- The official channel for PDPA complaints in Malaysia.

**Response time:**

We are committed to responding to all privacy inquiries within **21 days** of receipt, in accordance with Section 7 of PDPA 2010. For more complex requests, we will inform you if additional time is needed.`,
    },

    {
      id: 'bahasa-muktamad',
      title: '23. Prevailing Language',
      content: `This Policy is provided in two languages: **Bahasa Malaysia (BM)** and **English (EN)**.

**The Bahasa Malaysia version of this Policy is the authoritative and prevailing version.**

In the event of any discrepancy, difference in interpretation, or inconsistency between the Bahasa Malaysia version and the English translation, **the Bahasa Malaysia version shall prevail and supersede the English version**.

The English version is provided as a translation for convenience only, to help users more comfortable with English understand the terms. It does not constitute a separate legal document.

Any other translation versions (if launched in the future, for example Chinese or Tamil) are also provided for convenience only, and the Bahasa Malaysia version still prevails.`,
    },

    {
      id: 'persetujuan',
      title: '24. Consent',
      content: `By:

- Registering a BinaApp merchant account;
- Logging in and using the BinaApp dashboard;
- Using our AI features;
- Browsing a website hosted by BinaApp; or
- Interacting with our platform in any way,

**you acknowledge that:**

1. You have read and understood this Privacy Policy in its entirety;
2. You consent to the collection, use, disclosure, retention, and transfer of your personal data as described in this Policy;
3. You consent to the cross-border transfer of data to our AI and infrastructure providers in Singapore, the United States, and the People's Republic of China;
4. You acknowledge your rights under PDPA 2010 and know how to exercise those rights;
5. If you are a merchant, you confirm your responsibilities as data controller for customer data and other third-party data that you upload.

If you **do not agree** with any term in this Policy, you must:

- Stop using BinaApp services immediately;
- Contact us at admin@binaapp.my to begin the process of deleting your account and related data.`,
    },

    {
      id: 'riwayat-perubahan',
      title: '25. Version History',
      content: `Below is the version history of the BinaApp Privacy Policy. See the changelog list below for details of changes between versions.

**How to read the changelog:**

Each version update is listed with version number, date, and a summary of material changes. Minor changes such as grammar fixes or text clarifications are not listed individually.

**Current version:** v3.0 (21 May 2026)

**Previous versions can be requested** by contacting admin@binaapp.my if you wish to review earlier versions.`,
    },
  ],

  changelog: [
    {
      version: '3.0',
      date: '21 May 2026',
      changes: [
        'Complete restructuring following the purpose-based model, inspired by foodpanda Malaysia;',
        'Addition of a 1-minute executive summary at the start;',
        'Addition of a detailed AI provider table (8 features × vendor, region, data, PII risk, consent status);',
        'Explicit disclosure that BinaApp does NOT process customer food order payments (Section 9);',
        'Explicit disclosure that WhatsApp links are deep-links only (Section 10);',
        'New section on restaurant website visitor tracking (Section 11) and per-website opt-out toggle for merchants;',
        'New "Notice to End-Users" section for website visitors (Section 12);',
        'Explicit disclosure that BinaApp does not use third-party analytics SDKs (no Google Analytics, PostHog, etc.);',
        'Comprehensive data retention period table (Section 14, 12 rows);',
        "Restructuring of PDPA rights following foodpanda's model (6 specific rights, Section 15);",
        'Detailed disclosure of cross-border transfers with each provider and region (Section 16);',
        'Clarification of merchant responsibility for customer data under 18 (Section 17);',
        'New clause on third-party data uploaded by merchants (Section 18);',
        'AI algorithmic decision-making disclosure with manual review rights (Section 19);',
        'Formal 60-day commitment for AI consent UI, cookie banner, and DNT support (Section 20);',
        'Addition of a prevailing language clause establishing BM as the prevailing version (Section 23);',
        'Addition of Ezy Work Asia Solution details with SSM No. 002944700-D;',
        'Updated DPO email to admin@binaapp.my;',
        'Removal of references to obsolete AI providers (GLM removed from platform);',
        'Removal of references to obsolete payment processors (FPX placeholder removed from platform).',
      ],
    },
    {
      version: '2.0',
      date: '31 January 2025',
      changes: [
        'Addition of disclosure on the use of generative AI;',
        'Addition of delivery system details;',
        'Update of the payment processor list;',
        'Update of contact details.',
      ],
    },
    {
      version: '1.0',
      date: 'Early 2024',
      changes: ['Initial version of the Privacy Policy at the launch of BinaApp.'],
    },
  ],

  contact: {
    company: 'Ezy Work Asia Solution',
    ssm: '002944700-D',
    dpoEmail: 'admin@binaapp.my',
    supportEmail: 'support.team@binaapp.my',
    pdpDeptPhone: '1-300-88-2400',
    pdpDeptWebsite: 'www.pdp.gov.my',
  },

  prevailingLanguage: {
    title: 'Prevailing Language',
    content: `The Bahasa Malaysia version of this Policy is the authoritative version. In the event of any discrepancy between the Bahasa Malaysia version and the English translation, the Bahasa Malaysia version shall prevail.`,
  },
};
