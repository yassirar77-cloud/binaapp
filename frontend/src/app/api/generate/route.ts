import { NextRequest, NextResponse } from 'next/server';

export const maxDuration = 120;
export const dynamic = 'force-dynamic';

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY;
const QWEN_API_KEY = process.env.QWEN_API_KEY || process.env.DASHSCOPE_API_KEY;
const STABILITY_API_KEY = process.env.STABILITY_API_KEY;

// ==================== STABILITY AI IMAGE GENERATION ====================
async function generateImage(prompt: string): Promise<string | null> {
  if (!STABILITY_API_KEY) {
    console.log('🎨 No Stability API key');
    return null;
  }

  try {
    console.log(`🎨 Generating: ${prompt.substring(0, 50)}...`);

    const response = await fetch(
      'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${STABILITY_API_KEY}`,
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          text_prompts: [
            { text: prompt + ', professional photography, high quality, realistic, commercial photo', weight: 1 },
            { text: 'blurry, bad quality, cartoon, illustration, drawing, art, painting, sketch, anime', weight: -1 }
          ],
          cfg_scale: 7,
          width: 1024,
          height: 576,
          steps: 30,
          samples: 1,
          style_preset: 'photographic'
        })
      }
    );

    if (response.ok) {
      const data = await response.json();
      const base64 = data.artifacts[0].base64;
      console.log('🎨 ✅ Image generated');
      return `data:image/png;base64,${base64}`;
    } else {
      const error = await response.text();
      console.log('🎨 ❌ Failed:', response.status, error);
    }
  } catch (e) {
    console.error('🎨 ❌ Error:', e);
  }

  return null;
}

function getImagePrompts(description: string, businessType: string): { hero: string; gallery: string[] } {
  const d = description.toLowerCase();

  if (businessType === 'fish_shop' || d.includes('ikan') || d.includes('fish') || d.includes('seafood')) {
    return {
      hero: 'Fresh fish market stall with variety of colorful fish on ice display, seafood market, bright lighting',
      gallery: [
        'Fresh red snapper fish on crushed ice at fish market',
        'Fresh prawns and shrimp on ice at seafood market display',
        'Fresh salmon fillets and tuna steaks at fish counter',
        'Variety of fresh tropical fish at traditional market'
      ]
    };
  }

  if (businessType === 'restaurant' || d.includes('makan') || d.includes('restoran') || d.includes('nasi') || d.includes('cafe')) {
    return {
      hero: 'Modern Malaysian restaurant interior with warm ambient lighting and elegant dining tables',
      gallery: [
        'Delicious nasi lemak with sambal, fried chicken and egg on banana leaf',
        'Professional chef cooking in modern restaurant kitchen',
        'Elegant restaurant table with Malaysian food dishes',
        'Variety of Malaysian cuisine dishes on wooden table'
      ]
    };
  }

  if (businessType === 'pet_shop' || d.includes('kucing') || d.includes('cat') || d.includes('pet')) {
    return {
      hero: 'Modern pet shop interior with cute cats and pet supplies on shelves',
      gallery: [
        'Adorable orange tabby cat sitting and looking at camera',
        'Premium cat food and pet supplies display on shelves',
        'Cute playful kittens in pet store',
        'Professional cat grooming service'
      ]
    };
  }

  if (businessType === 'salon' || d.includes('salon') || d.includes('rambut') || d.includes('hair') || d.includes('beauty')) {
    return {
      hero: 'Modern luxury hair salon interior with styling chairs and large mirrors',
      gallery: [
        'Professional hairstylist cutting womans hair in salon',
        'Hair coloring treatment at beauty salon',
        'Hair washing station at modern salon spa',
        'Professional hair styling products display'
      ]
    };
  }

  if (businessType === 'toys' || d.includes('mainan') || d.includes('toys') || d.includes('kids') || d.includes('kanak')) {
    return {
      hero: 'Colorful toy store interior with shelves full of toys and games',
      gallery: [
        'Educational toys and learning games for children display',
        'Cute stuffed animals and plush toys collection',
        'Colorful building blocks and construction toys',
        'Happy children playing with toys in store'
      ]
    };
  }

  if (d.includes('bakery') || d.includes('roti') || d.includes('kek') || d.includes('cake')) {
    return {
      hero: 'Artisan bakery display case with fresh bread and pastries, warm lighting',
      gallery: [
        'Freshly baked bread loaves on wooden shelf',
        'Beautiful decorated birthday cakes in bakery display',
        'Fresh croissants and danish pastries',
        'Baker preparing fresh dough in bakery kitchen'
      ]
    };
  }

  if (d.includes('kereta') || d.includes('car') || d.includes('bengkel') || d.includes('workshop') || d.includes('auto')) {
    return {
      hero: 'Modern car workshop garage with vehicles being serviced',
      gallery: [
        'Mechanic working on car engine under hood',
        'Car tire service and wheel balancing machine',
        'Auto mechanic inspecting car underneath on lift',
        'Modern automotive service center reception'
      ]
    };
  }

  if (d.includes('bunga') || d.includes('flower') || d.includes('florist')) {
    return {
      hero: 'Beautiful flower shop interior with colorful flower arrangements',
      gallery: [
        'Fresh roses bouquet in various colors',
        'Florist arranging beautiful flower bouquet',
        'Wedding flower arrangements and decorations',
        'Tropical flowers display at flower shop'
      ]
    };
  }

  if (businessType === 'photography' || d.includes('photo') || d.includes('gambar') || d.includes('wedding')) {
    return {
      hero: 'Professional photography studio with lighting equipment and backdrop',
      gallery: [
        'Beautiful wedding couple photo shoot outdoors',
        'Professional photographer with camera equipment',
        'Family portrait photography session in studio',
        'Event photography at celebration venue'
      ]
    };
  }

  if (businessType === 'clothing' || d.includes('pakaian') || d.includes('baju') || d.includes('fashion') || d.includes('butik')) {
    return {
      hero: 'Modern fashion boutique interior with clothing racks and displays',
      gallery: [
        'Elegant womens clothing on display rack',
        'Traditional Malaysian baju kurung collection',
        'Fashion accessories and handbags display',
        'Stylish mens clothing store interior'
      ]
    };
  }

  // Default
  return {
    hero: `Modern ${description} business storefront with professional setup`,
    gallery: [
      `${description} products on display shelf`,
      `${description} service in action`,
      `Happy customers at ${description}`,
      `${description} interior workspace`
    ]
  };
}

