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

    def inject_ordering_system(
        self,
        html: str,
        menu_items: List[Dict],
        delivery_zones: List[Dict],
        business_info: Dict
    ) -> str:
        """
        Inject complete ordering system with cart, zone selection, and WhatsApp checkout
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

        # Organize menu by categories
        categories = {}
        for item in menu_items:
            cat_id = item.get('category_id', 'uncategorized')
            if cat_id not in categories:
                categories[cat_id] = []
            categories[cat_id].append(item)

        # Build menu items JSON
        menu_json = json.dumps(menu_items)
        zones_json = json.dumps(delivery_zones)

        ordering_html = f"""
<!-- Online Ordering System -->
<div id="ordering-app" style="display:none;position:fixed;inset:0;background:white;z-index:9999;overflow-y:auto;">
  <!-- Header -->
  <div style="position:sticky;top:0;background:white;border-bottom:2px solid #e5e7eb;z-index:100;">
    <div style="max-width:1400px;margin:0 auto;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;">
      <div>
        <h1 style="margin:0;font-size:1.5rem;font-weight:bold;color:#1f2937;">{business_name}</h1>
        <p style="margin:4px 0 0;color:#6b7280;font-size:0.875rem;">Order Delivery Online</p>
      </div>
      <button onclick="closeOrdering()" style="background:#ef4444;color:white;border:none;padding:10px 20px;border-radius:8px;font-weight:600;cursor:pointer;">
        ✕ Close
      </button>
    </div>
  </div>

  <!-- Main Content -->
  <div style="max-width:1400px;margin:0 auto;display:grid;grid-template-columns:1fr;gap:24px;padding:20px;">
    <!-- Left: Menu Section -->
    <div style="grid-column:1/-1;">
      <!-- Step 1: Zone Selection -->
      <div id="zone-section" style="margin-bottom:32px;">
        <h2 style="font-size:1.5rem;font-weight:bold;margin-bottom:16px;color:#1f2937;">📍 Step 1: Choose Delivery Area</h2>
        <div id="zones-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;">
          <!-- Zones will be injected here -->
        </div>
        <div id="zone-warning" style="margin-top:16px;padding:16px;background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;display:none;">
          ⚠️ Please select a delivery area to continue
        </div>
      </div>

      <!-- Step 2: Menu -->
      <div id="menu-section" style="opacity:0.5;pointer-events:none;">
        <h2 style="font-size:1.5rem;font-weight:bold;margin-bottom:16px;color:#1f2937;">🍽️ Step 2: Choose Your Meal</h2>

        <!-- Category Tabs -->
        <div id="category-tabs" style="display:flex;gap:8px;margin-bottom:24px;overflow-x:auto;padding-bottom:8px;">
          <button onclick="filterCategory('all')" class="category-tab active" data-category="all"
                  style="padding:10px 20px;border:2px solid #3b82f6;background:#3b82f6;color:white;border-radius:9999px;font-weight:600;cursor:pointer;white-space:nowrap;">
            All Items
          </button>
        </div>

        <!-- Menu Grid -->
        <div id="menu-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;">
          <!-- Menu items will be injected here -->
        </div>
      </div>
    </div>
  </div>

  <!-- Cart Sidebar (Desktop) -->
  <div id="cart-sidebar" style="position:fixed;top:0;right:0;width:380px;height:100vh;background:white;border-left:2px solid #e5e7eb;display:none;flex-direction:column;z-index:101;">
    <div style="padding:20px;border-bottom:2px solid #e5e7eb;">
      <h3 style="margin:0;font-size:1.25rem;font-weight:bold;">🛒 Your Order</h3>
    </div>

    <div id="cart-items-list" style="flex:1;overflow-y:auto;padding:20px;">
      <div style="text-align:center;color:#9ca3af;padding:40px 20px;">
        Cart is empty
      </div>
    </div>

    <div style="padding:20px;border-top:2px solid #e5e7eb;background:#f9fafb;">
      <div style="margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
          <span>Subtotal:</span>
          <span id="cart-subtotal">RM 0.00</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
          <span>Delivery Fee:</span>
          <span id="cart-delivery-fee">RM 0.00</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:1.25rem;font-weight:bold;padding-top:8px;border-top:2px solid #e5e7eb;">
          <span>Total:</span>
          <span id="cart-total">RM 0.00</span>
        </div>
      </div>

      <button id="checkout-btn" onclick="checkout()"
              style="width:100%;padding:16px;background:#25D366;color:white;border:none;border-radius:8px;font-size:1.125rem;font-weight:bold;cursor:pointer;display:none;">
        Checkout via WhatsApp
      </button>
    </div>
  </div>

  <!-- Cart Floating Button (Mobile) -->
  <button id="cart-float-btn" onclick="toggleMobileCart()"
          style="display:none;position:fixed;bottom:20px;right:20px;background:#3b82f6;color:white;border:none;padding:16px;border-radius:9999px;box-shadow:0 10px 30px rgba(59,130,246,0.4);cursor:pointer;z-index:102;">
    🛒 <span id="cart-count-badge" style="margin-left:8px;background:white;color:#3b82f6;padding:4px 10px;border-radius:9999px;font-weight:bold;">0</span>
  </button>
