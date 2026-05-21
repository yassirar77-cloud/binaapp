# Step 2b/2c/2d — Polisi & Terma Rewrite Proposal

**Branch:** `feature/update-polisi-terma-2026`
**Tarikh:** 21 Mei 2026
**Status:** Proposal — menunggu approval sebelum Step 3 (actual rewrite)
**Skop:** Rewrite penuh `frontend/src/app/privacy-policy/page.tsx` + `frontend/src/app/terms-of-service/page.tsx`, v2.0 → v3.0

---

## Decisions stack (locked, untuk reference)

1. Payment model: **Scenario C** (subscription only via ToyyibPay)
2. FPX placeholder: **removed** dalam Step 3 (UI cleanup)
3. Bilingual: **BM primary + English secondary, BM prevails**
4. PDPA dalam Terms s10: **link-out ke Privacy Policy** (no duplication)
5. Scope: **full rewrite** both docs
6. WhatsApp: **full explicit disclosure** — deep-link only, BinaApp tak access/store
7. AI vendors final list (4): **Stability (US), DeepSeek (China), Qwen (SG), Anthropic (US)**
8. GLM/Z.ai: **REMOVED dari codebase** (committed `e2b2e65`)
9. Stripe: **separate PR** — out of scope
10. PII strategy: **D + B-lite hybrid** — disclose semua + sanitize sender_email
11. Anthropic disclosure: **YES + trust signal framing** ("no training on customer data")
12. PII features: **PROCEED + commitment dalam polisi yang consent UI akan dibina dalam 30 hari**

---

## Step 2b — Feature ↔ Coverage Gap Matrix

### 📘 Table 1: Privacy Policy

