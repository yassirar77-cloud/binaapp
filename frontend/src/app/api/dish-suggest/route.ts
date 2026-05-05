import { NextRequest, NextResponse } from 'next/server'
import Anthropic from '@anthropic-ai/sdk'

export async function POST(req: NextRequest) {
  try {
    const { photoUrl } = await req.json()

    if (!photoUrl) {
      return NextResponse.json({ error: 'photoUrl required' }, { status: 400 })
    }

    const apiKey = process.env.ANTHROPIC_API_KEY
    if (!apiKey) {
      return NextResponse.json(
        { error: 'ANTHROPIC_API_KEY not configured', fallback: true },
        { status: 503 }
      )
    }

    const client = new Anthropic({ apiKey })

    const response = await client.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 200,
      messages: [{
        role: 'user',
        content: [
          {
            type: 'image',
            source: { type: 'url', url: photoUrl },
          },
          {
            type: 'text',
            text: 'What Malaysian dish is in this photo? Return JSON: {"name": "..." (Bahasa Melayu), "description": "..." (10 words BM), "suggested_price_rm": number}. Return ONLY valid JSON, no preamble.',
          },
        ],
      }],
    })

    const text = response.content[0].type === 'text' ? response.content[0].text : ''

    // Parse JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0])
      return NextResponse.json(parsed)
    }

    return NextResponse.json({ name: '', description: '', suggested_price_rm: 0, fallback: true })
  } catch (err: unknown) {
    console.error('Dish suggest error:', err)
    return NextResponse.json(
      { name: '', description: '', suggested_price_rm: 0, fallback: true },
      { status: 200 }
    )
  }
}
