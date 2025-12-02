# Supabase Storage Setup Guide

This guide explains how to set up Supabase Storage for hosting user-generated websites in BinaApp.

## Overview

BinaApp uses **Supabase Storage** to host all user-generated websites. Each website is stored in the following structure:

```
websites/
  ├── {user_id}/
  │   ├── {subdomain1}/
  │   │   ├── index.html
  │   │   └── assets/
  │   │       ├── image.jpg
  │   │       └── script.js
  │   └── {subdomain2}/
  │       └── index.html
  └── {another_user_id}/
      └── {subdomain}/
          └── index.html
```

## Step 1: Create Storage Bucket

1. **Go to your Supabase Dashboard**
   - Navigate to your project at [supabase.com](https://supabase.com)

2. **Open Storage Section**
   - Click on **Storage** in the left sidebar

3. **Create New Bucket**
   - Click **"New bucket"** button
   - Bucket name: `websites`
   - Public bucket: **Yes** (Enable public access)
   - Click **"Create bucket"**

## Step 2: Configure Bucket Policies

For public read access, you need to set up the correct policies:

1. **Go to Storage Policies**
   - In the Storage section, click on the `websites` bucket
   - Click on **"Policies"** tab

2. **Add SELECT Policy for Public Read**
   - Click **"New Policy"**
   - Policy name: `Public read access for websites`
   - Allowed operation: `SELECT`
   - Target roles: `public`
   - USING expression:
     ```sql
     true
     ```
   - Click **"Review"** then **"Save policy"**

3. **Add INSERT Policy for Authenticated Users**
   - Click **"New Policy"**
   - Policy name: `Users can upload their own websites`
   - Allowed operation: `INSERT`
   - Target roles: `authenticated`
   - USING expression:
     ```sql
     (bucket_id = 'websites' AND (storage.foldername(name))[1] = auth.uid()::text)
     ```
   - Click **"Review"** then **"Save policy"**

4. **Add UPDATE Policy for Authenticated Users**
   - Click **"New Policy"**
   - Policy name: `Users can update their own websites`
   - Allowed operation: `UPDATE`
   - Target roles: `authenticated`
   - USING expression:
     ```sql
     (bucket_id = 'websites' AND (storage.foldername(name))[1] = auth.uid()::text)
     ```
   - Click **"Review"** then **"Save policy"**

5. **Add DELETE Policy for Authenticated Users**
   - Click **"New Policy"**
   - Policy name: `Users can delete their own websites`
   - Allowed operation: `DELETE`
   - Target roles: `authenticated`
   - USING expression:
     ```sql
     (bucket_id = 'websites' AND (storage.foldername(name))[1] = auth.uid()::text)
     ```
   - Click **"Review"** then **"Save policy"**

## Step 3: Configure CORS (Optional)

If you need to access files from different domains:

1. Go to **Storage Settings**
2. Add allowed origins:
   ```
   https://binaapp.my
   http://localhost:3000
   ```

## Step 4: Update Environment Variables

Add this to your `backend/.env` file:

```env
STORAGE_BUCKET_NAME=websites
```

The Supabase URL and keys should already be configured:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

## Step 5: Test the Setup

You can test if storage is working correctly:

1. **Via Supabase Dashboard**
   - Go to Storage > websites bucket
   - Try uploading a test file manually
   - Check if you can access it via the public URL

2. **Via API**
   ```python
   from supabase import create_client

   supabase = create_client(
       "your-supabase-url",
       "your-service-role-key"
   )

   # Upload test file
   supabase.storage.from_("websites").upload(
       "test-user/test-site/index.html",
       b"<html><body>Test</body></html>",
       {"content-type": "text/html", "upsert": "true"}
   )

   # Get public URL
   url = supabase.storage.from_("websites").get_public_url(
       "test-user/test-site/index.html"
   )
   print(f"Public URL: {url}")
   ```

## File Structure Explained

### Why `{user_id}/{subdomain}/index.html`?

1. **Isolation**: Each user's websites are in their own folder
2. **Security**: RLS policies ensure users can only modify their own files
3. **Organization**: Easy to find and manage all websites for a user
4. **Scalability**: No naming conflicts between users

### Public URLs

When a website is uploaded to:
```
websites/abc123/myshop/index.html
```

It becomes accessible at:
```
https://your-project.supabase.co/storage/v1/object/public/websites/abc123/myshop/index.html
```

## Important Notes

### ✅ Advantages of Supabase Storage

- **Integrated**: Already using Supabase for database and auth
- **Free Tier**: 1GB storage free, then affordable pricing
- **CDN**: Automatic CDN distribution
- **Easy Setup**: No need for separate service configuration
- **RLS Support**: Row Level Security for access control

### ⚠️ Limitations

- **Custom Domains**: Supabase Storage URLs are long. For production, you may want to:
  - Use a reverse proxy with custom domain
  - Set up Cloudflare in front of Supabase Storage
  - Implement custom domain mapping (advanced)

### 🔒 Security

- **Row Level Security (RLS)**: Ensures users can only modify their own websites
- **Public Read**: Anyone can view published websites (as intended)
- **Authenticated Write**: Only logged-in users can upload

## Troubleshooting

### Issue: Files not publicly accessible

**Solution**: Ensure bucket is set to **Public** and SELECT policy exists for `public` role.

### Issue: Upload fails with permission error

**Solution**: Check that your service role key is correct and INSERT policy is configured.

### Issue: Can't delete files

**Solution**: Verify DELETE policy is set up correctly for authenticated users.

### Issue: URLs return 404

**Solution**:
1. Verify file was uploaded successfully in Supabase dashboard
2. Check the exact file path matches what you're requesting
3. Ensure bucket name is correct in the URL

## Migration from Cloudflare R2

If you were previously using R2, the migration steps are:

1. ✅ Update `storage_service.py` to use Supabase Storage
2. ✅ Remove R2 environment variables
3. ✅ Add `STORAGE_BUCKET_NAME` environment variable
4. ✅ Create Supabase Storage bucket with policies
5. ⚠️ **Optional**: Migrate existing files from R2 to Supabase

### File Migration Script (Optional)

If you have existing websites in R2, you can migrate them:

```python
# This is a one-time migration script
# Run this after setting up Supabase Storage

import boto3
from supabase import create_client

# R2 Client
r2 = boto3.client(
    's3',
    endpoint_url='your-r2-endpoint',
    aws_access_key_id='your-r2-key',
    aws_secret_access_key='your-r2-secret'
)

# Supabase Client
supabase = create_client('your-supabase-url', 'your-service-key')

# List all files in R2
response = r2.list_objects_v2(Bucket='binaapp-websites')

for obj in response.get('Contents', []):
    key = obj['Key']  # e.g., "myshop/index.html"

    # Download from R2
    file_obj = r2.get_object(Bucket='binaapp-websites', Key=key)
    content = file_obj['Body'].read()

    # Upload to Supabase Storage
    # Note: You need to add user_id to the path
    # Determine user_id from your database based on subdomain
    user_id = "get_user_id_from_database(subdomain)"
    new_path = f"{user_id}/{key}"

    supabase.storage.from_('websites').upload(
        new_path,
        content,
        {'content-type': 'text/html', 'upsert': 'true'}
    )
    print(f"Migrated: {key} -> {new_path}")
```

## Support

For issues with Supabase Storage:
- Check [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- Visit [Supabase Discord](https://discord.supabase.com)
- Open issue in BinaApp repository

---

**You're all set!** Your websites will now be stored in Supabase Storage with proper isolation and security. 🚀