| # | Feature / Topic | Current coverage (file:section) | Gap or Conflict | foodpanda reference (per user-supplied) | Proposed clause (BM 1-2 ayat) |
|---|---|---|---|---|---|
| 1 | Pengumpulan data akaun (merchant) | privacy-policy:s2.1 | ✅ Sufficient — covers nama, emel, telefon, SSM, alamat bisnes | — | Kekal seperti sedia ada, tambah "kata laluan disimpan secara hash, bukan dalam bentuk plain text". |
| 2 | Pembayaran subscription via ToyyibPay | privacy-policy:s2.1, s2.3 | ⚠️ Conflict — ayat "we do NOT process customer payments" mengelirukan; BinaApp **memang** proses subscription merchant via ToyyibPay | — | Jelaskan: BinaApp **memproses pembayaran langganan merchant** melalui ToyyibPay (FPX); butiran kad tidak disimpan di server BinaApp. |
| 3 | Pembayaran makanan customer (NON-PROCESSING) | privacy-policy:s callout, s5.3 | 🆕 Gap — tak explicit yang BinaApp **tidak** sentuh payment customer→merchant | foodpanda purpose-based (Section "When you place an order") | Ayat baru: "Pembayaran makanan oleh pelanggan kepada restoran berlaku **di luar BinaApp** (tunai kepada rider atau imbas QR bank merchant). Kami tidak memproses, menerima, atau menyimpan butiran pembayaran tersebut." |
| 4 | GPS tracking rider | privacy-policy:s8 (whole section) | ⚠️ Update needed — ayat sedia ada implies BinaApp control rider; perlu clarify rider = pekerja merchant, bukan BinaApp | — | Restructure: kekalkan transparency tentang what/who/how-long/control, tapi tambah "rider adalah pihak ketiga bebas yang dilantik oleh merchant; BinaApp hanya menyediakan alat penjejakan GPS". |
| 5 | Imej QR statik merchant (NEW) | (tiada) | 🆕 Gap — tiada langsung. Merchant upload imej QR bank/DuitNow mereka ke Supabase storage BinaApp; imej ni mengandungi nombor akaun atau ID bank merchant | — | Ayat baru: "Merchant boleh memuat naik imej QR pembayaran mereka sendiri (DuitNow, QR bank). Imej tersebut disimpan dalam storan BinaApp dan dipaparkan kepada pelanggan, tetapi BinaApp tidak menafsir, mengesahkan, atau menerima sebarang pembayaran yang dilakukan melalui QR tersebut." |
| 6 | Chat Pelanggan dalaman | privacy-policy:s9 (whole) | ✅ Sufficient — 90d retention, NOT e2e, do-not-share warning sudah ada | — | Kekal. Tambah satu poin: "mesej chat yang dianalisis oleh BinaBot AI dihantar ke penyedia AI pihak ketiga — lihat seksyen Penyedia AI". |
| 7 | WhatsApp deep-link (NEW) | (tiada) | 🆕 Gap penuh — perlu ada disclosure walaupun BinaApp tak proses | — | Seksyen baru: "Butang WhatsApp yang dijana untuk laman web restoran adalah pautan terus (`wa.me/<nombor>`). Bila ditekan, perbualan berlaku **dalam aplikasi WhatsApp pelanggan**, antara pelanggan dan merchant sahaja. BinaApp tidak akses, simpan, atau hantar mesej tersebut. Privacy lepas tu tertakluk kepada Polisi Privasi Meta dan merchant." |
| 8 | AI vendor disclosure — Stability AI (US) | (tiada) | 🆕 Gap — vendor baru | — | Senarai dalam jadual: nama, region, tujuan ("penjanaan imej menu/hero"), data yang dihantar ("hanya nama hidangan & prompt visual"), retention vendor. |
| 9 | AI vendor disclosure — DeepSeek (China) | (tiada) | 🆕 Gap **paling kritikal** — China data residency | — | Disclose explicit: "DeepSeek (`api.deepseek.com`, Republik Rakyat China) digunakan untuk penjanaan HTML laman web (kandungan perniagaan sahaja) **dan juga** analisis aduan + balasan AI chat (mengandungi teks aduan/mesej pelanggan)." Sertakan link ke polisi privasi DeepSeek. |
| 10 | AI vendor disclosure — Qwen/Alibaba (SG) | (tiada) | 🆕 Gap | — | Disclose: "Qwen (Alibaba Cloud International, endpoint Singapura) digunakan untuk penambahbaikan kandungan laman web (selamat) dan pengesahan foto penghantaran (foto mungkin tertangkap persekitaran pelanggan)." |
| 11 | AI vendor disclosure — Anthropic Claude (US) | (tiada) | 🆕 Gap | — | Disclose dengan trust framing: "Anthropic Claude (`api.anthropic.com`, AS) digunakan untuk analisis emel sokongan. Anthropic **tidak menggunakan data customer untuk melatih model mereka** (per kontrak komersial standard Anthropic). Alamat emel pengirim di-sanitize (di-hash kepada domain sahaja) sebelum dihantar." |
| 12 | Jadual per-feature AI data flow | (tiada) | 🆕 Gap | foodpanda purpose-based structure | Jadual baru: 8 baris (Penjanaan web, Penjanaan imej, Analisis aduan, Balasan aduan, BinaBot chat, Foto verifier, Emel sokongan, BinaBot merchant) × kolum (Vendor, Region, Data dihantar, Risiko PII, Status consent). |
| 13 | Cross-border transfer disclosure | privacy-policy:s13 | ⚠️ Insufficient — sebut Supabase SG + Vercel/Render global sahaja; tak liputi 4 AI vendor + cross-border PDPA s129 obligation | — | Expand: senaraikan semua jurisdiksi (Malaysia, Singapura, AS, China, EU/UK), state safeguards yang ada (Standard Contractual Clauses bila applicable), refer PDPA s129 compliance. |
| 14 | Hak data subject | privacy-policy:s7 | ⚠️ Restructure — sedia ada 6 hak dengan ikon-ikon. OK conceptually tapi boleh adopt structure yang lebih clean | foodpanda Access/Rectification/Withdraw pattern | Restructure ikut pattern: (a) Hak Akses, (b) Hak Pembetulan/Rectification, (c) Hak Penarikan Persetujuan, (d) Hak Padam, (e) Hak Mudah Alih, (f) Hak Hadkan Pemprosesan. Tambah explicit yang permohonan boleh dibuat melalui dashboard atau emel admin@binaapp.my. |
| 15 | Algorithmic decision-making disclosure (NEW) | (tiada) | 🆕 Gap — sistem dispute auto-resolution AI yang buat keputusan refund/reject ada, tapi tak disclose | foodpanda automated decision pattern | Seksyen baru: "Sebahagian keputusan pertikaian (refund, partial, reject) dijana oleh sistem AI berdasarkan analisis algoritma. Anda berhak meminta semakan manual oleh manusia dalam **7 hari** selepas keputusan AI dimaklumkan." |
| 16 | "Personal data of other individuals" (NEW) | (tiada) | 🆕 Gap — merchant upload data customer (nama, alamat, telefon) ke dashboard mereka. Merchant bertanggungjawab dapatkan consent customer | foodpanda "data of others" clause | Seksyen baru: "Jika anda (merchant) memuat naik atau memasukkan data peribadi pihak ketiga (cth: pelanggan) ke BinaApp, **anda mengesahkan yang anda telah mendapat keizinan mereka** untuk berbuat demikian dan akan bertanggungjawab penuh untuk pematuhan PDPA bagi data tersebut." |
| 17 | Cookies | privacy-policy:s10 | ✅ Sufficient untuk baseline | — | Kekal. Tambah disclaimer ringkas tentang analytics cookie (jika ada Plausible/PostHog dipasang — confirm dalam Step 3). |
| 18 | Jadual retention | privacy-policy:s4 | ⚠️ Update — perlu tambah baris untuk: (a) log permintaan AI, (b) foto penghantaran (verifier input), (c) imej QR merchant, (d) data quota usage tracking, (e) addon purchase records | — | Tambah 5 baris baru ke jadual existing. Cadangan period: AI logs 90d, photo verifier 30d, QR image while account active, quota usage 90d, addon record 7y (sama macam transaction). |
| 19 | International transfers | privacy-policy:s13 | ⚠️ Expand — lihat #13 | — | Sama macam #13. |
| 20 | Children's privacy | privacy-policy:s11 | ✅ Sufficient (18+) | — | Kekal. |
| 21 | Changes notification | privacy-policy:s14 | ✅ Sufficient | — | Kekal, tetapi tambah satu paragraf yang refer kepada seksyen "Riwayat Perubahan" di bawah (lihat Step 2d). |
| 22 | Contact / DPO | privacy-policy:s15 | ✅ Sufficient | — | Refresh: pastikan admin@binaapp.my masih aktif, support.team@binaapp.my masih aktif, alamat fizikal Ezy Work Asia Solution masih betul. Tambah nombor SSM 002944700-D. |
| 23 | Consent UI commitment (NEW) | (tiada) | 🆕 Gap — komitmen polisi yang AI consent UI akan ada dalam 30 hari | — | Ayat baru: "BinaApp komited membina UI persetujuan eksplisit untuk fitur AI yang memproses data pelanggan (analisis pertikaian, BinaBot chat, pengesahan foto, sokongan emel) dalam tempoh **30 hari dari tarikh efektif Polisi ini (21 Mei 2026)**. Sehingga ia siap, persetujuan diandaikan dari penggunaan berterusan perkhidmatan." |

---

### 📕 Table 2: Terms of Service