</div>

<style>
.category-tab {{
  transition: all 0.2s;
}}
.category-tab:hover {{
  transform: scale(1.05);
}}
.category-tab.active {{
  background: #3b82f6 !important;
  color: white !important;
}}
.menu-item-card {{
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
  background: white;
}}
.menu-item-card:hover {{
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
  border-color: #3b82f6;
}}
.zone-card {{
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}}
.zone-card:hover {{
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(59,130,246,0.2);
}}
.zone-card.selected {{
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 8px 24px rgba(59,130,246,0.3);
}}
@media (max-width: 768px) {{
  #cart-sidebar {{
    display: none !important;
  }}
  #cart-float-btn {{
    display: flex !important;
    align-items: center;
  }}
}}
@media (min-width: 769px) {{
  #ordering-app > div:first-child {{
    padding-right: 400px;
  }}
  #cart-sidebar {{
    display: flex !important;
  }}
}}
</style>

<script>
// Data
const menuItems = {menu_json};
const deliveryZones = {zones_json};
const businessName = "{business_name}";
const whatsappNumber = "{phone_clean}";

// State
let selectedZone = null;
let cart = [];
let currentCategory = 'all';

// Initialize
function initOrdering() {{
  renderZones();
  renderMenu();
  updateCart();
}}

// Render delivery zones
function renderZones() {{
  const grid = document.getElementById('zones-grid');
  grid.innerHTML = deliveryZones.map(zone => `
    <div class="zone-card" onclick="selectZone('${{zone.id}}')" data-zone="${{zone.id}}">
      <div style="font-size:1.5rem;margin-bottom:8px;">📍</div>
      <div style="font-weight:bold;font-size:1.125rem;margin-bottom:8px;">${{zone.zone_name}}</div>
      <div style="color:#6b7280;font-size:0.875rem;margin-bottom:4px;">
        <span style="color:#10b981;">⏱ ${{zone.estimated_time || '30-45 min'}}</span>
      </div>
      <div style="color:#3b82f6;font-weight:bold;font-size:1.125rem;">
        RM ${{zone.delivery_fee.toFixed(2)}}
      </div>
    </div>
  `).join('');
}}

// Select delivery zone
function selectZone(zoneId) {{
  selectedZone = deliveryZones.find(z => z.id === zoneId);

  // Update UI
  document.querySelectorAll('.zone-card').forEach(card => {{
    card.classList.remove('selected');
  }});
  document.querySelector(`[data-zone="${{zoneId}}"]`).classList.add('selected');

  // Enable menu
  document.getElementById('menu-section').style.opacity = '1';
  document.getElementById('menu-section').style.pointerEvents = 'auto';
  document.getElementById('zone-warning').style.display = 'none';

  updateCart();
}}

