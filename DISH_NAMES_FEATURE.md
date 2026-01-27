# Dish Names Generation Feature

## Overview
The dish names generation feature allows users to provide custom names for gallery images during website generation. The AI uses these names to create compelling content, headings, and descriptions for each dish/product in the generated website.

## Implementation Details

### Frontend Flow

#### 1. Image Upload Component (`VisualImageUpload.tsx`)
- **Location**: `frontend/src/app/create/components/VisualImageUpload.tsx`
- **Lines**: 269-276

The component provides text inputs below each gallery image where users can enter dish names:

```typescript
<input
  type="text"
  placeholder="Nama hidangan (cth: Nasi Lemak)"
  value={galleryData[index].name}
  onChange={(e) => handleGalleryNameChange(index, e.target.value)}
  className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
/>
```

#### 2. Data Structure
Gallery images are stored with the following structure:

```typescript
interface GalleryImage {
  url: string
  name: string
}
```

Each gallery item in the component state contains:
```typescript
{
  file: File | null
  preview: string
  url: string
  name: string
}
```

#### 3. Parent Component (`create/page.tsx`)
- **Location**: `frontend/src/app/create/page.tsx`
- **Lines**: 179-198

When generating, the component:
1. Combines hero and gallery images with metadata
2. Includes dish names in the payload
3. Sends to backend API

```typescript
const galleryWithMetadata = uploadedImages.gallery.map(g => ({
  url: g.url,
  name: g.name || ''  // Ensure name is always a string
}));

const allImages = uploadedImages.hero
  ? [{ url: uploadedImages.hero, name: 'Hero Image' }, ...galleryWithMetadata]
  : galleryWithMetadata;

const startResponse = await fetch('https://binaapp-backend.onrender.com/api/generate/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    description: description,
    business_description: description,
    language: language,
    user_id: user?.id || 'anonymous',
    email: user?.email,
    images: allImages.length > 0 ? allImages : undefined,
    gallery_metadata: uploadedImages.gallery
  }),
});
```

### Backend Flow

#### 1. API Endpoint (`backend/app/api/simple/generate.py`)
- **Location**: `backend/app/api/simple/generate.py`
- **Lines**: 24-44

The `SimpleGenerateRequest` model now supports:

```python
class SimpleGenerateRequest(BaseModel):
    """Simplified generation request"""
    description: str = Field(...)
    user_id: Optional[str] = Field(default="demo-user")
    images: Optional[List] = Field(
        default=[],
        description="Optional list of uploaded image URLs or image metadata objects with url and name"
    )
    gallery_metadata: Optional[List] = Field(
        default=[],
        description="Gallery images with metadata (url, name)"
    )
    business_description: Optional[str] = Field(default=None)
    language: Optional[str] = Field(default="ms")
    email: Optional[str] = Field(default=None)
    # ... other fields
```

#### 2. Image Processing (`backend/app/services/ai_service.py`)
- **Location**: `backend/app/services/ai_service.py`
- **Lines**: 1647-1672

Helper functions extract image URLs and names:

```python
def get_image_url(img):
    if isinstance(img, dict):
        return img.get('url', img.get('URL', ''))
    return str(img)

def get_image_name(img):
    if isinstance(img, dict):
        return img.get('name', '')
    return ''

# Map uploaded images to expected keys
if len(request.uploaded_images) > 0:
    image_urls["hero"] = get_image_url(request.uploaded_images[0])
if len(request.uploaded_images) > 1:
    image_urls["gallery1"] = get_image_url(request.uploaded_images[1])
    image_urls["gallery1_name"] = get_image_name(request.uploaded_images[1])
# ... repeat for gallery2, gallery3, gallery4
```

#### 3. AI Prompt Enhancement (`backend/app/services/ai_service.py`)
- **Location**: `backend/app/services/ai_service.py`
- **Lines**: 1754-1779

Dish names are included in the AI prompt:

```python
gallery_items = []
for i in range(1, 5):
    key = f'gallery{i}'
    name_key = f'gallery{i}_name'
    if key in image_urls:
        dish_name = image_urls.get(name_key, '')
        if dish_name:
            gallery_items.append(
                f"- Product/Gallery image {i}: {image_urls[key]} (Dish: {dish_name})"
            )
        else:
            gallery_items.append(
                f"- Product/Gallery image {i}: {image_urls[key]}"
            )

image_instructions = f"""
USE THESE EXACT IMAGE URLS IN THE HTML:
- Hero/Banner image: {image_urls.get('hero', 'generate appropriate image')}
{gallery_text}

IMPORTANT INSTRUCTIONS:
1. Use these EXACT URLs in the img src attributes. Do NOT use placeholder or Unsplash URLs.
2. For gallery images with dish names, use those names in your headings, titles, and descriptions.
3. Write compelling descriptions for each dish based on its name and the business type.
4. Make sure ALL 4 gallery images are displayed in the gallery section.
"""
```

## Data Flow Diagram