| # | Feature / Topic | Current coverage (file:section) | Gap or Conflict | foodpanda reference (per user-supplied) | Proposed clause (BM 1-2 ayat) |
|---|---|---|---|---|---|
| T1 | Service description as SaaS | terms:s1 + callout | ⚠️ Conflict — s1 cakap "restaurant delivery platform" (line 56). Tapi business model callout cakap **bukan** delivery service. Bercanggah dengan diri sendiri | — | Tukar s1 jadi: "BinaApp ialah platform Perisian-sebagai-Perkhidmatan (SaaS) untuk restoran Malaysia, menyediakan alat pembina laman web, pengurusan pesanan, penjejakan GPS, dan integrasi pembayaran langganan." Buang ayat "restaurant delivery platform". |
| T2 | Business model callout | terms:top callout | ⚠️ Refinement — kena differentiate explicit antara "subscription = processed" dan "customer food payment = NOT processed" | — | Refine list "What We Do NOT Do" jadi 2 bahagian: (a) **Pembayaran makanan**: BinaApp tidak proses, tidak terima, tidak simpan; (b) **Operasi penghantaran**: BinaApp tidak gaji rider, tidak control delivery. Tambah explicit: "**Yang BinaApp PROSES:** pembayaran langganan merchant via ToyyibPay." |
| T3 | Definitions | terms:s2 | ✅ Sufficient | — | Tambah definisi baru: "Addon", "Quota", "Penyedia AI", "QR Statik". |
| T4 | Eligibility & account | terms:s3 | ✅ Sufficient (18+) | — | Kekal. |
| T5 | Subscription plans | terms:s4.1 | ⚠️ Confirm tiers: Starter RM5 / Basic RM29 / Pro RM49 | — | Confirm RM5/RM29/RM49 betul (verified dalam code `payments.py:1335`). Tambah disclosure: "Harga boleh berubah dengan 30 hari notis emel." |
| T6 | Addon purchases (NEW) | (tiada) | 🆕 Gap penuh — 5 jenis addon (ai_image, ai_hero, website, rider, zone) | — | Seksyen baru s4.4: "Addon ialah pembelian sekali sahaja yang ditambah kepada akaun anda. Jenis: imej AI, AI hero, laman web tambahan, slot rider tambahan, zon penghantaran tambahan. **Tiada refund** untuk addon yang telah digunakan (consumed); addon yang belum digunakan boleh direfund dalam 7 hari pembelian dengan emel ke admin@binaapp.my." |
| T7 | Subscription quota enforcement (NEW) | (tiada) | 🆕 Gap — kuota per-tier ada dalam code tetapi tak disclose | — | Seksyen baru s4.5: Jadual ringkas — Starter: 1 web, 1 rider, kuota AI X/bulan; Basic: 5 web, 5 rider, kuota AI Y/bulan; Pro: ∞ web, 10 rider, kuota AI Z/bulan. Behavior at limit: **block** (bukan auto-charge). User boleh beli addon atau upgrade tier. (Nombor kuota perlu confirm dari code dalam Step 3.) |
| T8 | User responsibilities | terms:s5 | ⚠️ Strengthen — sedia ada terlalu ringkas | foodpanda s3.1 prohibited activities | Expand s5.2 dengan list lebih panjang: jangan reverse engineer, jangan automated scraping, jangan resell sub-license, jangan kongsi akaun, jangan gunakan untuk produk tidak halal/haram (alkohol, judi, dadah), jangan spam customer melalui chat, dll. |
| T9 | Merchant responsibilities | terms:s6 | ✅ Mostly OK | — | Tambah: "Merchant bertanggungjawab penuh untuk **integriti data pelanggan** yang dimasukkan ke BinaApp (lihat Polisi Privasi #16)." |
| T10 | Customer responsibilities | terms:s7 | ⚠️ Misplaced — BinaApp **tidak ada direct relationship dengan customer**. Customer adalah pelanggan merchant, bukan BinaApp | — | **REMOVE seksyen ini sepenuhnya** atau move sebagai panduan dalam Polisi Privasi sahaja. Customer terma terpakai melalui merchant's own terms (yang dipaparkan di laman web restoran mereka). Tukar konteks: BinaApp Terms ialah antara BinaApp ↔ Merchant sahaja. |
| T11 | Order cancellation & refund | terms:s8 | ⚠️ Major conflict — seksyen sedia ada describe FOOD ORDER cancellation (cust→merchant), tapi BinaApp tak proses food orders | — | **Replace** seluruh seksyen: tukar kepada "Pembatalan & Refund Langganan". Cover: cancel anytime, end of billing period, no partial refund untuk subscription mid-cycle, addon refund per s4.6. Polisi refund pesanan makanan ialah polisi merchant sendiri, BinaApp tiada kuasa atas itu. |
| T12 | Delivery operations disclaimer | terms:s9 | ⚠️ Strengthen — sedia ada bagus, tapi boleh jadi lebih kuat | — | Tambah: "Rider yang menggunakan PWA `/rider` BinaApp **bukan kakitangan, kontraktor, atau ejen BinaApp**. Hubungan undang-undang rider ialah dengan merchant yang melantik mereka. BinaApp tidak menyediakan insurans, EPF, SOCSO, atau apa-apa tuntutan pekerja kepada rider." |
| T13 | Static QR disclaimer (NEW) | (tiada) | 🆕 Gap | — | Seksyen baru: "Jika merchant memuat naik imej QR pembayaran (DuitNow, QR bank), BinaApp **hanya memaparkan** imej tersebut kepada pelanggan; BinaApp tidak mengesahkan ketulenan QR, tidak menjamin pembayaran sampai kepada merchant, dan tidak bertanggungjawab untuk sebarang pertikaian pembayaran yang berlaku di luar platform BinaApp." |
| T14 | AI-generated content disclaimer (NEW) | (tiada) | 🆕 Gap | foodpanda s6.11 pattern | Seksyen baru: "Kandungan yang dijana oleh AI (HTML laman web, imej menu, teks balasan) disediakan **as-is tanpa jaminan ketepatan**. AI boleh menghasilkan halusinasi (fakta palsu), kandungan tidak sesuai budaya, atau bahasa yang tidak tepat. Merchant bertanggungjawab untuk menyemak dan meluluskan semua kandungan AI sebelum diterbitkan. BinaApp tidak menjamin bahawa kandungan AI bebas pelanggaran hak cipta pihak ketiga." |
| T15 | PDPA section in Terms | terms:s10 (whole) | ⚠️ Duplication — duplicate Privacy Policy s2-7 | — | **REPLACE** dengan satu paragraf: "Pengumpulan, penggunaan, dan pemprosesan data peribadi anda ditadbir oleh [Polisi Privasi kami](/privacy-policy). Dengan menggunakan BinaApp anda bersetuju dengan terma Polisi Privasi tersebut." |
| T16 | Software tools (s11) | terms:s11 | ⚠️ Update — sedia ada cover GPS, Chat, Order Mgmt. Perlu tambah feature baru | — | Update senarai: tambah `/delivery` (dispatcher tool), `/menu-designer` (menu builder), AI generation pipeline (4 vendor), `/rider` PWA, addon system. |
| T17 | IP — BinaApp owns platform | terms:s12.1 | ✅ Sufficient | — | Kekal. |
| T18 | IP — Merchant owns content | terms:s12.2 | ⚠️ Add AI clause | — | Tambah satu poin: "Imej dan HTML yang dijana melalui pipeline AI BinaApp **dimiliki oleh merchant** (BinaApp tidak menuntut hak cipta). Lesen latar belakang: BinaApp memegang lesen royalty-free terhad untuk paparan & operasi platform." |
| T19 | IP — AI-generated ownership (NEW) | (tiada) | 🆕 Lihat T18 | — | Sebahagian dari T18. |
| T20 | Subdomain license | terms:s12.3 | ⚠️ Add revocation clause | — | Tambah: "BinaApp mengekalkan hak untuk membatalkan subdomain `[name].binaapp.my` tanpa notis jika ia digunakan untuk aktiviti haram, menyalahi terma ini, atau melanggar hak pihak ketiga (cth: tradmark squatting)." |
| T21 | Service availability | terms:s13 | ✅ Sufficient | — | Kekal. |
| T22 | Termination | terms:s14 | ✅ Sufficient | — | Kekal. |
| T23 | Third-party services | terms:s15 | ⚠️ Expand untuk AI vendors | — | Tambah 4 baris untuk AI vendor (Stability/DeepSeek/Qwen/Anthropic), masing-masing dengan link ke polisi mereka. |
| T24 | Limitation of Liability | terms:s16 | ⚠️ Adopt stronger drafting | foodpanda s10 pattern | Restructure: bahagikan kepada (a) Liability cap (kekal RM 12-month fees atau RM100), (b) Exclusions yang explicit (consequential damages, loss of profit, loss of data, third-party AI hallucinations, food poisoning, delivery accidents, rider negligence), (c) Carve-outs (kekal yang tak boleh excluded under Malaysian law — fraud, willful misconduct, death, personal injury). |
| T25 | Indemnity (NEW) | (tiada) | 🆕 Gap | foodpanda s13 pattern | Seksyen baru: "Merchant bersetuju untuk **menjamin (indemnify)** BinaApp daripada apa-apa tuntutan pihak ketiga (termasuk pelanggan, rider, pihak berkuasa) yang timbul dari (a) operasi perniagaan merchant, (b) kandungan yang dipaparkan oleh merchant, (c) data yang dimuat naik oleh merchant tanpa persetujuan subjek data, (d) pelanggaran terma ini." |
| T26 | Severability (NEW) | (tiada) | 🆕 Gap | foodpanda s17 pattern | Seksyen baru: "Jika mana-mana peruntukan dalam Terma ini didapati tidak sah atau tidak boleh dikuatkuasakan oleh mahkamah Malaysia, peruntukan tersebut hendaklah dipisahkan dan baki Terma ini kekal sah." |
| T27 | Governing law & disputes | terms:s17 | ✅ Sufficient | — | Kekal. |
| T28 | Prevailing language clause (NEW) | (tiada) | 🆕 Gap | — | Seksyen baru: lihat Step 2d untuk draft penuh. |
| T29 | Amendments | terms:s14 callout + s4 changes | ⚠️ Spread out — tak ada seksyen amendments tersendiri | foodpanda s16 pattern | Konsolidasi: seksyen tersendiri tentang amendments. 30 hari notis emel untuk material changes, paparan banner di dashboard, continuous use = acceptance. |
| T30 | Contact | terms:s18 | ✅ Sufficient | — | Refresh emel + tambah nombor SSM. |
| T31 | Acknowledgment | terms:s19 | ✅ Sufficient | — | Kekal, tetapi tambah satu checkbox baru dalam registration UI: "Saya mengesahkan saya telah membaca dan bersetuju dengan Polisi Privasi yang dikemas kini (v3.0) termasuk pendedahan penyedia AI." |

