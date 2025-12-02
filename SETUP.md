# BinaApp Setup Guide

Complete setup instructions for BinaApp development and deployment.

## Prerequisites

Ensure you have the following installed:

- **Node.js** 18+ (for frontend)
- **Python** 3.11+ (for backend)
- **Docker & Docker Compose** (recommended for local development)
- **Git**

### Required API Keys and Services

1. **Supabase** - Database and Authentication
   - Sign up at [supabase.com](https://supabase.com)
   - Create a new project
   - Get your project URL and API keys

2. **DeepSeek** - AI Generation
   - Sign up at [DeepSeek platform](https://platform.deepseek.com)
   - Get your API key

3. **Cloudflare R2** - Website Hosting
   - Sign up at [Cloudflare](https://cloudflare.com)
   - Create an R2 bucket named `binaapp-websites`
   - Get your Account ID and Access Keys

4. **Stripe** - Payments (optional for free tier)
   - Sign up at [stripe.com](https://stripe.com)
   - Get your API keys

5. **Google Maps API** - Maps Integration (optional)
   - Enable at [Google Cloud Console](https://console.cloud.google.com)

## Local Development Setup

### Option 1: Using Docker (Recommended)

1. **Clone and setup environment**
   ```bash
   git clone https://github.com/yassirar77-cloud/binaapp.git
   cd binaapp
   cp .env.example .env
   ```

2. **Configure environment variables**
   Edit `.env` and fill in your API keys

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000

#### Frontend Setup

```bash
# Navigate to frontend (in a new terminal)
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your credentials

# Run development server
npm run dev
```

Frontend will be available at http://localhost:3000

## Database Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a project
2. Wait for the project to be ready

### 2. Run Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Copy the contents of `database/supabase/schema.sql`
3. Paste and run the SQL

This will create:
- User profiles table
- Subscriptions table
- Websites table
- Analytics table
- Templates table
- All necessary triggers and functions

### 3. Configure Row Level Security (RLS)

The schema already includes RLS policies. Verify they're enabled:
1. Go to **Authentication** > **Policies**
2. Ensure all tables have policies enabled

## Environment Variables

### Backend (.env)

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DEEPSEEK_API_KEY=your_deepseek_key
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=binaapp-websites
R2_PUBLIC_URL=https://your-r2-url.com
JWT_SECRET_KEY=generate_random_string_here

# Optional
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
GOOGLE_MAPS_API_KEY=your_maps_key
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_...
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_maps_key
```

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Production Deployment

### Backend (Railway/Fly.io/Render)

1. **Railway**
   ```bash
   cd backend
   railway init
   railway up
   ```

2. **Fly.io**
   ```bash
   cd backend
   fly launch
   fly deploy
   ```

### Frontend (Vercel)

1. **Via Vercel CLI**
   ```bash
   cd frontend
   npm install -g vercel
   vercel --prod
   ```

2. **Via GitHub**
   - Connect your repository to Vercel
   - Set environment variables in Vercel dashboard
   - Deploy automatically on push

### Cloudflare R2 Setup

1. Create R2 bucket: `binaapp-websites`
2. Configure public access for the bucket
3. Set up custom domain (optional): `cdn.binaapp.my`

### Stripe Webhooks

1. In Stripe Dashboard, go to **Developers** > **Webhooks**
2. Add endpoint: `https://your-api-domain.com/api/v1/payments/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copy webhook secret to environment variables

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.11+)
- Ensure all environment variables are set
- Check if port 8000 is available

### Frontend build fails
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (should be 18+)

### Database connection errors
- Verify Supabase URL and keys
- Check if Supabase project is active
- Ensure RLS policies are configured correctly

### AI generation not working
- Verify DeepSeek API key
- Check API quota/limits
- Review backend logs for errors

## Support

For issues and questions:
- GitHub Issues: https://github.com/yassirar77-cloud/binaapp/issues
- Email: support@binaapp.my

## Next Steps

After setup:
1. Create a test account
2. Generate your first website
3. Test all integrations
4. Configure your domain
5. Set up monitoring (optional)
