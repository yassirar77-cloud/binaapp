# BinaApp 🚀

AI-powered no-code website builder for Malaysian SMEs

## Overview

BinaApp allows Malaysian SMEs to create fully functional websites by simply describing what they want in Bahasa Malaysia or English. Our AI generates complete HTML with pre-integrated features and publishes to a custom subdomain instantly.

## Features

- 🤖 **AI-Powered Generation**: Describe your website in plain language (Bahasa/English)
- 🚀 **One-Click Publish**: Instant deployment to `yourname.binaapp.my`
- 📱 **Auto-Integrations**: WhatsApp ordering, shopping cart, Google Maps, contact forms
- 💳 **Payment Ready**: Stripe integration for subscriptions
- 🎨 **Live Preview**: See your website as it's being generated
- 🔐 **Secure Authentication**: Powered by Supabase Auth
- 🖌️ **Design Studio**: 12 palettes, 27 font pairings, light/dark and a "shuffle"
  re-roll — applied instantly and **free**, because a recolour rewrites the
  live page's colour tokens instead of regenerating it (see
  [docs/DESIGN_STUDIO_AND_QR.md](docs/DESIGN_STUDIO_AND_QR.md))
- 🖨️ **QR Toolkit**: offline-rendered QR codes plus a print-ready A4 poster in
  the site's own colours — one code per table for dine-in
- 🔍 **SEO Files**: per-site `robots.txt` and `sitemap.xml`, generated from the
  page actually being served
- 📣 **Promo Kit**: branded WhatsApp link previews (an auto-generated
  `og:image` in the site's own palette, served at `/share-card.png`), a
  1080×1920 story poster with the site QR, a "scan to save our number"
  vCard QR poster, and a "scan to join our Wi-Fi" QR poster — all rendered
  offline and **free** (see [docs/PROMO_KIT.md](docs/PROMO_KIT.md))
- 🍽️ **Business Kit**: a print-ready A4 menu/price list generated from the
  merchant's real menu data, a "beri kami 5 bintang" Google-review QR
  poster, a scan-to-order WhatsApp QR (per-table), and a live
  "Buka sekarang / Tutup" badge computed from the page's own opening hours —
  all offline and **free** (see [docs/BUSINESS_KIT.md](docs/BUSINESS_KIT.md))

## Tech Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI**: DeepSeek V3
- **Storage**: Cloudflare R2
- **Auth**: Supabase Auth
- **Payments**: Stripe

## Project Structure

```
binaapp/
├── frontend/              # Next.js 14 application
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   ├── lib/          # Utilities and configs
│   │   └── types/        # TypeScript types
│   ├── public/           # Static assets
│   └── package.json
│
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Core configurations
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   └── main.py      # Application entry
│   ├── requirements.txt
│   └── Dockerfile
│
├── templates/            # HTML templates for generated sites
│   ├── base/
│   ├── components/
│   └── integrations/
│
├── database/            # Database migrations and schemas
│   └── supabase/
│
└── docker-compose.yml   # Local development setup
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- Supabase account
- DeepSeek API key
- Cloudflare R2 account
- Stripe account

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yassirar77-cloud/binaapp.git
   cd binaapp
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

3. **Start with Docker** (Recommended)
   ```bash
   docker-compose up -d
   ```

   Or run individually:

4. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

5. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Environment Variables

See `.env.example` for all required environment variables.

## Auto-Include Integrations

Every generated website automatically includes:

1. **WhatsApp Ordering**: Floating button + checkout flow
2. **Shopping Cart**: localStorage-based cart system
3. **Google Maps**: Embedded location maps
4. **Contact Forms**: Email-ready contact forms
5. **QR Codes**: Auto-generated for each page
6. **Social Sharing**: Share buttons for all major platforms

## Deployment

### Frontend (Vercel)
```bash
cd frontend
vercel --prod
```

### Backend (Railway/Fly.io)
```bash
cd backend
fly deploy
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, email support@binaapp.my or join our Telegram group.

## Roadmap

- [ ] Multi-language support (Bahasa, English, Chinese)
- [ ] Custom domain support
- [ ] Advanced e-commerce features
- [ ] Mobile app (React Native)
- [ ] White-label solutions
- [ ] AI chatbot integration

---

**Built with ❤️ for Malaysian SMEs**
# BinaApp 