---

## Step 2c — Conflict List

Format: file:line(s) → current wording → why conflict → proposed correction.

### Conflict 1 — "We do NOT process customer payments" (mengelirukan)

- **File:** `frontend/src/app/privacy-policy/page.tsx:22-25` (juga `terms-of-service/page.tsx:39`)
- **Current wording (Privacy):**
  > *"We do NOT process customer payments for food orders, employ delivery riders, or operate as a delivery service. Each restaurant manages their own operations independently."*
- **Current wording (Terms):**
  > *"❌ What We Do NOT Do: …Process customer payments (customers pay restaurants directly)…"*
- **Why conflict:** Ayat ini **separuh betul sahaja**. BinaApp memang tak proses pembayaran customer→merchant (food orders). Tetapi BinaApp **memang proses pembayaran subscription merchant→BinaApp** via ToyyibPay. Reader awam akan ingat BinaApp langsung tak proses apa-apa payment, padahal ToyyibPay integration handle RM5/RM29/RM49 + addons.
- **Proposed correction:** Pecahkan kepada 2 statement berasingan dan jelas:
  - **Yang BinaApp PROSES** (via ToyyibPay): pembayaran langganan merchant, pembayaran addon, pembaharuan, naik taraf.
  - **Yang BinaApp TIDAK PROSES**: pembayaran pesanan makanan (customer→merchant). Customer bayar tunai kepada rider (COD) atau imbas QR statik merchant (transfer bank terus).

---

