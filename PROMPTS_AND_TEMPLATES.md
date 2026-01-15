# BinaApp - AI Prompts & Templates Documentation

**Generated**: 2026-01-11
**Purpose**: Complete backup of all AI prompts, templates, and Malaysian-specific configurations

---

## Table of Contents

1. [Website Generation Prompts](#website-generation-prompts)
2. [Malaysian Food Prompts](#malaysian-food-prompts)
3. [Malaysian Fashion Prompts](#malaysian-fashion-prompts)
4. [Malaysian Services Prompts](#malaysian-services-prompts)
5. [Generic Business Prompts](#generic-business-prompts)
6. [HTML Templates](#html-templates)
7. [System Messages](#system-messages)

---

## Website Generation Prompts

### Main System Prompt (DeepSeek V3)

```python
SYSTEM_PROMPT = """
You are an expert web developer specializing in creating beautiful, responsive websites for Malaysian SMEs.

Your task is to generate COMPLETE, production-ready HTML websites that are:

1. **Fully Functional & Self-Contained**
   - Single HTML file with inline CSS and JavaScript
   - No external dependencies
   - All code embedded (no separate CSS/JS files)
   - Works immediately when opened

2. **Mobile-First & Responsive**
   - Looks perfect on phones (320px and up)
   - Adapts gracefully to tablets and desktops
   - Touch-friendly buttons and navigation
   - Readable text sizes on all devices

3. **Malaysian-Optimized**
   - Color schemes appropriate for Malaysian businesses
   - Bahasa Malaysia and English bilingual support
   - Malaysian currency (RM) for pricing
   - Malaysian phone format (01X-XXX XXXX)
   - Local business sensibilities

4. **Pre-Integrated Features** (MUST INCLUDE ALL):
   - WhatsApp ordering floating button (bottom-right)
   - Shopping cart system (localStorage-based)
   - Google Maps embed (if location provided)
   - Contact form with validation
   - QR code for easy sharing
   - Social media share buttons (Facebook, WhatsApp, Twitter)
   - Smooth scroll navigation
   - Sticky header on scroll

5. **Professional Design**
   - Modern, clean aesthetic
   - Proper spacing and typography
   - High-quality placeholder images (use Unsplash)
   - Professional color palette
   - Consistent branding throughout
   - Micro-interactions and animations

6. **Accessibility**
   - Semantic HTML5 tags
   - ARIA labels where needed
   - Keyboard navigation support
   - Sufficient color contrast
   - Alt text for images

7. **SEO-Ready**
   - Proper meta tags
   - Structured heading hierarchy
   - Descriptive page title
   - Meta description
   - Open Graph tags for social sharing

8. **Performance**
   - Optimized code
   - Lazy loading for images
   - Efficient CSS (no bloat)
   - Fast initial render

IMPORTANT RULES:
- Generate ONLY the complete HTML code
- Do NOT include markdown code fences (no ```html)
- Do NOT add explanations or comments
- Start directly with <!DOCTYPE html>
- Include ALL sections requested
- Make it production-ready

Remember: This HTML must work perfectly without any modifications. The user should be able to publish it immediately.
"""
```

### User Prompt Template

```python
def generate_website_prompt(business_info):
    return f"""
Create a complete, production-ready website for:

**Business Name:** {business_info['business_name']}
**Business Type:** {business_info['business_type']}
**Description:** {business_info['description']}

**Required Sections:**
1. Header / Navigation
   - Logo/business name
   - Navigation menu (Home, About, Menu/Services, Contact)
   - Mobile hamburger menu

2. Hero Section
   - Eye-catching headline about the business
   - Brief tagline
   - Call-to-action button (Order Now / Contact Us)
   - Background image relevant to business type

3. About Section
   - Business story
   - Why choose us (3-4 key points)
   - Optional: Team photo or business photo

4. Menu/Services Section
   - For restaurants: Display sample menu items with prices (RM)
   - For services: List services offered with brief descriptions
   - Use the description provided to create realistic items
   - Include 6-8 items minimum

5. Gallery Section (optional but recommended)
   - Grid of images related to the business
   - Use high-quality Unsplash images

6. Contact Section
   - Contact form (name, email, message)
   - Business address: {business_info.get('location_address', '')}
   - Google Maps embed (if address provided)
   - WhatsApp: {business_info.get('whatsapp_number', '')}

7. Footer
   - Copyright
   - Social media links
   - Quick links
   - Business hours

**Integration Requirements:**

WhatsApp Integration:
```javascript
<a href="https://wa.me/{whatsapp_number}?text=Saya%20nak%20order"
   class="whatsapp-float" target="_blank">
  <i class="fab fa-whatsapp"></i>
</a>
```

Shopping Cart:
- localStorage-based cart
- Add to cart buttons on menu items
- Cart icon with item count in header
- Mini cart dropdown or modal
- Checkout button that sends order via WhatsApp

**Styling Guidelines:**
- Use a color scheme appropriate for {business_info['business_type']}
- Modern, clean design
- Professional fonts (Google Fonts: Poppins, Inter, or Roboto)
- Smooth animations and transitions
- Card-based layouts for content

**Technical Requirements:**
- HTML5 semantic elements
- CSS Grid and Flexbox for layout
- Vanilla JavaScript (no frameworks needed)
- FontAwesome icons (CDN)
- Fully responsive (mobile-first)

Generate the COMPLETE HTML now. Start with <!DOCTYPE html> and end with </html>.
Include EVERYTHING in a single file.
"""
```

### DeepSeek API Call Example

```python
from openai import OpenAI

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": generate_website_prompt(business_info)}
    ],
    max_tokens=16000,  # DeepSeek V3 supports long outputs
    temperature=0.7,   # Balance creativity and consistency
    stream=False
)

html_content = response.choices[0].message.content
```

### Fallback to Qwen

```python
# If DeepSeek fails, try Qwen Max
try:
    html = generate_with_deepseek(business_info)
except Exception as e:
    print(f"DeepSeek failed: {e}. Trying Qwen...")
    html = generate_with_qwen(business_info)
```

---

## Malaysian Food Prompts

These prompts are used for AI food image generation (Stability AI).

**Source File**: `backend/app/data/malaysian_prompts.py`

### Rice Dishes (Nasi)

```python
MALAYSIAN_FOOD_PROMPTS = {
    "nasi kandar": "Malaysian nasi kandar plate with fluffy white rice, yellow curry chicken, fried chicken, vegetables, and variety of colorful curries, banana leaf, authentic mamak restaurant style, food photography, professional lighting",

    "nasi lemak": "Malaysian nasi lemak with fragrant coconut rice, sambal, fried anchovies ikan bilis, peanuts, cucumber slices, hard boiled egg, wrapped in banana leaf, food photography",

    "nasi goreng": "Malaysian nasi goreng fried rice with prawns, egg, vegetables, spicy red color, served on white plate, food photography",

    "nasi goreng kampung": "Village style nasi goreng kampung with anchovies, long beans, bird eye chili, egg, traditional Malaysian fried rice, food photography",

    "nasi goreng usa": "Malaysian nasi goreng USA with sunny side up egg, chicken, sausage, vegetables, special fried rice, food photography",

    "nasi goreng pattaya": "Nasi goreng pattaya wrapped in thin egg omelette, ketchup on top, Malaysian style, food photography",

    "nasi ayam": "Malaysian chicken rice nasi ayam with steamed chicken, rice cooked in chicken broth, chili sauce, cucumber, food photography",

    "nasi biryani": "Aromatic biryani rice with saffron, spices, tender meat, fried shallots, papadam, raita, food photography",
}
```

### Noodles (Mee)

```python
{
    "mee goreng": "Malaysian mee goreng mamak style, thick yellow noodles, egg, potato, tofu puff, bean sprouts, red spicy sauce, lime wedge, food photography",

    "char kuey teow": "Penang char kuey teow, flat rice noodles wok fried with prawns, cockles, egg, bean sprouts, chives, smoky wok hei, food photography",

    "mee rebus": "Malaysian mee rebus, yellow noodles in thick spicy gravy, hard boiled egg, tofu, green chili, lime, fried shallots, food photography",

    "laksa": "Malaysian curry laksa, thick rice noodles in spicy coconut curry soup, tofu puff, prawns, cockles, bean sprouts, food photography",

    "wantan mee": "Malaysian wonton noodles with char siu BBQ pork, wontons, choy sum, dark sauce, food photography",
}
```

### Chicken Dishes (Ayam)

```python
{
    "ayam goreng": "Malaysian ayam goreng berempah, crispy fried chicken with golden turmeric coating, served on banana leaf, food photography",

    "ayam rendang": "Malaysian dry rendang ayam, tender chicken in rich caramelized coconut curry, aromatic spices, food photography",

    "ayam masak merah": "Malaysian ayam masak merah, chicken in spicy red tomato chili sauce, garnished with fried shallots, food photography",

    "ayam percik": "Grilled ayam percik with spicy coconut sauce, charred marks, Kelantan style, food photography",

    "satay ayam": "Malaysian chicken satay skewers, grilled on charcoal, served with peanut sauce, ketupat rice cake, cucumber, onion, food photography",
}
```

### Seafood (Makanan Laut)

```python
{
    "ikan bakar": "Malaysian ikan bakar grilled fish with sambal sauce, wrapped in banana leaf, charred, food photography",

    "ikan goreng": "Crispy fried whole fish ikan goreng, golden brown, served with sambal, food photography",

    "sambal udang": "Spicy sambal prawns Malaysian style, red chili paste, onions, food photography",

    "sotong goreng": "Crispy fried squid sotong goreng, golden batter, served with chili sauce, food photography",
}
```

### Roti & Bread

```python
{
    "roti canai": "Malaysian roti canai flatbread, flaky layered, served with dhal curry and sambal, food photography",

    "roti telur": "Roti telur egg flatbread, crispy outside, egg inside, served with curry, food photography",

    "roti bom": "Thick round roti bom with condensed milk, Malaysian flatbread, food photography",

    "roti tisu": "Paper thin crispy roti tissue, cone shaped, drizzled with condensed milk, food photography",
}
```

### Drinks (Minuman)

```python
{
    "teh tarik": "Malaysian teh tarik being pulled, stretched milk tea, frothy, in glass mug, food photography",

    "kopi": "Malaysian kopi coffee in traditional kopitiam cup, dark roasted, condensed milk, food photography",

    "milo": "Iced milo chocolate malt drink, Malaysian style, topped with Milo powder, food photography",

    "sirap bandung": "Pink rose syrup sirap bandung drink with milk, refreshing Malaysian drink, food photography",

    "cendol": "Malaysian cendol shaved ice dessert, green rice jelly, coconut milk, gula melaka palm sugar, red beans, food photography",
}
```

### Desserts (Kuih)

```python
{
    "kuih": "Colorful Malaysian kuih traditional cakes assortment, nyonya kuih, layer cakes, food photography",

    "ondeh ondeh": "Green pandan balls ondeh ondeh with palm sugar filling, coated in coconut, food photography",

    "apam balik": "Fluffy peanut pancake apam balik, crispy edges, peanuts, corn, butter, sugar, food photography",

    "pisang goreng": "Crispy fried banana fritters pisang goreng, golden brown, food photography",
}
```

---

## Malaysian Fashion Prompts

For fashion/clothing businesses.

```python
MALAYSIAN_FASHION_PROMPTS = {
    "baju kurung": "Elegant Malaysian baju kurung traditional dress, flowing fabric, embroidered, worn by Malay woman, fashion photography",

    "baju kurung moden": "Modern baju kurung with contemporary cut, stylish design, Malaysian fashion, fashion photography",

    "baju melayu": "Traditional baju melayu for men with songkok cap, sampin, Hari Raya attire, fashion photography",

    "kebaya": "Elegant kebaya lace blouse with sarong, nyonya peranakan style, fashion photography",

    "tudung": "Elegant hijab tudung headscarf, various styles, Malaysian Muslim fashion, fashion photography",

    "tudung bawal": "Square tudung bawal hijab, draped elegantly, Malaysian style, fashion photography",

    "songket": "Traditional songket brocade fabric with gold thread, royal Malay textile, product photography",

    "batik": "Malaysian batik fabric with traditional patterns, colorful design, product photography",
}
```

---

## Malaysian Services Prompts

For service-based businesses.

### Salon & Beauty

```python
MALAYSIAN_SERVICES_PROMPTS = {
    "salon": "Modern Malaysian hair salon interior, styling chairs, mirrors, professional equipment, interior photography",

    "barber": "Traditional barber shop with barber chair, mirrors, grooming tools, interior photography",

    "facial": "Relaxing facial treatment, spa setting, skincare service, beauty photography",

    "spa": "Luxury spa interior with massage beds, candles, zen atmosphere, interior photography",

    "manicure": "Nail manicure service, nail polish application, beauty photography",

    "makeup": "Professional makeup application, bridal or event makeup, beauty photography",

    "bridal makeup": "Malaysian bridal makeup, elegant bride, traditional or modern style, beauty photography",
}
```

### Automotive

```python
{
    "car wash": "Car being washed, foam, water spray, car wash service, photography",

    "bengkel": "Malaysian car workshop bengkel, mechanic working on car, automotive service, photography",

    "tyre shop": "Tire shop with stacks of new tyres, wheel alignment service, automotive photography",
}
```

### Food Service

```python
{
    "catering": "Malaysian catering setup, buffet spread with local dishes, event catering, food photography",

    "warung": "Traditional Malaysian warung food stall, humble eatery, local atmosphere, photography",

    "mamak": "Busy mamak restaurant at night, 24 hour eatery, Malaysian street food culture, photography",

    "kopitiam": "Traditional kopitiam coffee shop, marble tables, wooden chairs, nostalgic Malaysian cafe, interior photography",
}
```

---

## Generic Business Prompts

Fallback prompts for businesses not in specific categories.

```python
GENERIC_BUSINESS_PROMPTS = {
    "restaurant": "Elegant restaurant interior, warm lighting, dining tables, Malaysian ambiance, interior photography",

    "cafe": "Cozy cafe interior, coffee bar, comfortable seating, natural light, interior photography",

    "shop": "Modern retail shop interior, product displays, clean design, interior photography",

    "office": "Professional office interior, modern workspace, clean design, interior photography",

    "clinic": "Clean medical clinic interior, waiting area, professional healthcare setting, interior photography",

    "hotel": "Luxury hotel lobby, elegant interior, Malaysian hospitality, interior photography",
}
```

---

## Smart Prompt Generator Function

```python
def get_smart_stability_prompt(item_name: str, business_type: str = "") -> str:
    """
    Generate accurate Stability AI prompt for Malaysian items.
    Searches through all dictionaries to find best match.
    """
    item_lower = item_name.lower().strip()
    business_lower = business_type.lower().strip()

    # 1. Direct match in food prompts
    if item_lower in MALAYSIAN_FOOD_PROMPTS:
        return MALAYSIAN_FOOD_PROMPTS[item_lower]

    # 2. Direct match in fashion prompts
    if item_lower in MALAYSIAN_FASHION_PROMPTS:
        return MALAYSIAN_FASHION_PROMPTS[item_lower]

    # 3. Direct match in services prompts
    if item_lower in MALAYSIAN_SERVICES_PROMPTS:
        return MALAYSIAN_SERVICES_PROMPTS[item_lower]

    # 4. Partial match - check if item contains any key
    all_prompts = {
        **MALAYSIAN_FOOD_PROMPTS,
        **MALAYSIAN_FASHION_PROMPTS,
        **MALAYSIAN_SERVICES_PROMPTS,
        **GENERIC_BUSINESS_PROMPTS
    }

    for key, prompt in all_prompts.items():
        if key in item_lower or item_lower in key:
            return prompt

    # 5. Keyword matching
    if any(word in item_lower for word in ["nasi", "rice"]):
        return "Malaysian rice dish {item_name}, food photography, professional lighting"

    if any(word in item_lower for word in ["mee", "noodle", "mie"]):
        return "Malaysian noodles {item_name}, food photography"

    if any(word in item_lower for word in ["ayam", "chicken"]):
        return "Malaysian chicken dish {item_name}, food photography"

    # 6. Business type fallback
    if business_lower in GENERIC_BUSINESS_PROMPTS:
        return GENERIC_BUSINESS_PROMPTS[business_lower]

    # 7. Generic fallback
    return f"Professional photograph of {item_name}, high quality, commercial photography, clean background"
```

### Hero Image Prompt Generator

```python
def get_hero_prompt(business_name: str, business_type: str, description: str = "") -> str:
    """
    Generate hero image prompt for business website.
    """
    business_lower = business_type.lower()

    if "restaurant" in business_lower or "food" in business_lower:
        return f"Beautiful Malaysian restaurant exterior or interior, warm lighting, {business_name} signage concept, welcoming atmosphere, professional photography"

    if "salon" in business_lower or "beauty" in business_lower:
        return "Elegant beauty salon interior, modern design, mirrors, styling stations, professional atmosphere, interior photography"

    if "fashion" in business_lower or "boutique" in business_lower:
        return "Stylish Malaysian fashion boutique interior, clothing displays, elegant design, retail photography"

    if "cafe" in business_lower or "coffee" in business_lower:
        return "Cozy Malaysian cafe interior, coffee bar, comfortable seating, warm lighting, interior photography"

    return f"Professional business establishment, {business_type}, modern design, welcoming atmosphere, commercial photography"
```

---

## HTML Templates

### Basic Restaurant Template

```html
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{business_name}} - {{business_type}}</title>

    <!-- Meta Tags -->
    <meta name="description" content="{{meta_description}}">
    <meta name="keywords" content="Malaysian food, {{business_name}}, restaurant">

    <!-- Open Graph -->
    <meta property="og:title" content="{{business_name}}">
    <meta property="og:description" content="{{meta_description}}">
    <meta property="og:type" content="website">

    <!-- FontAwesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
        }

        /* Header */
        header {
            background: #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 5%;
            max-width: 1200px;
            margin: 0 auto;
        }

        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            color: #e74c3c;
        }

        .nav-links {
            display: flex;
            list-style: none;
            gap: 2rem;
        }

        .nav-links a {
            text-decoration: none;
            color: #333;
            transition: color 0.3s;
        }

        .nav-links a:hover {
            color: #e74c3c;
        }

        /* WhatsApp Float Button */
        .whatsapp-float {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background: #25D366;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000;
            text-decoration: none;
            transition: transform 0.3s;
        }

        .whatsapp-float:hover {
            transform: scale(1.1);
        }

        /* Responsive */
        @media (max-width: 768px) {
            .nav-links {
                display: none;
            }
        }
    </style>
</head>
<body>
    <header>
        <nav>
            <div class="logo">{{business_name}}</div>
            <ul class="nav-links">
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#menu">Menu</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </nav>
    </header>

    <!-- WhatsApp Button -->
    <a href="https://wa.me/{{whatsapp_number}}?text=Saya%20nak%20order"
       class="whatsapp-float"
       target="_blank"
       aria-label="WhatsApp Us">
        <i class="fab fa-whatsapp"></i>
    </a>

    <!-- Content will be generated by AI -->

</body>
</html>
```

---

## System Messages

Messages used in chat system and notifications.

### Order Status Messages

```python
ORDER_STATUS_MESSAGES = {
    "pending": {
        "en": "Your order has been received. Waiting for confirmation.",
        "ms": "Pesanan anda telah diterima. Menunggu pengesahan."
    },
    "confirmed": {
        "en": "Order confirmed! Preparing your food now.",
        "ms": "Pesanan disahkan! Makanan anda sedang disediakan."
    },
    "preparing": {
        "en": "Your food is being prepared.",
        "ms": "Makanan anda sedang disediakan."
    },
    "ready": {
        "en": "Your order is ready! Rider will pick up soon.",
        "ms": "Pesanan anda sudah siap! Rider akan ambil tidak lama lagi."
    },
    "picked_up": {
        "en": "Rider has picked up your order and is on the way!",
        "ms": "Rider telah ambil pesanan anda dan sedang dalam perjalanan!"
    },
    "delivering": {
        "en": "Your order is being delivered. Estimated arrival in {{minutes}} minutes.",
        "ms": "Pesanan anda sedang dihantar. Jangkaan sampai dalam {{minutes}} minit."
    },
    "delivered": {
        "en": "Order delivered successfully! Enjoy your meal! 🎉",
        "ms": "Pesanan berjaya dihantar! Selamat menjamu selera! 🎉"
    },
    "cancelled": {
        "en": "Order has been cancelled. Reason: {{reason}}",
        "ms": "Pesanan telah dibatalkan. Sebab: {{reason}}"
    }
}
```

### Welcome Messages

```python
WELCOME_MESSAGES = {
    "new_customer": {
        "en": "Hi! Thank you for ordering from {{business_name}}. How can we help you?",
        "ms": "Hai! Terima kasih kerana order dari {{business_name}}. Apa yang kami boleh bantu?"
    },
    "returning_customer": {
        "en": "Welcome back! Happy to see you again!",
        "ms": "Selamat kembali! Gembira jumpa lagi!"
    }
}
```

### Error Messages

```python
ERROR_MESSAGES = {
    "generation_failed": {
        "en": "Oops! Website generation failed. Please try again.",
        "ms": "Maaf! Gagal menjana website. Sila cuba lagi."
    },
    "payment_failed": {
        "en": "Payment failed. Please check your details and try again.",
        "ms": "Pembayaran gagal. Sila semak maklumat anda dan cuba lagi."
    },
    "order_failed": {
        "en": "Failed to place order. Please try again or contact us.",
        "ms": "Gagal buat pesanan. Sila cuba lagi atau hubungi kami."
    }
}
```

---

## Prompt Best Practices

### 1. Be Specific

❌ **Bad**: "Create a restaurant website"

✅ **Good**: "Create a modern nasi kandar restaurant website with menu section showing 8 popular dishes, WhatsApp ordering button, and Google Maps showing Penang location"

### 2. Include Context

❌ **Bad**: "Generate menu items"

✅ **Good**: "Generate 8 authentic Malaysian nasi kandar menu items with Malay names, English descriptions, and prices in RM ranging from RM6.50 to RM15.00"

### 3. Specify Style

❌ **Bad**: "Make it look nice"

✅ **Good**: "Use warm orange and yellow colors reminiscent of curry, modern card-based layout, professional food photography from Unsplash, and Poppins font for headings"

### 4. Set Constraints

✅ **Good**: "Generate complete HTML in a single file, all CSS inline, no external dependencies except FontAwesome CDN, must work on mobile phones (320px width)"

---

## Prompt Testing Checklist

When testing new prompts:

- [ ] Does it generate valid HTML?
- [ ] Does it work on mobile (320px)?
- [ ] Does it work on desktop (1920px)?
- [ ] Are all required sections included?
- [ ] Is WhatsApp button functional?
- [ ] Is cart system working?
- [ ] Are colors appropriate?
- [ ] Is text readable?
- [ ] Are images loading?
- [ ] Does it match Malaysian business style?

---

## Maintenance

### Updating Prompts

1. Test new prompts in development first
2. Compare with existing generation quality
3. A/B test with real users
4. Monitor generation success rate
5. Update based on user feedback

### Adding New Food Items

```python
# 1. Add to malaysian_prompts.py
"nasi item baru": "Detailed English description for Stability AI, food photography, professional lighting"

# 2. Test image generation
from stability_ai import generate_image
image_url = generate_image("nasi item baru")

# 3. Verify quality
# 4. Deploy to production
```

---

**Last Updated**: 2026-01-11
**Total Prompts**: 80+ food items, 10+ fashion items, 15+ services
**Languages**: Bahasa Malaysia + English bilingual support
