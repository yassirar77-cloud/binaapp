"""Logo, favicon, theme-color; poster-style uploads shown whole."""

import pytest

from app.services.branding import apply_branding, favicon_from_initial, favicon_from_logo
from app.services.image_roles import ImageShape, fit_transform, fix_poster_images, public_id_url, same_image

LOGO = "https://res.cloudinary.com/demo/image/upload/v1/binaapp/logo.png"
PAGE = """<!DOCTYPE html><html><head><title>t</title>
<link rel="icon" href="data:image/svg+xml;charset=utf-8,%3Csvg%20fill%3D%27%23111827%27%3E">
<meta name="theme-color" content="#111827">
</head><body>
<header><nav><a href="#home" class="flex items-center gap-2"><span class="w-10 h-10 bg-gray-900 text-white">A</span><span>Ayam Gepuk Panglima</span></a></nav></header>
<section id="hero"><h1>Hi</h1></section>
<footer><p class="font-heading">Ayam Gepuk Panglima</p><p>&copy; 2026</p></footer></body></html>"""


def test_theme_color_is_the_brand_primary_and_favicon_is_the_logo():
    out, rep = apply_branding(PAGE, business_name="Ayam Gepuk Panglima", primary="#C8321A", logo_url=LOGO)
    assert '<meta name="theme-color" content="#C8321A">' in out and "#111827" not in out.split("<body")[0]
    assert out.count("theme-color") == 1 and out.count('rel="icon"') == 1
    assert 'rel="icon" href="https://res.cloudinary.com/demo/image/upload/c_pad,w_64,h_64,b_auto,q_auto,f_png/v1/binaapp/logo.png"' in out
    assert rep.theme_color == "#C8321A" and rep.favicon == "logo"


def test_logo_replaces_the_letter_badge_and_joins_the_footer():
    out, rep = apply_branding(PAGE, business_name="Ayam Gepuk Panglima", primary="#C8321A", logo_url=LOGO)
    header = out[out.index("<header"):out.index("</header>")]
    assert '>A</span>' not in header and f'<img src="{LOGO}"' in header and 'alt="Ayam Gepuk Panglima"' in header
    footer = out[out.index("<footer"):]
    assert f'<img src="{LOGO}"' in footer
    assert rep.logo_header and rep.logo_footer
    again, rep2 = apply_branding(out, business_name="Ayam Gepuk Panglima", primary="#C8321A", logo_url=LOGO)
    assert again.count("data-binaapp-logo") == 2  # idempotent


def test_no_logo_gives_a_brand_coloured_initial_favicon():
    out, rep = apply_branding(PAGE, business_name="Ayam Gepuk Panglima", primary="#C8321A")
    assert rep.favicon == "initial" and "%23C8321A" in out and "%3EA%3C" in out
    assert ">A</span>" in out  # the badge stays when there is no logo


def test_favicon_helpers():
    assert favicon_from_logo("https://example.com/l.png") == "https://example.com/l.png"
    assert favicon_from_logo("https://res.cloudinary.com/d/image/upload/c_fill,w_900/v1/x.jpg", 32).endswith("c_pad,w_32,h_32,b_auto,q_auto,f_png/v1/x.jpg")
    assert favicon_from_initial("kedai", "#FBEB02").count("%23111827") == 1  # dark text on a light brand


def test_poster_shape_rules():
    assert ImageShape("u", 800, 1200).poster and not ImageShape("u", 1200, 800).poster
    assert ImageShape("u", 1200, 800, text_heavy=True).poster and not ImageShape("u").poster
    a = "https://res.cloudinary.com/d/image/upload/c_fill,ar_4:3,g_auto,w_900,q_auto,f_auto/v1/binaapp/user_uploads/p.jpg"
    assert public_id_url(a) == "https://res.cloudinary.com/d/image/upload/v1/binaapp/user_uploads/p.jpg"
    assert same_image(a, "https://res.cloudinary.com/d/image/upload/v1/binaapp/user_uploads/p.jpg")
    assert fit_transform(a) == "https://res.cloudinary.com/d/image/upload/c_fit,w_900,q_auto,f_auto/v1/binaapp/user_uploads/p.jpg"


def test_poster_outside_the_menu_is_shown_whole_but_menu_tiles_are_left():
    poster = "https://res.cloudinary.com/d/image/upload/v1/binaapp/user_uploads/p.jpg"
    html = (
        '<section id="about"><img src="https://res.cloudinary.com/d/image/upload/c_fill,ar_4:3,g_auto,w_900,q_auto,f_auto/v1/binaapp/user_uploads/p.jpg" class="w-full aspect-[4/3] object-cover rounded-xl" alt="x"></section>'
        '<section id="menu"><img src="https://res.cloudinary.com/d/image/upload/c_fill,ar_4:3,g_auto,w_900,q_auto,f_auto/v1/binaapp/user_uploads/p.jpg" class="object-cover"></section>'
        '<section id="gallery"><img src="https://res.cloudinary.com/d/image/upload/v1/other.jpg" class="object-cover"></section>'
    )
    out, n = fix_poster_images(html, [poster])
    assert n == 1
    about = out[: out.index('<section id="menu"')]
    assert "object-contain" in about and "bg-black/5" in about and "object-cover" not in about and "c_fit,w_900" in about and 'data-binaapp-poster="1"' in about
    assert out[out.index('<section id="menu"'):].count("object-cover") == 2