### Conflict 2 — PDPA duplication antara Privacy & Terms

- **File:** `frontend/src/app/terms-of-service/page.tsx:284-353` (seksyen 10) vs `privacy-policy/page.tsx:42-298` (seksyen 2-7)
- **Current wording (Terms s10):** ~70 baris yang duplicate data collected, data use, retention table, dan PDPA rights. Sama 95% dengan Privacy Policy.
- **Why conflict:** Maintenance burden — kalau update Privacy Policy, kena update Terms s10 juga. Risiko drift apabila satu file di-update tapi yang lain terlepas. Juga panjangkan dokumen Terms tak perlu.
- **Proposed correction:** Replace seluruh Terms s10 dengan 1 paragraf 2-3 ayat: "Pengumpulan dan pemprosesan data peribadi anda ditadbir oleh Polisi Privasi BinaApp di `/privacy-policy`. Dengan menggunakan perkhidmatan, anda bersetuju dengan terma Polisi Privasi tersebut. Hak data subject anda (akses, pembetulan, padam, dll) boleh dilaksanakan melalui kaedah yang dinyatakan dalam Polisi Privasi."

---

### Conflict 3 — Date drift (Januari 2025 → Mei 2026)

- **Files:**
  - `frontend/src/app/privacy-policy/page.tsx:8`, `534`, `535`, `536`
  - `frontend/src/app/terms-of-service/page.tsx:8`, `566`, `568`, `569`
- **Current wording:** "Last updated: January 31, 2025" / "Effective Date: January 31, 2025" / "© 2025 Ezy Work Asia Solution"
- **Why conflict:** Hari ini 21 Mei 2026 — dokumen ~16 bulan lapuk. Footer landing pula tulis "© 2026 binaapp" (`LandingFooter.tsx:84`). Inkonsisten.
- **Proposed correction:** Update semua 8 occurrence kepada "Last updated: 21 Mei 2026 / Tarikh Efektif: 21 Mei 2026 / © 2026 Ezy Work Asia Solution". Tambah versi v3.0.

---

### Conflict 4 — "Restaurant delivery platform" vs SaaS-only positioning

- **File:** `frontend/src/app/terms-of-service/page.tsx:56`
- **Current wording:**
  > *"BinaApp is a restaurant delivery platform that provides website building, order management, GPS tracking, and payment integration services for restaurants in Malaysia."*
- **Why conflict:** Callout di atas seksyen 1 cakap **SaaS, BUKAN delivery service**. Tapi ayat seksyen 1 itu sendiri panggil ia "restaurant delivery platform". Bercanggah dalam 1 seksyen yang sama.
- **Proposed correction:** Replace dengan: "BinaApp ialah platform **Perisian-sebagai-Perkhidmatan (SaaS)** yang menyediakan alat pembina laman web, pengurusan pesanan, penjejakan GPS, dan integrasi pembayaran langganan untuk restoran di Malaysia. BinaApp **bukan** penyedia perkhidmatan penghantaran."

---

### Conflict 5 — English content vs BM footer label

- **Files:** Both policy pages full content English; `LandingFooter.tsx:15-16` label BM ("Polisi Privasi", "Terma Perkhidmatan")
- **Why conflict:** User klik "Polisi Privasi" (BM) → land kat page yang heading "Privacy Policy" + content fully English. Audience SME Malaysia, language friction.
- **Proposed correction:** Implement bilingual structure (lihat Step 2d Option C recommendation). Content BM primary, English version available via separate route.

---

### Conflict 6 — Customer Responsibilities seksyen (Terms s7)

- **File:** `frontend/src/app/terms-of-service/page.tsx:178-202`
- **Current wording:** Seksyen 7 cover "accurate delivery addresses", "age-restricted items (alcohol)", "must present valid ID upon delivery", "Health Warning: MEMINUM ARAK BOLEH MEMBAHAYAKAN KESIHATAN".
- **Why conflict:** Terms BinaApp adalah kontrak antara **BinaApp ↔ Merchant**. Customer **bukan** pihak kontrak — mereka adalah pelanggan merchant. BinaApp tak ada legal standing untuk mengikat customer dengan Terms ini. Customer berurusan dengan merchant melalui terma merchant sendiri.
- **Proposed correction:** **Remove seksyen ini sepenuhnya** dari Terms BinaApp. Sebaliknya, sediakan template "Terma Pelanggan" yang merchant boleh adopt untuk laman web mereka (out-of-scope untuk rewrite ini, tapi flag sebagai future enhancement). Sekiranya nak kekal sebagai panduan, jelaskan ia adalah cadangan untuk merchant adopt, bukan mengikat customer secara langsung.

---

### Conflict 7 — "Order Cancellation & Refund Policy" (Terms s8)

- **File:** `frontend/src/app/terms-of-service/page.tsx:204-244`
- **Current wording:** Seksyen 8 cover "Customer Cancellations" (food orders), "Refund Eligibility" (food orders), "RM2 cancellation fee", "Restaurant cancellation".
- **Why conflict:** Sama macam Conflict 6 — ini polisi refund untuk **pesanan makanan customer→merchant**, bukan untuk subscription merchant→BinaApp. BinaApp tak proses food order payments, jadi tak boleh ada kuasa refund. Ayat "BinaApp does not process refunds for accepted orders" sebenarnya betul tapi maksudnya BinaApp **memang tak boleh** proses, bukan dasar BinaApp.
- **Proposed correction:** Replace dengan seksyen baru "Pembatalan & Refund Langganan" yang cover: cancel subscription anytime, mid-cycle no partial refund, addon refund within 7 hari jika belum digunakan, refund processed via ToyyibPay reversal jika applicable. Refund untuk pesanan makanan ialah polisi merchant sendiri.

---

### Conflict 8 — Rider definition implies BinaApp control

- **File:** `frontend/src/app/terms-of-service/page.tsx:70`
- **Current wording:**
  > *"'Rider' or 'Delivery Partner' means any person performing delivery services for restaurants using BinaApp's GPS tracking tools."*
