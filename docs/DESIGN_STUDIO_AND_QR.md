# Design Studio, QR Toolkit & per-site SEO files

Three features that all share one idea: **the merchant's page already exists —
stop regenerating it.**

| Feature | What it replaces | Cost to the merchant |
|---|---|---|
| Design Studio | "tukar warna jadi biru" → full AI regenerate | **Free.** No AI call, no credit. |
| QR Toolkit | a QR image fetched from `api.qrserver.com` on every pageview | Free, and one fewer third party in the page |
| SEO files | `robots.txt` / `sitemap.xml` 404ing into the SPA | Free, automatic |

---

## 1. Design Studio — credit-free recolour & typography

### The problem

Asking to change a colour cost a generation credit and ~2 minutes, and came
back with different copy and different photos, because the only tool available
was "rebuild the whole page". Merchants learned not to touch it.

A recolour is not a redesign. The generator emits colour in exactly three
shapes — CSS custom properties, an inline `tailwind.config` block, and literal
hexes in `style=` attributes and Tailwind arbitrary values. Rewriting those
tokens is deterministic, instant and offline.

### API

```
GET   /api/v1/websites/design/options?color_mode=light[&business_type=cafe]
GET   /api/v1/websites/{id}/theme
PATCH /api/v1/websites/{id}/theme
```

`GET /design/options` is the picker catalogue — 12 named palettes (Malay
labels, full 8-role swatches, light + dark), 27 font pairings and 5 style
personalities. It is public: it holds no merchant data and the create page
renders the picker before a website row exists.

`GET /{id}/theme` reports what the page is wearing right now, read from the
**live storage snapshot** when the site is published (that is what visitors
see) and from the draft otherwise.

`PATCH /{id}/theme` repaints. Body — every field optional, precedence
`colors` > `palette` > `shuffle`:

```jsonc
{
  "palette": "navy",                  // named palette key
  "colors": { "primary": "#123456" }, // explicit brand hexes (partial is fine)
  "color_mode": "light",              // or "dark"
  "font_key": "bebas-neue__barlow",   // pairing slug from /design/options
  "shuffle": true,                    // advance to the next palette
  "shuffle_step": 1
}
```

Shuffle is seeded from the colour the page is currently wearing and advances
through the picker's display order, so it is **reproducible**: shuffling three
times and reloading still shows shuffle #3, and tapping back returns you to
where you were.

### What the repaint touches — and what it must not

`services/theme_patcher.py`:

**Rewritten**
- CSS custom properties, including the aliases the generator and the pre-built
  templates use (`--primary-color`, `--primary`, `--bg-color`, `--surface`, …)
- The inline `tailwind.config` colour entries (scoped to that `<script>` — an
  unrelated JSON blob with a `"primary"` key is never touched)
- Literal hexes belonging to the page's *current* palette, anywhere in the
  document, including Tailwind arbitrary values like `text-[#34d399]`
- `<meta name="theme-color">` (added if missing)
- The Google Fonts `<link>` and every reference to the old family names

**Never touched**
- **Greyscale hexes.** White is structural — hero text, card background,
  divider. Repainting every white in the document is how a recolour breaks a
  page, so `#FFFFFF` / `#000` / near-neutrals are excluded from the global
  swap. (The `--surface-color` *variable* still moves; only the loose literals
  are protected.)
- **Identifiers that look like colours**: `href="#EA580C-promo"`,
  `src="…jpg#EA580C"`, `fill="url(#EA580C)"`. These are masked out before the
  hex pass.
- **Copy, prices, images, layout.** A test asserts the word list of the page is
  byte-identical before and after.

The hex pass is single-pass, so replacements never cascade (old A → new B is
never re-read as old B → new C), which makes the whole operation idempotent.

### Publish safety

Identical rules to the credit-free contact-edit path, for the same reason (the
mimba regression, where republishing a truncated DB blob wiped a live site's
injected widgets):

