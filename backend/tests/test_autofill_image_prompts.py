"""
Tests for auto-fill image prompt correctness (the dfgdrfefefe salon bugs):

1. NO-TEXT SUFFIX EVERYWHERE — every AI-image prompt path (hero, item,
   gallery, portfolio/section, food pass, provider dispatchers) carries the
   "no text, no signage, no words, no lettering" suffix. The fix was
   originally applied to hero prompts only; gallery/item prompts shipped
   bare and their card titles came back baked into the images as garbled
   pseudo-text.

2. BUSINESS CLASSIFICATION — hair salon / barber / beauty (and other
   service businesses) classify as the 'services' prompt category, never
   'retail'/'generic', so a salon gets specialist-at-work imagery instead
   of coffee-bag/retail product shots.

3. BUSINESS-APPROPRIATE SUBJECTS + CARD NAMES — services gallery prompts
   make the named service-being-performed the subject, and gallery card
   names for service businesses derive from services (Potong Rambut...),
   never invented retail product language (Produk Pilihan/Barangan Popular).
"""

import pytest
from unittest.mock import AsyncMock

from app.services.ai_service import AIService
from app.services.business_types import detect_business_type


NO_TEXT_SUFFIX = "no text, no signage, no words, no lettering anywhere in the image"

RETAIL_PLACEHOLDERS = (
    "Produk Pilihan", "Koleksi Terbaru", "Tawaran Istimewa",
    "Barangan Popular", "Jualan Hangat", "Pilihan Utama",
)

SALON_DESCRIPTIONS = [
    "Salon rambut wanita di Shah Alam, potong rambut, rawatan dan pewarnaan",
    "Modern hair salon offering haircuts, colouring and keratin treatment",
    "Barbershop untuk lelaki, gunting rambut dan shaving",
    "Beauty salon kecantikan, facial, manicure dan pedicure",
]


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    monkeypatch.setenv("STABILITY_API_KEY", "test-stability-key")
    return AIService()


# ---------------------------------------------------------------------------
# 1. No-text suffix on ALL image-prompt paths
# ---------------------------------------------------------------------------

class TestNoTextSuffixEverywhere:
    ALL_CATEGORIES = ["food", "creative", "services", "retail", "generic"]

    @pytest.mark.parametrize("category", ALL_CATEGORIES)
    def test_hero_prompts_carry_suffix(self, service, category):
        prompt = service._autofill_hero_prompt(category, "hair salon")
        assert NO_TEXT_SUFFIX in prompt

    @pytest.mark.parametrize("category", ["creative", "services", "retail", "generic"])
    def test_item_prompts_carry_suffix(self, service, category):
        prompt = service._autofill_item_prompt(category, "Pewarnaan Rambut", "salon")
        assert NO_TEXT_SUFFIX in prompt

    def test_food_item_prompt_gets_suffix_via_malaysian_mapping(self, service):
        # Food items return the raw name from _autofill_item_prompt; the
        # suffix is applied by _get_malaysian_prompt inside the provider
        # dispatch — verify every branch of that mapping.
        assert NO_TEXT_SUFFIX in service._get_malaysian_prompt("nasi lemak")   # exact
        assert NO_TEXT_SUFFIX in service._get_malaysian_prompt("Nasi Lemak Special")  # fuzzy
        assert NO_TEXT_SUFFIX in service._get_malaysian_prompt("Unknown Dish 123")    # generic

    def test_suffix_helper_is_idempotent(self, service):
        once = service._with_no_text_suffix("a salon prompt")
        assert once.count("no text") == 1
        assert service._with_no_text_suffix(once).count("no text") == 1

    @pytest.mark.asyncio
    async def test_stability_nonfood_path_appends_suffix(self, service, monkeypatch):
        """Non-food prompts used to pass through _generate_stability_image
        verbatim — the dispatcher must now append the suffix."""
        captured = {}

        class _FakeResponse:
            status_code = 500
            text = "boom"

        async def _fake_post(self_client, url, **kwargs):
            captured["prompt"] = kwargs["data"]["prompt"]
            return _FakeResponse()

        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)
        await service._generate_stability_image("Pewarnaan Rambut, salon work", food=False)
        assert NO_TEXT_SUFFIX in captured["prompt"]

    @pytest.mark.asyncio
    async def test_zai_nonfood_path_appends_suffix(self, service, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        captured = {}

        async def _fake_zai(prompt):
            captured["prompt"] = prompt
            return "https://res.cloudinary.com/fake.png"

        service._generate_image_zai = AsyncMock(side_effect=_fake_zai)
        url = await service._generate_image("Rawatan Rambut, salon interior", food=False)
        assert url
        assert NO_TEXT_SUFFIX in captured["prompt"]

    @pytest.mark.asyncio
    async def test_legacy_sdxl_generate_image_appends_suffix(self, service, monkeypatch):
        """generate_image serves the get_image_prompts gallery/portfolio
        path (simple generate flow) — it must carry the suffix too."""
        captured = {}

        class _FakeResponse:
            status_code = 500

            @staticmethod
            def json():
                return {}

        async def _fake_post(self_client, url, **kwargs):
            captured["texts"] = [t["text"] for t in kwargs["json"]["text_prompts"] if t["weight"] > 0]
            return _FakeResponse()

        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)
        await service.generate_image("Hairstylist cutting hair in salon")
        assert captured["texts"], "prompt was not sent"
        assert all(NO_TEXT_SUFFIX in t for t in captured["texts"])