- **Why conflict:** Definisi OK secara teknikal, tapi tidak menegaskan rider ialah pihak ketiga bebas. Bila dibaca bersama seksyen GPS (Privacy s8), boleh dianggap BinaApp ada kawalan/hubungan kerja dengan rider.
- **Proposed correction:** Update kepada: *"'Rider' atau 'Rakan Penghantar' bermaksud individu yang melaksanakan perkhidmatan penghantaran untuk merchant menggunakan alat penjejakan GPS BinaApp. Rider ialah **kontraktor bebas merchant**, bukan pekerja atau ejen BinaApp."*

---

### Conflict 9 — Subscription tier list tak include addon

- **File:** `frontend/src/app/terms-of-service/page.tsx:95-101`
- **Current wording:**
  > *"4.1 Available Plans — Starter: RM5/month, Basic: RM29/month, Pro: RM49/month. Payments are processed securely through ToyyibPay."*
- **Why conflict:** Tak sebut addon (5 jenis) yang memang merchant boleh beli sebagai one-time purchase. Audit code confirm `subscription.py:480-487` ada `ai_image`, `ai_hero`, `website`, `rider`, `zone` addons.
- **Proposed correction:** Tambah seksyen 4.4 baharu untuk addon. Lihat Step 2b T6 untuk cadangan ayat.

---

### Conflict 10 — Subscription quota tidak disclose

- **File:** `frontend/src/app/terms-of-service/page.tsx:95-101`
- **Current wording:** Sebut tier sahaja, tak ada kuota.
- **Why conflict:** Code (`backend/app/middleware/subscription_guard.py`) enforce kuota — kalau merchant pukul limit (e.g., websites count, AI generations/month, riders), request akan **block**. Tak disclose dalam Terms = potensi dispute "saya tak tahu kuota".
- **Proposed correction:** Lihat Step 2b T7 untuk cadangan ayat + jadual ringkas kuota per tier.

---

### Conflict 11 — Children warning ada tapi tak refer ke merchant

- **File:** `frontend/src/app/privacy-policy/page.tsx:406-422`
- **Current wording:** "BinaApp is not intended for use by anyone under 18 years old."
- **Why conflict:** Betul untuk merchant (yang daftar akaun BinaApp). Tapi tak cover anak kecil customer yang dihantar order untuk parents/relatives. Tak masalah besar tapi worth clarify.
- **Proposed correction:** Refine: "Pengguna BinaApp (merchant) mesti berumur 18 tahun ke atas. BinaApp tidak mengumpul data peribadi daripada kanak-kanak di bawah 18 tahun secara sengaja. Sekiranya merchant memuat naik data customer di bawah 18, merchant bertanggungjawab mendapatkan keizinan ibu bapa/penjaga."

---

### Conflict 12 — "Email Communications" — marketing opt-out belum dilaksana

- **File:** `frontend/src/app/privacy-policy/page.tsx:354-361`
- **Current wording:**
  > *"Marketing emails: Promotional offers and news (you can opt-out anytime)"*
- **Why conflict:** Polisi janji opt-out mechanism, tapi audit code tak tunjuk ada email preferences UI atau unsubscribe link standard dalam transactional emails. Perlu confirm dalam Step 3.
- **Proposed correction:** Sama ada (a) implement opt-out UI dalam Step 3 atau PR berasingan, ATAU (b) sementara tukar ayat: "Marketing emails: kami akan tambah opt-out preference dalam dashboard dalam 30 hari Polisi efektif." (sama format dengan AI consent commitment).

---

### Conflict 13 — Cookies list incomplete (potensi tracking SDK yang tak listed)

- **File:** `frontend/src/app/privacy-policy/page.tsx:371-403`
- **Current wording:** Sebut Essential / Analytics / Preferences cookies tanpa nama specific tools.
- **Why conflict:** Belum confirm apakah Plausible / PostHog / Google Analytics / Vercel Analytics digunakan. Kalau ada — kena disclose by name. Kalau tiada — kena state explicit.
- **Proposed correction:** Audit dalam Step 3: grep frontend untuk `gtag`, `posthog`, `plausible`, `vercel/analytics`. Update polisi mengikut findings.

---

## Step 2d — Proposed Structure for Rewrite

### 1. Bilingual layout pattern

**Pilihan Recommended: Option C — Separate routes dengan hreflang cross-link.**

| Option | URL pattern | Pros | Cons | Verdict |
|---|---|---|---|---|
| A: Single scroll, BM atas + English bawah, anchor | `/privacy-policy` (1 URL) | 1 URL untuk SEO, simple maintenance | Page sangat panjang (>1100 baris), scroll friction, hreflang tak boleh implement properly | ❌ |
| B: Tab toggle BM/EN, `?lang=bm` | `/privacy-policy?lang=bm` | Single component, lighter | Query param SEO weaker; bot crawler mungkin tak detect EN version; React state tab tak ramah SSR/SEO | ❌ |
| C: Separate routes + hreflang | `/polisi-privasi` (BM, default) + `/privacy-policy` (EN) | Cleanest SEO (each URL indexed), hreflang declaration sokong, user toggle clear, server-side renderable | 2 component files (boleh share data) | ✅ |

**Justifikasi (Next.js 14 App Router + SEO):**
- Next.js 14 App Router sokong perfectly: 2 folder berasingan (`app/polisi-privasi/page.tsx`, `app/privacy-policy/page.tsx`). Same untuk terma.
- SEO: `<link rel="alternate" hreflang="ms-MY" href="...">` + `hreflang="en"` declare relationship — Google index dua-dua dan serve mengikut bahasa user.
- User experience: language toggle button di header polisi switch antara `/polisi-privasi` ↔ `/privacy-policy` (router.push).
- Maintenance: extract policy data ke shared TypeScript object (e.g., `frontend/src/lib/policy-content.ts`) dengan struktur `{ bm: {...}, en: {...} }` — satu place edit, kedua-dua page render.

