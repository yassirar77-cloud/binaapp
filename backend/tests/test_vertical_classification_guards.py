"""Guard tests for vertical classification (the "kopi bug").

A hair salon was published with a hero image of iced drinks. Root cause: the
salon's ambience copy said customers like to "duduk lama, minum kopi".
`_is_food_business` was a bare any() over a 40-term food keyword list and ran
BEFORE the comparative scorer, so that single word classified the whole site
as a food business, then as the 'drinks' sub-type, and selected a beverage
hero prompt. The merchant's own hero description could not correct it: no
code path carried a merchant prompt to the image provider.

Each test below is a business that mentions food or drink IN PASSING while
plainly being something else, plus regressions proving the core F&B verticals
still classify correctly. These are the cases that must never regress.
"""
import pytest

from app.services.ai_service import AIService
from app.services.business_types import normalize_business_type


@pytest.fixture
def service():
    return AIService.__new__(AIService)


# --- descriptions -----------------------------------------------------------

SALON_KOPI = """Nadira Hair Studio ialah salon rambut & spa kepala untuk wanita di Seksyen 13,
Shah Alam. Kami khusus dalam colouring dan hair treatment - balayage, korean perm, keratin
smoothing, dan scalp spa guna produk Olaplex dan Kerastase. Semua stylist kami trained dan
salon ini muslimah-friendly. Vibe salon: tenang, gelap, macam lounge. Pelanggan datang sebab
suka duduk lama, minum kopi, dan tak rasa rushed. Semua booking melalui WhatsApp."""

GYM_SMOOTHIE = """FitZone Gym Shah Alam - pusat kecergasan dengan peralatan moden, kelas HIIT
dan yoga. Personal trainer bertauliah untuk latihan individu. Ada juice bar dan protein
smoothie selepas workout. Keahlian bulanan dan tahunan."""

PHOTOGRAPHER_CATERING = """Studio Amir - jurugambar perkahwinan dan photography untuk majlis di
Selangor. Kami cover wedding, engagement dan portrait session. Pakej termasuk album dan
editing. Kami bekerjasama dengan vendor catering dan kek kahwin untuk majlis penuh."""

COWORKING_KOPI = """RuangKerja - co-working space di Petaling Jaya untuk freelancer dan startup.
Sewa meja harian atau bulanan, bilik meeting, internet laju. Ada kopi percuma sepanjang hari.
Perkhidmatan printing dan alamat perniagaan berdaftar juga disediakan."""

MAMAK = """Restoran Nasi Kandar Pak Din - kedai makan mamak di Penang sejak 1985. Kami hidangkan
nasi kandar, ayam goreng, ikan bakar, roti canai dan teh tarik. Masakan authentic Malaysia.
Buka 24 jam. Ramai pelanggan datang untuk makanan tengah hari."""

BAKERY = """Sweet Crumbs Bakery - kedai kek dan pastri di Bangi. Kami buat kek harijadi, kek
kahwin, cupcakes, brownies dan cheesecake. Fondant dan buttercream design mengikut tempahan."""

DRINKS_STALL = """Kedai Kopi Pak Mat - gerai minuman di Klang. Kami jual kopi, teh tarik, milo
ais, jus buah segar dan smoothie. Bungkus atau minum di sini."""


class TestIncidentalFoodWordsDoNotFlipVertical:
    """The exact reported bug, plus its siblings."""

    def test_salon_mentioning_kopi_is_not_food(self, service):
        assert service._is_food_business(SALON_KOPI) is False
        assert service._autofill_prompt_category(SALON_KOPI) == "services"

    def test_salon_hero_prompt_has_no_beverage_language(self, service):
        category = service._autofill_prompt_category(SALON_KOPI)
        prompt = service._autofill_hero_prompt(category, "salon", "Nadira Hair Studio")
        lowered = prompt.lower()
        for banned in ("drink", "beverage", "glasses", "ice", "garnish", "dish", "food"):
            assert banned not in lowered, f"{banned!r} leaked into a salon hero prompt: {prompt}"

    def test_gym_with_juice_bar_is_not_food(self, service):
        assert service._is_food_business(GYM_SMOOTHIE) is False
        assert service._autofill_prompt_category(GYM_SMOOTHIE) == "services"

    def test_photographer_with_catering_is_creative(self, service):
        assert service._is_food_business(PHOTOGRAPHER_CATERING) is False
        assert service._autofill_prompt_category(PHOTOGRAPHER_CATERING) == "creative"

    def test_coworking_with_free_coffee_is_not_food(self, service):
        assert service._is_food_business(COWORKING_KOPI) is False
        assert service._autofill_prompt_category(COWORKING_KOPI) == "services"


