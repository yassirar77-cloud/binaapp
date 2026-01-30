# BinaApp Support Knowledge Base

BinaApp is a comprehensive digital restaurant platform for Malaysian food businesses. This knowledge base covers common questions and solutions for restaurant owners using BinaApp.

---

## 1. Account Management

### How do I create a BinaApp account?
1. Visit https://binaapp.my
2. Click "Daftar" (Register) or "Get Started"
3. Enter your email address and create a password
4. Verify your email address by clicking the link sent to your inbox
5. Complete your business profile

### I forgot my password. How do I reset it?
1. Go to https://binaapp.my/login
2. Click "Lupa Kata Laluan?" (Forgot Password)
3. Enter your registered email address
4. Check your inbox for the password reset link
5. Click the link and create a new password (link expires in 1 hour)

### How do I change my email address?
Contact our support team at support.team@binaapp.my with:
- Your current email address
- Your new email address
- Your business name for verification

### How do I delete my account?
Email admin@binaapp.my with your deletion request. Please note:
- This action is permanent
- All your website data, orders, and settings will be deleted
- Active subscriptions will not be refunded

---

## 2. Restaurant Setup & Website

### How do I set up my restaurant website?
1. Log in to your BinaApp dashboard
2. Go to "Laman Web" (Website) section
3. Choose a template or use AI to generate your design
4. Add your restaurant details:
   - Business name and logo
   - Description
   - Operating hours
   - Contact information
   - Address with GPS coordinates

### How do I customize my website design?
In the website editor, you can:
- Change colors and fonts
- Upload your logo and images
- Edit menu layout
- Add promotional banners
- Customize the header and footer

### How do I set up my subdomain?
BinaApp provides free subdomains in the format: yourname.binaapp.my
1. Go to Settings → Domain
2. Enter your preferred subdomain name
3. Click "Simpan" (Save)
4. Your site will be live at yourname.binaapp.my

### Can I use my own custom domain?
Custom domains are available on PRO and BUSINESS plans.
1. Purchase your domain from a domain registrar
2. Go to Settings → Custom Domain in BinaApp
3. Enter your domain name
4. Configure DNS settings as instructed:
   - Add A record pointing to our IP
   - Add CNAME record for www subdomain
5. Wait for DNS propagation (up to 48 hours)

---

## 3. Menu Management

### How do I add menu items?
1. Go to "Menu" section in dashboard
2. Click "Tambah Item" (Add Item)
3. Fill in:
   - Item name (Bahasa Malaysia or English)
   - Description
   - Price (in RM)
   - Category
   - Image (recommended size: 800x800px)
4. Set availability status
5. Click "Simpan" (Save)

### How do I create menu categories?
1. Go to Menu → Categories
2. Click "Tambah Kategori" (Add Category)
3. Enter category name (e.g., "Nasi", "Minuman", "Pencuci Mulut")
4. Set display order
5. Save changes

### How do I mark items as sold out?
1. Go to Menu
2. Find the item
3. Toggle "Tersedia" (Available) to OFF
4. The item will show as "Habis" (Sold Out) on your website

### How do I set item variations and add-ons?
1. Edit the menu item
2. Scroll to "Pilihan" (Options) section
3. Add variations (e.g., size: Regular RM5, Large RM7)
4. Add add-ons (e.g., Extra cheese +RM1)
5. Save changes

---

## 4. Order Management

### How do I view new orders?
1. Log in to your dashboard
2. Go to "Pesanan" (Orders) section
3. New orders appear with notification sound
4. Orders show status: Pending, Confirmed, Preparing, Ready, Delivered

### What are the order statuses?
- **Pending**: Customer placed order, waiting for confirmation
- **Confirmed**: You accepted the order
- **Preparing**: Kitchen is preparing the food
- **Ready**: Food is ready for pickup/delivery
- **Picked Up**: Rider has collected the order
- **Delivered**: Order completed successfully
- **Cancelled**: Order was cancelled

### How do I accept or reject an order?
1. Click on the new order notification
2. Review order details
3. Click "Terima" (Accept) or "Tolak" (Reject)
4. If rejecting, provide a reason (e.g., item unavailable)

### How do I track order history?
Go to Orders → History to view:
- All past orders
- Filter by date range
- Filter by status
- Export orders to CSV

---

## 5. Subscription Plans

### What subscription plans are available?

**FREE Plan - RM0/month**
- Basic website
- Up to 20 menu items
- Basic order management
- BinaApp branding on website
- Community support

**PRO Plan - RM29/month**
- Everything in FREE
- Unlimited menu items
- Custom subdomain
- Remove BinaApp branding
- Priority support
- Basic analytics
- SMS notifications

**BUSINESS Plan - RM49/month**
- Everything in PRO
- Custom domain support
- Advanced analytics
- Multi-branch support
- API access
- Dedicated support
- BinaChat real-time messaging
- Delivery management system

### How do I upgrade my plan?
1. Go to Settings → Subscription
2. Click "Naik Taraf" (Upgrade)
3. Select your new plan
4. Complete payment via ToyyibPay
5. New features activate immediately