// Render menu
function renderMenu() {{
  const grid = document.getElementById('menu-grid');

  const filteredItems = currentCategory === 'all'
    ? menuItems
    : menuItems.filter(item => item.category_id === currentCategory);

  grid.innerHTML = filteredItems.map(item => `
    <div class="menu-item-card">
      ${{item.image_url ? `<img src="${{item.image_url}}" style="width:100%;height:180px;object-fit:cover;" alt="${{item.name}}">` : `<div style="width:100%;height:180px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;align-items:center;justify-content:center;"><span style="font-size:3rem;">🍽️</span></div>`}}
      <div style="padding:16px;">
        <h4 style="margin:0 0 8px;font-size:1.125rem;font-weight:bold;">${{item.name}}</h4>
        ${{item.description ? `<p style="margin:0 0 12px;color:#6b7280;font-size:0.875rem;">${{item.description}}</p>` : ''}}
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:1.25rem;font-weight:bold;color:#3b82f6;">RM ${{item.price.toFixed(2)}}</span>
          <div id="controls-${{item.id}}">
            <button onclick="addToCart('${{item.id}}')"
                    style="background:#10b981;color:white;border:none;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;">
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  `).join('');
}}

// Filter by category
function filterCategory(category) {{
  currentCategory = category;

  // Update active tab
  document.querySelectorAll('.category-tab').forEach(btn => {{
    btn.classList.remove('active');
    btn.style.background = 'white';
    btn.style.color = '#3b82f6';
  }});
  event.target.classList.add('active');
  event.target.style.background = '#3b82f6';
  event.target.style.color = 'white';

  renderMenu();
  updateCartControls();
}}

// Add to cart
function addToCart(itemId) {{
  if (!selectedZone) {{
    document.getElementById('zone-warning').style.display = 'block';
    document.getElementById('zone-section').scrollIntoView({{ behavior: 'smooth' }});
    return;
  }}

  const item = menuItems.find(i => i.id === itemId);
  const existing = cart.find(c => c.id === itemId);

  if (existing) {{
    existing.quantity++;
  }} else {{
    cart.push({{ ...item, quantity: 1 }});
  }}

  updateCart();
  updateCartControls();
}}

// Remove from cart
function removeFromCart(itemId) {{
  const existing = cart.find(c => c.id === itemId);
  if (existing) {{
    existing.quantity--;
    if (existing.quantity === 0) {{
      cart = cart.filter(c => c.id !== itemId);
    }}
  }}

  updateCart();
  updateCartControls();
}}

// Update cart controls on menu items
function updateCartControls() {{
  menuItems.forEach(item => {{
    const cartItem = cart.find(c => c.id === item.id);
    const controls = document.getElementById(`controls-${{item.id}}`);

    if (controls) {{
      if (cartItem) {{
        controls.innerHTML = `
          <div style="display:flex;align-items:center;gap:8px;">
            <button onclick="removeFromCart('${{item.id}}')"
                    style="background:#ef4444;color:white;border:none;width:32px;height:32px;border-radius:8px;font-weight:bold;cursor:pointer;">
              -
            </button>
            <span style="font-weight:bold;min-width:24px;text-align:center;">${{cartItem.quantity}}</span>
            <button onclick="addToCart('${{item.id}}')"
                    style="background:#10b981;color:white;border:none;width:32px;height:32px;border-radius:8px;font-weight:bold;cursor:pointer;">
              +
            </button>
          </div>
        `;
      }} else {{
        controls.innerHTML = `
          <button onclick="addToCart('${{item.id}}')"
                  style="background:#10b981;color:white;border:none;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;">
            Add
          </button>
        `;
      }}
    }}
  }});
}}

