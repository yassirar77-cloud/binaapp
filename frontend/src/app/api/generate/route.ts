import { NextRequest, NextResponse } from 'next/server';

export const maxDuration = 120;
export const dynamic = 'force-dynamic';

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY;
const QWEN_API_KEY = process.env.QWEN_API_KEY || process.env.DASHSCOPE_API_KEY;
const STABILITY_API_KEY = process.env.STABILITY_API_KEY;

// ==================== STABILITY AI ====================
async function generateImage(prompt: string): Promise<string | null> {
  if (!STABILITY_API_KEY) return null;

  try {
    console.log(`🎨 Generating: ${prompt.substring(0, 40)}...`);

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
            { text: `${prompt}, professional photography, high quality, realistic, commercial photo`, weight: 1 },
            { text: 'blurry, bad quality, cartoon, illustration, drawing, anime, sketch', weight: -1 }
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
      console.log('🎨 ✅ Image generated');
      return `data:image/png;base64,${data.artifacts[0].base64}`;
    }
    console.log('🎨 ❌ Failed:', response.status);
  } catch (e) {
    console.error('🎨 Error:', e);
  }
  return null;
}

function getImagePrompts(description: string): { hero: string; gallery: string[] } {
  const d = description.toLowerCase();

  // Teddy Bear / Plush toys
  if (d.includes('teddy') || d.includes('bear') || d.includes('plush') || d.includes('patung')) {
    return {
      hero: 'Cute teddy bear shop with many soft plush toys on wooden shelves, warm cozy lighting, gift shop interior',
      gallery: [
        'Adorable brown teddy bear sitting, soft fluffy plush toy, cute',
        'Collection of colorful teddy bears on display shelf, toy store',
        'Giant pink teddy bear in gift shop, cute plush toy',
        'Small cute teddy bears with ribbon bows, gift wrapped'
      ]
    };
  }

  // Fish / Seafood
  if (d.includes('ikan') || d.includes('fish') || d.includes('seafood') || d.includes('laut')) {
    return {
      hero: 'Fresh fish market stall with variety of seafood on crushed ice, bright clean display',
      gallery: [
        'Fresh red snapper fish on ice at market',
        'Fresh prawns and shrimp on ice display',
        'Fresh salmon and tuna fillets at fish counter',
        'Variety of tropical fish at wet market'
      ]
    };
  }

  // Restaurant / Food
  if (d.includes('makan') || d.includes('restoran') || d.includes('food') || d.includes('nasi') || d.includes('cafe')) {
    return {
      hero: 'Modern Malaysian restaurant interior with warm lighting and elegant dining tables',
      gallery: [
        'Delicious nasi lemak with sambal and fried chicken on banana leaf',
        'Chef cooking in professional restaurant kitchen',
        'Elegant restaurant table setting with food',
        'Malaysian cuisine dishes spread on table'
      ]
    };
  }

  // Pet Shop / Cats
  if (d.includes('kucing') || d.includes('cat') || d.includes('pet') || d.includes('haiwan')) {
    return {
      hero: 'Modern pet shop interior with cute cats and pet supplies on shelves',
      gallery: [
        'Adorable orange tabby cat portrait',
        'Cat food and pet supplies on shelves',
        'Cute playful kittens in pet store',
        'Cat grooming service'
      ]
    };
  }

  // Salon / Beauty
  if (d.includes('salon') || d.includes('rambut') || d.includes('hair') || d.includes('beauty')) {
    return {
      hero: 'Modern luxury hair salon interior with styling chairs and mirrors',
      gallery: [
        'Hairstylist cutting hair in salon',
        'Hair coloring treatment at beauty salon',
        'Hair washing station at modern salon',
        'Hair styling products display'
      ]
    };
  }

  // Bakery / Cakes
  if (d.includes('bakery') || d.includes('roti') || d.includes('kek') || d.includes('cake')) {
    return {
      hero: 'Artisan bakery display with fresh bread and pastries, warm lighting',
      gallery: [
        'Fresh baked bread loaves on shelf',
        'Beautiful decorated birthday cakes',
        'Fresh croissants and pastries',
        'Baker preparing dough in kitchen'
      ]
    };
  }

  // Car Workshop
  if (d.includes('kereta') || d.includes('car') || d.includes('bengkel') || d.includes('workshop')) {
    return {
      hero: 'Modern car workshop garage with vehicles being serviced',
      gallery: [
        'Mechanic working on car engine',
        'Car tire service and wheel balancing',
        'Auto mechanic under car on lift',
        'Automotive service center'
      ]
    };
  }

  // Florist
  if (d.includes('bunga') || d.includes('flower') || d.includes('florist')) {
    return {
      hero: 'Beautiful flower shop with colorful arrangements and bouquets',
      gallery: [
        'Fresh roses bouquet in various colors',
        'Florist arranging flower bouquet',
        'Wedding flower decorations',
        'Tropical flowers display'
      ]
    };
  }

  // Default
  return {
    hero: `${description} business storefront, modern professional`,
    gallery: [
      `${description} products display`,
      `${description} service`,
      `Happy customer at ${description}`,
      `${description} interior`
    ]
  };
}

