"""
Template Service
Handles website type detection and feature injection
"""

from typing import List, Dict, Tuple
from loguru import logger
import re
import json

from app.services.business_types import (
    detect_business_type,
    get_business_config,
    get_categories_for_business_type,
    detect_item_category,
    generate_category_buttons_html,
    get_delivery_button_label,
    get_order_config,
)
from app.services.menu_validator import log_menu_flow


class TemplateService:
    """Service for website template detection and feature injection"""

    # Keywords for website type detection
    WEBSITE_TYPES = {
        "restaurant": [
            "restoran", "restaurant", "cafe", "kedai makan", "makanan", "food",
            "menu", "hidangan", "nasi", "mamak", "warung", "gerai", "stall",
            "kopi", "minuman", "beverages", "tomyam", "goreng", "ayam"
        ],
        "booking": [
            "salon", "spa", "temujanji", "appointment", "booking", "tempahan",
            "clinic", "klinik", "doctor", "doktor", "studio", "gunting rambut",
            "barber", "workshop", "class", "kelas", "training", "latihan"
        ],
        "portfolio": [
            "portfolio", "photographer", "jurugambar", "designer", "artist",
            "freelancer", "creative", "works", "karya", "gallery", "galeri",
            "model", "videographer", "graphic", "architecture", "arkitek"
        ],
        "shop": [
            "kedai", "shop", "store", "toko", "butik", "boutique", "pakaian",
            "baju", "clothes", "fashion", "tudung", "hijab", "kasut", "shoes",
            "aksesori", "accessories", "produk", "products", "jualan", "jual"
        ],
        "general": []  # Fallback
    }

    # Keywords for feature detection
    FEATURE_KEYWORDS = {
        "whatsapp": [
            "whatsapp", "wa", "phone", "telefon", "hubungi", "contact",
            "order", "tempah", "call", "message", "chat"
        ],
        "cart": [
            "menu", "produk", "products", "jualan", "jual", "beli", "buy",
            "cart", "bakul", "order", "tempah", "harga", "price", "rm"
        ],
        "maps": [
            "address", "alamat", "location", "lokasi", "maps", "peta",
            "direction", "arah", "navigate", "tempat", "area", "cawangan"
        ],
        "booking": [
            "booking", "tempahan", "appointment", "temujanji", "reserve",
            "schedule", "jadual", "slot", "available", "tersedia"
        ],
        "contact": [
            "contact", "hubungi", "email", "form", "borang", "inquiry",
            "pertanyaan", "message", "mesej", "feedback", "maklumbalas"
        ]
    }

    def detect_website_type(self, description: str) -> str:
        """
        Detect website type based on description
        Returns: restaurant, booking, portfolio, shop, or general
        """
        description_lower = description.lower()

        # Count matches for each type
        type_scores = {}
        for website_type, keywords in self.WEBSITE_TYPES.items():
            if website_type == "general":
                continue

            score = sum(1 for keyword in keywords if keyword in description_lower)
            type_scores[website_type] = score

        # Get type with highest score
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:
                logger.info(f"Detected website type: {best_type[0]} (score: {best_type[1]})")
                return best_type[0]

        logger.info("No specific type detected, using: general")
        return "general"

    def detect_features(self, description: str) -> List[str]:
        """
        Detect required features based on description
        Returns: List of features ["whatsapp", "cart", "maps", "booking", "contact"]
        """
        description_lower = description.lower()
        detected_features = []

        for feature, keywords in self.FEATURE_KEYWORDS.items():
            # Check if any keyword matches
            if any(keyword in description_lower for keyword in keywords):
                detected_features.append(feature)

        # Always include contact form
        if "contact" not in detected_features:
            detected_features.append("contact")

        logger.info(f"Detected features: {detected_features}")
        return detected_features

    def inject_whatsapp_button(
        self,
        html: str,
        phone_number: str,
        default_message: str = "Hi, I'm interested in your services"
    ) -> str:
        """
        Inject WhatsApp floating button into HTML
        """
        # Clean phone number
        phone_clean = re.sub(r'[^\d+]', '', phone_number)
        if not phone_clean.startswith('+'):
            # Assume Malaysian number if no country code
            if phone_clean.startswith('60'):
                phone_clean = '+' + phone_clean
            elif phone_clean.startswith('0'):
                phone_clean = '+6' + phone_clean
            else:
                phone_clean = '+60' + phone_clean

        whatsapp_html = f"""
<!-- WhatsApp Floating Button -->
<a href="https://wa.me/{phone_clean}?text={default_message.replace(' ', '%20')}"
   id="whatsapp-button"
   target="_blank"
   rel="noopener"
   style="position:fixed;bottom:20px;right:20px;background:#25D366;color:white;
          width:60px;height:60px;border-radius:50%;display:flex;align-items:center;
          justify-content:center;font-size:30px;z-index:1000;text-decoration:none;
          box-shadow:0 4px 12px rgba(37,211,102,0.4);transition:all 0.3s ease;
          animation:pulse 2s infinite;">
  <svg viewBox="0 0 24 24" width="32" height="32" fill="white">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.890-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
  </svg>
</a>
<style>
@keyframes pulse {{
  0%, 100% {{ transform: scale(1); }}
  50% {{ transform: scale(1.05); }}
}}
#whatsapp-button:hover {{
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(37,211,102,0.6);
}}
</style>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", whatsapp_html + "\n</body>")
        else:
            html += whatsapp_html

        return html

    def inject_google_maps(
        self,
        html: str,
        address: str
    ) -> str:
        """
        Inject Google Maps embed into HTML
        """
        # Encode address for URL
        address_encoded = address.replace(' ', '+')

        maps_html = f"""
<!-- Google Maps Section -->
<section id="location" style="padding:60px 20px;background:#f9fafb;">
  <div style="max-width:1200px;margin:0 auto;">
    <h2 style="text-align:center;font-size:2.5rem;margin-bottom:1rem;color:#1f2937;">📍 Our Location</h2>
    <p style="text-align:center;color:#6b7280;margin-bottom:2rem;">{address}</p>
    <div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.1);">
      <iframe
        src="https://www.google.com/maps?q={address_encoded}&output=embed"
        width="100%"
        height="100%"
        style="position:absolute;top:0;left:0;border:0;"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade">
      </iframe>
    </div>
  </div>
</section>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", maps_html + "\n</body>")
        else:
            html += maps_html

        return html

    def inject_shopping_cart(self, html: str) -> str:
        """
        Inject shopping cart functionality into HTML
        """
        cart_js = """
<!-- Shopping Cart System -->
<div id="cart-icon" style="position:fixed;top:20px;right:20px;background:#3b82f6;color:white;
     width:50px;height:50px;border-radius:50%;display:flex;align-items:center;
     justify-content:center;cursor:pointer;z-index:999;box-shadow:0 4px 12px rgba(59,130,246,0.4);"
     onclick="toggleCart()">
  🛒
  <span id="cart-count" style="position:absolute;top:-5px;right:-5px;background:#ef4444;
        width:24px;height:24px;border-radius:50%;display:flex;align-items:center;
        justify-content:center;font-size:12px;font-weight:bold;">0</span>
</div>

<div id="cart-modal" style="display:none;position:fixed;top:0;right:0;width:100%;max-width:400px;
     height:100vh;background:white;box-shadow:-4px 0 20px rgba(0,0,0,0.2);z-index:1000;
     overflow-y:auto;padding:20px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h3 style="margin:0;font-size:1.5rem;">🛒 Cart</h3>
    <button onclick="toggleCart()" style="background:none;border:none;font-size:1.5rem;cursor:pointer;">✕</button>
  </div>
  <div id="cart-items"></div>
  <div style="margin-top:20px;padding-top:20px;border-top:2px solid #e5e7eb;">
    <div style="display:flex;justify-content:space-between;font-size:1.2rem;font-weight:bold;margin-bottom:15px;">
      <span>Total:</span>
      <span id="cart-total">RM 0.00</span>
    </div>
    <button onclick="checkout()" style="width:100%;padding:15px;background:#25D366;color:white;
            border:none;border-radius:8px;font-size:1.1rem;font-weight:bold;cursor:pointer;">
      Checkout via WhatsApp
    </button>
  </div>
</div>

<script>
let cart = JSON.parse(localStorage.getItem('cart')) || [];

function addToCart(name, price) {
  const item = { name, price, quantity: 1, id: Date.now() };
  cart.push(item);
  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartUI();

  // Show notification
  const notification = document.createElement('div');
  notification.textContent = '✓ Added to cart';
  notification.style.cssText = 'position:fixed;top:80px;right:20px;background:#10b981;color:white;padding:15px 25px;border-radius:8px;z-index:1001;animation:slideIn 0.3s ease';
  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 2000);
}

function removeFromCart(id) {
  cart = cart.filter(item => item.id !== id);
  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartUI();
}

function updateCartUI() {
  const cartCount = document.getElementById('cart-count');
  const cartItems = document.getElementById('cart-items');
  const cartTotal = document.getElementById('cart-total');

  cartCount.textContent = cart.length;

  if (cart.length === 0) {
    cartItems.innerHTML = '<p style="text-align:center;color:#9ca3af;padding:40px 0;">Cart is empty</p>';
    cartTotal.textContent = 'RM 0.00';
    return;
  }

  let total = 0;
  cartItems.innerHTML = cart.map(item => {
    total += item.price;
    return `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:15px;
           background:#f9fafb;border-radius:8px;margin-bottom:10px;">
        <div>
          <div style="font-weight:600;">${item.name}</div>
          <div style="color:#6b7280;">RM ${item.price.toFixed(2)}</div>
        </div>
        <button onclick="removeFromCart(${item.id})"
                style="background:#ef4444;color:white;border:none;padding:5px 10px;
                border-radius:6px;cursor:pointer;">Remove</button>
      </div>
    `;
  }).join('');

  cartTotal.textContent = `RM ${total.toFixed(2)}`;
}

function toggleCart() {
  const modal = document.getElementById('cart-modal');
  modal.style.display = modal.style.display === 'none' ? 'block' : 'none';
}

function checkout() {
  if (cart.length === 0) {
    alert('Your cart is empty!');
    return;
  }

  const orderText = cart.map(item => `${item.name} - RM ${item.price.toFixed(2)}`).join('%0A');
  const total = cart.reduce((sum, item) => sum + item.price, 0);
  const message = `Hi! I would like to order:%0A%0A${orderText}%0A%0ATotal: RM ${total.toFixed(2)}`;

  // Get WhatsApp number from button if exists
  const waButton = document.querySelector('a[href*="wa.me"]');
  const phoneNumber = waButton ? waButton.href.match(/wa.me\/([^?]+)/)[1] : '60123456789';

  window.open(`https://wa.me/${phoneNumber}?text=${message}`, '_blank');
}

// Initialize
updateCartUI();
</script>
<style>
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
</style>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", cart_js + "\n</body>")
        else:
            html += cart_js

        return html

    def inject_contact_form(self, html: str, email: str = "") -> str:
        """
        Inject contact form into HTML
        """
        form_html = f"""
