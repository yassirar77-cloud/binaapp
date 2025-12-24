import { NextRequest, NextResponse } from 'next/server';

export const maxDuration = 120;
export const dynamic = 'force-dynamic';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'https://binaapp-backend.onrender.com';
const USE_ASYNC_GENERATION = true; // Set to true to use async polling instead of direct call

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY;
const QWEN_API_KEY = process.env.QWEN_API_KEY || process.env.DASHSCOPE_API_KEY;

const IMAGES: Record<string, { hero: string; gallery: string[] }> = {
  pet_shop: {
    hero: "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800&q=80","https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800&q=80","https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800&q=80","https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80"]
  },
  restaurant: {
    hero: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80","https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80","https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80","https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800&q=80"]
  },
  salon: {
    hero: "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80","https://images.unsplash.com/photo-1559599101-f09722fb4948?w=800&q=80","https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=800&q=80","https://images.unsplash.com/photo-1562322140-8baeececf3df?w=800&q=80"]
  },
  photography: {
    hero: "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1554048612-b6a482bc67e5?w=800&q=80","https://images.unsplash.com/photo-1606916066621-f89e521a4b51?w=800&q=80","https://images.unsplash.com/photo-1519741497674-611481863552?w=800&q=80","https://images.unsplash.com/photo-1511285560929-80b456fea0bc?w=800&q=80"]
  },
  default: {
    hero: "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80",
    gallery: ["https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80","https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&q=80","https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800&q=80","https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&q=80"]
  }
};

function detectType(desc: string): string {
  const d = desc.toLowerCase();
  if (d.includes('kucing') || d.includes('cat') || d.includes('pet')) return 'pet_shop';
  if (d.includes('makan') || d.includes('restoran') || d.includes('food') || d.includes('nasi')) return 'restaurant';
  if (d.includes('salon') || d.includes('rambut') || d.includes('hair')) return 'salon';
  if (d.includes('photo') || d.includes('wedding') || d.includes('gambar')) return 'photography';
  return 'default';
}

function buildPrompt(description: string): string {
  const type = detectType(description);
  const imgs = IMAGES[type] || IMAGES.default;
  return `Generate a complete HTML website.

BUSINESS: ${description}

USE THESE EXACT IMAGES:
Hero: ${imgs.hero}
Gallery: ${imgs.gallery.join(', ')}

REQUIREMENTS:
1. Single HTML with Tailwind CDN
2. Mobile responsive
3. NO placeholder images or text
4. WhatsApp button (60123456789)
5. Sections: Header, Hero, About, Services, Gallery, Contact, Footer
6. Bahasa Malaysia if description is in Malay

Output ONLY HTML code.`;
}

async function callAI(prompt: string): Promise<string | null> {
  if (DEEPSEEK_API_KEY) {
    try {
      const res = await fetch('https://api.deepseek.com/v1/chat/completions', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${DEEPSEEK_API_KEY}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'deepseek-chat', messages: [{ role: 'user', content: prompt }], max_tokens: 8000 }),
      });
      if (res.ok) return (await res.json()).choices[0].message.content;
    } catch (e) { console.error('DeepSeek:', e); }
  }
  if (QWEN_API_KEY) {
    try {
      const res = await fetch('https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${QWEN_API_KEY}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'qwen-max', messages: [{ role: 'user', content: prompt }], max_tokens: 8000 }),
      });
      if (res.ok) return (await res.json()).choices[0].message.content;
    } catch (e) { console.error('Qwen:', e); }
  }
  return null;
}

function extractHtml(text: string): string {
  if (!text) return '';
  if (text.includes('```html')) return text.split('```html')[1].split('```')[0].trim();
  if (text.includes('```')) return text.split('```')[1].split('```')[0].trim();
  return text.trim();
}

async function pollJobStatus(jobId: string, maxAttempts = 60): Promise<any> {
  const pollInterval = 3000; // Poll every 3 seconds

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const statusResponse = await fetch(`${BACKEND_API_URL}/api/generate/status/${jobId}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!statusResponse.ok) {
        throw new Error(`Status check failed: ${statusResponse.status}`);
      }

      const status = await statusResponse.json();
      console.log(`Job ${jobId} status: ${status.status} (${status.progress}%)`);

      if (status.status === 'completed') {
        return status;
      }

      if (status.status === 'failed') {
        throw new Error(status.error || 'Generation failed');
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    } catch (error) {
      console.error(`Poll attempt ${attempt + 1} failed:`, error);
      if (attempt === maxAttempts - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }

  throw new Error('Generation timeout - exceeded maximum wait time');
}

export async function POST(request: NextRequest) {
  try {
    const { business_description } = await request.json();
    if (!business_description) {
      return NextResponse.json({ error: 'Description required' }, { status: 400 });
    }

    // Use async generation with backend polling
    if (USE_ASYNC_GENERATION) {
      console.log('Using async generation with backend polling...');

      // Step 1: Start async generation
      const startResponse = await fetch(`${BACKEND_API_URL}/api/generate/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: business_description,
          user_id: 'demo-user',
          multi_style: true, // Always generate 3 variants
          images: [],
        }),
      });

      if (!startResponse.ok) {
        const errorText = await startResponse.text();
        throw new Error(`Failed to start generation: ${startResponse.status} - ${errorText}`);
      }

      const { job_id } = await startResponse.json();
      console.log(`Job created: ${job_id}`);

      // Step 2: Poll for completion
      const result = await pollJobStatus(job_id);

      // Step 3: Return variations
      return NextResponse.json({
        success: true,
        variations: result.variants.reduce((acc: any, variant: any, index: number) => {
          acc[variant.style || `Variant ${index + 1}`] = {
            html_content: variant.html,
            html: variant.html,
            thumbnail: variant.thumbnail,
            preview_image: variant.preview_image,
            social_preview: variant.social_preview,
          };
          return acc;
        }, {}),
        detected_features: result.detected_features || [],
        template_used: result.template_used || 'general',
      });
    }

    // Fallback: Direct AI call (old method)
    console.log('Using direct AI generation (fallback)...');
    const result = await callAI(buildPrompt(business_description));
    if (!result) {
      return NextResponse.json({ error: 'AI failed' }, { status: 500 });
    }
    const html = extractHtml(result);
    return NextResponse.json({ success: true, html, styles: [{ style: 'modern', html }] });

  } catch (error: any) {
    console.error('Generation error:', error);
    return NextResponse.json({
      error: error.message || 'Failed to generate website',
      details: error.toString()
    }, { status: 500 });
  }
}