### How do I downgrade or cancel my subscription?
1. Go to Settings → Subscription
2. Click "Tukar Pelan" (Change Plan)
3. Select the new plan or "Batal Langganan" (Cancel)
4. Your current plan remains active until the end of billing period

### My subscription payment failed. What do I do?
1. Check your payment method has sufficient funds
2. Go to Settings → Subscription → Payment History
3. Click "Cuba Lagi" (Try Again) on the failed payment
4. If problems persist, contact support.team@binaapp.my

---

## 6. Payment Integration (ToyyibPay)

### How do I set up ToyyibPay?
1. Create account at https://toyyibpay.com
2. Complete merchant verification (IC, SSM for businesses)
3. Get your API Secret Key and Category Code
4. In BinaApp: Settings → Payments → ToyyibPay
5. Enter your Secret Key and Category Code
6. Enable payment gateway
7. Test with a small transaction

### Why are my payments not going through?
Common issues:
- **Invalid API Key**: Double-check your ToyyibPay credentials
- **Category Code mismatch**: Ensure correct category code
- **Account not verified**: Complete ToyyibPay verification
- **Sandbox mode**: Ensure sandbox is disabled for live payments

### How do customers pay?
Customers can pay via:
- FPX (online banking)
- Credit/Debit cards
- E-wallets (supported by ToyyibPay)

### When do I receive my money?
ToyyibPay settlements typically process:
- Within 1-3 business days for FPX
- Within 7 business days for card payments
- Contact ToyyibPay for specific settlement queries

---

## 7. Delivery System

### How do I enable delivery?
1. Go to Settings → Delivery
2. Toggle "Aktifkan Penghantaran" (Enable Delivery)
3. Set delivery radius (in km)
4. Set delivery fees based on distance
5. Configure delivery hours

### How do I add delivery riders?
1. Go to Delivery → Riders
2. Click "Tambah Rider" (Add Rider)
3. Enter rider details:
   - Name
   - Phone number
   - Vehicle type
   - Vehicle number
4. Rider will receive login credentials via SMS

### How does GPS tracking work?
- Riders use the BinaApp Rider app
- Real-time GPS location updates every 30 seconds
- Customers can track rider location on map
- Restaurant dashboard shows all active deliveries

### How do I assign orders to riders?
1. When order status is "Ready"
2. Click "Tugaskan Rider" (Assign Rider)
3. Select available rider from list
4. Rider receives notification
5. Track delivery progress in real-time

---

## 8. BinaChat (Real-Time Messaging)

### What is BinaChat?
BinaChat enables real-time messaging between:
- Customers and Restaurant
- Restaurant and Riders
- Support communication

### How do I use BinaChat?
1. Go to Chat section in dashboard
2. View active conversations
3. Reply to customer messages
4. Send order updates
5. Coordinate with riders

### How do customers contact me via chat?
Customers can:
- Click "Chat" button on your website
- Message through order tracking page
- Send inquiries about menu items

---

## 9. Common Errors & Solutions

### "Sesi Tamat Tempoh" (Session Expired)
- Your login session has expired
- Solution: Log in again with your credentials

### "Tidak Dapat Menyimpan" (Unable to Save)
- Check your internet connection
- Ensure all required fields are filled
- Try refreshing the page
- Clear browser cache and try again

### "Pembayaran Gagal" (Payment Failed)
- Check payment method validity
- Ensure sufficient funds
- Try a different payment method
- Contact support if issue persists

### "Menu Tidak Dikemaskini" (Menu Not Updating)
- Clear your browser cache
- Wait 5 minutes for CDN to update
- Try viewing in incognito mode

### "Gambar Tidak Dapat Dimuat Naik" (Image Upload Failed)
- Check image format (JPG, PNG only)
- Maximum file size: 5MB
- Recommended dimensions: 800x800px
- Try compressing the image

### "Pesanan Tidak Diterima" (Orders Not Received)
- Check notification settings
- Ensure you're logged into dashboard
- Check internet connection
- Enable browser notifications

---

## 10. Contact Information

### Support Team
- Email: support.team@binaapp.my
- Response time: Within 24 hours on business days
- Languages: Bahasa Malaysia, English

### Admin/Billing
- Email: admin@binaapp.my
- For subscription and billing inquiries

### Emergency Support
For urgent issues affecting your business:
- Email: admin@binaapp.my with subject "URGENT"
- Include your business name and detailed description

### Operating Hours
Support is available:
- Monday - Friday: 9:00 AM - 6:00 PM (MYT)
- Saturday: 9:00 AM - 1:00 PM (MYT)
- Sunday & Public Holidays: Closed

### Social Media
- Website: https://binaapp.my
- Facebook: BinaApp Malaysia

---

## 11. Tips for Success

### Optimize Your Menu
- Use high-quality food photos
- Write clear, appetizing descriptions
- Keep prices competitive
- Organize into logical categories
- Update availability regularly

### Improve Order Efficiency
- Set realistic preparation times
- Update order status promptly
- Communicate delays to customers
- Maintain adequate rider coverage

### Grow Your Business
- Share your BinaApp website on social media
- Collect customer feedback
- Analyze order trends in analytics
- Offer promotions during slow periods

---

*Last updated: January 2026*
*BinaApp - Platform Restoran Digital Malaysia*