<!-- Contact Form Section -->
<section id="contact" style="padding:60px 20px;background:#ffffff;">
  <div style="max-width:600px;margin:0 auto;">
    <h2 style="text-align:center;font-size:2.5rem;margin-bottom:1rem;color:#1f2937;">📬 Contact Us</h2>
    <p style="text-align:center;color:#6b7280;margin-bottom:2rem;">Get in touch with us for inquiries</p>

    <form id="contact-form" onsubmit="return handleContactSubmit(event)"
          style="background:#f9fafb;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.05);">
      <div style="margin-bottom:20px;">
        <label style="display:block;margin-bottom:8px;font-weight:600;color:#374151;">Name</label>
        <input type="text" name="name" required
               style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;font-size:1rem;">
      </div>

      <div style="margin-bottom:20px;">
        <label style="display:block;margin-bottom:8px;font-weight:600;color:#374151;">Email</label>
        <input type="email" name="email" required
               style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;font-size:1rem;">
      </div>

      <div style="margin-bottom:20px;">
        <label style="display:block;margin-bottom:8px;font-weight:600;color:#374151;">Phone</label>
        <input type="tel" name="phone"
               style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;font-size:1rem;">
      </div>

      <div style="margin-bottom:20px;">
        <label style="display:block;margin-bottom:8px;font-weight:600;color:#374151;">Message</label>
        <textarea name="message" rows="5" required
                  style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:8px;font-size:1rem;resize:vertical;"></textarea>
      </div>

      <button type="submit"
              style="width:100%;padding:15px;background:linear-gradient(135deg,#3b82f6,#2563eb);
              color:white;border:none;border-radius:8px;font-size:1.1rem;font-weight:bold;cursor:pointer;">
        Send Message
      </button>
    </form>
  </div>
</section>

<script>
function handleContactSubmit(e) {{
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const name = formData.get('name');
  const email = formData.get('email');
  const phone = formData.get('phone');
  const message = formData.get('message');

  // Send via WhatsApp if available
  const waButton = document.querySelector('a[href*="wa.me"]');
  if (waButton) {{
    const phoneNumber = waButton.href.match(/wa.me\/([^?]+)/)[1];
    const text = `Contact Form Submission:%0A%0AName: ${{name}}%0AEmail: ${{email}}%0APhone: ${{phone}}%0A%0AMessage:%0A${{message}}`;
    window.open(`https://wa.me/${{phoneNumber}}?text=${{text}}`, '_blank');
  }} else {{
    // Fallback to mailto
    const mailto = `mailto:{email}?subject=Contact from ${{name}}&body=${{message}}%0A%0AFrom: ${{name}}%0AEmail: ${{email}}%0APhone: ${{phone}}`;
    window.location.href = mailto;
  }}

  form.reset();
  alert('Thank you! We will get back to you soon.');
  return false;
}}
</script>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", form_html + "\n</body>")
        else:
            html += form_html

        return html

    def inject_qr_code(self, html: str, url: str) -> str:
        """
        Inject QR code for the website
        """
        qr_html = f"""
<!-- QR Code Section -->
<div style="text-align:center;padding:40px 20px;background:#f9fafb;">
  <h3 style="font-size:1.5rem;margin-bottom:1rem;color:#1f2937;">📱 Scan to Visit</h3>
  <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
       alt="QR Code"
       style="border:4px solid white;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
</div>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", qr_html + "\n</body>")
        else:
            html += qr_html

        return html

    def inject_delivery_section(
        self,
        html: str,
        delivery_data: Dict,
        phone_number: str
    ) -> str:
        """
        Inject delivery section with order form into HTML
        """
        delivery_area = delivery_data.get('area', 'Dalam 5km')
        delivery_fee = delivery_data.get('fee', 'RM5')
        minimum_order = delivery_data.get('minimum', 'RM20')
        delivery_hours = delivery_data.get('hours', '11am-9pm')

        # Clean phone number for WhatsApp link
        phone_clean = re.sub(r'[^\d+]', '', phone_number)
        if not phone_clean.startswith('+'):
            if phone_clean.startswith('60'):
                phone_clean = '+' + phone_clean
            elif phone_clean.startswith('0'):
                phone_clean = '+6' + phone_clean
            else:
                phone_clean = '+60' + phone_clean

        delivery_html = f"""
<!-- Delivery Section -->
<section id="delivery" style="padding:60px 20px;background:linear-gradient(135deg, #fff5eb 0%, #ffe4cc 100%);">
  <div style="max-width:1200px;margin:0 auto;">
    <div style="text-align:center;margin-bottom:40px;">
      <h2 style="font-size:2.5rem;font-weight:bold;margin-bottom:16px;color:#c2410c;">🛵 Delivery Sendiri</h2>
      <p style="font-size:1.25rem;color:#7c2d12;margin-bottom:32px;">Kami hantar terus ke rumah anda!</p>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;max-width:800px;margin:0 auto 32px;">
        <div style="background:white;padding:24px;border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
          <div style="font-size:2rem;margin-bottom:8px;">📍</div>
          <div style="font-weight:bold;color:#1f2937;">Kawasan</div>
          <div style="color:#6b7280;margin-top:4px;">{delivery_area}</div>
        </div>
        <div style="background:white;padding:24px;border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
          <div style="font-size:2rem;margin-bottom:8px;">💰</div>
          <div style="font-weight:bold;color:#1f2937;">Caj Delivery</div>
          <div style="color:#6b7280;margin-top:4px;">{delivery_fee}</div>
        </div>
        <div style="background:white;padding:24px;border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
          <div style="font-size:2rem;margin-bottom:8px;">🛒</div>
          <div style="font-weight:bold;color:#1f2937;">Minimum</div>
          <div style="color:#6b7280;margin-top:4px;">{minimum_order}</div>
        </div>
        <div style="background:white;padding:24px;border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
          <div style="font-size:2rem;margin-bottom:8px;">🕐</div>
          <div style="font-weight:bold;color:#1f2937;">Waktu</div>
          <div style="color:#6b7280;margin-top:4px;">{delivery_hours}</div>
        </div>
      </div>

      <a href="https://wa.me/{phone_clean}?text=Saya%20nak%20order%20delivery"
         style="display:inline-flex;align-items:center;background:#ea580c;color:white;padding:16px 32px;
                border-radius:9999px;font-weight:bold;font-size:1.125rem;text-decoration:none;
                box-shadow:0 10px 25px rgba(234,88,12,0.4);transition:all 0.3s ease;"
         onmouseover="this.style.background='#c2410c';this.style.transform='scale(1.05)';this.style.boxShadow='0 12px 30px rgba(234,88,12,0.5)';"
         onmouseout="this.style.background='#ea580c';this.style.transform='scale(1)';this.style.boxShadow='0 10px 25px rgba(234,88,12,0.4)';">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="white" style="margin-right:8px;">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.890-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
        </svg>
        Order Delivery Sekarang
      </a>
    </div>
  </div>
