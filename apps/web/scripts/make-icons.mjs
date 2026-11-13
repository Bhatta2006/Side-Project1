// Renders the favicon and installable-app icons from public/icons/owl.svg.
// Run from apps/web after changing the mark: node scripts/make-icons.mjs
// src/app/favicon.ico is the pack's .ico, copied as-is (sharp cannot write .ico).
import { readFileSync } from 'node:fs';
import sharp from 'sharp';

// Crop the viewBox to the owl's circle so it sits centred.
const owl = readFileSync('public/icons/owl.svg', 'utf8').replace(/viewBox="[^"]*" width="\d+" height="\d+"/, 'viewBox="107 75 876 876"');

const render = async (file, size, pad = 0, bg) => {
  const inner = await sharp(Buffer.from(owl)).resize(size - pad * 2, size - pad * 2).png().toBuffer();
  await sharp({ create: { width: size, height: size, channels: 4, background: bg ?? { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: inner, top: pad, left: pad }])
    .png()
    .toFile(file);
  console.log(file);
};

await render('src/app/icon.png', 512);
await render('public/icons/icon-48.png', 48);
await render('public/icons/icon-192.png', 192);
await render('public/icons/icon-512.png', 512);
await render('public/icons/maskable-512.png', 512, 72, '#292420'); // keeps the owl inside the safe zone
await render('public/icons/apple-touch-icon.png', 180, 10, '#F6F5F0'); // iOS paints transparency black