**Final URL map untuk Step 3:**
- `/polisi-privasi` → BM (default, primary, prevails)
- `/privacy-policy` → English (secondary, redirect dari old URL preserved)
- `/terma-perkhidmatan` → BM
- `/terms-of-service` → English

Footer link update: tukar `/privacy-policy` jadi `/polisi-privasi`, `/terms-of-service` jadi `/terma-perkhidmatan`. Old English URLs redirect tetap kerja.

---

### 2. Prevailing language clause

**Draft BM (1 ayat):**
> *"Versi Bahasa Malaysia Polisi ini adalah versi muktamad. Sekiranya terdapat percanggahan antara versi Bahasa Malaysia dan terjemahan Bahasa Inggeris, versi Bahasa Malaysia akan diguna pakai."*

**Draft English (1 sentence):**
> *"The Bahasa Malaysia version of this Policy is the authoritative version. In the event of any discrepancy between the Bahasa Malaysia version and the English translation, the Bahasa Malaysia version shall prevail."*

**Placement:** Akhir dokumen, **sebelum** seksyen Acknowledgment/Consent, **selepas** seksyen Contact. Sama untuk kedua-dua Privacy Policy dan Terms. Heading: "Bahasa Muktamad / Prevailing Language".

---

### 3. Versioning

- **Privacy Policy:** v2.0 → **v3.0**
- **Terms of Service:** v2.0 → **v3.0**
- **Effective Date:** 21 Mei 2026
- **Justification untuk major bump:** Material changes — bilingual restructure, 4 AI vendor disclosure, addon/quota terms, removal of customer-facing clauses (Terms s7/s8 replace), Static QR disclaimer, indemnity & severability additions, prevailing language clause.

---

### 4. Section ordering

**Privacy Policy — adopt purpose-based structure (per foodpanda pattern):**

