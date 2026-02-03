import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

export async function POST(request: NextRequest) {
  try {
    const { html, instruction } = await request.json();

    if (!html || !instruction) {
      console.error('❌ AI Edit: Missing html or instruction');
      return NextResponse.json({ error: 'Missing data', success: false }, { status: 400 });
    }

    console.log(`🤖 AI Edit: Calling backend at ${API_URL}/api/edit-html`);
    console.log(`🤖 AI Edit: Instruction: ${instruction}`);

    // Call backend to edit with AI
    const response = await fetch(`${API_URL}/api/edit-html`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html, instruction }),
    });

    console.log(`🤖 AI Edit: Backend response status: ${response.status}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ AI Edit: Backend error: ${errorText}`);
      return NextResponse.json({ error: 'Backend error', success: false }, { status: response.status });
    }

    const data = await response.json();
    console.log(`🤖 AI Edit: Success: ${data.success}, HTML length: ${data.html?.length || 0}`);
    return NextResponse.json(data);

  } catch (error) {
    console.error('❌ AI Edit: Exception:', error);
    return NextResponse.json({ error: 'Failed to edit', success: false }, { status: 500 });
  }
}