```
┌──────────────────────────────────────┐
│  User enters dish name in text input │
│  (e.g., "Nasi Lemak")                │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  handleGalleryNameChange()           │
│  - Updates galleryData[index].name   │
│  - Calls onImagesUploaded callback   │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Create Page State                   │
│  - uploadedImages.gallery[]          │
│  - Each item: { url, name }          │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  handleGenerate()                    │
│  - Combines hero + gallery images    │
│  - Sends to backend API              │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  POST /api/generate/start            │
│  Request body:                       │
│  {                                   │
│    images: [                         │
│      { url: "...", name: "Hero" },   │
│      { url: "...", name: "Nasi" }    │
│    ],                                │
│    gallery_metadata: [...]           │
│  }                                   │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Backend Processing                  │
│  - generate_variants_background()    │
│  - Creates WebsiteGenerationRequest  │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  AI Service                          │
│  - Extracts image URLs and names     │
│  - Builds image_urls dict            │
│  - Creates prompt with dish names    │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  DeepSeek AI Generation              │
│  - Receives prompt with dish names   │
│  - Generates HTML with:              │
│    • Dish names in headings          │
│    • Custom descriptions             │
│    • Proper image placement          │
└──────────────────────────────────────┘
```

## Usage Example

### User Input
1. Uploads hero image
2. Uploads 4 gallery images:
   - Image 1: Uploads `nasi-lemak.jpg`, enters name: "Nasi Lemak Special"
   - Image 2: Uploads `mee-goreng.jpg`, enters name: "Mee Goreng Mamak"
   - Image 3: Uploads `roti-canai.jpg`, enters name: "Roti Canai Crispy"
   - Image 4: Uploads `teh-tarik.jpg`, enters name: "Teh Tarik Original"

### Generated Output
The AI will create a website with:
- Hero section with the hero image
- Menu/gallery section with 4 items:
  - **Nasi Lemak Special** - Compelling description based on "Nasi Lemak Special"
  - **Mee Goreng Mamak** - Compelling description based on "Mee Goreng Mamak"
  - **Roti Canai Crispy** - Compelling description based on "Roti Canai Crispy"
  - **Teh Tarik Original** - Compelling description based on "Teh Tarik Original"

## Key Features

1. **Real-time Updates**: Dish names update immediately when user types
2. **Optional Names**: If no name provided, defaults to "Hidangan X" or generates generic content
3. **Multiple Languages**: Supports both Malay and English dish names
4. **Context-Aware**: AI uses dish names with business context to create better descriptions
5. **Flexible Input**: Accepts various image metadata formats for backward compatibility

## Technical Notes

- **Type Safety**: Uses TypeScript interfaces to ensure type safety
- **Backward Compatibility**: Supports both string URLs and object metadata
- **Error Handling**: Gracefully handles missing names with defaults
- **Performance**: Names sent with initial request, no additional API calls needed
- **Validation**: No strict validation on names, allows user creativity

## Future Enhancements

Potential improvements:
1. Add price fields for each dish
2. Allow dish descriptions/ingredients input
3. Support dietary tags (vegetarian, halal, spicy, etc.)
4. Enable image categorization (appetizers, mains, desserts)
5. Allow custom sorting/ordering of dishes in generated site

## Testing

To test the feature:

1. Navigate to `/create` page
2. Upload 1 hero image and 1-4 gallery images
3. Enter custom names for each gallery image
4. Click "Generate"
5. Verify generated website uses the custom dish names in:
   - Menu headings
   - Item titles
   - Descriptions
   - Alt text (if implemented)

## Related Files

### Frontend
- `frontend/src/app/create/components/VisualImageUpload.tsx` - Image upload component
- `frontend/src/app/create/page.tsx` - Main generation page
- `frontend/src/lib/env.ts` - API base URL configuration

### Backend
- `backend/app/api/simple/generate.py` - Generation API endpoint
- `backend/app/services/ai_service.py` - AI generation logic
- `backend/app/models/schemas.py` - Request/response models
- `backend/app/services/job_service.py` - Async job management

## API Reference

### POST /api/generate/start

**Request Body:**
```json
{
  "description": "A Malaysian restaurant serving traditional food",
  "business_description": "A Malaysian restaurant serving traditional food",
  "language": "ms",
  "user_id": "user123",
  "email": "user@example.com",
  "images": [
    { "url": "https://cloudinary.../hero.jpg", "name": "Hero Image" },
    { "url": "https://cloudinary.../dish1.jpg", "name": "Nasi Lemak Special" },
    { "url": "https://cloudinary.../dish2.jpg", "name": "Mee Goreng Mamak" }
  ],
  "gallery_metadata": [
    { "url": "https://cloudinary.../dish1.jpg", "name": "Nasi Lemak Special" },
    { "url": "https://cloudinary.../dish2.jpg", "name": "Mee Goreng Mamak" }
  ]
}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Generation started. Poll /generate/status/{job_id} for updates."
}
```

### GET /api/generate/status/{job_id}

**Response:**
```json
{
  "status": "completed",
  "progress": 100,
  "styles": [
    {
      "style": "Modern",
      "html": "<html>...</html>",
      "preview_image": "https://..."
    },
    {
      "style": "Minimal",
      "html": "<html>...</html>",
      "preview_image": "https://..."
    },
    {
      "style": "Bold",
      "html": "<html>...</html>",
      "preview_image": "https://..."
    }
  ],
  "metadata": {
    "features": ["whatsapp", "menu", "gallery"],
    "template_used": "Restaurant Template"
  }
}
```

## Conclusion

The dish names generation feature enhances the AI-generated websites by providing context-aware content based on user-provided names. This creates more personalized and accurate website content, particularly for food businesses, restaurants, and cafes.
