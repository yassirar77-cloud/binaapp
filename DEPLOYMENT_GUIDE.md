# BinaApp Deployment Guide

This guide will help you deploy BinaApp's backend and frontend to production.

## Overview

- **Backend**: FastAPI app deployed on Render
- **Frontend**: Next.js app deployed on Vercel
- **Domain**: binaapp.my (Namecheap)

---

## 🚀 Part 1: Deploy Backend to Render

### Step 1: Push Code to GitHub

Make sure all your changes are committed and pushed to the `claude/fix-vercel-deployment-01UckqG3tPyMFWTb1U8ZydW5` branch (or merge to main).

### Step 2: Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `yassirar77-cloud/binaapp`
4. Configure the service:
   - **Name**: `binaapp-backend`
   - **Region**: Singapore (or closest to your users)
   - **Branch**: `main` (or your deployment branch)
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: Leave empty (uses render.yaml)
   - **Start Command**: Leave empty (uses render.yaml)
   - **Instance Type**: Starter ($7/month)

### Step 3: Configure Environment Variables

In the Render dashboard, add these environment variables:

```
DATABASE_URL=postgresql://...  # Your PostgreSQL connection string (if using Render PostgreSQL)
SUPABASE_URL=<your-supabase-url>
SUPABASE_ANON_KEY=<your-supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-supabase-service-role-key>
JWT_SECRET_KEY=binaapp-secret-2025
QWEN_API_KEY=<your-qwen-api-key>
DEEPSEEK_API_KEY=<your-deepseek-api-key>
STRIPE_SECRET_KEY=sk_test_placeholder
FRONTEND_URL=https://binaapp.my
ENVIRONMENT=production
PYTHON_VERSION=3.11.7
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Detect `render.yaml`
   - Use `runtime.txt` to install Python 3.11.7
   - Install dependencies from `requirements.txt`
   - Start your FastAPI app

3. Wait for deployment to complete (5-10 minutes first time)
4. Your backend will be available at: `https://binaapp-backend.onrender.com`
5. Test health endpoint: `https://binaapp-backend.onrender.com/health`

### Troubleshooting Render

If deployment fails:
- Check the **Logs** tab in Render dashboard
- Verify Python version: Should show `Python 3.11.7`
- Ensure all environment variables are set
- Check that `runtime.txt` contains exactly: `python-3.11.7`

---

## 🎨 Part 2: Deploy Frontend to Vercel

### Step 1: Install Vercel CLI (Optional)

```bash
npm i -g vercel
```

Or use the Vercel web dashboard (recommended for first deployment).

### Step 2: Deploy via Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Import `yassirar77-cloud/binaapp` repository
4. Configure project:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend` ✅ (Very Important!)
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)
   - **Install Command**: `npm install` (auto-detected)

### Step 3: Configure Environment Variables

In Vercel project settings, add these environment variables:

```
NEXT_PUBLIC_API_URL=https://binaapp-backend.onrender.com
NEXT_PUBLIC_SUPABASE_URL=<your-supabase-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=<your-stripe-public-key>
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<your-google-maps-key>
```

### Step 4: Deploy

1. Click **"Deploy"**
2. Vercel will:
   - Install dependencies from `frontend/package.json`
   - Build your Next.js app
   - Deploy to production

3. Your frontend will be available at: `https://binaapp-frontend.vercel.app` (or similar)

### Troubleshooting Vercel

If deployment fails:
- Check **Build Logs** in Vercel dashboard
- Verify **Root Directory** is set to `frontend`
- Ensure all `NEXT_PUBLIC_*` environment variables are set
- Check that `vercel.json` is configured correctly

---

## 🌐 Part 3: Connect Custom Domain (binaapp.my)

### Step 1: Configure Vercel for Custom Domain

1. In Vercel project, go to **Settings** → **Domains**
2. Add your domain: `binaapp.my`
3. Also add: `www.binaapp.my`
4. Vercel will provide DNS records to configure

### Step 2: Update Namecheap DNS

