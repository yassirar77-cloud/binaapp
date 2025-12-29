"""
Template Service
Handles website type detection and feature injection
"""

from typing import List, Dict, Tuple
from loguru import logger
import re
import json


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
        business_info: Dict
    ) -> str:
        """
        COMPLETE DELIVERY PAGE - Using User's Proven Template
        Exact structure from complete-website-with-delivery.html
        """
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

        # Format menu items with category auto-detection
        formatted_menu = []
        for idx, item in enumerate(menu_items):
            name = item.get('name', f'Item {idx+1}')
            category = 'lauk'
            name_lower = name.lower()
            if any(x in name_lower for x in ['nasi', 'rice', 'briyani']):
                category = 'nasi'
            elif any(x in name_lower for x in ['air', 'minuman', 'drink', 'juice', 'tea', 'kopi']):
                category = 'minuman'

            formatted_menu.append({
                'id': idx + 1,
                'name': name,
                'desc': item.get('description', 'Hidangan istimewa dari dapur kami'),
                'price': float(item.get('price', 15)),
                'image': item.get('image_url', 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80'),
                'category': category
            })

        # Format zones
        formatted_zones = []
        for idx, zone in enumerate(delivery_zones):
            formatted_zones.append({
                'id': idx + 1,
                'name': zone.get('zone_name', zone.get('name', f'Zone {idx+1}')),
                'fee': float(zone.get('delivery_fee', 5)),
                'time': zone.get('estimated_time', zone.get('delivery_time', '30-45 min')),
                'active': True
            })

        menu_json = json.dumps(formatted_menu)
        zones_json = json.dumps(formatted_zones)
        minimum_order = 30
        delivery_hours = '11am - 5pm'

        # STEP 1: CSS - User's exact styles
        delivery_css = '''
<style>
.page { display: none; }
.page.active { display: block; }
.zone-card { transition: all 0.2s ease; border: 2px solid transparent; }
.zone-card:hover { border-color: #ea580c; background: #fff7ed; }
.zone-card.selected { border-color: #ea580c; background: #fff7ed; box-shadow: 0 0 0 3px rgba(234,88,12,0.2); }
.menu-card { transition: all 0.2s ease; }
.menu-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.1); }
.qty-btn { transition: transform 0.1s; }
.qty-btn:active { transform: scale(0.9); }
.floating-cart { animation: float 3s ease-in-out infinite; }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
@keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
.cart-badge { animation: pulse 2s infinite; }
</style>'''
        
        if "</head>" in html:
            html = html.replace("</head>", delivery_css + "\n</head>")
        elif "<body" in html:
            html = html.replace("<body", delivery_css + "\n<body", 1)

        # STEP 2: Wrap existing content + add delivery page
        if "<body" in html:
            body_start = html.find("<body")
            body_content_start = html.find(">", body_start) + 1
            body_end = html.find("</body>")

            if body_content_start > 0 and body_end > 0:
                body_content = html[body_content_start:body_end]
                
                # User's exact delivery page HTML structure
                page_html = f'''<div id="page-home" class="page active">{body_content}</div>
<div id="page-order" class="page">
    <div class="bg-gradient-to-r from-orange-500 to-orange-600 text-white py-6 sticky top-0 z-40">
        <div class="container mx-auto px-4">
            <div class="flex items-center justify-between">
                <div>
                    <button onclick="showPage('home')" class="text-white/80 hover:text-white text-sm mb-1 flex items-center gap-1">
                        <i class="fas fa-arrow-left"></i> Kembali
                    </button>
                    <h1 class="text-2xl font-bold">🛵 Pesan Delivery</h1>
                    <p class="text-white/80 text-sm">{business_name} • {delivery_hours}</p>
                </div>
                <button onclick="toggleMobileCart()" class="lg:hidden relative bg-white/20 hover:bg-white/30 p-3 rounded-full">
                    <i class="fas fa-shopping-cart text-xl"></i>
                    <span id="cart-badge-mobile" class="hidden absolute -top-1 -right-1 bg-yellow-400 text-orange-900 text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center cart-badge">0</span>
                </button>
            </div>
        </div>
    </div>

    <div class="container mx-auto px-4 py-6">
        <div class="grid lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 space-y-6">
                
                <div class="bg-white rounded-2xl p-6 shadow-lg">
                    <div class="flex items-center gap-3 mb-5">
                        <div class="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">1</div>
                        <div>
                            <h2 class="font-bold text-xl text-gray-900">Pilih Kawasan Delivery</h2>
                            <p class="text-gray-500 text-sm">Min. order: RM{minimum_order}</p>
                        </div>
                    </div>
                    <div id="delivery-zones" class="grid sm:grid-cols-2 gap-3"></div>
                    <div id="selected-zone-info" class="hidden mt-4 p-4 bg-green-50 border border-green-200 rounded-xl">
                        <div class="flex items-center gap-2 text-green-700">
                            <i class="fas fa-check-circle"></i>
                            <span class="font-semibold">Kawasan: <span id="zone-name-display">-</span></span>
                            <span class="ml-auto">Caj: RM<span id="zone-fee-display">0</span></span>
                        </div>
                    </div>
                </div>

                <div class="bg-white rounded-2xl p-6 shadow-lg">
                    <div class="flex items-center gap-3 mb-5">
                        <div class="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">2</div>
                        <div>
                            <h2 class="font-bold text-xl text-gray-900">Pilih Menu</h2>
                            <p class="text-gray-500 text-sm">Klik untuk tambah ke bakul</p>
                        </div>
                    </div>
                    <div class="flex gap-2 mb-6 overflow-x-auto pb-2">
                        <button onclick="filterCategory('all')" class="cat-btn active bg-orange-500 text-white px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap">Semua</button>
                        <button onclick="filterCategory('nasi')" class="cat-btn bg-gray-100 text-gray-700 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap hover:bg-gray-200">🍚 Nasi</button>
                        <button onclick="filterCategory('lauk')" class="cat-btn bg-gray-100 text-gray-700 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap hover:bg-gray-200">🍗 Lauk</button>
                        <button onclick="filterCategory('minuman')" class="cat-btn bg-gray-100 text-gray-700 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap hover:bg-gray-200">🥤 Minuman</button>
                    </div>
                    <div id="menu-grid" class="grid sm:grid-cols-2 gap-4"></div>
                </div>
            </div>

            <div class="hidden lg:block">
                <div class="bg-white rounded-2xl shadow-lg sticky top-28 overflow-hidden">
                    <div class="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-5">
                        <h3 class="font-bold text-lg flex items-center gap-2">
                            <i class="fas fa-shopping-cart"></i> Bakul Pesanan
                            <span id="cart-count-desktop" class="bg-white text-orange-600 text-sm px-2 py-0.5 rounded-full ml-auto">0</span>
                        </h3>
                    </div>
                    <div class="p-5">
                        <div id="cart-empty-desktop" class="text-center py-8">
                            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i class="fas fa-shopping-basket text-gray-400 text-2xl"></i>
                            </div>
                            <p class="text-gray-500">Bakul anda kosong</p>
                        </div>
                        <div id="cart-items-desktop" class="hidden space-y-3 max-h-[280px] overflow-y-auto"></div>
                        <div id="cart-summary-desktop" class="hidden border-t border-gray-100 pt-4 mt-4 space-y-2">
                            <div class="flex justify-between text-gray-600"><span>Subtotal</span><span>RM<span id="subtotal-desktop">0.00</span></span></div>
                            <div class="flex justify-between text-gray-600"><span>Caj Delivery</span><span>RM<span id="delivery-fee-desktop">0.00</span></span></div>
                            <div class="flex justify-between text-xl font-bold pt-2 border-t border-gray-100"><span>Jumlah</span><span class="text-orange-600">RM<span id="total-desktop">0.00</span></span></div>
                        </div>
                        <button id="checkout-btn-desktop" onclick="checkout()" class="hidden w-full mt-5 bg-gradient-to-r from-green-500 to-green-600 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-3">
                            <i class="fab fa-whatsapp text-2xl"></i> Hantar Pesanan
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="floating-cart-btn" class="lg:hidden fixed bottom-6 right-6 hidden z-50">
        <button onclick="toggleMobileCart()" class="floating-cart bg-gradient-to-r from-orange-500 to-orange-600 text-white px-5 py-4 rounded-full shadow-2xl flex items-center gap-3">
            <i class="fas fa-shopping-cart text-xl"></i>
            <span class="font-bold">RM<span id="floating-total">0</span></span>
            <span class="bg-white text-orange-600 text-sm font-bold w-6 h-6 rounded-full flex items-center justify-center" id="floating-count">0</span>
        </button>
    </div>

    <div id="mobile-cart-overlay" class="lg:hidden fixed inset-0 z-50 hidden">
        <div class="absolute inset-0 bg-black/50" onclick="toggleMobileCart()"></div>
        <div class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl max-h-[85vh] overflow-hidden">
            <div class="p-4 border-b flex items-center justify-between">
                <h3 class="font-bold text-lg">Bakul Pesanan</h3>
                <button onclick="toggleMobileCart()" class="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center"><i class="fas fa-times"></i></button>
            </div>
            <div class="p-4 max-h-[40vh] overflow-y-auto">
                <div id="cart-empty-mobile" class="text-center py-8"><p class="text-gray-500">Bakul anda kosong</p></div>
                <div id="cart-items-mobile" class="hidden space-y-3"></div>
            </div>
            <div id="cart-footer-mobile" class="hidden p-4 border-t bg-gray-50">
                <div class="space-y-2 mb-4">
                    <div class="flex justify-between"><span>Subtotal</span><span>RM<span id="subtotal-mobile">0</span></span></div>
                    <div class="flex justify-between"><span>Caj Delivery</span><span>RM<span id="delivery-fee-mobile">0</span></span></div>
                    <div class="flex justify-between font-bold text-lg"><span>Jumlah</span><span class="text-orange-600">RM<span id="total-mobile">0</span></span></div>
                </div>
                <button onclick="checkout()" class="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-3">
                    <i class="fab fa-whatsapp text-2xl"></i> Hantar WhatsApp
                </button>
            </div>
        </div>
    </div>
</div>'''

                html = html[:body_content_start] + page_html + html[body_end:]

        # STEP 3: Add delivery button to navigation
        delivery_button = '''<button onclick="showPage('order')" class="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg font-semibold transition flex items-center gap-2 shadow-md">
    <i class="fas fa-motorcycle"></i>
    <span class="hidden sm:inline">Pesan Delivery</span>
</button>'''
        
        for pattern in ["</nav>", "</header>", '<a href="https://wa.me/']:
            if pattern in html:
                if pattern.startswith('<a href="https://wa.me/'):
                    pos = html.find(pattern)
                    html = html[:pos] + delivery_button + "\n" + html[pos:]
                else:
                    html = html.replace(pattern, delivery_button + "\n" + pattern, 1)
                break

        # STEP 4: JavaScript - User's exact implementation
        script = f'''<script>
function showPage(page) {{
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    window.scrollTo(0, 0);
}}

const WHATSAPP_NUMBER = '{phone_clean}';
const BUSINESS_NAME = '{business_name}';
const MINIMUM_ORDER = {minimum_order};
const deliveryZones = {zones_json};
const menuItems = {menu_json};

let cart = [];
let selectedZone = null;
let deliveryFee = 0;
let currentCategory = 'all';

function renderDeliveryZones() {{
    const container = document.getElementById('delivery-zones');
    container.innerHTML = deliveryZones.filter(z => z.active).map(zone => `
        <button onclick="selectZone(${{zone.id}}, '${{zone.name}}', ${{zone.fee}})" id="zone-${{zone.id}}" class="zone-card p-4 rounded-xl text-left bg-gray-50">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center"><i class="fas fa-map-marker-alt text-orange-600"></i></div>
                    <div><div class="font-semibold text-gray-900">${{zone.name}}</div><div class="text-sm text-gray-500">${{zone.time}}</div></div>
                </div>
                <div class="text-orange-600 font-bold">RM${{zone.fee}}</div>
            </div>
        </button>
    `).join('');
}}

function renderMenuItems() {{
    const container = document.getElementById('menu-grid');
    const filtered = currentCategory === 'all' ? menuItems : menuItems.filter(i => i.category === currentCategory);
    container.innerHTML = filtered.map(item => {{
        const inCart = cart.find(c => c.id === item.id);
        return `
        <div class="menu-card bg-gray-50 rounded-xl overflow-hidden flex gap-3 p-3">
            <div class="w-20 h-20 rounded-lg overflow-hidden flex-shrink-0">
                <img src="${{item.image}}" alt="${{item.name}}" class="w-full h-full object-cover">
            </div>
            <div class="flex-1 flex flex-col justify-between min-w-0">
                <div><h4 class="font-bold text-gray-900 truncate">${{item.name}}</h4><p class="text-xs text-gray-500 truncate">${{item.desc}}</p></div>
                <div class="flex items-center justify-between mt-2">
                    <span class="font-bold text-orange-600">RM${{item.price.toFixed(2)}}</span>
                    ${{inCart ? `
                        <div class="flex items-center gap-2">
                            <button onclick="updateQty(${{item.id}}, -1)" class="qty-btn w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center"><i class="fas fa-minus text-xs"></i></button>
                            <span class="font-bold w-6 text-center">${{inCart.qty}}</span>
                            <button onclick="updateQty(${{item.id}}, 1)" class="qty-btn w-8 h-8 bg-orange-500 text-white rounded-full flex items-center justify-center"><i class="fas fa-plus text-xs"></i></button>
                        </div>
                    ` : `<button onclick="addToCart(${{item.id}})" class="bg-orange-500 text-white text-sm font-semibold py-2 px-4 rounded-full">+ Tambah</button>`}}
                </div>
            </div>
        </div>`;
    }}).join('');
}}

function selectZone(id, name, fee) {{
    document.querySelectorAll('.zone-card').forEach(el => el.classList.remove('selected'));
    document.getElementById('zone-' + id).classList.add('selected');
    selectedZone = {{ id, name, fee }};
    deliveryFee = fee;
    document.getElementById('selected-zone-info').classList.remove('hidden');
    document.getElementById('zone-name-display').textContent = name;
    document.getElementById('zone-fee-display').textContent = fee;
    updateCartDisplay();
}}

function addToCart(id) {{
    const item = menuItems.find(m => m.id === id);
    if (item) {{ cart.push({{...item, qty: 1}}); updateCartDisplay(); renderMenuItems(); }}
}}

function updateQty(id, delta) {{
    const idx = cart.findIndex(c => c.id === id);
    if (idx > -1) {{ cart[idx].qty += delta; if (cart[idx].qty <= 0) cart.splice(idx, 1); }}
    updateCartDisplay(); renderMenuItems();
}}

function updateCartDisplay() {{
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const total = subtotal + deliveryFee;
    const count = cart.reduce((sum, item) => sum + item.qty, 0);
    const hasItems = cart.length > 0;

    ['desktop', 'mobile'].forEach(t => {{
        document.getElementById('subtotal-' + t).textContent = subtotal.toFixed(2);
        document.getElementById('delivery-fee-' + t).textContent = deliveryFee.toFixed(2);
        document.getElementById('total-' + t).textContent = total.toFixed(2);
    }});

    document.getElementById('cart-count-desktop').textContent = count;
    document.getElementById('cart-empty-desktop').classList.toggle('hidden', hasItems);
    document.getElementById('cart-items-desktop').classList.toggle('hidden', !hasItems);
    document.getElementById('cart-summary-desktop').classList.toggle('hidden', !hasItems);
    document.getElementById('checkout-btn-desktop').classList.toggle('hidden', !hasItems);
    document.getElementById('cart-empty-mobile').classList.toggle('hidden', hasItems);
    document.getElementById('cart-items-mobile').classList.toggle('hidden', !hasItems);
    document.getElementById('cart-footer-mobile').classList.toggle('hidden', !hasItems);

    const floatingBtn = document.getElementById('floating-cart-btn');
    if (hasItems) {{ floatingBtn.classList.remove('hidden'); document.getElementById('floating-total').textContent = total.toFixed(0); document.getElementById('floating-count').textContent = count; }}
    else {{ floatingBtn.classList.add('hidden'); }}

    const badge = document.getElementById('cart-badge-mobile');
    if (count > 0) {{ badge.textContent = count; badge.classList.remove('hidden'); }} else {{ badge.classList.add('hidden'); }}

    renderCartItems();
}}

function renderCartItems() {{
    const html = cart.map(item => `
        <div class="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
            <img src="${{item.image}}" class="w-12 h-12 rounded-lg object-cover">
            <div class="flex-1 min-w-0"><div class="font-semibold text-sm truncate">${{item.name}}</div><div class="text-orange-600 font-bold">RM${{(item.price * item.qty).toFixed(2)}}</div></div>
            <div class="flex items-center gap-2">
                <button onclick="updateQty(${{item.id}}, -1)" class="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center text-xs"><i class="fas fa-minus"></i></button>
                <span class="font-bold w-4 text-center text-sm">${{item.qty}}</span>
                <button onclick="updateQty(${{item.id}}, 1)" class="w-7 h-7 bg-orange-500 text-white rounded-full flex items-center justify-center text-xs"><i class="fas fa-plus"></i></button>
            </div>
        </div>
    `).join('');
    document.getElementById('cart-items-desktop').innerHTML = html;
    document.getElementById('cart-items-mobile').innerHTML = html;
}}

function filterCategory(category) {{
    currentCategory = category;
    document.querySelectorAll('.cat-btn').forEach(btn => {{ btn.classList.remove('active','bg-orange-500','text-white'); btn.classList.add('bg-gray-100','text-gray-700'); }});
    event.target.classList.add('active','bg-orange-500','text-white');
    event.target.classList.remove('bg-gray-100','text-gray-700');
    renderMenuItems();
}}

function toggleMobileCart() {{
    document.getElementById('mobile-cart-overlay').classList.toggle('hidden');
}}

function checkout() {{
    if (cart.length === 0) {{ alert('Sila tambah item ke dalam bakul'); return; }}
    if (!selectedZone) {{ alert('Sila pilih kawasan delivery'); return; }}
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    if (subtotal < MINIMUM_ORDER) {{ alert('Minimum order adalah RM' + MINIMUM_ORDER); return; }}
    const total = subtotal + deliveryFee;

    let msg = '🍛 *PESANAN BARU - ' + BUSINESS_NAME + '*\\n\\n';
    msg += '📍 *Kawasan:* ' + selectedZone.name + '\\n━━━━━━━━━━━━━━━━\\n\\n📝 *Pesanan:*\\n';
    cart.forEach(item => {{ msg += '• ' + item.name + ' x' + item.qty + ' - RM' + (item.price * item.qty).toFixed(2) + '\\n'; }});
    msg += '\\n━━━━━━━━━━━━━━━━\\nSubtotal: RM' + subtotal.toFixed(2) + '\\nCaj Delivery: RM' + deliveryFee.toFixed(2) + '\\n*JUMLAH: RM' + total.toFixed(2) + '*\\n\\nSila nyatakan alamat penuh. Terima kasih! 🙏';
    window.open('https://wa.me/' + WHATSAPP_NUMBER + '?text=' + encodeURIComponent(msg), '_blank');
}}

document.addEventListener('DOMContentLoaded', function() {{
    renderDeliveryZones();
    renderMenuItems();
}});
</script>'''

        if "</body>" in html:
            html = html.replace("</body>", script + "\n</body>")
        else:
            html += script

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

        # Delivery System
        if user_data.get("delivery") and user_data.get("phone"):
            logger.info("Injecting delivery section")
            html = self.inject_delivery_section(
                html,
                user_data["delivery"],
                user_data["phone"]
            )

        # Contact Form
        if "contact" in features:
            html = self.inject_contact_form(html, user_data.get("email", ""))

        # Ordering System (check if delivery system feature is enabled)
        if "delivery_system" in features or user_data.get("delivery"):
            logger.info("Injecting ordering system (deliverySystem feature enabled)")
            # Get menu items and delivery zones (may be empty initially)
            menu_items = user_data.get("menu_items", [])
            delivery_zones = user_data.get("delivery_zones", [])

            # If no delivery zones exist yet but delivery settings were provided during generation,
            # create a default zone from those settings
            if not delivery_zones and user_data.get("delivery"):
                delivery_data = user_data["delivery"]
                default_zone = {
                    "id": "default",
                    "zone_name": delivery_data.get("area", "Kawasan Delivery"),
                    "delivery_fee": float(delivery_data.get("fee", "5").replace("RM", "").strip()),
                    "estimated_time": delivery_data.get("hours", "30-45 min"),
                    "is_active": True
                }
                delivery_zones = [default_zone]

            # Always inject the ordering system structure
            html = self.inject_ordering_system(
                html,
                menu_items,
                delivery_zones,
                {
                    "name": user_data.get("business_name", "Our Business"),
                    "phone": user_data.get("phone", "+60123456789")
                }
            )

        # QR Code
        if user_data.get("url"):
            html = self.inject_qr_code(html, user_data["url"])

        return html


# Create singleton instance
template_service = TemplateService()
