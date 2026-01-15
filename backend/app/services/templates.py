"""
Template Service
Handles website type detection and feature injection
"""

from typing import List, Dict, Tuple
from loguru import logger
import re


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
        ],
        "delivery": [
            "delivery", "penghantaran", "pesan", "order", "hantar", "deliver",
            "food", "makanan", "restaurant", "restoran", "cafe", "kedai makan",
            "nasi", "mee", "ayam", "lauk", "catering"
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

    def inject_delivery_widget(
        self,
        html: str,
        website_id: str = "",
        whatsapp_number: str = "",
        delivery_areas: list = None
    ) -> str:
        """
        Inject delivery order widget into HTML for mobile-friendly ordering

        This widget:
        - Properly handles null/undefined values (mobile browser fix)
        - Auto-generates customer_id if not available
        - Shows delivery form with area selection
        - Submits to /api/delivery/orders endpoint
        - Falls back to WhatsApp if API fails
        """
        if delivery_areas is None:
            delivery_areas = ["Bandar Sunway", "Petaling Jaya", "Subang Jaya", "Shah Alam"]

        # Clean phone number for WhatsApp fallback
        phone_clean = re.sub(r'[^\d+]', '', whatsapp_number) if whatsapp_number else ""
        if phone_clean and not phone_clean.startswith('+'):
            if phone_clean.startswith('60'):
                phone_clean = '+' + phone_clean
            elif phone_clean.startswith('0'):
                phone_clean = '+6' + phone_clean
            else:
                phone_clean = '+60' + phone_clean

        areas_options = "\n".join([f'<option value="{area}">{area}</option>' for area in delivery_areas])

        delivery_widget_html = f"""
<!-- Delivery Order Widget - Mobile Optimized -->
<div id="delivery-widget-overlay" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;
     background:rgba(0,0,0,0.5);z-index:9998;" onclick="closeDeliveryWidget()"></div>

<div id="delivery-widget" style="display:none;position:fixed;bottom:0;left:0;right:0;
     background:white;border-radius:20px 20px 0 0;z-index:9999;max-height:90vh;overflow-y:auto;
     box-shadow:0 -4px 20px rgba(0,0,0,0.15);padding:20px;">

  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
    <h3 style="margin:0;font-size:1.4rem;color:#1f2937;">🛵 Pesan Delivery</h3>
    <button onclick="closeDeliveryWidget()" style="background:none;border:none;font-size:1.5rem;cursor:pointer;color:#6b7280;">✕</button>
  </div>

  <form id="delivery-form" onsubmit="return submitDeliveryOrder(event)">
    <div style="margin-bottom:15px;">
      <label style="display:block;margin-bottom:5px;font-weight:600;color:#374151;font-size:0.9rem;">Nama *</label>
      <input type="text" id="delivery-name" name="customer_name" required
             style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:10px;font-size:1rem;box-sizing:border-box;"
             placeholder="Nama anda">
    </div>

    <div style="margin-bottom:15px;">
      <label style="display:block;margin-bottom:5px;font-weight:600;color:#374151;font-size:0.9rem;">No. Telefon *</label>
      <input type="tel" id="delivery-phone" name="customer_phone" required
             style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:10px;font-size:1rem;box-sizing:border-box;"
             placeholder="012-3456789">
    </div>

    <div style="margin-bottom:15px;">
      <label style="display:block;margin-bottom:5px;font-weight:600;color:#374151;font-size:0.9rem;">Kawasan Delivery *</label>
      <select id="delivery-area" name="delivery_area" required
              style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:10px;font-size:1rem;box-sizing:border-box;background:white;">
        <option value="">Pilih kawasan...</option>
        {areas_options}
        <option value="other">Lain-lain</option>
      </select>
    </div>

    <div style="margin-bottom:15px;">
      <label style="display:block;margin-bottom:5px;font-weight:600;color:#374151;font-size:0.9rem;">Alamat Penuh *</label>
      <textarea id="delivery-address" name="delivery_address" required rows="3"
                style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:10px;font-size:1rem;box-sizing:border-box;resize:none;"
                placeholder="No. rumah, jalan, taman, poskod"></textarea>
    </div>

    <div style="margin-bottom:15px;">
      <label style="display:block;margin-bottom:5px;font-weight:600;color:#374151;font-size:0.9rem;">Nota Tambahan</label>
      <textarea id="delivery-notes" name="notes" rows="2"
                style="width:100%;padding:12px;border:2px solid #e5e7eb;border-radius:10px;font-size:1rem;box-sizing:border-box;resize:none;"
                placeholder="Arahan khas, landmark, dll."></textarea>
    </div>

    <div id="delivery-summary" style="background:#f9fafb;padding:15px;border-radius:10px;margin-bottom:15px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span style="color:#6b7280;">Jumlah Item:</span>
        <span id="delivery-item-count" style="font-weight:600;">0 item</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span style="color:#6b7280;">Subtotal:</span>
        <span id="delivery-subtotal" style="font-weight:600;">RM 0.00</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span style="color:#6b7280;">Delivery Fee:</span>
        <span id="delivery-fee-display" style="font-weight:600;">RM 0.00</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding-top:8px;border-top:1px solid #e5e7eb;">
        <span style="font-weight:700;font-size:1.1rem;">Jumlah:</span>
        <span id="delivery-total" style="font-weight:700;font-size:1.1rem;color:#059669;">RM 0.00</span>
      </div>
    </div>

    <div id="delivery-error" style="display:none;background:#fef2f2;color:#dc2626;padding:12px;border-radius:10px;margin-bottom:15px;font-size:0.9rem;"></div>

    <button type="submit" id="delivery-submit-btn"
            style="width:100%;padding:15px;background:linear-gradient(135deg,#059669,#10b981);color:white;
            border:none;border-radius:10px;font-size:1.1rem;font-weight:bold;cursor:pointer;
            display:flex;align-items:center;justify-content:center;gap:8px;">
      <span>🛵</span>
      <span>Hantar Pesanan</span>
    </button>
  </form>
</div>

<!-- Delivery Button (Floating) -->
<button id="delivery-btn" onclick="openDeliveryWidget()"
        style="position:fixed;bottom:90px;right:20px;background:linear-gradient(135deg,#059669,#10b981);
        color:white;padding:12px 20px;border-radius:30px;border:none;font-size:1rem;font-weight:600;
        cursor:pointer;z-index:1000;box-shadow:0 4px 15px rgba(5,150,105,0.4);
        display:flex;align-items:center;gap:8px;">
  <span>🛵</span>
  <span>Pesan Delivery</span>
</button>

<script>
// Delivery Widget JavaScript - Mobile Optimized
const DELIVERY_API_URL = 'https://binaapp-backend.onrender.com/api/delivery/orders';
const WEBSITE_ID = '{website_id}';
const WHATSAPP_NUMBER = '{phone_clean}';
const DELIVERY_FEES = {{
  'Bandar Sunway': 5,
  'Petaling Jaya': 7,
  'Subang Jaya': 6,
  'Shah Alam': 8,
  'other': 10
}};

// Safe string conversion - prevents "undefined" strings
function safeString(value) {{
  if (value === null || value === undefined || value === 'null' || value === 'undefined') {{
    return '';
  }}
  return String(value).trim();
}}

function openDeliveryWidget() {{
  document.getElementById('delivery-widget').style.display = 'block';
  document.getElementById('delivery-widget-overlay').style.display = 'block';
  document.body.style.overflow = 'hidden';
  updateDeliverySummary();
}}

function closeDeliveryWidget() {{
  document.getElementById('delivery-widget').style.display = 'none';
  document.getElementById('delivery-widget-overlay').style.display = 'none';
  document.body.style.overflow = '';
}}

function getCartItems() {{
  try {{
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    return cart;
  }} catch (e) {{
    return [];
  }}
}}

function updateDeliverySummary() {{
  const cart = getCartItems();
  const subtotal = cart.reduce((sum, item) => sum + (item.price || 0), 0);
  const area = document.getElementById('delivery-area').value;
  const deliveryFee = DELIVERY_FEES[area] || 0;
  const total = subtotal + deliveryFee;

  document.getElementById('delivery-item-count').textContent = cart.length + ' item';
  document.getElementById('delivery-subtotal').textContent = 'RM ' + subtotal.toFixed(2);
  document.getElementById('delivery-fee-display').textContent = 'RM ' + deliveryFee.toFixed(2);
  document.getElementById('delivery-total').textContent = 'RM ' + total.toFixed(2);
}}

// Update delivery fee when area changes
document.getElementById('delivery-area').addEventListener('change', updateDeliverySummary);

async function submitDeliveryOrder(event) {{
  event.preventDefault();

  const errorDiv = document.getElementById('delivery-error');
  const submitBtn = document.getElementById('delivery-submit-btn');

  // Disable button and show loading
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span>⏳</span><span>Menghantar...</span>';
  errorDiv.style.display = 'none';

  try {{
    // Get form values with safe conversion
    const customerName = safeString(document.getElementById('delivery-name').value);
    const customerPhone = safeString(document.getElementById('delivery-phone').value);
    const deliveryArea = safeString(document.getElementById('delivery-area').value);
    const deliveryAddress = safeString(document.getElementById('delivery-address').value);
    const notes = safeString(document.getElementById('delivery-notes').value);

    // Validate required fields
    if (!customerName || !customerPhone || !deliveryArea || !deliveryAddress) {{
      throw new Error('Sila isi semua ruangan yang diperlukan');
    }}

    // Get cart and calculate totals
    const cart = getCartItems();
    const subtotal = cart.reduce((sum, item) => sum + (item.price || 0), 0);
    const deliveryFee = DELIVERY_FEES[deliveryArea] || 0;
    const totalAmount = subtotal + deliveryFee;

    // Build order payload - all values are guaranteed strings/numbers
    const orderPayload = {{
      website_id: safeString(WEBSITE_ID),
      customer_name: customerName,
      customer_phone: customerPhone,
      customer_id: '', // Will be auto-generated by backend
      delivery_address: deliveryAddress,
      delivery_area: deliveryArea,
      items: JSON.stringify(cart.map(item => ({{
        name: safeString(item.name),
        price: Number(item.price) || 0,
        quantity: Number(item.quantity) || 1
      }}))),
      notes: notes,
      subtotal: Number(subtotal),
      delivery_fee: Number(deliveryFee),
      total_amount: Number(totalAmount),
      payment_method: 'cash'
    }};

    console.log('📦 Submitting order:', orderPayload);

    // Try API submission first
    const response = await fetch(DELIVERY_API_URL, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }},
      body: JSON.stringify(orderPayload)
    }});

    const result = await response.json();

    if (result.success) {{
      // Success! Show confirmation
      alert('✅ Pesanan berjaya dihantar!\\n\\nNo. Pesanan: ' + result.order_number + '\\n\\nKami akan hubungi anda untuk pengesahan.');

      // Clear cart
      localStorage.removeItem('cart');
      if (typeof updateCartUI === 'function') updateCartUI();

      // Close widget
      closeDeliveryWidget();

      // Reset form
      document.getElementById('delivery-form').reset();
    }} else {{
      // API returned error
      throw new Error(result.error_ms || result.error || 'Gagal menghantar pesanan');
    }}

  }} catch (error) {{
    console.error('❌ Order submission failed:', error);

    // Show error message
    errorDiv.textContent = error.message || 'Gagal menghantar pesanan. Sila cuba lagi.';
    errorDiv.style.display = 'block';

    // Offer WhatsApp fallback
    if (WHATSAPP_NUMBER && confirm('Pesanan gagal dihantar. Hantar melalui WhatsApp?')) {{
      sendViaWhatsApp();
    }}
  }} finally {{
    // Re-enable button
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<span>🛵</span><span>Hantar Pesanan</span>';
  }}

  return false;
}}

function sendViaWhatsApp() {{
  const customerName = safeString(document.getElementById('delivery-name').value);
  const customerPhone = safeString(document.getElementById('delivery-phone').value);
  const deliveryArea = safeString(document.getElementById('delivery-area').value);
  const deliveryAddress = safeString(document.getElementById('delivery-address').value);
  const notes = safeString(document.getElementById('delivery-notes').value);

  const cart = getCartItems();
  const subtotal = cart.reduce((sum, item) => sum + (item.price || 0), 0);
  const deliveryFee = DELIVERY_FEES[deliveryArea] || 0;
  const total = subtotal + deliveryFee;

  const itemsList = cart.map(item => '• ' + item.name + ' - RM ' + (item.price || 0).toFixed(2)).join('%0A');

  const message = `🛵 *PESANAN DELIVERY*%0A%0A` +
    `*Nama:* ${{customerName}}%0A` +
    `*Telefon:* ${{customerPhone}}%0A` +
    `*Kawasan:* ${{deliveryArea}}%0A` +
    `*Alamat:* ${{deliveryAddress}}%0A` +
    (notes ? `*Nota:* ${{notes}}%0A` : '') +
    `%0A*PESANAN:*%0A${{itemsList}}%0A%0A` +
    `Subtotal: RM ${{subtotal.toFixed(2)}}%0A` +
    `Delivery: RM ${{deliveryFee.toFixed(2)}}%0A` +
    `*JUMLAH: RM ${{total.toFixed(2)}}*`;

  window.open('https://wa.me/' + WHATSAPP_NUMBER + '?text=' + message, '_blank');
}}
</script>
"""

        # Inject before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", delivery_widget_html + "\n</body>")
        else:
            html += delivery_widget_html

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

        # Delivery Widget (for restaurants/food businesses)
        if "delivery" in features:
            html = self.inject_delivery_widget(
                html,
                website_id=user_data.get("website_id", ""),
                whatsapp_number=user_data.get("phone", ""),
                delivery_areas=user_data.get("delivery_areas")
            )

        # Contact Form
        if "contact" in features:
            html = self.inject_contact_form(html, user_data.get("email", ""))

        # QR Code
        if user_data.get("url"):
            html = self.inject_qr_code(html, user_data["url"])

        return html


# Create singleton instance
template_service = TemplateService()
