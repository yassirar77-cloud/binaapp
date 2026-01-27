/**
 * PWA Icon Generator Script for BinaApp
 *
 * This script generates PNG icons of various sizes from the base SVG icon.
 *
 * RECOMMENDED: Use online tools for best quality:
 *   1. Go to https://www.pwabuilder.com/imageGenerator
 *   2. Upload the SVG from: frontend/public/icons/icon.svg
 *   3. Download generated icons and replace files in frontend/public/icons/
 *
 * Alternative online tools:
 *   - https://realfavicongenerator.net
 *   - https://maskable.app/editor (for testing maskable icons)
 *
 * Local generation (requires sharp):
 *   npm install sharp --save-dev
 *   node scripts/generate-icons.js
 */

const fs = require('fs');
const path = require('path');

const ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512];

async function generateIcons() {
  const iconDir = path.join(__dirname, '../public/icons');
  const svgPath = path.join(iconDir, 'icon.svg');

  // Check if SVG exists
  if (!fs.existsSync(svgPath)) {
    console.error('Error: icon.svg not found at', svgPath);
    process.exit(1);
  }

  // Check if sharp is installed
  let sharp;
  try {
    sharp = require('sharp');
  } catch (e) {
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║  Sharp not installed. Use online tools instead:          ║');
    console.log('╠══════════════════════════════════════════════════════════╣');
    console.log('║  1. Go to: https://www.pwabuilder.com/imageGenerator     ║');
    console.log('║  2. Upload: frontend/public/icons/icon.svg               ║');
    console.log('║  3. Download and replace icons in public/icons/          ║');
    console.log('╠══════════════════════════════════════════════════════════╣');
    console.log('║  Or install sharp locally:                               ║');
    console.log('║  npm install sharp --save-dev                            ║');
    console.log('║  node scripts/generate-icons.js                          ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
    return;
  }

  // Read SVG
  const svg = fs.readFileSync(svgPath);

  console.log('Generating BinaApp PWA icons...\n');

  for (const size of ICON_SIZES) {
    const outputPath = path.join(iconDir, `icon-${size}x${size}.png`);

    await sharp(svg)
      .resize(size, size)
      .png({ quality: 100 })
      .toFile(outputPath);

    console.log(`  ✓ icon-${size}x${size}.png`);
  }

  console.log('\n✨ Done! All icons generated successfully.');
  console.log('\nTest your icons at: https://maskable.app/editor');
}

generateIcons().catch((err) => {
  console.error('Error generating icons:', err);
  process.exit(1);
});
