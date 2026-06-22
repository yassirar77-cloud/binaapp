# BinaApp — Design Concept vs Actual Code (Order Journey)

Comparison of the animated concept `BinaApp_Order_Journey_standalone.html`
against what is actually implemented in this repo (June 2026).

**Verdict: the FLOW shape matches, but 3 core mechanics in the design do
NOT exist in the code, and many labels/statuses differ.**

Legend: ✅ same · ⚠️ partial / different · ❌ missing in code

---

## SCENE 1 — CUSTOMER (website order)

| # | Design concept shows | Actual code | Status |
|---|----------------------|-------------|--------|
| 1 | Storefront: hero, menu, RM prices, `+` add buttons, bottom cart bar | Implemented (`order/menu`) | ✅ |
| 2 | Bottom bar label **"Lihat troli"**, cart titled **"Troli anda"** | Label is **"Lihat keranjang"** / "keranjang" | ⚠️ wording |
| 3 | Cart toggle **"Ambil sendiri / Penghantaran"** (pickup vs delivery) | **No toggle. No pickup option at all.** Delivery zone auto-detected from address at checkout | ❌ |
| 4 | Fees: delivery fee **+ "Yuran perkhidmatan RM0.50"** (service fee) | Delivery fee yes (zone-based). **No service fee.** | ⚠️ |
| 5 | **Pay online: ToyyibPay / FPX**, bank list (Maybank2u, CIMB, TnG), "Bayar — RM24.50", spinner "Memproses bayaran" | **No online payment at all.** COD only: "Bayar tunai semasa hantar". No ToyyibPay, no FPX, no bank picker, no gateway | ❌ **biggest gap** |
| 6 | Success "Pesanan dihantar!", **"RM24.50 DIBAYAR"** (paid) | Redirect to tracking page. Shows **"Tunai semasa hantar (COD)"**, NOT paid | ⚠️ |
| 7 | Order ID format **`ORD-260420-007`** (date-based) | Customer side: `ORD-XXXX` (e.g. `ORD-3847`). Dashboard card shows `#BNA-12345`. **Two inconsistent formats in code** | ⚠️ |

**Note:** the design's whole payment premise (ToyyibPay) contradicts the
real product model. The wrap-up slide even says **"Komisen 0%"** — which is
TRUE precisely because the real app does NOT process payment (COD direct to
rider). So: either the concept's ToyyibPay screens should be dropped to match
reality, OR online payment is a genuine new feature to build. **Decide this
first — it changes everything downstream.**

---

## SCENE 2 — OWNER DASHBOARD

| # | Design concept shows | Actual code | Status |
|---|----------------------|-------------|--------|
| 1 | Orders **TABLE**, columns: Pesanan / Pelanggan / Jumlah / **Saluran** / Status / Masa | Card-based **list**, not a table | ⚠️ layout |
| 2 | **"Saluran"** column = channel (web / whatsapp / datang) | **Channel/source is NOT tracked anywhere** (no DB column, no field) | ❌ |
| 3 | Status pills: **Baru · Diterima · Masak · Hantar · Siap** | Different labels: pending→"Menunggu", confirmed→"Disahkan", preparing→"Sedang Disiapkan", ready→"Sedia", delivering→"Sedang Dihantar", completed→"Selesai" | ⚠️ rename |
| 4 | **Real-time toast "Pesanan baru masuk!" + sound** on new order | **No real-time.** 30s polling + a count badge only. No WebSocket, no sound, no desktop notification | ❌ |
| 5 | Order detail: timeline (garis masa), items + notes | Implemented | ✅ |
| 6 | Detail shows **"DIBAYAR VIA TOYYIBPAY"** | Shows COD (see Scene 1) | ⚠️ |
| 7 | **"Terima pesanan" / "Tolak"** wired to action | Implemented ("Terima"/"Tolak", real API) | ✅ |
| 8 | **"Tugaskan penghantar"** → rider picker showing **distance + ETA** (Hafiz 2.4km·8min, Siti "Di kedai"…) | Picker exists ("Pilih Rider") but shows only **Online/Offline + plate + phone. No distance, no ETA, no location** | ⚠️ |
| 9 | **"Tawaran dihantar ke Hafiz"** → order is OFFERED, rider must accept; detail shows "Menunggu terima…" | **No offer model.** Owner assigns → rider is assigned immediately (WhatsApp notice sent). No "waiting for rider to accept" state | ❌ |

---

## SCENE 3 — RIDER PHONE

| # | Design concept shows | Actual code | Status |
|---|----------------------|-------------|--------|
| 1 | **"TAWARAN BARU" offer screen with 15-second COUNTDOWN ring** | `NewOrderBanner` UI exists but is **UI-only / non-functional**. No countdown, no dispatch channel | ❌ |
| 2 | Offer card: **payout +RM5**, pickup (1.2km) + dropoff (2.4km), items | Banner shows payout + distance + dropoff + customer. **No separate pickup line; items only after opening detail** | ⚠️ |
| 3 | **"Terima — RM5" / "Tolak"** buttons | Buttons exist but are **stubs (just show a toast). No accept/reject API endpoint** | ❌ |
| 4 | Accept model: rider chooses to take the job | **No rider acceptance.** Orders are pre-assigned by owner; rider only sees an assigned list | ❌ |
| 5 | After accept: "Pesanan diterima!", distance 1.2km, **ETA 4 min**, **"Mula navigasi →"** | Has GPS tracking + live map + external Waze/Google Maps links + status buttons. **No "Mula navigasi" button; ETA is static (not recalculated); map is a straight line, not real routing** | ⚠️ |
| 6 | PWA, Malay | PWA, Malay | ✅ |

---

## THE 3 CORE THINGS MISSING (build these to match the concept)

1. **Online payment (ToyyibPay / FPX)** — entire customer payment flow in the
   concept does not exist. App is COD-only today. *(Or: cut these screens from
   the concept and keep COD + "Komisen 0%".)*
2. **Rider dispatch with timed offer + accept/reject** — the concept's Uber-style
   loop (owner sends offer → rider gets 15s countdown → rider accepts → "in
   transit") is not built. Today the owner directly assigns and the rider just
   sees a list. Needs: dispatch channel (push/WebSocket), `accept`/`reject`
   endpoints, countdown UI, "waiting for rider" state on the dashboard.
3. **Real-time new-order alert** — concept shows instant toast + sound on the
   dashboard and a push offer on the rider phone. Today it's 30s polling, no
   sound, no push pipeline.

## SMALLER FIXES TO MATCH THE CONCEPT

- Pickup vs Delivery toggle ("Ambil sendiri / Penghantaran") on cart — not built.
- Service fee line ("Yuran perkhidmatan") — not built.
- Order "Saluran"/channel tracking (web/whatsapp/walk-in) — not built.
- Rider picker should show **distance + ETA per rider**, not just online/offline.
- Rider "Mula navigasi" button + dynamic ETA + real road routing.
- Unify order-ID format (concept `ORD-260420-007`; code has both `ORD-3847`
  and `#BNA-12345`).
- Rename statuses to the concept's simpler set if desired
  (Baru / Diterima / Masak / Hantar / Siap).

## WHAT ALREADY MATCHES (leave alone)

- Customer menu → cart → checkout → tracking flow exists and works (COD).
- Owner accept/reject orders, order detail + timeline, rider assignment, status
  progression.
- Rider PWA with GPS tracking, live map, external navigation, status buttons.
- Full Malay UI and the indigo `#4F3DFF` + volt-green `#C7FF3D` brand direction.
