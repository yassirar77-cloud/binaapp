"""'Gambar hiasan' on AI-generated food photos; no menu photo reused in
Tentang Kami."""


from app.services import menu_fidelity as mf
from app.services.illustrative_images import label_ai_images, remove_menu_photo_reuse

AI = "https://res.cloudinary.com/demo/image/upload/v1/ai_set_a.png"
AI_CROPPED = "https://res.cloudinary.com/demo/image/upload/c_fill,ar_4:3,g_auto,w_900,q_auto,f_auto/v1/ai_set_a.png"
HERO_AI = "https://res.cloudinary.com/demo/image/upload/c_fill,ar_16:9,w_1600/v1/ai_hero.jpg"
UPLOAD = "https://res.cloudinary.com/demo/image/upload/v1/binaapp/user_uploads/kedai.jpg"


class TestMenuBlockLabel:
    def test_ai_photo_labelled_upload_not(self):
        items = mf.normalize_items([
            {"name": "Set A", "price": "12.50", "category": "Set Ayam"},
            {"name": "Set B", "price": "13.50", "category": "Set Ayam"},
        ])
        items, n = mf.attach_item_images(items, [("Set A", AI_CROPPED), ("Set B", UPLOAD)], ai_urls=[AI])
        assert n == 2 and [it.illustrative for it in items] == [True, False]
        block = mf.render_menu_block(items)
        a = block[block.index("ai_set_a"):]
        assert a[:400].count('<span class="bmf-ai-label">Gambar hiasan</span>') == 1
        b = block[block.index("kedai.jpg"):]
        assert "bmf-ai-label" not in b[:200]
        assert ".binaapp-menu-block .bmf-ai-label{position:absolute" in block

    def test_english_label(self):
        items, _ = mf.attach_item_images(mf.normalize_items([{"name": "Set A", "price": "1", "category": "Set"}]),
                                         [("Set A", AI)], ai_urls=[AI])
        assert "Image for illustration" in mf.render_menu_block(items, language="en")


PAGE = (
    '<section id="hero" class="relative"><img src="' + HERO_AI + '" class="absolute inset-0 w-full h-full object-cover"></section>'
    '<section id="menu"><div class="binaapp-menu-block"><ul class="bmf-grid"><li class="bmf-card"><div class="bmf-media">'
    '<img src="' + AI_CROPPED + '" alt="Set A"><span class="bmf-ai-label">Gambar hiasan</span></div></li></ul></div></section>'
    '<section id="about" class="py-16"><div class="grid md:grid-cols-2 gap-8"><div><h2>Tentang Kami</h2><p>Cerita kami.</p></div>'
    '<div><img src="' + AI_CROPPED + '" alt="Set A" class="w-full rounded-lg"></div></div></section>'
    '<section id="gallery"><img src="' + UPLOAD + '" class="w-full"></section>'
)


class TestAboutReuse:
    def test_menu_photo_removed_and_about_becomes_text_only(self):
        out, n = remove_menu_photo_reuse(PAGE, [AI_CROPPED])
        assert n == 1
        about = out[out.index('id="about"'):out.index('id="gallery"')]
        assert "<img" not in about and "md:grid-cols-1" in about and "Cerita kami." in about
        assert out.count("ai_set_a") == 1  # the menu card keeps it
        assert UPLOAD in out

    def test_other_about_images_stay(self):
        page = PAGE.replace(AI_CROPPED + '" alt="Set A" class="w-full rounded-lg"', HERO_AI + '" class="w-full"')
        out, n = remove_menu_photo_reuse(page, [AI_CROPPED])
        assert n == 0 and out == page


class TestPageLabels:
    def test_hero_and_about_ai_images_labelled_menu_and_uploads_not(self):
        page = PAGE.replace('<div><img src="' + AI_CROPPED + '" alt="Set A" class="w-full rounded-lg"></div>',
                            '<div><img src="https://res.cloudinary.com/demo/image/upload/v1/ai_about.png" class="w-full h-full"></div>')
        ai = [AI, "https://res.cloudinary.com/demo/image/upload/v1/ai_hero.jpg", "https://res.cloudinary.com/demo/image/upload/v1/ai_about.png"]
        out, n = label_ai_images(page, ai)
        assert n == 2  # hero + about; the menu block labels its own
        hero = out[:out.index('id="menu"')]
        assert 'class="binaapp-ai-label" style="position:absolute;right:.5rem;top:.5rem' in hero
        about = out[out.index('id="about"'):out.index('id="gallery"')]
        assert '<span class="binaapp-ai-wrap" style="position:relative;display:block;height:100%;">' in about
        assert "bottom:.5rem" in about and "Gambar hiasan" in about
        assert "Gambar hiasan" not in out[out.index('id="gallery"'):]
        assert out.count("Gambar hiasan") == 3  # menu card + hero + about
        assert label_ai_images(out, ai) == (out, 0)
