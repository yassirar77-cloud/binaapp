import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { html, instruction } = await request.json();

    // Call backend to edit with AI
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/edit-html`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html, instruction }),
    });

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json({ error: 'Failed to edit' }, { status: 500 });
  }
}