class TestCoreFnbVerticalsStillWork:
    """The fix must not be bought by breaking the primary vertical."""

    def test_mamak_is_food_general_subtype(self, service):
        assert service._is_food_business(MAMAK) is True
        assert service._autofill_prompt_category(MAMAK) == "food"
        assert service._food_subtype(MAMAK) == "general"

    def test_bakery_is_food_bakery_subtype(self, service):
        assert service._is_food_business(BAKERY) is True
        assert service._autofill_prompt_category(BAKERY) == "food"
        assert service._food_subtype(BAKERY) == "bakery"

    def test_drinks_stall_is_food_drinks_subtype(self, service):
        assert service._is_food_business(DRINKS_STALL) is True
        assert service._autofill_prompt_category(DRINKS_STALL) == "food"
        assert service._food_subtype(DRINKS_STALL) == "drinks"

    def test_mamak_hero_prompt_is_still_food(self, service):
        prompt = service._autofill_hero_prompt("food", "restaurant", "Pak Din", food_subtype="general")
        assert "food photography" in prompt.lower()


class TestExplicitSelectionIsAuthoritative:
    """An explicit pick outranks anything the description says."""

    def test_explicit_salon_beats_a_description_full_of_food(self, service):
        assert service._autofill_prompt_category(MAMAK, "salon") == "services"

    def test_explicit_food_beats_a_salon_description(self, service):
        assert service._autofill_prompt_category(SALON_KOPI, "food") == "food"

    def test_explicit_general_defers_to_the_classifier(self, service):
        # "Lain-lain" is the merchant saying "none of these fit, you figure
        # it out" — an absence of an answer. It must behave exactly like
        # 'auto' and let the scorer decide, including for food. This market
        # is F&B-heavy: a caterer or home baker picking "lain-lain" over
        # "Restoran" is the common case, so defaulting them to retail would
        # be choosing the more frequent failure.
        assert service._autofill_prompt_category(MAMAK, "general") == "food"
        assert service._autofill_prompt_category(MAMAK, "general") == \
            service._autofill_prompt_category(MAMAK, "auto")

    def test_explicit_general_with_no_signal_still_lands_on_retail(self, service):
        assert service._autofill_prompt_category("Sebuah perniagaan kecil.", "general") == "retail"

    def test_other_explicit_picks_stay_authoritative(self, service):
        # Only 'general' defers. A real pick is never overruled by prose.
        assert service._autofill_prompt_category(MAMAK, "salon") == "services"
        assert service._autofill_prompt_category(MAMAK, "clothing") == "retail"
        assert service._autofill_prompt_category(SALON_KOPI, "food") == "food"

    @pytest.mark.parametrize("picked,expected", [
        ("food", "food"), ("bakery", "food"), ("salon", "services"),
        ("services", "services"), ("clothing", "retail"), ("general", "retail"),
    ])
    def test_every_picker_value_maps_to_a_category(self, service, picked, expected):
        assert service._autofill_prompt_category("Sebuah perniagaan.", picked) == expected

    def test_auto_and_placeholders_mean_no_explicit_pick(self):
        for value in ("auto", "", "business", None, "unknown-vertical"):
            assert normalize_business_type(value) is None
        assert normalize_business_type("Salon") == "salon"
        assert normalize_business_type("lain-lain") == "general"


class TestMerchantHeroPromptOverrides:
    """A merchant-supplied hero prompt must reach the provider verbatim."""

    MERCHANT = "dark luxury hair salon interior, warm gold lighting, empty styling chair, cinematic"

    def test_merchant_prompt_replaces_the_template(self, service):
        prompt = service._autofill_hero_prompt(
            "services", "salon", "Nadira", merchant_prompt=self.MERCHANT
        )
        assert prompt.startswith(self.MERCHANT)

    def test_merchant_prompt_overrides_even_a_food_category(self, service):
        # Belt and braces: even if classification were still wrong, the
        # merchant's own words must win.
        prompt = service._autofill_hero_prompt(
            "food", "restaurant", "Nadira", food_subtype="drinks",
            merchant_prompt=self.MERCHANT,
        )
        assert prompt.startswith(self.MERCHANT)
        assert "beverage" not in prompt.lower()

    def test_blank_merchant_prompt_falls_back_to_the_template(self, service):
        for blank in (None, "", "   "):
            prompt = service._autofill_hero_prompt(
                "services", "salon", "Nadira", merchant_prompt=blank
            )
            assert "professional at work with a client" in prompt

    def test_merchant_prompt_still_forbids_lettering(self, service):
        prompt = service._autofill_hero_prompt(
            "services", "salon", "Nadira", merchant_prompt=self.MERCHANT
        )
        assert "no text" in prompt.lower()
