# BINA-36-B Animation Test Plan

## How to verify animations work

1. Start preview server: `cd docs && python3 -m http.server 8888`
2. Open each test preview in Chrome:
   - http://localhost:8888/previews/test_pasar_malam_neon.html
   - http://localhost:8888/previews/test_kampung_serene.html
   - http://localhost:8888/previews/test_fine_dining_obsidian.html
   - http://localhost:8888/previews/test_streetfood_bold.html
   - http://localhost:8888/previews/test_kopitiam_nostalgia.html
   - http://localhost:8888/previews/menu_grid_classic.html (teh_tarik_warm default)

## Per-preview checklist

For each preview, verify:

### Page entrance (first 1.5 seconds after load)
- [ ] Hero headline fades up from below (200ms delay)
- [ ] Hero subheadline appears next (400ms delay)
- [ ] CTA buttons appear last (600ms delay)
- [ ] Sequence feels intentional, not simultaneous

### Scroll reveals
- [ ] Scroll to About section -- content fades up as it enters viewport
- [ ] Scroll to Menu section -- cards fade up with stagger
- [ ] Reveal happens ONCE (not retriggering on scroll-up)
- [ ] Reveal threshold ~15% of element visible

### Hover states
- [ ] Buttons lift on hover (translateY)
- [ ] Menu cards lift on hover with scale
- [ ] Lift amount matches style DNA personality

### Style DNA personality
- **pasar_malam_neon**: animations should feel SNAPPY, FAST (400ms), with overshoot easing
- **kampung_serene**: animations should feel SLOW, GRACEFUL (900ms), deliberate
- **fine_dining_obsidian**: animations should feel REFINED, LONG (1000ms), smooth
- **streetfood_bold**: animations should feel BOUNCY, PUNCHY (350ms), fast
- **kopitiam_nostalgia**: animations should feel CLASSICAL, GENTLE (800ms), vintage
- **teh_tarik_warm**: animations should feel WARM, NATURAL (700ms), balanced

If pasar_malam and fine_dining feel the same -> easing tokens not applied per DNA. BUG.

## Verification commands

```bash
# AOS fully removed
grep -r "aos@" docs/previews/
# Expected: empty

grep -r "AOS.init" docs/previews/
# Expected: empty

# data-reveal attributes present
grep -c "data-reveal" docs/previews/menu_grid_classic.html
# Expected: 8+

# data-entrance attributes present
grep -c "data-entrance" docs/previews/menu_grid_classic.html
# Expected: 3+

# Animation CSS variables present
grep "reveal-easing" docs/previews/menu_grid_classic.html
# Expected: --reveal-easing with cubic-bezier value
```

## Determinism check

```bash
cd /home/yassir/binaapp
source backend/.venv/bin/activate
cd backend
md5sum ../docs/previews/*.html > /tmp/run1.txt
python scripts/generate_v2_previews.py
md5sum ../docs/previews/*.html > /tmp/run2.txt
diff /tmp/run1.txt /tmp/run2.txt
# Expected: empty (identical output)
```