# ---------------------------------------------------------------------------
# 2. Salon / barber / beauty classify as services, never retail
# ---------------------------------------------------------------------------

class TestSalonClassification:
    @pytest.mark.parametrize("description", SALON_DESCRIPTIONS)
    def test_detect_business_type_is_salon(self, description):
        assert detect_business_type(description) == "salon"

    @pytest.mark.parametrize("description", SALON_DESCRIPTIONS)
    def test_autofill_category_is_services_not_retail(self, service, description):
        category = service._autofill_prompt_category(description)
        assert category == "services"
        assert category not in ("retail", "generic")

    def test_generic_service_business_is_services(self, service):
        assert (
            service._autofill_prompt_category(
                "Servis baiki aircond dan cleaning rumah di Puchong"
            )
            == "services"
        )

    def test_photography_still_creative(self, service):
        # The creative template (silhouette/venue compositions) must keep
        # priority over the generic services template for photographers.
        assert (
            service._autofill_prompt_category("Jurugambar perkahwinan profesional")
            == "creative"
        )

    def test_retail_shops_still_retail(self, service):
        assert service._autofill_prompt_category("Butik pakaian muslimah, tudung dan jubah") == "retail"


# ---------------------------------------------------------------------------
# 3. Business-appropriate subjects + gallery card names
# ---------------------------------------------------------------------------

