# BinaApp HTML Templates

This directory contains HTML templates and integration components that are used for generating websites.

## Directory Structure

```
templates/
├── base/                   # Base HTML structures
│   └── modern.html        # Modern base template
├── components/            # Reusable HTML components
│   ├── header.html
│   ├── footer.html
│   ├── hero.html
│   └── sections/
└── integrations/          # Integration code snippets
    ├── whatsapp.html      # WhatsApp floating button
    ├── cart.html          # Shopping cart system
    ├── maps.html          # Google Maps embed
    ├── contact-form.html  # Contact form
    ├── qr-code.html       # QR code generator
    └── social-share.html  # Social sharing buttons
```

## Auto-Include Integrations

Every generated website automatically includes:

1. **WhatsApp Ordering** (`whatsapp.html`)
   - Floating button (bottom-right)
   - Click-to-chat functionality
   - Optional: Quick order form

2. **Shopping Cart** (`cart.html`)
   - localStorage-based cart
   - Add to cart buttons
   - Cart icon with count
   - Simple checkout flow

3. **Google Maps** (`maps.html`)
   - Responsive map embed
   - Location marker
   - Address display

4. **Contact Form** (`contact-form.html`)
   - Name, email, phone, message fields
   - Client-side validation
   - Form submission handling

5. **QR Code** (`qr-code.html`)
   - Auto-generated QR for website URL
   - Downloadable QR code

6. **Social Sharing** (`social-share.html`)
   - Facebook, WhatsApp, Twitter, LinkedIn
   - Native share API support

## Usage in AI Generation

The AI service (`backend/app/services/ai_service.py`) uses these templates as reference when generating websites. The templates provide:

- Structure guidelines
- Code patterns
- Integration examples
- Best practices

## Customization

Templates can be customized for different:
- Business types (restaurant, retail, services)
- Languages (Malay, English)
- Color schemes
- Layouts
