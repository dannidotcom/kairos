import sharp from 'sharp';
const variants = [
  `<rect x="9" y="8" width="9" height="48" rx="4.5" fill="#1E1B4B"/><path d="M20 34L45 10" stroke="#1E1B4B" stroke-width="9" stroke-linecap="round"/><path d="M20 30L45 54" stroke="#1E1B4B" stroke-width="9" stroke-linecap="round"/><circle cx="20" cy="32" r="5.4" fill="#F59E0B"/>`,
  `<rect x="9" y="8" width="9" height="48" rx="4.5" fill="#1E1B4B"/><path d="M20 34L45 10" stroke="#1E1B4B" stroke-width="9" stroke-linecap="round"/><path d="M20 30L45 54" stroke="#1E1B4B" stroke-width="9" stroke-linecap="round"/><circle cx="26" cy="32" r="5" fill="#F59E0B"/>`,
  `<rect x="8" y="8" width="10" height="48" rx="5" fill="#1E1B4B"/><path d="M19 35L47 8" stroke="#1E1B4B" stroke-width="10" stroke-linecap="round"/><path d="M19 29L47 56" stroke="#1E1B4B" stroke-width="10" stroke-linecap="round"/><circle cx="21" cy="32" r="4.8" fill="#F59E0B"/>`
];
for (let i=0;i<variants.length;i++) {
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 64 64"><rect width="64" height="64" fill="#FAFAF9"/>${variants[i]}</svg>`;
 await sharp(Buffer.from(svg)).png().toFile(`scripts/test-${i}.png`);
 const small=`<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 64 64"><rect width="64" height="64" fill="#FAFAF9"/>${variants[i]}</svg>`;
 await sharp(Buffer.from(small)).resize(256,256,{kernel:'nearest'}).png().toFile(`scripts/test-${i}-16.png`);
}
