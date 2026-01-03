/**
 * PWA Screenshot Generator using Playwright
 * Generates a screenshot for the manifest.json
 */

const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

async function generateScreenshot() {
  const screenshotDir = path.join(__dirname, '../public/screenshots');

  // Ensure directory exists
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  console.log('Generating BinaApp PWA screenshot...\n');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Set mobile viewport (1080x1920 for narrow form factor)
  await page.setViewportSize({ width: 1080, height: 1920 });

  // Create a promotional screenshot HTML
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            width: 1080px;
            height: 1920px;
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
            font-family: system-ui, -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
          }
          .logo {
            width: 200px;
            height: 200px;
            background: white;
            border-radius: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 60px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.15);
          }
          .sparkle {
            font-size: 100px;
          }
          h1 {
            font-size: 72px;
            font-weight: 700;
            margin-bottom: 24px;
            text-shadow: 0 4px 20px rgba(0,0,0,0.2);
          }
          p {
            font-size: 36px;
            opacity: 0.9;
            text-align: center;
            max-width: 800px;
            line-height: 1.5;
          }
          .features {
            margin-top: 80px;
            display: flex;
            flex-direction: column;
            gap: 30px;
          }
          .feature {
            display: flex;
            align-items: center;
            gap: 20px;
            font-size: 32px;
            background: rgba(255,255,255,0.15);
            padding: 20px 40px;
            border-radius: 20px;
          }
          .check {
            font-size: 36px;
          }
        </style>
      </head>
      <body>
        <div class="logo">
          <span class="sparkle">✨</span>
        </div>
        <h1>BinaApp</h1>
        <p>Bina website perniagaan anda<br>dengan AI dalam 60 saat</p>
        <div class="features">
          <div class="feature"><span class="check">✓</span> Mudah & Pantas</div>
          <div class="feature"><span class="check">✓</span> Design Profesional</div>
          <div class="feature"><span class="check">✓</span> 100% Percuma</div>
        </div>
      </body>
    </html>
  `;

  await page.setContent(html);

  const outputPath = path.join(screenshotDir, 'screenshot1.png');
  await page.screenshot({
    path: outputPath,
    omitBackground: false
  });

  console.log('  ✓ screenshot1.png (1080x1920)');

  await browser.close();
  console.log('\n✨ Screenshot generated successfully!');
}

generateScreenshot().catch((err) => {
  console.error('Error generating screenshot:', err);
  process.exit(1);
});