async function generateBusinessImages(description: string): Promise<{ hero: string; gallery: string[] } | null> {
  const prompts = getImagePrompts(description);

  console.log('🎨 GENERATING IMAGES WITH STABILITY AI...');

  const hero = await generateImage(prompts.hero);
  if (!hero) return null;

  const gallery: string[] = [];
  for (let i = 0; i < prompts.gallery.length; i++) {
    console.log(`🎨 Gallery ${i + 1}/4...`);
    const img = await generateImage(prompts.gallery[i]);
    if (img) gallery.push(img);
    await new Promise(r => setTimeout(r, 300));
  }

  if (gallery.length < 3) return null;

  console.log(`🎨 ✅ Generated ${gallery.length + 1} images`);
  return { hero, gallery };
}

// ==================== FALLBACK IMAGES ====================
const FALLBACK_IMAGES: Record<string, { hero: string; gallery: string[] }> = {
  teddy: {
    hero: "https://images.unsplash.com/photo-1558679908-541bcf1249ff?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1562040506-a9b32cb51b94?w=800&q=80","https://images.unsplash.com/photo-1559454403-b8fb88521f11?w=800&q=80","https://images.unsplash.com/photo-1530325553241-4f6e7690cf36?w=800&q=80","https://images.unsplash.com/photo-1566669437687-7040a6926753?w=800&q=80"]
  },
  default: {
    hero: "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80","https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&q=80","https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800&q=80","https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&q=80"]
  }
};

// ==================== AI CALLS ====================
async function callDeepSeek(prompt: string): Promise<string | null> {
  if (!DEEPSEEK_API_KEY) return null;
  try {
    console.log('🔷 Calling DeepSeek...');
    const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${DEEPSEEK_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], temperature: 0.7, max_tokens: 8000 }),
    });
    if (res.ok) {
      console.log('🔷 ✅ DeepSeek success');
      return (await res.json()).choices[0].message.content;
    }
  } catch (e) { console.error('DeepSeek error:', e); }
  return null;
}

async function callQwen(prompt: string): Promise<string | null> {
  if (!QWEN_API_KEY) return null;
  try {
    console.log('🟡 Calling Qwen...');
    const res = await fetch('https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${QWEN_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'qwen-max', messages: [{ role: 'user', content: prompt }], temperature: 0.8, max_tokens: 8000 }),
    });
    if (res.ok) {
      console.log('🟡 ✅ Qwen success');
      return (await res.json()).choices[0].message.content;
    }
  } catch (e) { console.error('Qwen error:', e); }
  return null;
}

function extractHtml(text: string): string {
  if (!text) return '';
  if (text.includes('```html')) return text.split('```html')[1].split('```')[0].trim();
  if (text.includes('```')) return text.split('```')[1].split('```')[0].trim();
  return text.trim();
}

