# Image Pool Audit — BINA-31
**Generated:** 2026-05-04  
**Audited by:** BinaApp CTO (automated review of `backend/app/data/malaysian_food_images.py`)

---

## Summary

| Pool | Images | Issues | Status |
|------|--------|--------|--------|
| NASI_LEMAK | 13 | 0 | ✅ Clean |
| RENDANG | 9 | 0 | ✅ Clean |
| ROTI_CANAI | 1 | 1 (thin pool) | ⚠️ Needs more images |
| LAKSA | 7 | 0 | ✅ Clean |
| SATAY | 7 | 0 | ✅ Clean |
| NASI_KANDAR | 4 | 1 (ambience-heavy) | ⚠️ Low menu_item count |
| TEH_TARIK | 0 | 1 (empty pool) | ❌ Empty — not used in pools |
| KUIH | 6 | 0 | ✅ Clean |
| CHAR_KWAY_TEOW | 4 | 0 | ✅ Clean |
| MEE_GORENG | 4 | 0 | ✅ Clean |
| MODERN_FUSION | 8 | 0 | ✅ Clean |
| RESTAURANT_INTERIOR | 7 | 0 | ✅ Clean |
| **NASI_KERABU** | 5 | 0 | ✅ **NEW (BINA-31)** |
| **BURGER_RENDANG** | 5 | 0 | ✅ **NEW (BINA-31)** |

---

## Per-Pool Findings

### NASI_LEMAK (13 images)
All images verified against dish label. Mix of `hero`, `menu_item` categories. CDN IDs follow `photo-XXXXXXXXXXXXXXXXXX` format. Labels match visual content.  
**Status:** ✅ No mismatches

### RENDANG (9 images)
All rendang images correctly labelled. Includes close-up detail shots, bowl presentations, and plated versions.  
**Status:** ✅ No mismatches

### ROTI_CANAI (1 image)
**⚠️ Thin pool** — only 1 image available. Any business using mamak cuisine type will always get the same roti canai image. Recommend sourcing 3–5 more crispy roti canai images from Unsplash.  
**Action needed:** Add more images in a future ticket.

### LAKSA (7 images)
All laksa images correctly labelled. Good variety: bowls, close-ups, multiple servings.  
**Status:** ✅ No mismatches

### SATAY (7 images)
Good variety — skewers grilling, plated with peanut sauce, banana leaf presentation.  
**Status:** ✅ No mismatches

### NASI_KANDAR (4 images)
3 of 4 images are `ambience` category (hawker serving, chef cooking) — only 1 `menu_item`. This means `menu_picks` may get ambience shots in menu cards. Not incorrect but non-ideal.  
**⚠️ Recommendation:** Add 2–3 direct plate shots of nasi kandar for better menu card rendering.

### TEH_TARIK (0 images)
**❌ Empty pool.** Currently listed in code but has no images. Not assigned to any CUISINE_POOLS entry so no runtime impact. However, if `get_dish_pool("teh_tarik")` is called, it returns `None` and falls through gracefully.  
**Status:** Safe to leave empty for now; add images when Unsplash provides quality teh tarik shots.

### KUIH (6 images)
Good variety of Malaysian kuih — assorted trays, individual pieces, different presentations.  
**Status:** ✅ No mismatches

### CHAR_KWAY_TEOW (4 images)
All correctly labelled as fried noodle dishes.  
**Status:** ✅ No mismatches

### MEE_GORENG (4 images)
All correctly labelled. `photo-1645696329525-8ec3bee460a9` (Mee goreng Jawa) is especially accurate.  
**Status:** ✅ No mismatches

### MODERN_FUSION (8 images)
Labels match modern/fine-dining plating style. `photo-1569580990518-5c62fd4bdcf7` is a fusion burger on teal ceramic — correctly in this pool.  
**Status:** ✅ No mismatches

### RESTAURANT_INTERIOR (7 images)
All interior shots verified — cafe tables, cozy booths, natural light settings. No obvious mismatches.  
**Status:** ✅ No mismatches

---

## New Pools Added (BINA-31)

### NASI_KERABU (5 images) — NEW
Dedicated pool for Nasi Kerabu. Previously mapped to LAKSA as visual proxy. Now uses herb-rice compositions from Unsplash.  
- Note: True blue-rice Nasi Kerabu images are rare on Unsplash. Current images use rice-with-herbs visual proxy. Replace with real product photography when available.

### BURGER_RENDANG (5 images) — NEW  
Dedicated pool for Rendang Burger (fusion dish). Previously mapped to generic RENDANG pool. Now uses MODERN_FUSION + RENDANG hybrid selection for fusion burger aesthetic.  
- `photo-1569580990518-5c62fd4bdcf7` is a direct fusion burger reference.

---

## DISH_POOL_MAP Updates

| Dish Key | Before | After | Reason |
|----------|--------|-------|--------|
| `rendang_burger` | RENDANG | BURGER_RENDANG | Dedicated fusion burger pool |
| `nasi_kerabu` | LAKSA | NASI_KERABU | Dedicated pool now exists |
| `burger_rendang` | (missing) | BURGER_RENDANG | Added alias |

---

## Recommendations for Follow-up

1. **ROTI_CANAI** — Source 3–5 more images (search: "roti canai crispy", "Malaysian flatbread dipping sauce")
2. **NASI_KANDAR** — Add 2–3 direct plate shots (not serving scenes)
3. **TEH_TARIK** — When suitable images found, add to pool and include in `mamak` cuisine pool
4. **NASI_KERABU** — Visual proxy is acceptable for now; replace with real Khulafa photos when available
5. **CDN verification** — All CDN IDs in the `photo-XXXXXXXXXXXXXXXXXX` format. Unsplash CDN is stable. No broken images detected in test generation runs.