async function generateBusinessImages(description: string, businessType: string): Promise<{ hero: string; gallery: string[] } | null> {
  const prompts = getImagePrompts(description, businessType);

  console.log('🎨 GENERATING CUSTOM IMAGES WITH STABILITY AI');
  console.log(`   Business type: ${businessType}`);

  // Generate hero image
  const heroImage = await generateImage(prompts.hero);
  if (!heroImage) {
    console.log('🎨 ❌ Hero image failed');
    return null;
  }

  // Generate gallery images
  const galleryImages: string[] = [];
  for (let i = 0; i < prompts.gallery.length; i++) {
    console.log(`🎨 Gallery image ${i + 1}/${prompts.gallery.length}...`);
    const img = await generateImage(prompts.gallery[i]);
    if (img) {
      galleryImages.push(img);
    }
    // Small delay to avoid rate limiting
    await new Promise(r => setTimeout(r, 500));
  }

  if (galleryImages.length < 3) {
    console.log('🎨 ❌ Not enough gallery images');
    return null;
  }

  console.log(`🎨 ✅ Generated ${galleryImages.length + 1} images successfully`);

  return {
    hero: heroImage,
    gallery: galleryImages
  };
}

// ==================== FALLBACK STOCK IMAGES ====================
const STOCK_IMAGES: Record<string, { hero: string; gallery: string[] }> = {
  fish_shop: {
    hero: "https://images.unsplash.com/photo-1534043464124-3be32fe000c9?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1510130387422-82bed34b37e9?w=800&q=80","https://images.unsplash.com/photo-1498654200943-1088dd4438ae?w=800&q=80","https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=800&q=80","https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&q=80"]
  },
  restaurant: {
    hero: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80","https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80","https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80","https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800&q=80"]
  },
  pet_shop: {
    hero: "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800&q=80","https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800&q=80","https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800&q=80","https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80"]
  },
  salon: {
    hero: "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80","https://images.unsplash.com/photo-1559599101-f09722fb4948?w=800&q=80","https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=800&q=80","https://images.unsplash.com/photo-1562322140-8baeececf3df?w=800&q=80"]
  },
  toys: {
    hero: "https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=800&q=80","https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=800&q=80","https://images.unsplash.com/photo-1545558014-8692077e9b5c?w=800&q=80","https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=800&q=80"]
  },
  default: {
    hero: "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80","https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&q=80","https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800&q=80","https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&q=80"]
  }
};

