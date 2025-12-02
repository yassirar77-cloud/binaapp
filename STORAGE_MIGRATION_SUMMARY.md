# Storage Migration Summary: R2 → Supabase Storage

## ✅ Changes Completed

### 1. **Updated Storage Service** (`backend/app/services/storage_service.py`)

**Before (Cloudflare R2):**
- Used boto3 S3-compatible client
- File structure: `{subdomain}/index.html`
- Required R2 credentials and endpoint

**After (Supabase Storage):**
- Uses Supabase Storage API via supabase-py
- File structure: `{user_id}/{subdomain}/index.html`
- Uses existing Supabase credentials

**New Functions Added:**
```python
async def upload_website(user_id, subdomain, html_content) -> str
async def get_website_url(user_id, subdomain) -> Optional[str]
async def delete_website(user_id, subdomain) -> bool
async def list_user_websites(user_id) -> List[Dict]
async def get_website_content(user_id, subdomain) -> Optional[str]
async def upload_asset(user_id, subdomain, file_name, file_content, content_type) -> str
```

**Maintained for Compatibility:**
```python
async def publish_website(subdomain, html_content, website_id, user_id) -> str
async def check_subdomain_exists(subdomain) -> bool
```

### 2. **Updated Configuration** (`backend/app/core/config.py`)

**Removed:**
```python
R2_ACCOUNT_ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME
R2_PUBLIC_URL
R2_ENDPOINT
```

**Added:**
```python
STORAGE_BUCKET_NAME: str = Field(default="websites", env="STORAGE_BUCKET_NAME")
```

### 3. **Updated Environment Files**

**Files Modified:**
- `.env.example`
- `backend/.env.example`

**Removed Variables:**
```env
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
R2_PUBLIC_URL=...
```

**Added Variable:**
```env
STORAGE_BUCKET_NAME=websites
```

### 4. **Updated API Endpoints** (`backend/app/api/v1/endpoints/websites.py`)

**Publish Endpoint:**
```python
# Now passes user_id to storage service
public_url = await storage_service.publish_website(
    subdomain=website["subdomain"],
    html_content=website["html_content"],
    website_id=website_id,
    user_id=current_user.get("sub")  # ← Added
)
```

**Delete Endpoint:**
```python
# Now passes user_id to storage service
await storage_service.delete_website(
    user_id=current_user.get("sub"),  # ← Added
    subdomain=website["subdomain"]
)
```

### 5. **Updated Dependencies** (`backend/requirements.txt`)

**Removed:**
```
boto3==1.34.34
botocore==1.34.34
```

**Already Present:**
```
supabase==2.3.4  # Already included, no changes needed
```

### 6. **Added Documentation**

**New File:** `database/SUPABASE_STORAGE_SETUP.md`

Comprehensive setup guide covering:
- Step-by-step bucket creation
- RLS policy configuration
- CORS setup
- Testing procedures
- Migration guide from R2
- Troubleshooting

---

## 📋 Setup Checklist

To use the new Supabase Storage setup, you need to:

- [ ] **1. Create Supabase Storage Bucket**
  - Go to Supabase Dashboard → Storage
  - Create bucket named `websites`
  - Make it **public**

- [ ] **2. Configure Bucket Policies**
  - Add SELECT policy for `public` role (read access)
  - Add INSERT/UPDATE/DELETE policies for `authenticated` role
  - See `database/SUPABASE_STORAGE_SETUP.md` for exact SQL

- [ ] **3. Update Environment Variables**
  ```bash
  # Add to backend/.env
  STORAGE_BUCKET_NAME=websites

  # Make sure these are already set:
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
  ```

- [ ] **4. Install/Update Dependencies**
  ```bash
  cd backend
  pip install -r requirements.txt
  ```

- [ ] **5. Restart Backend**
  ```bash
  # If running with Docker
  docker-compose restart backend

  # If running manually
  uvicorn app.main:app --reload
  ```

---

## 🔄 File Structure Change