// ==================== MAIN GENERATION ====================
async function generateWebsite(
  description: string,
  opts?: { image_choice?: string; features?: Record<string, any> }
): Promise<string | null> {
  console.log('');
  console.log('🌐 WEBSITE GENERATION - TRIPLE AI MODE');
  console.log(`   Description: ${description.substring(0, 50)}...`);

  const imageChoice = (opts?.image_choice || 'ai').toLowerCase().trim();
  const features = opts?.features || {};
  const whatsappEnabled = typeof features.whatsapp === 'boolean' ? features.whatsapp : true;

  // Step 1: Generate images (ONLY if user wants images)
  let imgs: { hero: string; gallery: string[] } | null = null;
  if (imageChoice !== 'none') {
    imgs = FALLBACK_IMAGES.default;
    if (description.toLowerCase().includes('teddy') || description.toLowerCase().includes('bear')) {
      imgs = FALLBACK_IMAGES.teddy;
    }

    if (STABILITY_API_KEY && imageChoice === 'ai') {
      console.log('🎨 Step 1: Generating custom images...');
      const customImgs = await generateBusinessImages(description);
      if (customImgs) {
        imgs = customImgs;
      } else {
        console.log('🎨 Using fallback images');
      }
    }
  }

  // Step 2: Generate HTML with DeepSeek
  console.log('🔷 Step 2: Generating HTML...');

  const imageRequirements =
    imageChoice === 'none'
      ? `IMAGES:
- DO NOT include ANY images.
- Do NOT use <img> tags.
- Do NOT use background-image CSS.
- Do NOT use Unsplash/Pexels/placeholder images.
`
      : `USE THESE EXACT IMAGE URLs:
- Hero: ${imgs?.hero}
- Gallery 1: ${imgs?.gallery?.[0]}
- Gallery 2: ${imgs?.gallery?.[1]}
- Gallery 3: ${imgs?.gallery?.[2]}
- Gallery 4: ${imgs?.gallery?.[3] || imgs?.gallery?.[2]}
`;

  const whatsappRequirements = whatsappEnabled
    ? `- WhatsApp floating button (60123456789)\n`
    : `- DO NOT include WhatsApp button or WhatsApp links\n`;

  const sectionsRequirements =
    imageChoice === 'none'
      ? `4. Sections: Header, Hero (no image), About, Services (3 cards), Contact, Footer\n`
      : `4. Sections: Header, Hero (full-width image), About, Services (3 cards), Gallery (4 images), Contact, Footer\n`;

  const htmlPrompt = `Create a complete HTML website for: ${description}

${imageRequirements}

REQUIREMENTS:
1. Single HTML file with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive design
3. Modern professional look with gradients
${sectionsRequirements}${whatsappRequirements}6. Use Bahasa Malaysia if description is in Malay
7. If image_choice is 'none', strictly follow the no-images rules above.
8. If image_choice is not 'none', use the EXACT image URLs provided - do not change them

Output ONLY the complete HTML code.`;

  let html = await callDeepSeek(htmlPrompt);
  if (!html) html = await callQwen(htmlPrompt);
  if (!html) return null;

  html = extractHtml(html);
  console.log('✅ Website generated!');

  // Safety: enforce opts (remove WhatsApp/images if disabled)
  if (!whatsappEnabled) {
    html = html.replace(/<a[^>]*(wa\.me|whatsapp)[^>]*>[\s\S]*?<\/a>/gi, '');
    html = html.replace(/href="https?:\/\/wa\.me[^"]*"/gi, 'href="#"');
    html = html.replace(/href="https?:\/\/(?:api\.)?whatsapp\.com[^"]*"/gi, 'href="#"');
  }
  if (imageChoice === 'none') {
    html = html.replace(/<img[^>]*>/gi, '');
    html = html.replace(/background-image\s*:\s*url\([^)]*\)\s*;?/gi, '');
    html = html.replace(/https?:\/\/(?:images\.)?unsplash\.com[^\s'"<>]*/gi, '');
    html = html.replace(/https?:\/\/(?:www\.)?pexels\.com[^\s'"<>]*/gi, '');
  }

  return html;
}

// ==================== API ENDPOINT ====================
export async function POST(request: NextRequest) {
  console.log('');
  console.log('═'.repeat(50));
  console.log('🚀 /api/generate called');
  console.log('Keys:', {
    deepseek: !!DEEPSEEK_API_KEY,
    qwen: !!QWEN_API_KEY,
    stability: !!STABILITY_API_KEY
  });
  console.log('═'.repeat(50));

  try {
    const body = await request.json();
    const description = body.business_description || body.description || '';
    const image_choice = body.image_choice || body.imageChoice || 'ai';
    const features = body.features || {};

    if (!description) {
      return NextResponse.json({ error: 'Description required' }, { status: 400 });
    }

    if (!DEEPSEEK_API_KEY && !QWEN_API_KEY) {
      return NextResponse.json({ error: 'No AI API keys' }, { status: 500 });
    }

    const html = await generateWebsite(description, { image_choice, features });

    if (!html) {
      return NextResponse.json({ error: 'Generation failed' }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      html,
      styles: [{ style: 'modern', html }]
    });

  } catch (error: any) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    keys: {
      deepseek: !!DEEPSEEK_API_KEY,
      qwen: !!QWEN_API_KEY,
      stability: !!STABILITY_API_KEY
    }
  });
}