// ==================== BUSINESS TYPE DETECTION ====================
function detectBusinessType(desc: string): string {
  const d = desc.toLowerCase();
  if (d.includes('ikan') || d.includes('fish') || d.includes('seafood') || d.includes('laut')) return 'fish_shop';
  if (d.includes('makan') || d.includes('restoran') || d.includes('food') || d.includes('nasi') || d.includes('cafe')) return 'restaurant';
  if (d.includes('kucing') || d.includes('cat') || d.includes('pet') || d.includes('haiwan')) return 'pet_shop';
  if (d.includes('salon') || d.includes('rambut') || d.includes('hair') || d.includes('beauty')) return 'salon';
  if (d.includes('mainan') || d.includes('toys') || d.includes('kids') || d.includes('kanak')) return 'toys';
  if (d.includes('photo') || d.includes('gambar') || d.includes('wedding')) return 'photography';
  if (d.includes('pakaian') || d.includes('baju') || d.includes('fashion') || d.includes('butik')) return 'clothing';
  if (d.includes('bakery') || d.includes('roti') || d.includes('kek') || d.includes('cake')) return 'bakery';
  if (d.includes('kereta') || d.includes('car') || d.includes('bengkel') || d.includes('workshop')) return 'car_workshop';
  if (d.includes('bunga') || d.includes('flower') || d.includes('florist')) return 'florist';
  if (d.includes('gym') || d.includes('fitness') || d.includes('senaman')) return 'gym';
  return 'default';
}

// ==================== DEEPSEEK V3 API ====================
async function callDeepSeek(prompt: string, task: string): Promise<string | null> {
  if (!DEEPSEEK_API_KEY) return null;
  try {
    console.log(`🔷 DEEPSEEK [${task}] - Calling API...`);
    const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${DEEPSEEK_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], temperature: 0.7, max_tokens: 8000 }),
    });
    if (res.ok) {
      const data = await res.json();
      console.log(`🔷 DEEPSEEK [${task}] - ✅ Success`);
      return data.choices[0].message.content;
    }
    console.log(`🔷 DEEPSEEK [${task}] - ❌ Failed: ${res.status}`);
  } catch (e) { console.error(`🔷 DEEPSEEK [${task}] - ❌ Error:`, e); }
  return null;
}

// ==================== QWEN API ====================
async function callQwen(prompt: string, task: string): Promise<string | null> {
  if (!QWEN_API_KEY) return null;
  try {
    console.log(`🟡 QWEN [${task}] - Calling API...`);
    const res = await fetch('https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${QWEN_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'qwen-max', messages: [{ role: 'user', content: prompt }], temperature: 0.8, max_tokens: 8000 }),
    });
    if (res.ok) {
      const data = await res.json();
      console.log(`🟡 QWEN [${task}] - ✅ Success`);
      return data.choices[0].message.content;
    }
    console.log(`🟡 QWEN [${task}] - ❌ Failed: ${res.status}`);
  } catch (e) { console.error(`🟡 QWEN [${task}] - ❌ Error:`, e); }
  return null;
}

function extractHtml(text: string): string {
  if (!text) return '';
  if (text.includes('```html')) return text.split('```html')[1].split('```')[0].trim();
  if (text.includes('```')) return text.split('```')[1].split('```')[0].trim();
  return text.trim();
}