</section>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", delivery_html + "\n</body>")
        else:
            html += delivery_html

        return html

    def create_delivery_order_page(
        self,
        business_name: str,
        menu_items: List[Dict],
        delivery_zones: List[Dict],
        phone_number: str,
        business_description: str = ""
    ) -> str:
        """
        NEW METHOD - Creates a complete standalone delivery order page

        This is the CRITICAL FIX for Problem #1: Missing Delivery Page
        Creates a SEPARATE page (not just a section) with:
        - Delivery zone selection cards
        - Full menu grid with AI-generated images
        - Shopping cart (sidebar on desktop, floating button on mobile)
        - WhatsApp checkout integration

        Args:
            business_name: Name of the business
            menu_items: List of menu items with {'name', 'price', 'description', 'image_url', 'category'}
            delivery_zones: List of zones with {'name', 'location', 'delivery_time', 'fee'}
            phone_number: WhatsApp phone number
            business_description: Optional business description

        Returns:
            Complete HTML for standalone delivery order page
        """
        # Clean phone number
        phone_clean = re.sub(r'[^\d+]', '', phone_number)
        if not phone_clean.startswith('+'):
            if phone_clean.startswith('60'):
                phone_clean = '+' + phone_clean
            elif phone_clean.startswith('0'):
                phone_clean = '+6' + phone_clean
            else:
                phone_clean = '+60' + phone_clean

        # Prepare menu items JSON
        menu_json = json.dumps(menu_items)
        zones_json = json.dumps(delivery_zones)

        # Build zone cards HTML
        zone_cards_html = ""
        for zone in delivery_zones:
            zone_cards_html += f"""
        <div class="zone-card" onclick="selectZone('{zone['name']}', '{zone['fee']}')">
          <div class="zone-icon">📍</div>
          <h3>{zone['name']}</h3>
          <div class="zone-details">
            <div>🕐 {zone.get('delivery_time', '30-45 min')}</div>
            <div>💰 {zone['fee']}</div>
          </div>
        </div>
"""

        # Build menu items HTML by category
        categories = {}
        for item in menu_items:
            cat = item.get('category', 'Menu')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        menu_html = ""
        for category, items in categories.items():
            menu_html += f"""
      <div class="category-section">
        <h2 class="category-title">{category}</h2>
        <div class="menu-grid">
"""
            for item in items:
                img_url = item.get('image_url', 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80')
                menu_html += f"""
          <div class="menu-card">
            <img src="{img_url}" alt="{item['name']}" class="menu-image">
            <div class="menu-content">
              <h3>{item['name']}</h3>
              <p class="menu-desc">{item.get('description', '')}</p>
              <div class="menu-footer">
                <span class="price">{item['price']}</span>
                <button class="add-btn" onclick="addToCart('{item['name']}', '{item['price']}', '{img_url}')">
                  <svg width="20" height="20" fill="white" viewBox="0 0 20 20">
                    <path d="M10 5v10M5 10h10" stroke="white" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                  Tambah
                </button>
              </div>
            </div>
          </div>
"""
            menu_html += """
        </div>
      </div>
"""

        # Complete HTML
        html = f"""<!DOCTYPE html>
<html lang="ms">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Order Delivery - {business_name}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; }}

    /* Header */
    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .header-content {{ max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
    .back-btn {{ background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; }}
    .back-btn:hover {{ background: rgba(255,255,255,0.3); }}

    /* Zone Selection */
    .zone-section {{ max-width: 1400px; margin: 40px auto; padding: 0 20px; }}
    .zone-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 24px; }}
    .zone-card {{ background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); cursor: pointer; transition: all 0.3s; border: 3px solid transparent; }}
    .zone-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }}
    .zone-card.selected {{ border-color: #25D366; background: #f0fdf4; }}
    .zone-icon {{ font-size: 3rem; text-align: center; margin-bottom: 12px; }}
    .zone-card h3 {{ text-align: center; margin-bottom: 12px; color: #1f2937; }}
    .zone-details {{ display: flex; justify-content: space-around; color: #6b7280; font-size: 0.9rem; }}

    /* Menu */
    .menu-section {{ max-width: 1400px; margin: 40px auto; padding: 0 20px; }}
    .category-section {{ margin-bottom: 48px; }}
    .category-title {{ font-size: 2rem; margin-bottom: 24px; color: #1f2937; }}
    .menu-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }}
    .menu-card {{ background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.3s; }}
    .menu-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }}
    .menu-image {{ width: 100%; height: 200px; object-fit: cover; }}
    .menu-content {{ padding: 20px; }}
    .menu-card h3 {{ font-size: 1.25rem; margin-bottom: 8px; color: #1f2937; }}
    .menu-desc {{ color: #6b7280; font-size: 0.9rem; margin-bottom: 16px; line-height: 1.5; }}
    .menu-footer {{ display: flex; justify-content: space-between; align-items: center; }}
    .price {{ font-size: 1.5rem; font-weight: bold; color: #667eea; }}
    .add-btn {{ background: #25D366; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-weight: bold; }}
    .add-btn:hover {{ background: #1fa855; }}

    /* Cart Sidebar (Desktop) */
    .cart-sidebar {{ position: fixed; right: 0; top: 0; width: 400px; height: 100vh; background: white; box-shadow: -4px 0 24px rgba(0,0,0,0.1); transform: translateX(100%); transition: transform 0.3s; z-index: 200; display: flex; flex-direction: column; }}
    .cart-sidebar.open {{ transform: translateX(0); }}
    .cart-header {{ padding: 24px; background: #667eea; color: white; display: flex; justify-content: space-between; align-items: center; }}
    .cart-close {{ background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; }}
    .cart-items {{ flex: 1; overflow-y: auto; padding: 20px; }}
    .cart-item {{ display: flex; gap: 12px; padding: 16px; background: #f9fafb; border-radius: 12px; margin-bottom: 12px; }}
    .cart-item-img {{ width: 60px; height: 60px; border-radius: 8px; object-fit: cover; }}
    .cart-item-details {{ flex: 1; }}
    .cart-item-name {{ font-weight: bold; margin-bottom: 4px; }}
    .cart-item-price {{ color: #667eea; }}
    .cart-remove {{ background: #ef4444; color: white; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }}
    .cart-footer {{ padding: 24px; border-top: 2px solid #e5e7eb; }}
    .cart-total {{ display: flex; justify-content: space-between; font-size: 1.5rem; font-weight: bold; margin-bottom: 16px; }}
    .checkout-btn {{ width: 100%; background: #25D366; color: white; border: none; padding: 16px; border-radius: 12px; font-size: 1.1rem; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; }}
    .checkout-btn:hover {{ background: #1fa855; }}

    /* Cart Button (Mobile) */
    .cart-fab {{ display: none; position: fixed; bottom: 20px; right: 20px; width: 64px; height: 64px; background: #667eea; color: white; border-radius: 50%; border: none; box-shadow: 0 8px 24px rgba(102,126,234,0.4); cursor: pointer; z-index: 150; align-items: center; justify-content: center; font-size: 1.5rem; }}
    .cart-count {{ position: absolute; top: -8px; right: -8px; background: #ef4444; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: bold; }}

    @media (max-width: 768px) {{
      .cart-sidebar {{ width: 100%; }}
      .cart-fab {{ display: flex; }}
      .header-content {{ flex-direction: column; gap: 12px; }}
    }}
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div class="header-content">
      <h1>🛵 {business_name} - Delivery</h1>
      <a href="/" class="back-btn">← Kembali</a>
    </div>
  </div>

  <!-- Zone Selection -->
  <div class="zone-section">
    <h2 style="font-size: 2rem; color: #1f2937;">Pilih Kawasan Delivery</h2>
    <div class="zone-grid">
{zone_cards_html}
    </div>
  </div>

  <!-- Menu -->
  <div class="menu-section" id="menu-section">
    <h2 style="font-size: 2.5rem; color: #1f2937; margin-bottom: 32px;">Menu Kami</h2>
{menu_html}
  </div>

  <!-- Cart Sidebar -->
  <div class="cart-sidebar" id="cartSidebar">
    <div class="cart-header">
      <h2>Troli Saya</h2>
      <button class="cart-close" onclick="toggleCart()">×</button>
    </div>
    <div class="cart-items" id="cartItems">
      <p style="text-align: center; color: #6b7280; margin-top: 40px;">Troli masih kosong</p>
    </div>
    <div class="cart-footer">
      <div class="cart-total">
        <span>Total:</span>
        <span id="cartTotal">RM 0.00</span>
      </div>
      <button class="checkout-btn" onclick="checkout()">
        <svg width="24" height="24" fill="white" viewBox="0 0 24 24">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.890-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
        </svg>
        Checkout via WhatsApp
      </button>
    </div>
  </div>

  <!-- Cart FAB (Mobile) -->
  <button class="cart-fab" onclick="toggleCart()">
    🛒
    <span class="cart-count" id="cartCount">0</span>
  </button>

  <script>
    let cart = [];
    let selectedZone = null;

    function selectZone(name, fee) {{
      selectedZone = {{ name, fee }};
      document.querySelectorAll('.zone-card').forEach(card => card.classList.remove('selected'));
      event.currentTarget.classList.add('selected');

      // Scroll to menu
      document.getElementById('menu-section').scrollIntoView({{ behavior: 'smooth' }});
    }}

    function addToCart(name, price, image) {{
      if (!selectedZone) {{
        alert('Sila pilih kawasan delivery terlebih dahulu!');
        window.scrollTo({{ top: 0, behavior: 'smooth' }});
        return;
      }}

      cart.push({{ name, price, image, id: Date.now() }});
      updateCart();

      // Show cart on mobile
      if (window.innerWidth <= 768) {{
        toggleCart();
      }}
    }}

    function removeFromCart(id) {{
      cart = cart.filter(item => item.id !== id);
      updateCart();
    }}

    function updateCart() {{
      const cartItems = document.getElementById('cartItems');
      const cartCount = document.getElementById('cartCount');
      const cartTotal = document.getElementById('cartTotal');

      if (cart.length === 0) {{
        cartItems.innerHTML = '<p style="text-align: center; color: #6b7280; margin-top: 40px;">Troli masih kosong</p>';
        cartCount.textContent = '0';
        cartTotal.textContent = 'RM 0.00';
        return;
      }}

      // Update count
      cartCount.textContent = cart.length;

      // Calculate total
      const total = cart.reduce((sum, item) => {{
        const price = parseFloat(item.price.replace('RM', '').replace(',', ''));
        return sum + price;
      }}, 0);

      cartTotal.textContent = `RM ${{total.toFixed(2)}}`;

      // Render items
      cartItems.innerHTML = cart.map(item => `
        <div class="cart-item">
          <img src="${{item.image}}" class="cart-item-img" alt="${{item.name}}">
          <div class="cart-item-details">
            <div class="cart-item-name">${{item.name}}</div>
            <div class="cart-item-price">${{item.price}}</div>
          </div>
          <button class="cart-remove" onclick="removeFromCart(${{item.id}})">×</button>
        </div>
      `).join('');
    }}

    function toggleCart() {{
      document.getElementById('cartSidebar').classList.toggle('open');
    }}

    function checkout() {{
      if (cart.length === 0) {{
        alert('Troli masih kosong!');
        return;
      }}

      if (!selectedZone) {{
        alert('Sila pilih kawasan delivery!');
        toggleCart();
        window.scrollTo({{ top: 0, behavior: 'smooth' }});
        return;
      }}

      // Build WhatsApp message
      let message = `*Order Delivery dari {business_name}*%0A%0A`;
      message += `*Kawasan:* ${{selectedZone.name}}%0A`;
      message += `*Caj Delivery:* ${{selectedZone.fee}}%0A%0A`;
      message += `*Pesanan:*%0A`;

      cart.forEach((item, index) => {{
        message += `${{index + 1}}. ${{item.name}} - ${{item.price}}%0A`;
      }});

      const total = cart.reduce((sum, item) => {{
        const price = parseFloat(item.price.replace('RM', '').replace(',', ''));
        return sum + price;
      }}, 0);

      const deliveryFee = parseFloat(selectedZone.fee.replace('RM', '').replace(',', ''));
      const grandTotal = total + deliveryFee;

      message += `%0A*Subtotal:* RM ${{total.toFixed(2)}}%0A`;
      message += `*Delivery:* ${{selectedZone.fee}}%0A`;
      message += `*TOTAL:* RM ${{grandTotal.toFixed(2)}}`;

      // Open WhatsApp
      window.open(`https://wa.me/{phone_clean}?text=${{message}}`, '_blank');
    }}
  </script>
</body>
</html>
"""
        return html

    def inject_ordering_system(
        self,
        html: str,
        menu_items: List[Dict],
        delivery_zones: List[Dict],
        business_info: Dict,
        business_type: str = None,
        language: str = "ms",
        description: str = ""
    ) -> str:
        """
        COMPLETE DELIVERY PAGE - With all dependencies included
        Uses inline styles to avoid CSS framework dependency issues

        Now supports dynamic business types:
        - food: Restaurants, cafes (Nasi, Lauk, Minuman)
        - clothing: Boutiques, fashion (Baju, Tudung, Aksesori)
        - services: Service providers (Perkhidmatan, Pakej)
        - general: Other businesses (Produk, Lain-lain)
        """
        # Auto-detect business type if not provided
        if not business_type:
            desc_for_detection = description or business_info.get("description", business_info.get("name", ""))
            business_type = detect_business_type(desc_for_detection)
        
        logger.info(f"🏢 Business type for delivery system: {business_type}")
        business_name = business_info.get("name", "Our Restaurant")
        phone_number = business_info.get("phone", "+60123456789")

        # Clean phone for WhatsApp
        phone_clean = re.sub(r'[^\d+]', '', phone_number)
        if not phone_clean.startswith('+'):
            if phone_clean.startswith('60'):
                phone_clean = '+' + phone_clean
            elif phone_clean.startswith('0'):
                phone_clean = '+6' + phone_clean
            else:
                phone_clean = '+60' + phone_clean

        # Extract payment data for QR payment support
        payment_data = business_info.get("payment", {})
        payment_qr_url = payment_data.get("qr_image", "") if payment_data else ""
        payment_cod_enabled = payment_data.get("cod", True) if payment_data else True
        payment_qr_enabled = payment_data.get("qr", False) if payment_data else False
        logger.info(f"💳 Payment config: COD={payment_cod_enabled}, QR={payment_qr_enabled}, QR Image={'Yes' if payment_qr_url else 'No'}")

        # Get business config for this type
        biz_config = get_business_config(business_type)
        default_description = biz_config.get("item_description_default", "Produk berkualiti pilihan kami")
        if language == "en":
            default_description = biz_config.get("item_description_default_en", default_description)
        
        # =========================================================================
        # RALPH LOOP: Log menu items received for injection
        # =========================================================================
        log_menu_flow("STEP 3: Menu items received in inject_ordering_system", menu_items)

        # Format menu items with dynamic category auto-detection based on business type
        # CRITICAL: Use user's EXACT names - do not generate or modify names
        formatted_menu = []
        for idx, item in enumerate(menu_items):
            # Use user's exact name - DO NOT fallback to generic names
            raw_name = item.get('name', '')
            name = raw_name.strip() if raw_name and raw_name.strip() else None
            
            # Skip items without valid names
            if not name:
                logger.warning(f"   ⚠️ Skipping menu item {idx} - no valid name (got: '{raw_name}')")
                continue
            
            # Use dynamic category detection based on business type
            category = detect_item_category(name, business_type)

            formatted_menu.append({
                'id': idx + 1,
                'name': name,  # User's exact name
                'desc': item.get('description', default_description),
                'price': float(item.get('price', 15)),
                'image': item.get('image_url', 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80'),
                'category': category
            })
            logger.info(f"   ✅ Menu item: {name} - RM{float(item.get('price', 15)):.2f} [{category}]")

        # Format zones - ensure we have at least one default zone
        formatted_zones = []
        if delivery_zones:
            for idx, zone in enumerate(delivery_zones):
                # CRITICAL: Ensure zone name is never empty
                zone_name = zone.get('zone_name') or zone.get('name') or f'Zone {idx+1}'
                if not zone_name or str(zone_name).strip() == '':
                    zone_name = 'Kawasan Delivery'

                formatted_zones.append({
                    'id': idx + 1,
                    'name': zone_name,
                    'fee': float(zone.get('delivery_fee', zone.get('fee', 5))),
                    'time': zone.get('estimated_time', zone.get('delivery_time', '30-45 min')),
                    'active': True
                })
                logger.info(f"   ✓ Zone: {zone_name} - RM{zone.get('delivery_fee', zone.get('fee', 5))}")
        else:
            # Default zone if none provided
            formatted_zones = [{
                'id': 1,
                'name': 'Kawasan Sekitar',
                'fee': 5.0,
                'time': '30-45 min',
                'active': True
            }]

        menu_json = json.dumps(formatted_menu)
        zones_json = json.dumps(formatted_zones)
        minimum_order = 30
        delivery_hours = '11am - 9pm'

        # =========================================================================
        # RALPH LOOP: Final log before injecting into HTML
        # This is the FINAL data that will appear in deliveryMenuData
        # =========================================================================
        log_menu_flow("STEP 4: FINAL formatted_menu (will become deliveryMenuData)", formatted_menu)

        # Get dynamic labels and configuration based on business type
        order_config = get_order_config(business_type, language)
        button_label = get_delivery_button_label(business_type, language)
        category_buttons_html = generate_category_buttons_html(business_type, language)

        order_emoji = order_config["order_emoji"]
        order_title = order_config["order_title"]
        page_title = order_config["page_title"]
        whatsapp_closing = order_config["whatsapp_closing"]

        logger.info(f"🛵 Injecting delivery system: {len(formatted_menu)} items, {len(formatted_zones)} zones, type: {business_type}")

        # STEP 1: Add Tailwind CSS and Font Awesome (CRITICAL!)
        css_libraries = '''
<!-- Tailwind CSS for Delivery System -->
<script src="https://cdn.tailwindcss.com"></script>
<!-- Font Awesome for Icons -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
/* Delivery System Styles */
.delivery-page { display: none; }
.delivery-page.active { display: block; }
.delivery-zone-card { transition: all 0.2s ease; border: 2px solid transparent; cursor: pointer; }
.delivery-zone-card:hover { border-color: #ea580c; background: #fff7ed; }
.delivery-zone-card.selected { border-color: #ea580c; background: #fff7ed; box-shadow: 0 0 0 3px rgba(234,88,12,0.2); }
.delivery-menu-card { transition: all 0.2s ease; }
.delivery-menu-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.1); }
.delivery-qty-btn { transition: transform 0.1s; }
.delivery-qty-btn:active { transform: scale(0.9); }
.delivery-floating-cart { animation: deliveryFloat 3s ease-in-out infinite; }
@keyframes deliveryFloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
@keyframes deliveryPulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
.delivery-cart-badge { animation: deliveryPulse 2s infinite; }

/* MOBILE RESPONSIVE FIXES */
@media (max-width: 768px) {
    /* Menu grid - single column on mobile */
    #delivery-menu-grid { grid-template-columns: 1fr !important; }
    /* Zone grid - single column on mobile */
    #delivery-zones { grid-template-columns: 1fr !important; }
    /* Hide desktop cart sidebar on mobile */
    #delivery-cart-sidebar { display: none !important; }
    /* Show mobile cart button */
    #mobile-cart-btn { display: flex !important; }
    /* Category buttons scroll on mobile */
    .delivery-cat-btn { flex-shrink: 0; }
    /* Full width buttons on mobile */
    #page-order button[style*="fixed"] { width: calc(100% - 32px) !important; left: 16px !important; right: 16px !important; }
    /* Mobile cart overlay */
    .mobile-cart-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; display: none; }
    .mobile-cart-overlay.active { display: block; }
    .mobile-cart-panel { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-radius: 24px 24px 0 0; max-height: 85vh; overflow-y: auto; z-index: 101; transform: translateY(100%); transition: transform 0.3s ease; padding-bottom: 20px; }
    .mobile-cart-panel.active { transform: translateY(0); }
    /* Make cart footer scrollable content visible */
    #cart-footer-mobile { padding-bottom: 120px !important; }
    /* QR display mobile fixes - increased margin for scrollability */
    #qr-payment-display-mobile { margin-bottom: 140px !important; }
    /* Ensure QR download button is always accessible */
    #qr-payment-display-mobile a[download] { 
        position: relative; 
        z-index: 10; 
        margin-bottom: 20px !important;
        display: inline-block !important;
    }
    /* Fix cart overlay to allow scrolling */
    .mobile-cart-overlay.active > div:last-child {
        max-height: 90vh !important;
        overflow-y: auto !important;
        padding-bottom: env(safe-area-inset-bottom, 20px) !important;
    }
}
@media (max-width: 480px) {
    /* Smaller padding on very small screens */
    #page-order > div:first-child > div { padding: 0 12px !important; }
    /* Smaller header text */
    #page-order h1 { font-size: 20px !important; }
}
</style>'''
        
        if "</head>" in html:
            html = html.replace("</head>", css_libraries + "\n</head>")
        elif "<head>" in html:
            html = html.replace("<head>", "<head>\n" + css_libraries)
        else:
            # No head tag - add it at the beginning
            html = "<!DOCTYPE html><html><head>" + css_libraries + "</head>" + html

        # STEP 2: Wrap existing content + add delivery page
        if "<body" in html:
            body_start = html.find("<body")
            body_content_start = html.find(">", body_start) + 1
            body_end = html.find("</body>")

            if body_content_start > 0 and body_end > 0:
                body_content = html[body_content_start:body_end]
                
                # Complete delivery page HTML with inline styles as fallback
                page_html = f'''<div id="page-home" class="delivery-page active">{body_content}</div>
                <div id="page-order" class="delivery-page">
    <div style="background:linear-gradient(to right,#f97316,#ea580c);color:white;padding:24px 0;position:sticky;top:0;z-index:40;">
        <div style="max-width:1200px;margin:0 auto;padding:0 16px;">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <button onclick="showDeliveryPage('home')" style="background:none;border:none;color:rgba(255,255,255,0.8);cursor:pointer;font-size:14px;margin-bottom:4px;display:flex;align-items:center;gap:4px;">
                        ← Kembali
                    </button>
                    <h1 style="font-size:24px;font-weight:bold;margin:0;">{button_label}</h1>
                    <p style="color:rgba(255,255,255,0.8);font-size:14px;margin:4px 0 0 0;">{business_name} • {delivery_hours}</p>
                </div>
                <button onclick="toggleDeliveryMobileCart()" id="mobile-cart-btn" style="display:none;background:rgba(255,255,255,0.2);border:none;padding:12px;border-radius:50%;cursor:pointer;position:relative;">
                    🛒
                    <span id="cart-badge-mobile" style="display:none;position:absolute;top:-4px;right:-4px;background:#facc15;color:#7c2d12;font-size:12px;font-weight:bold;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;">0</span>
                </button>
            </div>
        </div>
    </div>

    <div style="max-width:1200px;margin:0 auto;padding:24px 16px;">
        <div style="display:grid;grid-template-columns:1fr;gap:24px;">
            <div style="display:flex;flex-direction:column;gap:24px;">
                
                <!-- Zone Selection -->
                <div style="background:white;border-radius:16px;padding:24px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
                        <div style="width:40px;height:40px;background:#f97316;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:18px;">1</div>
                        <div>
                            <h2 style="font-weight:bold;font-size:20px;color:#111827;margin:0;">Pilih Kawasan Delivery</h2>
                            <p style="color:#6b7280;font-size:14px;margin:4px 0 0 0;">Min. order: RM{minimum_order}</p>
                        </div>
                    </div>
                    <div id="delivery-zones" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;"></div>
                    <div id="selected-zone-info" style="display:none;margin-top:16px;padding:16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;">
                        <div style="display:flex;align-items:center;gap:8px;color:#15803d;">
                            ✓ <span style="font-weight:600;">Kawasan: <span id="zone-name-display">-</span></span>
                            <span style="margin-left:auto;">Caj: RM<span id="zone-fee-display">0</span></span>
                        </div>
                    </div>
                </div>

                <!-- Menu -->
                <div style="background:white;border-radius:16px;padding:24px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
                        <div style="width:40px;height:40px;background:#f97316;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:18px;">2</div>
                        <div>
                            <h2 style="font-weight:bold;font-size:20px;color:#111827;margin:0;">Pilih Menu</h2>
                            <p style="color:#6b7280;font-size:14px;margin:4px 0 0 0;">Klik untuk tambah ke bakul</p>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;margin-bottom:24px;overflow-x:auto;padding-bottom:8px;">
                        {category_buttons_html}
                    </div>
                    <div id="delivery-menu-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;"></div>
                </div>
            </div>

            <!-- Desktop Cart Sidebar -->
            <div id="delivery-cart-sidebar" style="display:none;position:fixed;right:20px;top:120px;width:380px;background:white;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.15);overflow:hidden;z-index:50;">
                <div style="background:linear-gradient(to right,#f97316,#ea580c);color:white;padding:20px;">
                    <h3 style="font-weight:bold;font-size:18px;display:flex;align-items:center;gap:8px;margin:0;">
                        🛒 Bakul Pesanan
                        <span id="cart-count-desktop" style="background:white;color:#ea580c;font-size:14px;padding:2px 8px;border-radius:9999px;margin-left:auto;">0</span>
                    </h3>
                </div>
                <div style="padding:20px;">
                    <div id="cart-empty-desktop" style="text-align:center;padding:32px 0;">
                        <div style="width:64px;height:64px;background:#f3f4f6;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px auto;font-size:24px;">🛒</div>
                        <p style="color:#6b7280;margin:0;">Bakul anda kosong</p>
                    </div>
                    <div id="cart-items-desktop" style="display:none;max-height:280px;overflow-y:auto;"></div>
                    <div id="cart-summary-desktop" style="display:none;border-top:1px solid #e5e7eb;padding-top:16px;margin-top:16px;">
                        <div style="display:flex;justify-content:space-between;color:#6b7280;margin-bottom:8px;"><span>Subtotal</span><span>RM<span id="subtotal-desktop">0.00</span></span></div>
                        <div style="display:flex;justify-content:space-between;color:#6b7280;margin-bottom:8px;"><span>Caj Delivery</span><span>RM<span id="delivery-fee-desktop">0.00</span></span></div>
                        <div style="display:flex;justify-content:space-between;font-size:20px;font-weight:bold;padding-top:8px;border-top:1px solid #e5e7eb;"><span>Jumlah</span><span style="color:#ea580c;">RM<span id="total-desktop">0.00</span></span></div>
                    </div>
                    <!-- Payment Options Section -->
                    <div id="payment-section-desktop" style="display:none;border-top:1px solid #e5e7eb;padding-top:16px;margin-top:16px;">
                        <h4 style="font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;">💳 Cara Bayaran</h4>
                        <div id="payment-options-desktop"></div>
                    </div>
                    <button id="checkout-btn-desktop" onclick="deliveryCheckout()" style="display:none;width:100%;margin-top:20px;background:linear-gradient(to right,#22c55e,#16a34a);color:white;font-weight:bold;padding:16px;border-radius:12px;border:none;cursor:pointer;font-size:16px;">
                        📱 Hantar Pesanan via WhatsApp
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Floating Cart Button (Mobile) -->
    <div id="delivery-floating-cart-btn" style="display:none;position:fixed;bottom:24px;right:24px;z-index:50;">
        <button onclick="toggleDeliveryMobileCart()" style="background:linear-gradient(to right,#f97316,#ea580c);color:white;padding:16px 20px;border-radius:9999px;box-shadow:0 8px 24px rgba(234,88,12,0.4);display:flex;align-items:center;gap:12px;border:none;cursor:pointer;">
            🛒
            <span style="font-weight:bold;">RM<span id="floating-total">0</span></span>
            <span style="background:white;color:#ea580c;font-size:14px;font-weight:bold;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;" id="floating-count">0</span>
        </button>
    </div>

    <!-- Mobile Cart Overlay -->
    <div id="delivery-mobile-cart-overlay" style="display:none;position:fixed;inset:0;z-index:100;">
        <div style="position:absolute;inset:0;background:rgba(0,0,0,0.5);" onclick="toggleDeliveryMobileCart()"></div>
        <div style="position:absolute;bottom:0;left:0;right:0;background:white;border-radius:24px 24px 0 0;max-height:90vh;overflow-y:auto;-webkit-overflow-scrolling:touch;">
            <div style="position:sticky;top:0;z-index:10;padding:16px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;background:white;border-radius:24px 24px 0 0;">
                <h3 style="font-weight:bold;font-size:18px;margin:0;">Bakul Pesanan</h3>
                <button onclick="toggleDeliveryMobileCart()" style="width:40px;height:40px;background:#f3f4f6;border-radius:50%;border:none;cursor:pointer;font-size:18px;">✕</button>
            </div>
            <div style="padding:16px;">
                <div id="cart-empty-mobile" style="text-align:center;padding:32px 0;"><p style="color:#6b7280;margin:0;">Bakul anda kosong</p></div>
                <div id="cart-items-mobile" style="display:none;"></div>
            </div>
            <div id="cart-footer-mobile" style="display:none;padding:16px;padding-bottom:140px;border-top:1px solid #e5e7eb;background:#f9fafb;">
                <div style="margin-bottom:16px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span>Subtotal</span><span>RM<span id="subtotal-mobile">0</span></span></div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span>Caj Delivery</span><span>RM<span id="delivery-fee-mobile">0</span></span></div>
                    <div style="display:flex;justify-content:space-between;font-weight:bold;font-size:18px;"><span>Jumlah</span><span style="color:#ea580c;">RM<span id="total-mobile">0</span></span></div>
                </div>
                <!-- Payment Options Section - Mobile -->
                <div style="margin-bottom:16px;">
                    <h4 style="font-weight:600;margin-bottom:12px;display:flex;align-items:center;gap:8px;">💳 Cara Bayaran</h4>
                    <div id="payment-options-mobile"></div>
                </div>
                <button onclick="deliveryCheckout()" style="width:100%;background:linear-gradient(to right,#22c55e,#16a34a);color:white;font-weight:bold;padding:16px;border-radius:12px;border:none;cursor:pointer;font-size:16px;margin-bottom:env(safe-area-inset-bottom, 20px);">
                    📱 Hantar WhatsApp
                </button>
            </div>
        </div>
    </div>
</div>'''

                html = html[:body_content_start] + page_html + html[body_end:]

        # STEP 3: Add delivery button - multiple injection points with INLINE STYLES
        delivery_button_inline = f'''
<!-- Delivery Button - BinaApp -->
<button onclick="showDeliveryPage('order')" id="binaapp-delivery-btn" style="position:fixed;bottom:24px;left:24px;background:linear-gradient(135deg,#f97316,#ea580c);color:white;padding:14px 24px;border-radius:50px;font-weight:600;z-index:9999;display:flex;align-items:center;gap:8px;border:none;cursor:pointer;box-shadow:0 4px 20px rgba(234,88,12,0.4);font-family:sans-serif;font-size:15px;">
    {button_label}
</button>'''
        
        # Always inject the button before </body> if not already present
        if "binaapp-delivery-btn" not in html and "</body>" in html:
            html = html.replace("</body>", delivery_button_inline + "\n</body>")

        # Convert Python booleans to JavaScript string for injection
        payment_qr_enabled_js = "true" if payment_qr_enabled else "false"
        payment_cod_enabled_js = "true" if payment_cod_enabled else "false"

        # STEP 4: JavaScript - Complete delivery system with prefixed functions
        script = f'''
<script>
// BinaApp Delivery System - Complete Implementation
(function() {{
    const DELIVERY_WHATSAPP = '{phone_clean}';
    const DELIVERY_BUSINESS = '{business_name}';
    const DELIVERY_MINIMUM = {minimum_order};
    const deliveryZonesData = {zones_json};
    const deliveryMenuData = {menu_json};

    // Payment configuration
    const PAYMENT_QR_URL = '{payment_qr_url}';
    const PAYMENT_COD_ENABLED = {payment_cod_enabled_js};
    const PAYMENT_QR_ENABLED = {payment_qr_enabled_js};

    let deliveryCart = [];
    let deliverySelectedZone = null;
    let deliveryFeeAmount = 0;
    let deliveryCurrentCategory = 'all';
    let selectedPaymentMethod = PAYMENT_COD_ENABLED ? 'cod' : (PAYMENT_QR_ENABLED ? 'qr' : 'cod');

    // Page switching
    window.showDeliveryPage = function(page) {{
        document.querySelectorAll('.delivery-page').forEach(p => p.classList.remove('active'));
        const targetPage = document.getElementById('page-' + page);
        if (targetPage) {{
            targetPage.classList.add('active');
            window.scrollTo(0, 0);
            // Show/hide cart sidebar on desktop
            const sidebar = document.getElementById('delivery-cart-sidebar');
            if (sidebar) {{
                sidebar.style.display = page === 'order' ? 'block' : 'none';
            }}
        }}
    }};

    // Mobile cart toggle
    window.toggleDeliveryMobileCart = function() {{
        const overlay = document.getElementById('delivery-mobile-cart-overlay');
        if (overlay) {{
            const isVisible = overlay.style.display === 'flex';
            overlay.style.display = isVisible ? 'none' : 'flex';
        }}
    }};

    // Render zones
    function renderDeliveryZones() {{
        const container = document.getElementById('delivery-zones');
        if (!container) return;
        container.innerHTML = deliveryZonesData.filter(z => z.active).map(zone => `
            <button onclick="selectDeliveryZone(${{zone.id}}, '${{zone.name}}', ${{zone.fee}})" id="delivery-zone-${{zone.id}}" class="delivery-zone-card" style="padding:16px;border-radius:12px;text-align:left;background:#f9fafb;border:2px solid transparent;cursor:pointer;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <div style="width:40px;height:40px;background:#fed7aa;border-radius:50%;display:flex;align-items:center;justify-content:center;">📍</div>
                        <div><div style="font-weight:600;color:#111827;">${{zone.name}}</div><div style="font-size:14px;color:#6b7280;">${{zone.time}}</div></div>
                    </div>
                    <div style="color:#ea580c;font-weight:bold;">RM${{zone.fee}}</div>
                </div>
            </button>
        `).join('');
    }}

    // Render menu
    function renderDeliveryMenu() {{
        const container = document.getElementById('delivery-menu-grid');
        if (!container) return;
        const filtered = deliveryCurrentCategory === 'all' ? deliveryMenuData : deliveryMenuData.filter(i => i.category === deliveryCurrentCategory);
        container.innerHTML = filtered.map(item => {{
            const inCart = deliveryCart.find(c => c.id === item.id);
            return `
            <div class="delivery-menu-card" style="background:#f9fafb;border-radius:12px;overflow:hidden;display:flex;gap:12px;padding:12px;">
                <div style="width:80px;height:80px;border-radius:8px;overflow:hidden;flex-shrink:0;">
                    <img src="${{item.image}}" alt="${{item.name}}" style="width:100%;height:100%;object-fit:cover;">
                </div>
                <div style="flex:1;display:flex;flex-direction:column;justify-content:space-between;min-width:0;">
                    <div><h4 style="font-weight:bold;color:#111827;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{item.name}}</h4><p style="font-size:12px;color:#6b7280;margin:4px 0 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{item.desc}}</p></div>
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;">
                        <span style="font-weight:bold;color:#ea580c;">RM${{item.price.toFixed(2)}}</span>
                        ${{inCart ? `
                            <div style="display:flex;align-items:center;gap:8px;">
                                <button onclick="updateDeliveryQty(${{item.id}}, -1)" class="delivery-qty-btn" style="width:32px;height:32px;background:#e5e7eb;border-radius:50%;border:none;cursor:pointer;">-</button>
                                <span style="font-weight:bold;width:24px;text-align:center;">${{inCart.qty}}</span>
                                <button onclick="updateDeliveryQty(${{item.id}}, 1)" class="delivery-qty-btn" style="width:32px;height:32px;background:#f97316;color:white;border-radius:50%;border:none;cursor:pointer;">+</button>
                            </div>
                        ` : `<button onclick="addToDeliveryCart(${{item.id}})" style="background:#f97316;color:white;font-size:14px;font-weight:600;padding:8px 16px;border-radius:9999px;border:none;cursor:pointer;">+ Tambah</button>`}}
                    </div>
                </div>
            </div>`;
        }}).join('');
    }}

    // Select zone
    window.selectDeliveryZone = function(id, name, fee) {{
        document.querySelectorAll('.delivery-zone-card').forEach(el => el.classList.remove('selected'));
        const zoneEl = document.getElementById('delivery-zone-' + id);
        if (zoneEl) zoneEl.classList.add('selected');
        deliverySelectedZone = {{ id, name, fee }};
        deliveryFeeAmount = fee;
        const zoneInfo = document.getElementById('selected-zone-info');
        if (zoneInfo) zoneInfo.style.display = 'block';
        const zoneName = document.getElementById('zone-name-display');
        if (zoneName) zoneName.textContent = name;
        const zoneFee = document.getElementById('zone-fee-display');
        if (zoneFee) zoneFee.textContent = fee;
        updateDeliveryCartDisplay();
    }};

    // Add to cart
    window.addToDeliveryCart = function(id) {{
        const item = deliveryMenuData.find(m => m.id === id);
        if (item) {{
            deliveryCart.push({{...item, qty: 1}});
            updateDeliveryCartDisplay();
            renderDeliveryMenu();
        }}
    }};

    // Update quantity
    window.updateDeliveryQty = function(id, delta) {{
        const idx = deliveryCart.findIndex(c => c.id === id);
        if (idx > -1) {{
            deliveryCart[idx].qty += delta;
            if (deliveryCart[idx].qty <= 0) deliveryCart.splice(idx, 1);
        }}
        updateDeliveryCartDisplay();
        renderDeliveryMenu();
    }};

    // Update cart display
    function updateDeliveryCartDisplay() {{
        const subtotal = deliveryCart.reduce((sum, item) => sum + (item.price * item.qty), 0);
        const total = subtotal + deliveryFeeAmount;
        const count = deliveryCart.reduce((sum, item) => sum + item.qty, 0);
        const hasItems = deliveryCart.length > 0;

        ['desktop', 'mobile'].forEach(t => {{
            const sub = document.getElementById('subtotal-' + t);
            const fee = document.getElementById('delivery-fee-' + t);
            const tot = document.getElementById('total-' + t);
            if (sub) sub.textContent = subtotal.toFixed(2);
            if (fee) fee.textContent = deliveryFeeAmount.toFixed(2);
            if (tot) tot.textContent = total.toFixed(2);
        }});

        const cartCount = document.getElementById('cart-count-desktop');
        if (cartCount) cartCount.textContent = count;
        
        const emptyD = document.getElementById('cart-empty-desktop');
        const itemsD = document.getElementById('cart-items-desktop');
        const summaryD = document.getElementById('cart-summary-desktop');
        const checkoutD = document.getElementById('checkout-btn-desktop');
        const paymentD = document.getElementById('payment-section-desktop');
        const emptyM = document.getElementById('cart-empty-mobile');
        const itemsM = document.getElementById('cart-items-mobile');
        const footerM = document.getElementById('cart-footer-mobile');

        if (emptyD) emptyD.style.display = hasItems ? 'none' : 'block';
        if (itemsD) itemsD.style.display = hasItems ? 'block' : 'none';
        if (summaryD) summaryD.style.display = hasItems ? 'block' : 'none';
        if (checkoutD) checkoutD.style.display = hasItems ? 'block' : 'none';
        if (paymentD) paymentD.style.display = hasItems ? 'block' : 'none';
        if (emptyM) emptyM.style.display = hasItems ? 'none' : 'block';
        if (itemsM) itemsM.style.display = hasItems ? 'block' : 'none';
        if (footerM) footerM.style.display = hasItems ? 'block' : 'none';

        // Update QR total amount if payment method is QR
        if (hasItems && selectedPaymentMethod === 'qr') {{
            const qrTotal = document.getElementById('qr-total-amount');
            const qrTotalMobile = document.getElementById('qr-total-amount-mobile');
            if (qrTotal) qrTotal.textContent = total.toFixed(2);
            if (qrTotalMobile) qrTotalMobile.textContent = total.toFixed(2);
        }}

        const floatingBtn = document.getElementById('delivery-floating-cart-btn');
        if (floatingBtn) {{
            floatingBtn.style.display = hasItems ? 'block' : 'none';
            const floatTotal = document.getElementById('floating-total');
            const floatCount = document.getElementById('floating-count');
            if (floatTotal) floatTotal.textContent = total.toFixed(0);
            if (floatCount) floatCount.textContent = count;
        }}

        renderDeliveryCartItems();
    }}

    // Render cart items
    function renderDeliveryCartItems() {{
        const html = deliveryCart.map(item => `
            <div style="display:flex;align-items:center;gap:12px;padding:12px;background:#f9fafb;border-radius:12px;margin-bottom:8px;">
                <img src="${{item.image}}" style="width:48px;height:48px;border-radius:8px;object-fit:cover;">
                <div style="flex:1;min-width:0;"><div style="font-weight:600;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{item.name}}</div><div style="color:#ea580c;font-weight:bold;">RM${{(item.price * item.qty).toFixed(2)}}</div></div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <button onclick="updateDeliveryQty(${{item.id}}, -1)" style="width:28px;height:28px;background:#e5e7eb;border-radius:50%;border:none;cursor:pointer;font-size:12px;">-</button>
                    <span style="font-weight:bold;width:16px;text-align:center;font-size:14px;">${{item.qty}}</span>
                    <button onclick="updateDeliveryQty(${{item.id}}, 1)" style="width:28px;height:28px;background:#f97316;color:white;border-radius:50%;border:none;cursor:pointer;font-size:12px;">+</button>
                </div>
            </div>
        `).join('');
        const desktopItems = document.getElementById('cart-items-desktop');
        const mobileItems = document.getElementById('cart-items-mobile');
        if (desktopItems) desktopItems.innerHTML = html;
        if (mobileItems) mobileItems.innerHTML = html;
    }}

    // Filter category
    window.filterDeliveryCategory = function(category) {{
        deliveryCurrentCategory = category;
        document.querySelectorAll('.delivery-cat-btn').forEach(btn => {{
            btn.style.background = '#f3f4f6';
            btn.style.color = '#374151';
        }});
        event.target.style.background = '#f97316';
        event.target.style.color = 'white';
        renderDeliveryMenu();
    }};

    // Toggle mobile cart
    window.toggleDeliveryMobileCart = function() {{
        const overlay = document.getElementById('delivery-mobile-cart-overlay');
        if (overlay) {{
            overlay.style.display = overlay.style.display === 'none' ? 'block' : 'none';
        }}
    }};

    // Payment selection
    window.selectPaymentMethod = function(method) {{
        selectedPaymentMethod = method;
        // Update UI
        document.querySelectorAll('.payment-option').forEach(el => {{
            el.classList.remove('selected');
            el.style.borderColor = '#e5e7eb';
        }});
        const selected = document.querySelector('.payment-option[data-method="' + method + '"]');
        if (selected) {{
            selected.classList.add('selected');
            selected.style.borderColor = '#f97316';
        }}
        // Show/hide QR display
        const qrDisplay = document.getElementById('qr-payment-display');
        const qrDisplayMobile = document.getElementById('qr-payment-display-mobile');
        if (qrDisplay) qrDisplay.style.display = method === 'qr' ? 'block' : 'none';
        if (qrDisplayMobile) qrDisplayMobile.style.display = method === 'qr' ? 'block' : 'none';
        // Update QR total amount
        if (method === 'qr') {{
            const subtotal = deliveryCart.reduce((sum, item) => sum + (item.price * item.qty), 0);
            const total = subtotal + deliveryFeeAmount;
            const qrTotal = document.getElementById('qr-total-amount');
            const qrTotalMobile = document.getElementById('qr-total-amount-mobile');
            if (qrTotal) qrTotal.textContent = total.toFixed(2);
            if (qrTotalMobile) qrTotalMobile.textContent = total.toFixed(2);
        }}
    }};

    // Render payment options
    function renderPaymentOptions() {{
        const paymentHtml = [];
        if (PAYMENT_COD_ENABLED) {{
            paymentHtml.push(`
                <div class="payment-option ${{selectedPaymentMethod === 'cod' ? 'selected' : ''}}" data-method="cod" onclick="selectPaymentMethod('cod')" style="display:flex;align-items:center;gap:12px;padding:12px;border:2px solid ${{selectedPaymentMethod === 'cod' ? '#f97316' : '#e5e7eb'}};border-radius:12px;cursor:pointer;margin-bottom:8px;">
                    <span style="font-size:20px;">💵</span>
                    <div><p style="font-weight:600;margin:0;">Bayar Tunai (COD)</p><p style="font-size:12px;color:#6b7280;margin:0;">Bayar bila terima</p></div>
                </div>
            `);
        }}
                        if (PAYMENT_QR_ENABLED && PAYMENT_QR_URL) {{
                            paymentHtml.push(`
                                <div class="payment-option ${{selectedPaymentMethod === 'qr' ? 'selected' : ''}}" data-method="qr" onclick="selectPaymentMethod('qr')" style="display:flex;align-items:center;gap:12px;padding:12px;border:2px solid ${{selectedPaymentMethod === 'qr' ? '#f97316' : '#e5e7eb'}};border-radius:12px;cursor:pointer;margin-bottom:8px;">
                                    <span style="font-size:20px;">📱</span>
                                    <div><p style="font-weight:600;margin:0;">QR Payment</p><p style="font-size:12px;color:#6b7280;margin:0;">Scan & bayar sekarang</p></div>
                                </div>
                                <div id="qr-payment-display" style="display:${{selectedPaymentMethod === 'qr' ? 'block' : 'none'}};text-align:center;padding:20px;background:#f0fdf4;border-radius:16px;margin-bottom:140px;border:2px solid #bbf7d0;">
                                    <p style="font-weight:600;margin-bottom:16px;font-size:16px;">📱 Scan untuk bayar</p>
                                    <img src="${{PAYMENT_QR_URL}}" alt="Payment QR" style="width:200px;height:200px;border-radius:12px;border:4px solid white;box-shadow:0 4px 16px rgba(0,0,0,0.15);">
                                    <p style="margin-top:16px;font-size:16px;">Jumlah: <strong style="color:#ea580c;font-size:24px;">RM<span id="qr-total-amount">0.00</span></strong></p>
                                    <a href="${{PAYMENT_QR_URL}}" download="payment-qr.png" style="display:inline-flex;align-items:center;gap:8px;margin-top:16px;margin-bottom:20px;padding:14px 28px;background:#10b981;color:white;border-radius:10px;text-decoration:none;font-weight:600;font-size:16px;box-shadow:0 4px 12px rgba(16,185,129,0.3);">📥 Download QR</a>
                                    <p style="font-size:13px;color:#6b7280;margin-top:12px;padding-bottom:30px;">Screenshot bukti bayaran & hantar via WhatsApp</p>
                                </div>
                            `);
                        }}

        // Inject payment options into desktop cart
        const paymentContainer = document.getElementById('payment-options-desktop');
        if (paymentContainer) paymentContainer.innerHTML = paymentHtml.join('');

        // Inject payment options into mobile cart
        const paymentContainerMobile = document.getElementById('payment-options-mobile');
        if (paymentContainerMobile) {{
            // Clone for mobile with mobile-specific IDs
            const mobileHtml = paymentHtml.join('').replace('qr-payment-display', 'qr-payment-display-mobile').replace('qr-total-amount', 'qr-total-amount-mobile');
            paymentContainerMobile.innerHTML = mobileHtml;
        }}
    }}

    // Checkout - Dynamic based on business type with payment method
    window.deliveryCheckout = function() {{
        if (deliveryCart.length === 0) {{ alert('Sila tambah item ke dalam bakul'); return; }}
        if (!deliverySelectedZone) {{ alert('Sila pilih kawasan delivery terlebih dahulu'); return; }}
        const subtotal = deliveryCart.reduce((sum, item) => sum + (item.price * item.qty), 0);
        if (subtotal < DELIVERY_MINIMUM) {{ alert('Minimum order adalah RM' + DELIVERY_MINIMUM); return; }}
        const total = subtotal + deliveryFeeAmount;

        let msg = '{order_emoji} *{order_title} - ' + DELIVERY_BUSINESS + '*\\n\\n';
        msg += '📍 *Kawasan:* ' + deliverySelectedZone.name + '\\n';
        msg += '💳 *Bayaran:* ' + (selectedPaymentMethod === 'cod' ? 'Tunai (COD)' : 'QR Payment') + '\\n';
        if (selectedPaymentMethod === 'qr') {{
            msg += '✅ *Status:* Sudah bayar\\n';
            msg += '📸 *Bukti:* (Sila hantar screenshot)\\n';
        }}
        msg += '━━━━━━━━━━━━━━━━\\n\\n📝 *Pesanan:*\\n';
        deliveryCart.forEach(item => {{ msg += '• ' + item.name + ' x' + item.qty + ' - RM' + (item.price * item.qty).toFixed(2) + '\\n'; }});
        msg += '\\n━━━━━━━━━━━━━━━━\\nSubtotal: RM' + subtotal.toFixed(2) + '\\nCaj Delivery: RM' + deliveryFeeAmount.toFixed(2) + '\\n*JUMLAH: RM' + total.toFixed(2) + '*\\n\\n';
        if (selectedPaymentMethod === 'qr') {{
            msg += '⚠️ Sila hantar bukti pembayaran bersama mesej ini.\\n\\n';
        }}
        msg += '{whatsapp_closing}';
        window.open('https://wa.me/' + DELIVERY_WHATSAPP + '?text=' + encodeURIComponent(msg), '_blank');
    }};

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {{
        renderDeliveryZones();
        renderDeliveryMenu();
        renderPaymentOptions();
        console.log('🛵 BinaApp Delivery System loaded: ' + deliveryMenuData.length + ' items, ' + deliveryZonesData.length + ' zones');
        console.log('💳 Payment config: COD=' + PAYMENT_COD_ENABLED + ', QR=' + PAYMENT_QR_ENABLED);
    }});
}})();
</script>'''

        if "</body>" in html:
            html = html.replace("</body>", script + "\n</body>")
        else:
            html += script

        logger.info(f"✅ Delivery system injected successfully")
        return html

    def inject_delivery_widget(
        self,
        html: str,
        website_id: str,
        whatsapp_number: str,
        primary_color: str = "#ea580c",
        business_type: str = None,
        description: str = "",
        language: str = "ms"
    ) -> str:
        """
        Inject BinaApp Delivery Widget
        Shows floating button for ordering based on business type

        Args:
            html: Website HTML
            website_id: Website UUID
            whatsapp_number: WhatsApp number for orders
            primary_color: Brand color (hex)
            business_type: Type of business (food, clothing, services, general)
            description: Business description for auto-detection
            language: "ms" or "en"

        Returns:
            HTML with delivery widget injected
        """
        # Auto-detect business type if not provided
        if not business_type:
            business_type = detect_business_type(description)
        
        # Get dynamic button label
        button_label = get_delivery_button_label(business_type, language)
        
        # Clean WhatsApp number
        whatsapp_clean = re.sub(r'[^\d+]', '', whatsapp_number)
        if not whatsapp_clean.startswith('+'):
            if whatsapp_clean.startswith('60'):
                whatsapp_clean = '+' + whatsapp_clean
            elif whatsapp_clean.startswith('0'):
                whatsapp_clean = '+6' + whatsapp_clean
            else:
                whatsapp_clean = '+60' + whatsapp_clean

        # Simple delivery button link (replaces complex widget)
        delivery_button = f'''
<!-- BinaApp Standalone Delivery Page Link -->
<a href="https://binaapp.my/delivery/{website_id}"
   target="_blank"
   style="position:fixed;bottom:24px;left:24px;background:linear-gradient(135deg,#f97316,#ea580c);color:white;padding:16px 24px;border-radius:50px;font-weight:600;z-index:9999;display:flex;align-items:center;gap:8px;text-decoration:none;font-family:sans-serif;box-shadow:0 4px 20px rgba(234,88,12,0.4);transition:transform 0.2s,box-shadow 0.2s;"
   onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 25px rgba(234,88,12,0.5)';"
   onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 20px rgba(234,88,12,0.4)';">
    {button_label}
</a>'''

        # Inject before </body>
        if "</body>" in html:
            html = html.replace("</body>", delivery_button + "\n</body>")
        else:
            # Fallback: append to end
            html += delivery_button

        logger.info(f"✅ Delivery button link injected for website {website_id}")
        return html


    def inject_integrations(
        self,
        html: str,
        features: List[str],
        user_data: Dict
    ) -> str:
        """
        Inject all requested integrations into HTML
        """
        logger.info(f"Injecting integrations: {features}")

        # Check if delivery widget is enabled (mutually exclusive with legacy delivery UI)
        # Widget is enabled when: website_id exists AND delivery features are requested
        delivery_widget_enabled = bool(
            user_data.get("website_id") and 
            ("delivery_system" in features or user_data.get("delivery"))
        )

        # WhatsApp
        if "whatsapp" in features and user_data.get("phone"):
            html = self.inject_whatsapp_button(
                html,
                user_data["phone"],
                user_data.get("whatsapp_message", "Hi, I'm interested")
            )

        # Google Maps
        if "maps" in features and user_data.get("address"):
            html = self.inject_google_maps(html, user_data["address"])

        # Shopping Cart
        if "cart" in features:
            html = self.inject_shopping_cart(html)

        # Legacy Delivery Section - SKIP if widget is enabled
        if user_data.get("delivery") and user_data.get("phone") and not delivery_widget_enabled:
            logger.info("Injecting legacy delivery section")
            html = self.inject_delivery_section(
                html,
                user_data["delivery"],
                user_data["phone"]
            )

        # Contact Form
        if "contact" in features:
            html = self.inject_contact_form(html, user_data.get("email", ""))

        # QR Code - Inject BEFORE delivery system so it ends up inside page-home div
        # SKIP if widget is enabled (widget has its own flow)
        if user_data.get("url") and not delivery_widget_enabled:
            html = self.inject_qr_code(html, user_data["url"])

        # Delivery System handling
        if "delivery_system" in features or user_data.get("delivery"):
            website_id = user_data.get("website_id", "")
            whatsapp = user_data.get("phone", "+60123456789")
            primary_color = user_data.get("primary_color", "#ea580c")

            if delivery_widget_enabled:
                # NEW: Only inject the delivery widget (single source of truth)
                logger.info("Injecting delivery widget ONLY (legacy UI skipped)")
                html = self.inject_delivery_widget(
                    html,
                    website_id,
                    whatsapp,
                    primary_color
                )
            else:
                # LEGACY: Inject full ordering system when no website_id
                menu_items = user_data.get("menu_items", [])
                delivery_zones = user_data.get("delivery_zones", [])
                payment_data = user_data.get("payment", {})

                logger.info(f"Injecting legacy ordering system - {len(menu_items)} menu items, {len(delivery_zones)} zones")

                if not delivery_zones and (user_data.get("delivery") or user_data.get("fulfillment")):
                    delivery_data = user_data.get("delivery", {})
                    fulfillment_data = user_data.get("fulfillment", {})

                    # Get fee from either source
                    fee_value = delivery_data.get("fee") or fulfillment_data.get("delivery_fee") or "5"
                    if isinstance(fee_value, str):
                        fee_value = float(fee_value.replace("RM", "").replace(",", "").strip()) if fee_value.strip() else 5.0
                    else:
                        fee_value = float(fee_value) if fee_value else 5.0

                    # Get zone name from either source - FIXED: Check fulfillment_data too
                    area_from_delivery = (delivery_data.get("area") or "").strip()
                    area_from_fulfillment = (fulfillment_data.get("delivery_area") or "").strip()
                    zone_name = area_from_delivery if area_from_delivery else (area_from_fulfillment if area_from_fulfillment else "Kawasan Delivery")

                    default_zone = {
                        "id": "default",
                        "zone_name": zone_name,
                        "delivery_fee": fee_value,
                        "estimated_time": delivery_data.get("hours") or fulfillment_data.get("hours") or "30-45 min",
                        "is_active": True
                    }
                    delivery_zones = [default_zone]
                    logger.info(f"Created fallback delivery zone: {zone_name} - RM{fee_value}")

                # Get business type for proper categories
                business_type = user_data.get("business_type", "")
                description = user_data.get("description", user_data.get("business_name", ""))

                html = self.inject_ordering_system(
                    html,
                    menu_items,
                    delivery_zones,
                    {
                        "name": user_data.get("business_name", "Our Business"),
                        "phone": user_data.get("phone", "+60123456789"),
                        "payment": payment_data  # Pass payment data for QR support
                    },
                    business_type=business_type,
                    description=description
                )

        return html

    def apply_image_safety_guard(
        self,
        html: str,
        image_choice: str,
        user_images: List[str] = None
    ) -> str:
        """
        SAFETY GUARD: Remove unwanted images from HTML

        STRICT RULES:
        - image_choice == 'none' → Remove ALL images from HTML
        - image_choice == 'upload' → Keep only user-uploaded images
        - image_choice == 'ai' → Keep all images (AI was explicitly requested)

        This is the LAST LINE OF DEFENSE before returning HTML to user.

        Args:
            html: The HTML content
            image_choice: User's explicit choice ('none', 'upload', 'ai')
            user_images: List of user-uploaded image URLs

        Returns:
            HTML with unwanted images removed
        """
        if not html:
            return html

        user_images = user_images or []

        if image_choice == 'ai':
            # User explicitly wanted AI images - keep everything
            logger.info("🖼️ SAFETY GUARD: image_choice='ai' - keeping all images")
            return html

        if image_choice == 'none':
            # User wants NO images - remove all img tags and background-images
            logger.info("🚫 SAFETY GUARD: image_choice='none' - removing ALL images")

            # Remove <img> tags (keep alt text for accessibility)
            img_pattern = r'<img[^>]*src=["\'][^"\']*["\'][^>]*/?>'
            html = re.sub(img_pattern, '', html, flags=re.IGNORECASE)

            # Remove background-image styles
            bg_pattern = r'background-image\s*:\s*url\([^)]*\)\s*;?'
            html = re.sub(bg_pattern, '', html, flags=re.IGNORECASE)

            # Remove src attributes that might have images
            src_pattern = r'src=["\']https?://[^"\']*\.(jpg|jpeg|png|gif|webp|svg)["\']'
            html = re.sub(src_pattern, 'src=""', html, flags=re.IGNORECASE)

            logger.info("✅ SAFETY GUARD: All images removed from HTML")
            return html

        if image_choice == 'upload':
            # User wants only THEIR images - this is handled upstream
            # But as a safety net, we log a warning if we detect non-user images
            if user_images:
                user_image_domains = set()
                for img_url in user_images:
                    if img_url:
                        # Extract domain from URL
                        import urllib.parse
                        parsed = urllib.parse.urlparse(img_url)
                        user_image_domains.add(parsed.netloc)

                # Check for images from known AI/stock domains
                ai_domains = ['stability.ai', 'replicate.com', 'cloudinary.com', 'unsplash.com']
                for domain in ai_domains:
                    if domain in html and domain not in str(user_image_domains):
                        logger.warning(f"⚠️ SAFETY GUARD: Detected potential AI image from {domain} when user wanted uploads only")

            logger.info("📷 SAFETY GUARD: image_choice='upload' - using user images only")
            return html

        # Unknown image_choice - log warning and return as-is
        logger.warning(f"⚠️ SAFETY GUARD: Unknown image_choice='{image_choice}' - no changes made")
        return html


# Create singleton instance
template_service = TemplateService()