Cadangan urutan baru:
1. Pengenalan & Tentang BinaApp
2. **Bila anda mendaftar akaun BinaApp (merchant)** — data dikumpul, tujuan
3. **Bila anda menggunakan dashboard BinaApp** — usage data, telemetry, quota tracking
4. **Bila merchant menerima pesanan** — order data, customer info yang merchant input
5. **Bila rider melaksanakan penghantaran** — GPS data, photo verifier
6. **Bila anda berinteraksi dengan AI BinaApp** — per-feature data flow (sertakan jadual 8-baris)
7. **Bila anda menghubungi sokongan** — chat data, email content, BinaBot interaksi
8. **Bila anda buat pembayaran langganan** — ToyyibPay data, transaction records
9. Pembayaran makanan customer (NON-PROCESSING disclosure)
10. WhatsApp deep-link (NON-PROCESSING disclosure)
11. Cookies & tracking technologies
12. Tempoh penyimpanan data (jadual)
13. Hak anda di bawah PDPA 2010
14. Pemindahan data merentas sempadan
15. Kanak-kanak
16. Data pihak ketiga (merchant uploaded data)
17. Algorithmic decision-making
18. Komitmen UI persetujuan AI (30 hari)
19. Perubahan kepada Polisi ini
20. Hubungi kami / Aduan
21. Bahasa Muktamad
22. Persetujuan
23. Riwayat Perubahan (lihat #6 di bawah)

**Terms of Service — kekal urutan asal dengan additions:**

Urutan baru:
1. Penerangan Perkhidmatan (SaaS)
2. Definisi
3. Kelayakan & Akaun
4. Pelan Langganan & Pengebilan (subscription)
   - 4.1 Pelan tersedia (RM5/RM29/RM49)
   - 4.2 Pembaharuan auto
   - 4.3 Kegagalan pembayaran
   - 4.4 **Addon (NEW)**
   - 4.5 **Kuota & enforcement (NEW)**
5. Pembatalan & Refund Langganan (replace lama)
6. Tanggungjawab pengguna (merchant)
7. Tanggungjawab merchant
8. ~~Tanggungjawab pelanggan~~ → **REMOVED**
9. ~~Order cancellation~~ → already covered di #5
10. Disclaimer operasi penghantaran (strengthened)
11. **Disclaimer QR Statik (NEW)**
12. **Disclaimer kandungan AI (NEW)**
13. PDPA → link-out ke Privacy Policy
14. Alat perisian & fitur (updated dengan feature baru)
15. Hak harta intelek
    - 15.1 BinaApp owns platform
    - 15.2 Merchant owns content (termasuk kandungan AI-generated)
    - 15.3 Lesen subdomain (with revocation)
16. Ketersediaan perkhidmatan
17. Penamatan akaun
18. Perkhidmatan pihak ketiga (expanded dengan AI vendors)
19. Had Liabiliti
20. **Indemniti (NEW)**
21. **Pemecahan / Severability (NEW)**
22. Undang-undang & pertikaian
23. **Pindaan terma (NEW konsolidasi)**
24. Hubungi
25. Bahasa Muktamad (NEW)
26. Pengakuan & penerimaan
27. Riwayat Perubahan

---

### 5. Reading length indicator

Adopt pattern: paparkan estimated reading time atas page.

**Implementation:**
- Header polisi tambah: "⏱ Anggaran masa baca: **X minit**"
- Kira berdasarkan word count: ~200 perkataan/minit untuk dewasa Malaysian.
- Privacy Policy current ~6,500 perkataan (English) → ~33 minit. Selepas restructure + bilingual: ~8,000 perkataan BM → ~40 minit.
- Terms current ~7,200 perkataan → ~36 minit. Selepas restructure: ~9,000 perkataan BM → ~45 minit.

**Component:** small badge atas h1, refresh dynamically kalau content berubah.

---

### 6. Changelog / Riwayat Perubahan section

Tambah seksyen di **bawah sekali** kedua-dua dokumen.

**Format yang dicadang:**

```
## Riwayat Perubahan / Version History

### v3.0 — 21 Mei 2026
- Restructure bilingual (BM primary + English secondary)
- Tambah pendedahan 4 penyedia AI (Stability, DeepSeek, Qwen, Anthropic)
- Tambah Addon terms (5 jenis) dan quota enforcement
- Tambah disclaimer QR statik, kandungan AI, indemniti, severability
- Buang seksyen "Customer Responsibilities" (tidak applicable)
- Replace Terms s10 (PDPA) dengan link-out ke Privacy Policy
- Tambah komitmen UI persetujuan AI dalam 30 hari
- Bahasa muktamad: Bahasa Malaysia

### v2.0 — 31 Januari 2025
- (Existing — kekalkan ringkasan dari version sedia ada untuk audit trail)

### v1.0 — Awal 2024
- Versi awal
```

Auditor-friendly. Tarikh, perubahan utama, satu liner satu bullet.

---

### 7. Component reuse strategy

**Recommendation:** Layout custom untuk legal docs, footer kongsi, header kongsi.

| Component | Reuse from landing? | Justification |
|---|---|---|
| `LandingFooter` | ✅ **Yes** — share | Footer (link grup Produk/Undang-undang/Hubungi) sudah ada link polisi. Reuse exact component sebab consistency penting untuk legal pages (footer Polisi → link Polisi sendiri = recursive but standard). |
| Header / brand mark | ✅ **Yes** — share via existing `LandingNav` or new `LegalDocHeader` extends it | Brand consistency. Tambah language toggle button. |
| Page layout (`<main>`, container width, typography) | ❌ **Custom** new `<LegalDocLayout>` component | Legal docs perlu typography lebih reader-friendly: max-width 720px (vs 1200px landing), serif body font option, larger line-height, better heading hierarchy, anchor link auto-generated dari h2/h3. |
| TOC sidebar | ❌ **Custom** new `<LegalDocTOC>` component | Lihat #8. |
| Per-section card styling | ❌ **Custom** | Current pages guna ad-hoc card styling (`bg-blue-50`, `bg-amber-50`, dll). Standardize jadi `<PolicyCallout variant="info|warning|critical">` component. |

**Folder structure cadangan:**
```
frontend/src/components/legal/
  LegalDocLayout.tsx        # Wrapper layout
  LegalDocTOC.tsx           # Sticky TOC sidebar
  LegalDocHeader.tsx        # Header dengan language toggle + reading time
  PolicyCallout.tsx         # Standardised callout boxes
  
frontend/src/lib/legal/
  policy-content-bm.ts      # Privacy content BM
  policy-content-en.ts      # Privacy content EN
  terms-content-bm.ts       # Terms content BM
  terms-content-en.ts       # Terms content EN
  changelog.ts              # Shared changelog data (both docs)
```

---

### 8. TOC sidebar

**Recommendation:** ✅ **Yes — sticky TOC sebelah kiri (desktop), drawer toggle (mobile).**

Justifikasi: dokumen 23-27 seksyen, ~40-45 minit baca. Tanpa TOC, user akan hilang dalam scroll panjang. Auditor / PDPA enforcement officer akan lebih mudah verify clause specific kalau ada navigation.

**Implementation cadangan:**
- Desktop (≥1024px): sticky sidebar kiri, width 240px, list seksyen h2 dengan indented h3 sub-items. Active section highlighted (IntersectionObserver).
- Mobile (<1024px): floating "≡" button kanan-bawah, expand jadi drawer overlay.
- Anchor link: setiap h2/h3 ada `id` auto-derived dari heading text (slugified). URL friendly (e.g., `/polisi-privasi#hak-anda-di-bawah-pdpa`).
- "Back to top" button kanan-bawah selepas scroll 500px.

---

## Ringkasan keperluan untuk Step 3

Selepas approval proposal ini, Step 3 akan execute (semua pada `feature/update-polisi-terma-2026`):

1. **FPX placeholder removal** — edit `frontend/src/components/order/checkout/PaymentMethodSection.tsx` (buang radio "online" disabled, simplify ke COD-only).
2. **Email sanitization (B-lite)** — edit `backend/app/services/ai_email_support.py:179-216` (hash sender_email ke domain je sebelum hantar ke Anthropic).
3. **Quota disclosure data gathering** — scan code untuk per-tier limits (websites, AI generations, riders, zones), extract numerical kuota untuk dokumen Terms s4.5.
4. **Cookies audit** — grep `gtag|posthog|plausible|vercel/analytics` untuk confirm tracking SDK actual yang digunakan.
5. **Buat folder structure baru** — `frontend/src/components/legal/` dan `frontend/src/lib/legal/`.
6. **Tulis polisi BM** — full content untuk Privacy Policy v3.0 (BM) + Terms v3.0 (BM).
7. **Translate ke EN** — full content untuk Privacy Policy v3.0 (EN) + Terms v3.0 (EN).
8. **Create routes** — `app/polisi-privasi/page.tsx`, `app/terma-perkhidmatan/page.tsx`, kemas kini `app/privacy-policy/page.tsx`, `app/terms-of-service/page.tsx`.
9. **Update LandingFooter** — link kepada BM URLs primary.
10. **Update register page** — checkbox consent text + link ke BM URLs.
11. **hreflang + sitemap.xml** — tambah cross-language references.
12. **Reading time + TOC** — implement components.
13. **Test Vercel preview** — review render, language toggle, mobile UX.

---

## ✅ Ready untuk approval

Proposal ini menyenaraikan:
- **23 baris matrix** untuk Privacy Policy (5 sufficient, 5 update, 13 NEW gap)
- **31 baris matrix** untuk Terms (12 sufficient, 12 update/replace, 7 NEW gap)
- **13 conflict items** dengan quote actual + cadangan correction
- **Structure decision** untuk bilingual, prevailing language, versioning, ordering, reading time, changelog, components, TOC

**Tindakan kau:**
- Review proposal (kalau ada section yang miss, flag now)
- Approve / request changes
- Lepas approve, aku terus ke Step 3 (full rewrite + supporting edits) pada branch sedia ada `feature/update-polisi-terma-2026`.
