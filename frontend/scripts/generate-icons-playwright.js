/**
 * PWA Icon Generator using Playwright
 * Generates PNG icons from SVG by rendering in a headless browser
 */

const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512];

async function generateIcons() {
  const iconDir = path.join(__dirname, '../public/icons');
  const svgPath = path.join(iconDir, 'icon.svg');

  if (!fs.existsSync(svgPath)) {
    console.error('Error: icon.svg not found at', svgPath);
    process.exit(1);
  }

  const svgContent = fs.readFileSync(svgPath, 'utf-8');

  console.log('Generating BinaApp PWA icons using Playwright...\n');

  const browser = await chromium.launch({ headless: true });

  for (const size of ICON_SIZES) {
    const page = await browser.newPage();

    // Set viewport to exact icon size
    await page.setViewportSize({ width: size, height: size });

    // Create an HTML page with the SVG scaled to fill the viewport
    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            * { margin: 0; padding: 0; }
            body {
              width: ${size}px;
              height: ${size}px;
              overflow: hidden;
            }
            svg {
              width: ${size}px;
              height: ${size}px;
            }
          </style>
        </head>
        <body>${svgContent}</body>
      </html>
    `;

    await page.setContent(html);

    const outputPath = path.join(iconDir, `icon-${size}x${size}.png`);
    await page.screenshot({
      path: outputPath,
      omitBackground: false
    });

    console.log(`  ✓ icon-${size}x${size}.png`);
    await page.close();
  }

  await browser.close();

  console.log('\n✨ Done! All icons generated successfully.');
  console.log('\nTest your icons at: https://maskable.app/editor');
}

generateIcons().catch((err) => {
  console.error('Error generating icons:', err);
  process.exit(1);
});