### Old Structure (Cloudflare R2):
```
binaapp-websites/
  ├── myshop/
  │   └── index.html
  ├── restaurant/
  │   └── index.html
  └── salon/
      └── index.html
```

**Issues:**
- No user isolation
- Subdomain conflicts possible
- Hard to manage multi-user

### New Structure (Supabase Storage):
```
websites/
  ├── user-abc-123/
  │   ├── myshop/
  │   │   ├── index.html
  │   │   └── assets/
  │   └── restaurant/
  │       └── index.html
  └── user-def-456/
      └── salon/
          └── index.html
```

**Benefits:**
✅ User isolation (each user has their own folder)
✅ No subdomain conflicts between users
✅ Easy to list all websites for a user
✅ RLS policies for security
✅ Better organization

---

## 🔒 Security Improvements

### Supabase Row Level Security (RLS):

**Public Read Policy:**
- Anyone can view published websites
- Required for websites to be publicly accessible

**Authenticated Write Policies:**
- Users can only upload to their own folder (`{user_id}/`)
- Users can only update their own files
- Users can only delete their own files

**Example RLS Policy:**
```sql
-- Users can only modify files in their own folder
(bucket_id = 'websites' AND (storage.foldername(name))[1] = auth.uid()::text)
```

---

## 🌐 Public URLs

### Before (R2):
```
https://your-r2-public-url.com/myshop/index.html
```

### After (Supabase Storage):
```
https://your-project.supabase.co/storage/v1/object/public/websites/user-abc-123/myshop/index.html
```

**Note:** URLs are longer with Supabase Storage. For production, consider:
- Custom domain mapping
- Cloudflare proxy in front of Supabase
- URL shortening service

---

## ✅ Benefits of Supabase Storage

1. **Integrated Setup**
   - Already using Supabase for database and auth
   - No need for separate service credentials
   - Single dashboard for everything

2. **Cost-Effective**
   - 1GB free tier
   - $0.021/GB after that
   - No egress fees for first 2GB/day

3. **Security**
   - Built-in Row Level Security
   - User isolation by default
   - Granular access control

4. **Developer Experience**
   - Simple Python API via supabase-py
   - No need for boto3 or S3 client
   - Native async support

5. **Performance**
   - Automatic CDN distribution
   - Global edge caching
   - Fast file delivery

---

## ⚠️ Important Notes

### No Breaking Changes for Frontend
The API interface remains the same. Frontend code does **not** need any changes.

### Existing Websites
If you have existing websites in Cloudflare R2, you'll need to migrate them. See the migration script in `database/SUPABASE_STORAGE_SETUP.md`.

### Testing
After setup, test by:
1. Creating a new website via the dashboard
2. Publishing it
3. Checking if the public URL works
4. Verifying file is in Supabase Storage dashboard

---

## 📚 Documentation

- **Setup Guide:** `database/SUPABASE_STORAGE_SETUP.md`
- **Supabase Docs:** https://supabase.com/docs/guides/storage
- **Storage API Reference:** https://supabase.com/docs/reference/javascript/storage-from-upload

---

## 🐛 Troubleshooting

### Error: "Permission denied"
**Solution:** Check that RLS policies are configured correctly in Supabase dashboard.

### Error: "Bucket not found"
**Solution:** Ensure you created the `websites` bucket and set `STORAGE_BUCKET_NAME=websites` in .env

### Error: "Module not found: boto3"
**Solution:** This is expected. Run `pip install -r requirements.txt` to update dependencies.

### Public URL returns 404
**Solution:**
1. Check file was uploaded successfully in Supabase Storage dashboard
2. Verify bucket is set to **public**
3. Confirm SELECT policy exists for `public` role

---

## 🚀 Next Steps

1. Follow the setup checklist above
2. Read `database/SUPABASE_STORAGE_SETUP.md` for detailed instructions
3. Test website creation and publishing
4. Monitor storage usage in Supabase dashboard

All changes have been committed and pushed to the repository! 🎉