1. rewrite against the **live storage snapshot** when published, falling back
   to the DB blob;
2. only ever accept a structurally **balanced** base;
3. refuse to publish a result that is not balanced;
4. when no safe base exists, change nothing and return
   `422 no_balanced_html_base` rather than a false success.

### Quota

This is a protected zone: the router never touches `check_limit`,
`subscription_service`, `usage_tracking` or any credit counter. A test pins
that no AI call and no usage increment happens during a repaint.

### Generation-time shuffle

`design_system.build()` gained `variant`, `palette_override` and
`style_override`. `variant=0` reproduces every existing site's look exactly;
each increment walks fonts, palette, hero and personality one step forward
through their pools. It is an offset, not randomness — re-rolls are
reproducible and shareable.

### UI

`frontend/src/components/DesignStudioPanel.tsx`, mounted in the editor beneath
the AI assistant. Deliberately a separate surface from the assistant, labelled
**Percuma**, because a merchant who has been burned by "tukar warna" costing a
generation needs to see that this button is not that button.

---

## 2. QR Toolkit

### Offline rendering

Every published page loaded its footer QR from `api.qrserver.com`. That put a
third party on the render path of every merchant's site (their QR breaks when
that service does) and handed that host every visitor's IP.

QR encoding is a solved offline problem. `services/qr_service.py` renders it
locally with `segno` (pure Python, zero dependencies) and inlines it as a
base64 SVG — no external request, crisp at any print size, cached per
subdomain since the payload only changes when the subdomain does. If `segno`
is ever missing at runtime the old remote URL is used as a fallback, so a
missing encoder can never take a merchant's page down.

### Endpoints

```
GET /api/v1/websites/{id}/qr.svg?table=5&campaign=raya&scale=8&dark=%23111827
GET /api/v1/websites/{id}/qr-poster.html?table=5&language=ms
```

Owner-only. `qr-poster.html` is a **print-ready A4 poster** wearing the site's
own palette (read from the stored page), in Bahasa Melayu by default, with
`@page size: A4` rules and a Print button that hides itself when printing —
for the shop counter, a table tent, or a flyer insert.

`table=N` encodes `?meja=N` in the URL so each table's code is a distinct URL,
and prints "Meja N" on the poster. `campaign=` does the same for a flyer batch.
The page itself ignores unknown params, so this is always safe.

Everything on the poster comes from merchant-supplied data — business name,
real published URL, real palette. No invented taglines, ratings or badges; a
test asserts that.

---

## 3. Per-site `robots.txt` and `sitemap.xml`

Generated pages already carry Open Graph tags and JSON-LD
(`services/seo_metadata.py`), but the two files a crawler asks for *first* did
not exist. The subdomain middleware now serves both.

- **`/robots.txt`** — allows crawling and points at the sitemap.
- **`/sitemap.xml`** — the homepage plus the in-page section anchors, which
  *are* the structure of a one-pager.

An anchor is only listed when the page **both** links to it and actually
contains a section with that id, so a sitemap can never advertise a section the
generator dropped. `lastmod` is omitted rather than guessed.

A **locked or downgraded** site serves `Disallow: /` and an empty urlset, so a
temporary error page can never get indexed and then outrank the real site
later.

---

## Tests

| Area | File |
|---|---|
| Repaint engine (detection, masking, idempotency, contrast) | `backend/tests/test_theme_patcher.py` |
| Design Studio endpoints (catalogue, repaint, shuffle, publish safety, credit-free) | `backend/tests/test_design_studio_api.py` |
| QR service + endpoints + poster escaping | `backend/tests/test_qr_toolkit.py` |
| robots.txt / sitemap.xml | `backend/tests/test_site_seo_files.py` |
| Offline QR in the served page | `backend/tests/test_subdomain_injection.py` |
| Frontend client + helpers | `frontend/src/lib/designStudio.test.ts` |
| Frontend panel | `frontend/src/components/DesignStudioPanel.test.tsx` |
