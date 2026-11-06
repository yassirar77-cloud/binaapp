"""Follow-ups from the first agp regeneration after #824.

- Outline variant did not fire: the page outlined its cards with
  ``border: 3px solid #1A120B`` / ``border-3 border-[#1A120B]`` (its own
  near-black ink), and detection only knew #000/#111/black.
- Set items lost their photos: the food image prompt was the raw menu row
  ("Set Panglima Signature – Ayam Gepuk Telur Mata"), glm-image lettered
  that label into the photo twice, and the text gate (correctly) dropped
  it. A stricter retry of "Ayam Gepuk" came back as live roosters.
"""

import pytest

from app.services import menu_fidelity as mf
from app.services.image_subjects import food_dish_subject


class TestOutlineDetection:
    def test_near_black_css_outline(self):
        css = "<style>.a{border: 3px solid #1A120B}.b{border-top: 3px solid #1A120B}.c{border:4px solid #222}</style>"
        assert mf.detect_outline_style(css)

    def test_tailwind_border_3_with_near_black(self):
        html = '<div class="border-3 border-[#1A120B] p-4">x</div>' * 3
        assert mf.detect_outline_style(html)

    def test_coloured_or_thin_borders_are_not_outline_style(self):
        html = ("<style>.c{border:3px solid #E5E7EB}.d{border:3px solid #DC2626}.e{border:4px solid #F5B400}</style>"
                + '<div class="border-2 border-black"></div><div class="border-4 border-red-600"></div>' * 3)
        assert not mf.detect_outline_style(html)


class TestFoodDishSubject:
    @pytest.mark.parametrize("name,dish", [
        ("Set Panglima Signature – Ayam Gepuk Telur Mata", "Ayam Gepuk Telur Mata"),
        ("Set A – Ayam Gepuk", "Ayam Gepuk"),
        ("Set Panglima Krispy – Ayam Krispy", "Ayam Krispy"),
        ("Set Sotong Krispy", "Sotong Krispy"),
        ("Pedal Ayam Goreng (3 pcs)", "Pedal Ayam Goreng"),
        ("Nasi Lemak Special", "Nasi Lemak"),
        ("Mee Goreng - Pedas", "Mee Goreng - Pedas"),
        ("Set B", "Set B"),
        ("Teh O Ice", "Teh O Ice"),
    ])
    def test_menu_label_removed(self, name, dish):
        assert food_dish_subject(name) == dish

    def test_autofill_food_prompt_uses_the_dish(self):
        from app.services.ai_service import AIService
        svc = AIService.__new__(AIService)
        assert svc._autofill_item_prompt("food", "Set Panglima Signature – Ayam Gepuk Telur Mata", "restaurant") == "Ayam Gepuk Telur Mata"

    def test_generic_food_prompt_is_a_cooked_plated_dish_and_drinks_a_glass(self):
        from app.services.ai_service import AIService
        svc = AIService.__new__(AIService)
        p = svc._get_malaysian_prompt("Ayam Gepuk Telur Mata")
        assert "cooked dish served plated" in p and "Set Panglima" not in p
        assert "a drink served in a glass" in svc._get_malaysian_prompt("Teh O Ice Limau")
