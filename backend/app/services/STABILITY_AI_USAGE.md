# Stability AI Image Generation for BinaApp

## Overview

BinaApp now supports AI-generated images for Malaysian businesses using Stability AI. This provides custom, professional images that perfectly match your business description instead of stock photos.

## Features

- ✅ **150+ Malaysian-specific prompts** for food, fashion, salon services, and more
- ✅ **Automatic fallback** to stock Unsplash images if AI generation fails
- ✅ **Smart image caching** in Supabase Storage
- ✅ **Cost-effective** - only generates when needed
- ✅ **High-quality** images using Stability AI Core

## Setup

### 1. Get Stability AI API Key

1. Sign up at [Stability AI](https://platform.stability.ai/)
2. Get your API key from [Account Settings](https://platform.stability.ai/account/keys)

### 2. Add to Environment Variables

Add to your Render environment (or `.env` file):

```bash
STABILITY_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Verify Storage is Set Up

Make sure these are also configured:

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
```

## Usage

### Basic Usage - Get Product Image

```python
from app.services.ai_service import ai_service

# Get image for a Malaysian product (tries AI first, falls back to stock)
image_url = await ai_service.get_product_image(
    item_name="Nasi Kandar",
    business_type="food",
    use_ai=True  # Set to False to skip AI and use stock images only
)

# Use the image URL in your HTML
html = f'<img src="{image_url}" alt="Nasi Kandar" />'
```

### Direct Stability AI Generation

```python
from app.services.stability_service import (
    generate_malaysian_image,
    save_image_to_storage,
    get_malaysian_prompt
)
import os

# Generate an AI image
image_base64 = await generate_malaysian_image(
    item_name="Baju Kurung",
    business_type="fashion",
    aspect_ratio="1:1"  # or "16:9", "4:3", etc.
)

# Save to Supabase Storage
if image_base64:
    filename = "baju-kurung-12345.webp"
    public_url = await save_image_to_storage(
        image_base64,
        filename,
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
    )
    print(f"Image saved at: {public_url}")
```

### Get Custom Prompt

```python
from app.services.stability_service import get_malaysian_prompt, MALAYSIAN_PROMPTS

# Get the AI prompt for a specific item
prompt = get_malaysian_prompt("Laksa Penang", "food")
print(prompt)
# Output: "Penang assam laksa with rice noodles in tangy fish broth, cucumber, onion, pineapple, mint, shrimp paste, food photography"

# Browse all available prompts
for item, prompt in MALAYSIAN_PROMPTS.items():
    print(f"{item}: {prompt[:60]}...")
```

## Supported Categories

### Food (60+ dishes)
- Rice dishes: Nasi Kandar, Nasi Lemak, Nasi Kerabu, Nasi Biryani, etc.
- Noodles: Mee Goreng, Char Kway Teow, Laksa, Hokkien Mee, etc.
- Chicken: Ayam Goreng, Ayam Rendang, Ayam Percik, etc.
- Seafood: Ikan Bakar, Udang Sambal, Ketam Masak Cili, etc.
- Snacks: Satay, Karipap, Pisang Goreng, Rojak, etc.
- Drinks: Teh Tarik, Milo Dinosaur, Sirap Bandung, etc.

### Fashion
- Women: Baju Kurung, Tudung, Hijab, Kebaya, Jubah, etc.
- Men: Baju Melayu, Sampin, Songkok
- Accessories: Rantai, Anting, Handbag, Jam Tangan, etc.

### Services
- Hair Salon: Haircut, Hair Coloring, Hair Treatment, Styling, etc.
- Beauty & Spa: Facial, Massage, Manicure, Pedicure, Makeup, etc.
- Automotive: Car Wash, Bengkel, Car Service, Tayar, etc.

### General Business
- Restaurant, Cafe, Bakery, Grocery, Pharmacy, Gym, etc.

## Pricing & Cost Control

Stability AI Core costs approximately **$0.03 per image**.

### Cost Control Strategies

1. **Hero images only**: Use AI for hero/banner images, stock for products
2. **Cache images**: Images are automatically saved to Supabase Storage
3. **Conditional generation**: Only use AI for key products/services
4. **Disable AI**: Set `use_ai=False` to use stock images only

### Example: Selective AI Usage

```python
# Use AI for hero image
hero_image = await ai_service.get_product_image(
    "Nasi Kandar Special",
    business_type="food",
    use_ai=True  # Generate custom hero image
)

# Use stock for gallery
gallery_images = []
for item in ["Ayam Goreng", "Ikan Bakar", "Rendang"]:
    img = await ai_service.get_product_image(
        item,
        business_type="food",
        use_ai=False  # Use stock images to save cost
    )
    gallery_images.append(img)
```

## API Reference

### `generate_malaysian_image()`

Generate AI image for Malaysian products/services.

**Parameters:**
- `item_name` (str): Product/service name (e.g., "Nasi Lemak")
- `business_type` (str, optional): Business category ("food", "fashion", "salon", etc.)
- `aspect_ratio` (str, optional): Image ratio ("1:1", "16:9", "4:3", etc.) - default "1:1"

**Returns:**
- Base64 encoded image string or None if failed

### `get_malaysian_prompt()`

Get the optimized prompt for a Malaysian item.

**Parameters:**
- `item_name` (str): Product/service name
- `business_type` (str, optional): Business category

**Returns:**
- Detailed prompt string for Stability AI

### `save_image_to_storage()`

Save generated image to Supabase Storage.

**Parameters:**
- `image_base64` (str): Base64 encoded image
- `filename` (str): Filename to save as (e.g., "nasi-lemak-abc123.webp")
- `supabase_url` (str): Supabase project URL
- `supabase_key` (str): Supabase anon key

**Returns:**
- Public URL of saved image or None if failed

## Troubleshooting

### Images not generating

1. **Check API key**: Verify `STABILITY_API_KEY` is set correctly
2. **Check logs**: Look for error messages in application logs
3. **Check balance**: Ensure you have credits in your Stability AI account
4. **Test connectivity**: Try generating a simple image manually

### Images not saving

1. **Check Supabase**: Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
2. **Check bucket**: Ensure `menu-images` bucket exists in Supabase Storage
3. **Check permissions**: Verify bucket has public access enabled

### Fallback to stock images

This is normal! If AI generation fails for any reason, the system automatically falls back to curated Unsplash stock images. Your website will still have beautiful images.

## Examples

See the AI service for examples of how images are automatically integrated into website generation.

## Support

For issues or questions, please check:
- [Stability AI Documentation](https://platform.stability.ai/docs)
- [BinaApp GitHub Issues](https://github.com/yassirar77-cloud/binaapp/issues)