// ==================== DUAL AI + STABILITY IMAGE GENERATION ====================
async function generateWebsite(description: string): Promise<string | null> {
  const businessType = detectBusinessType(description);

  console.log('');
  console.log('═'.repeat(60));
  console.log('🌐 WEBSITE GENERATION - TRIPLE AI MODE');
  console.log(`   Business: ${description.substring(0, 50)}...`);
  console.log(`   Type: ${businessType}`);
  console.log('═'.repeat(60));

  // STEP 1: Generate images with Stability AI
  let imgs = STOCK_IMAGES[businessType] || STOCK_IMAGES.default;

  if (STABILITY_API_KEY) {
    console.log('');
    console.log('🎨 STEP 1: Generating custom images with Stability AI...');
    const customImages = await generateBusinessImages(description, businessType);
    if (customImages) {
      imgs = customImages;
      console.log('🎨 ✅ Using AI-generated custom images');
    } else {
      console.log('🎨 ⚠️ Using fallback stock images');
    }
  } else {
    console.log('🎨 No Stability API key, using stock images');
  }

  // STEP 2: DeepSeek generates HTML structure
  console.log('');
  console.log('🔷 STEP 2: DeepSeek generating HTML structure...');

  const structurePrompt = `Generate a complete HTML website.

BUSINESS: ${description}
TYPE: ${businessType}

USE THESE EXACT IMAGES:
- Hero: ${imgs.hero}
- Gallery 1: ${imgs.gallery[0]}
- Gallery 2: ${imgs.gallery[1]}
- Gallery 3: ${imgs.gallery[2]}
- Gallery 4: ${imgs.gallery[3] || imgs.gallery[2]}

REQUIREMENTS:
1. Single HTML file with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive
3. Use EXACT image URLs - don't modify them
4. Modern professional design with gradient accents
5. Sections: Header, Hero (full width image), About, Services (3 cards), Gallery (4 images grid), Contact, Footer
6. WhatsApp floating button (60123456789)
7. Smooth scroll navigation

USE PLACEHOLDER TEXT:
[BUSINESS_NAME], [TAGLINE], [ABOUT_TEXT], [SERVICE_1_NAME], [SERVICE_1_DESC], [SERVICE_2_NAME], [SERVICE_2_DESC], [SERVICE_3_NAME], [SERVICE_3_DESC], [CONTACT_TEXT]

Output ONLY HTML code.`;

  let html = await callDeepSeek(structurePrompt, 'html_structure');
  if (!html) html = await callQwen(structurePrompt, 'html_fallback');
  if (!html) return null;

  html = extractHtml(html);

  // STEP 3: Qwen improves content
  console.log('');
  console.log('🟡 STEP 3: Qwen improving content...');

  const isMalay = /[a-z]*\s+(di|dan|untuk|dengan|yang|ini|itu|ada|jual|kami|saya)/i.test(description);

  const contentPrompt = `You are a Malaysian copywriter. Replace placeholders with compelling content.

BUSINESS: ${description}
LANGUAGE: ${isMalay ? 'Bahasa Malaysia' : 'English'}

REPLACE:
[BUSINESS_NAME] → Business name
[TAGLINE] → Catchy tagline (max 8 words)
[ABOUT_TEXT] → About section (2-3 sentences)
[SERVICE_1_NAME], [SERVICE_1_DESC] → First service
[SERVICE_2_NAME], [SERVICE_2_DESC] → Second service
[SERVICE_3_NAME], [SERVICE_3_DESC] → Third service
[CONTACT_TEXT] → Contact message

HTML TO UPDATE:
${html.substring(0, 8000)}

Return complete HTML with placeholders replaced. Output ONLY HTML.`;

  const improved = await callQwen(contentPrompt, 'content');
  if (improved) {
    html = extractHtml(improved);
    console.log('🟡 ✅ Content improved');
  }

  console.log('');
  console.log('═'.repeat(60));
  console.log('✅ GENERATION COMPLETE');
  console.log(`📄 Final HTML: ${html.length} chars`);
  console.log('═'.repeat(60));

  return html;
}

// ==================== API ENDPOINT ====================
export async function POST(request: NextRequest) {
  console.log('');
  console.log('🚀 API /api/generate called');
  console.log('🔑 DEEPSEEK:', DEEPSEEK_API_KEY ? '✅' : '❌');
  console.log('🔑 QWEN:', QWEN_API_KEY ? '✅' : '❌');
  console.log('🔑 STABILITY:', STABILITY_API_KEY ? '✅' : '❌');

  try {
    const { business_description } = await request.json();
    if (!business_description) {
      return NextResponse.json({ error: 'Description required' }, { status: 400 });
    }

    if (!DEEPSEEK_API_KEY && !QWEN_API_KEY) {
      return NextResponse.json({ error: 'No AI API keys configured' }, { status: 500 });
    }

    const html = await generateWebsite(business_description);
    if (!html) {
      return NextResponse.json({ error: 'Generation failed' }, { status: 500 });
    }

    return NextResponse.json({ success: true, html, styles: [{ style: 'modern', html }] });
  } catch (error: any) {
    console.error('❌ API error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    mode: 'triple-ai',
    deepseek: !!DEEPSEEK_API_KEY,
    qwen: !!QWEN_API_KEY,
    stability: !!STABILITY_API_KEY
  });
}
