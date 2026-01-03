/**
 * PWA Icon Generator Script
 *
 * This script generates PNG icons of various sizes from the base SVG icon.
 *
 * Usage:
 *   npm install sharp --save-dev
 *   node scripts/generate-icons.js
 *
 * Or use an online tool like:
 *   - https://realfavicongenerator.net
 *   - https://www.pwabuilder.com/imageGenerator
 */

const fs = require('fs');
const path = require('path');

// Try to use sharp if available
async function generateIcons() {
  const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
  const iconDir = path.join(__dirname, '../public/icons');
  const svgPath = path.join(iconDir, 'icon.svg');

  // Check if sharp is installed
  let sharp;
  try {
    sharp = require('sharp');
  } catch (e) {
    console.log('Sharp not installed. To generate icons:');
    console.log('1. Run: npm install sharp --save-dev');
    console.log('2. Run: node scripts/generate-icons.js');
    console.log('');
    console.log('Or use online tools:');
    console.log('- https://realfavicongenerator.net');
    console.log('- https://www.pwabuilder.com/imageGenerator');
    console.log('');
    console.log('Upload the SVG from: frontend/public/icons/icon.svg');
    return;
  }

  // Read SVG
  const svg = fs.readFileSync(svgPath);

  console.log('Generating PWA icons...');

  for (const size of sizes) {
    const outputPath = path.join(iconDir, `icon-${size}x${size}.png`);

    await sharp(svg)
      .resize(size, size)
      .png()
      .toFile(outputPath);

    console.log(`Created: icon-${size}x${size}.png`);
  }

  console.log('Done! All icons generated.');
}

generateIcons().catch(console.error);