// Update cart display
function updateCart() {{
  const itemsList = document.getElementById('cart-items-list');
  const subtotalEl = document.getElementById('cart-subtotal');
  const deliveryFeeEl = document.getElementById('cart-delivery-fee');
  const totalEl = document.getElementById('cart-total');
  const checkoutBtn = document.getElementById('checkout-btn');
  const countBadge = document.getElementById('cart-count-badge');

  if (cart.length === 0) {{
    itemsList.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px 20px;">Cart is empty</div>';
    checkoutBtn.style.display = 'none';
    countBadge.textContent = '0';
    return;
  }}

  let subtotal = 0;
  itemsList.innerHTML = cart.map(item => {{
    const itemTotal = item.price * item.quantity;
    subtotal += itemTotal;
    return `
      <div style="padding:12px;background:#f9fafb;border-radius:8px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">
          <div>
            <div style="font-weight:600;">${{item.name}}</div>
            <div style="color:#6b7280;font-size:0.875rem;">RM ${{item.price.toFixed(2)}} each</div>
          </div>
          <div style="font-weight:bold;color:#3b82f6;">RM ${{itemTotal.toFixed(2)}}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <button onclick="removeFromCart('${{item.id}}')"
                  style="background:#ef4444;color:white;border:none;width:28px;height:28px;border-radius:6px;cursor:pointer;">-</button>
          <span style="font-weight:600;min-width:24px;text-align:center;">${{item.quantity}}</span>
          <button onclick="addToCart('${{item.id}}')"
                  style="background:#10b981;color:white;border:none;width:28px;height:28px;border-radius:6px;cursor:pointer;">+</button>
        </div>
      </div>
    `;
  }}).join('');

  const deliveryFee = selectedZone ? selectedZone.delivery_fee : 0;
  const total = subtotal + deliveryFee;

  subtotalEl.textContent = `RM ${{subtotal.toFixed(2)}}`;
  deliveryFeeEl.textContent = `RM ${{deliveryFee.toFixed(2)}}`;
  totalEl.textContent = `RM ${{total.toFixed(2)}}`;
  checkoutBtn.style.display = 'block';
  countBadge.textContent = cart.reduce((sum, item) => sum + item.quantity, 0);
}}

// Checkout via WhatsApp
function checkout() {{
  if (!selectedZone) {{
    alert('Please select a delivery area');
    return;
  }}

  if (cart.length === 0) {{
    alert('Your cart is empty');
    return;
  }}

  let message = `🍛 *PESANAN BARU - ${{businessName}}*\\n\\n`;
  message += `📍 *Kawasan:* ${{selectedZone.zone_name}}\\n`;
  message += `━━━━━━━━━━━━━━━━\\n\\n`;
  message += `📝 *Pesanan:*\\n`;

  cart.forEach(item => {{
    message += `• ${{item.name}} x${{item.quantity}} - RM${{(item.price * item.quantity).toFixed(2)}}\\n`;
  }});

  const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  const deliveryFee = selectedZone.delivery_fee;
  const total = subtotal + deliveryFee;

  message += `\\n━━━━━━━━━━━━━━━━\\n`;
  message += `Subtotal: RM${{subtotal.toFixed(2)}}\\n`;
  message += `Caj Delivery: RM${{deliveryFee.toFixed(2)}}\\n`;
  message += `*JUMLAH: RM${{total.toFixed(2)}}*\\n\\n`;
  message += `Sila nyatakan alamat penuh anda.`;

  const whatsappUrl = `https://wa.me/${{whatsappNumber}}?text=${{encodeURIComponent(message)}}`;
  window.open(whatsappUrl, '_blank');
}}

// Toggle mobile cart
function toggleMobileCart() {{
  const sidebar = document.getElementById('cart-sidebar');
  if (sidebar.style.display === 'flex') {{
    sidebar.style.display = 'none';
  }} else {{
    sidebar.style.display = 'flex';
    sidebar.style.position = 'fixed';
    sidebar.style.left = '0';
    sidebar.style.width = '100%';
    sidebar.style.zIndex = '1000';
  }}
}}

// Open/close ordering app
function openOrdering() {{
  document.getElementById('ordering-app').style.display = 'block';
  document.body.style.overflow = 'hidden';
  initOrdering();
}}

function closeOrdering() {{
  document.getElementById('ordering-app').style.display = 'none';
  document.body.style.overflow = 'auto';
}}
</script>

<!-- Order Now Button -->
<button onclick="openOrdering()"
        style="position:fixed;bottom:20px;right:20px;background:#ea580c;color:white;border:none;padding:18px 32px;border-radius:9999px;font-size:1.125rem;font-weight:bold;cursor:pointer;box-shadow:0 10px 30px rgba(234,88,12,0.4);z-index:100;animation:pulse 2s infinite;">
  🛵 Order Delivery
</button>

<style>
@keyframes pulse {{
  0%, 100% {{ transform: scale(1); }}
  50% {{ transform: scale(1.05); }}
}}
</style>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", ordering_html + "\n</body>")
        else:
            html += ordering_html

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

        # Ordering System (menu + delivery zones)
        if user_data.get("menu_items") and user_data.get("delivery_zones"):
            logger.info("Injecting complete ordering system")
            html = self.inject_ordering_system(
                html,
                user_data["menu_items"],
                user_data["delivery_zones"],
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
