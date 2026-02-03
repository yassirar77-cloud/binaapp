import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

export async function POST(request: NextRequest) {
  try {
    const { html, instruction } = await request.json();

    if (!instruction) {
      console.error('❌ AI Edit: Missing instruction');
      return NextResponse.json({ error: 'Missing data', success: false }, { status: 400 });
    }

    // Use a minimal template if HTML is empty
    const htmlToEdit = html || `<!DOCTYPE html>
<html lang="ms">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Laman Web Saya</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
  </style>
</head>
<body>
  <h1>Selamat Datang</h1>
  <p>Ini adalah laman web anda.</p>
</body>
</html>`;

    console.log(`🤖 AI Edit: Calling backend at ${API_URL}/api/edit-html`);
    console.log(`🤖 AI Edit: Instruction: ${instruction}`);
    console.log(`🤖 AI Edit: HTML provided: ${html ? 'yes' : 'no (using template)'}`);

    // Call backend to edit with AI
    const response = await fetch(`${API_URL}/api/edit-html`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html: htmlToEdit, instruction }),
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