class TestServiceSubjectsAndCardNames:
    def test_services_hero_shows_specialist_at_work(self, service):
        prompt = service._autofill_hero_prompt("services", "salon").lower()
        assert "at work with a client" in prompt
        # Never a shelf-product arrangement.
        assert "products" not in prompt
        assert "product shot" not in prompt

    def test_services_item_prompt_subject_is_the_service(self, service):
        prompt = service._autofill_item_prompt("services", "Pewarnaan Rambut", "salon")
        assert prompt.startswith("Pewarnaan Rambut")
        assert "performing the service on a client" in prompt
        assert "salon" in prompt
        # Not the retail product-shot template.
        assert "product photography" not in prompt
        assert "commercial product shot" not in prompt

    def test_salon_fallback_names_are_services_not_retail(self, service):
        names = service._fallback_service_names(SALON_DESCRIPTIONS[0], 4)
        assert len(names) == 4
        for placeholder in RETAIL_PLACEHOLDERS:
            assert placeholder not in names
        # Hairstyling language, matching what the salon actually does.
        assert "Potong Rambut" in names
        assert "Pewarnaan Rambut" in names

    def test_generic_service_fallback_names_are_service_language(self, service):
        names = service._fallback_service_names("Servis baiki aircond di Puchong", 4)
        assert len(names) == 4
        for placeholder in RETAIL_PLACEHOLDERS:
            assert placeholder not in names

    @pytest.mark.asyncio
    async def test_service_extractor_falls_back_without_api_key(self, service, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        names = await service.extract_service_names(SALON_DESCRIPTIONS[0], n=4)
        assert names == service._fallback_service_names(SALON_DESCRIPTIONS[0], 4)

    @pytest.mark.asyncio
    async def test_autofill_salon_uses_service_extractor_and_prompts(self, service, monkeypatch):
        """End-to-end through _autofill_missing_images for a salon: the
        SERVICE extractor is used (never the retail product extractor), the
        gallery prompts put the service in a salon context, and every
        prompt carries the no-text suffix."""
        from app.models.schemas import WebsiteGenerationRequest, Language

        request = WebsiteGenerationRequest(
            description=SALON_DESCRIPTIONS[0],
            language=Language.MALAY,
            business_name="Salon Ayu",
            business_type="salon",
            subdomain="salonayu",
            include_whatsapp=False,
            include_maps=False,
            include_ecommerce=False,
        )

        service.extract_service_names = AsyncMock(
            return_value=["Potong Rambut", "Pewarnaan Rambut", "Rawatan Rambut", "Solekan"]
        )
        service.extract_product_category_names = AsyncMock(
            side_effect=AssertionError("retail product extractor must not run for a salon")
        )
        service.extract_menu_item_names = AsyncMock(
            side_effect=AssertionError("menu extractor must not run for a salon")
        )

        sent_prompts = []

        async def _fake_generate(prompt, food=True, zai_phase=None):
            sent_prompts.append((prompt, food))
            return f"https://res.cloudinary.com/gen{len(sent_prompts)}.png"

        service._generate_image = AsyncMock(side_effect=_fake_generate)

        image_urls = {}
        count = await service._autofill_missing_images(request, image_urls, None)

        assert count == 5  # hero + 4 services
        service.extract_service_names.assert_awaited_once()
        # Card names are the services, not retail placeholders.
        assert image_urls["gallery1_name"] == "Potong Rambut"
        assert image_urls["gallery2_name"] == "Pewarnaan Rambut"
        # Every prompt sent to the generator is non-food, salon-appropriate,
        # and carries the no-text suffix.
        for prompt, food in sent_prompts:
            assert food is False
            assert NO_TEXT_SUFFIX in prompt
            for placeholder in RETAIL_PLACEHOLDERS:
                assert placeholder not in prompt
        item_prompts = [p for p, _ in sent_prompts[1:]]
        assert all("performing the service on a client" in p for p in item_prompts)

    @pytest.mark.asyncio
    async def test_autofill_retail_still_uses_product_extractor(self, service, monkeypatch):
        """Regression: goods-selling businesses keep the retail path."""
        from app.models.schemas import WebsiteGenerationRequest, Language

        request = WebsiteGenerationRequest(
            description="Butik pakaian muslimah, tudung, jubah dan aksesori",
            language=Language.MALAY,
            business_name="Butik Aisyah",
            business_type="clothing",
            subdomain="butikaisyah",
            include_whatsapp=False,
            include_maps=False,
            include_ecommerce=False,
        )

        service.extract_product_category_names = AsyncMock(
            return_value=["Baju Kurung", "Tudung Bawal", "Jubah", "Aksesori"]
        )
        service.extract_service_names = AsyncMock(
            side_effect=AssertionError("service extractor must not run for a boutique")
        )

        async def _fake_generate(prompt, food=True, zai_phase=None):
            return "https://res.cloudinary.com/gen.png"

        service._generate_image = AsyncMock(side_effect=_fake_generate)

        image_urls = {}
        count = await service._autofill_missing_images(request, image_urls, None)
        assert count == 5
        service.extract_product_category_names.assert_awaited_once()


# ---------------------------------------------------------------------------
# 4. Business context in EVERY auto-fill image prompt (the gogoo bug)
# ---------------------------------------------------------------------------
# A phone shop ("kedai phone & smart line", Shah Alam) generated with correct
# copy but its 4 product cards came back as a handbag, cosmetics, a cream jar
# and a mug: the retail item prompt sent ONLY the generic card title
# ("Koleksi Terbaru") — no business name, description, or type. Every image
# prompt must now carry the business context.

PHONE_SHOP_NAME = "Kedai Phone & Smart Line"
PHONE_SHOP_DESC = (
    "kedai phone & smart line, jual smartphone, gadget dan pelan smart line "
    "di Shah Alam"
)


class TestBusinessContextInPrompts:
    NON_FOOD_CATEGORIES = ["creative", "services", "retail", "generic"]

    def _ctx(self, service):
        return service._autofill_business_context(PHONE_SHOP_NAME, PHONE_SHOP_DESC)

    def test_context_snippet_contains_name_and_description(self, service):
        ctx = self._ctx(service)
        # Name check is case-insensitive: when the merchant description
        # opens with the business name, the context keeps only that copy.
        assert PHONE_SHOP_NAME.lower() in ctx.lower()
        assert "jual smartphone" in ctx

    def test_context_snippet_handles_missing_fields(self, service):
        assert service._autofill_business_context("", "") == ""
        assert service._autofill_business_context("Kedai A", "") == "Kedai A"
        assert "desc here" in service._autofill_business_context("", "desc here")

    @pytest.mark.parametrize("category", NON_FOOD_CATEGORIES)
    def test_item_prompts_carry_business_context(self, service, category):
        prompt = service._autofill_item_prompt(
            category, "Koleksi Terbaru", "phone shop", self._ctx(service)
        )
        assert PHONE_SHOP_NAME.lower() in prompt.lower()
        assert "jual smartphone" in prompt
        assert NO_TEXT_SUFFIX in prompt

    @pytest.mark.parametrize("category", ["food", "creative", "services", "retail", "generic"])
    def test_hero_prompts_carry_business_context(self, service, category):
        prompt = service._autofill_hero_prompt(category, "phone shop", self._ctx(service))
        assert PHONE_SHOP_NAME.lower() in prompt.lower()

    def test_retail_prompt_is_never_title_only(self, service):
        """The exact gogoo failure: a generic fallback title must never be
        the entire subject the image model sees."""
        prompt = service._autofill_item_prompt(
            "retail", "Koleksi Terbaru", "phone shop", self._ctx(service)
        )
        # Business type is in the template itself now, not just the title.
        assert "a phone shop product" in prompt
        assert PHONE_SHOP_NAME.lower() in prompt.lower()

    @pytest.mark.asyncio
    async def test_autofill_prompts_include_business_context_end_to_end(self, service):
        """Every prompt _autofill_missing_images sends to the image
        provider — hero AND all 4 product cards — must contain the business
        name and description, even when the card names are the generic
        retail fallbacks that caused the gogoo bug."""
        from app.models.schemas import WebsiteGenerationRequest, Language

        request = WebsiteGenerationRequest(
            description=PHONE_SHOP_DESC,
            language=Language.MALAY,
            business_name=PHONE_SHOP_NAME,
            business_type="general",
            subdomain="gogoo",
            include_whatsapp=False,
            include_maps=False,
            include_ecommerce=False,
        )

        # The generic fallback titles from _fallback_category_names — the
        # worst case that produced handbag/cosmetics/mug images.
        service.extract_product_category_names = AsyncMock(
            return_value=["Produk Pilihan", "Koleksi Terbaru",
                          "Tawaran Istimewa", "Barangan Popular"]
        )

        sent_prompts = []

        async def _fake_generate(prompt, food=True, zai_phase=None):
            sent_prompts.append(prompt)
            return f"https://res.cloudinary.com/gen{len(sent_prompts)}.png"

        service._generate_image = AsyncMock(side_effect=_fake_generate)

        image_urls = {}
        count = await service._autofill_missing_images(request, image_urls, None)

        assert count == 5  # hero + 4 cards
        assert len(sent_prompts) == 5
        for prompt in sent_prompts:
            assert PHONE_SHOP_NAME.lower() in prompt.lower(), f"business name missing: {prompt}"
            assert "jual smartphone" in prompt, f"description missing: {prompt}"
            assert NO_TEXT_SUFFIX in prompt