1. Log in to [Namecheap](https://www.namecheap.com/)
2. Go to **Domain List** → Click **Manage** next to `binaapp.my`
3. Go to **Advanced DNS** tab
4. Add/Update these records:

**For Root Domain (binaapp.my):**
```
Type: A Record
Host: @
Value: 76.76.21.21 (Vercel IP - check Vercel dashboard for latest)
TTL: Automatic
```

**For WWW:**
```
Type: CNAME Record
Host: www
Value: cname.vercel-dns.com
TTL: Automatic
```

**Alternative (if Vercel gives you CNAME for root):**
```
Type: CNAME Record
Host: @
Value: cname.vercel-dns.com
TTL: Automatic
```

### Step 3: Configure Backend CORS

The backend is already configured to allow your domain in `render.yaml`:
```yaml
FRONTEND_URL=https://binaapp.my
```

Make sure your FastAPI CORS settings allow your domain (check `backend/app/main.py`).

### Step 4: Wait for DNS Propagation

- DNS changes can take 5 minutes to 48 hours
- Usually takes 15-30 minutes
- Check status: https://dnschecker.org/#A/binaapp.my

---

## ✅ Final Verification

### 1. Test Backend
```bash
curl https://binaapp-backend.onrender.com/health
```
Should return:
```json
{"status": "healthy", "timestamp": "...", "version": "1.0.0"}
```

### 2. Test Frontend
Visit: https://binaapp.my
- Should load your Next.js app
- Check browser console for any API connection errors

### 3. Test Full Integration
1. Try creating an account
2. Try logging in
3. Check if API calls work properly

---

## 🔧 Post-Deployment Configuration

### Update Backend URL in Frontend

If you haven't already, update the `NEXT_PUBLIC_API_URL` in Vercel:
```
NEXT_PUBLIC_API_URL=https://binaapp-backend.onrender.com
```

Then redeploy the frontend.

### Enable HTTPS Only

Both Render and Vercel automatically provide SSL certificates. Ensure:
- Always use `https://` URLs
- Enable "Force HTTPS" in Vercel settings if needed

### Monitor Your Apps

**Render:**
- Check logs at: https://dashboard.render.com/
- Monitor performance and errors
- Free tier: Service sleeps after 15 minutes of inactivity (Starter plan: Always on ✅)

**Vercel:**
- Check deployments at: https://vercel.com/dashboard
- Monitor analytics
- Check function logs

---

## 💡 Quick Commands Reference

### Redeploy Backend (Render)
```bash
git push origin main  # Render auto-deploys on push
```

### Redeploy Frontend (Vercel)
```bash
git push origin main  # Vercel auto-deploys on push
# OR
cd frontend && vercel --prod
```

### Check Logs
```bash
# Render: Use dashboard
# Vercel: Use dashboard or CLI
vercel logs <deployment-url>
```

---

## 🆘 Common Issues & Solutions

### Issue: "Python 3.13 not compatible with greenlet"
**Solution**: ✅ Fixed! We added `runtime.txt` with `python-3.11.7`

### Issue: Vercel deployment fails
**Solution**:
- Ensure **Root Directory** is set to `frontend` in Vercel settings
- Check that `vercel.json` exists and is configured correctly
- Verify all environment variables are set

### Issue: API calls fail from frontend
**Solution**:
- Check `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Verify CORS is configured properly in backend
- Check browser console for CORS errors

### Issue: Domain not working
**Solution**:
- Wait 15-30 minutes for DNS propagation
- Verify DNS records in Namecheap
- Check Vercel domain status

### Issue: Render service is slow
**Solution**:
- Starter plan keeps service always active ($7/month) ✅
- Free tier services sleep after 15 minutes (not your case)

---

## 📞 Support

If you encounter issues:
1. Check Render logs: https://dashboard.render.com/
2. Check Vercel logs: https://vercel.com/dashboard
3. Review this guide
4. Check the deployment configuration files:
   - `backend/runtime.txt`
   - `render.yaml`
   - `vercel.json`
   - `frontend/next.config.js`

---

## 🎉 Success!

Once everything is deployed:
- Frontend: https://binaapp.my
- Backend: https://binaapp-backend.onrender.com
- API Docs: https://binaapp-backend.onrender.com/docs

Your BinaApp is now live! 🚀
