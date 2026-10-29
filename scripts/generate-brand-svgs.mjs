import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const publicBrand = path.join(root, "frontend", "public", "brand");
const srcBrand = path.join(root, "frontend", "src", "assets", "brand");
const data = JSON.parse(fs.readFileSync(path.join(__dirname, "wordmark.json"), "utf8"));

const INDIGO = "#1E1B4B";
const AMBER = "#F59E0B";
const WHITE = "#FFFFFF";
const SLATE = "#64748B";

function symbol({ ink = INDIGO, accent = AMBER, includeTitle = false } = {}) {
  return `${includeTitle ? "<title>Kairos</title>" : ""}
  <g>
    <rect x="9" y="8" width="9" height="48" rx="4.5" fill="${ink}"/>
    <path d="M20 34 45 10" fill="none" stroke="${ink}" stroke-width="9" stroke-linecap="round"/>
    <path d="M20 30 45 54" fill="none" stroke="${ink}" stroke-width="9" stroke-linecap="round"/>
    <circle cx="20" cy="32" r="5.4" fill="${accent}"/>
  </g>`;
}

function markSvg(options = {}) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-labelledby="kairos-mark-title">
  <title id="kairos-mark-title">Kairos</title>
  ${symbol(options)}
</svg>
`;
}

function monoMarkSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-labelledby="kairos-mono-title" color="${INDIGO}">
  <title id="kairos-mono-title">Kairos</title>
  <g fill="currentColor">
    <rect x="9" y="8" width="9" height="48" rx="4.5"/>
    <path d="M20 34 45 10" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round"/>
    <path d="M20 30 45 54" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round"/>
    <circle cx="20" cy="32" r="5.4"/>
  </g>
</svg>
`;
}

function logoBody({ ink, accent }) {
  return `<g transform="translate(16 12) scale(0.875)">
    ${symbol({ ink, accent })}
  </g>
  <path fill="${ink}" d="${data.word.d}"/>`;
}

function logoSvg({ ink, accent, background = null }) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 304 80" width="304" height="80" role="img" aria-labelledby="kairos-logo-title">
  <title id="kairos-logo-title">Kairos</title>
  ${background ? `<rect width="304" height="80" fill="${background}"/>` : ""}
  ${logoBody({ ink, accent })}
</svg>
`;
}

function tileSvg({ padded = false } = {}) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-labelledby="kairos-icon-title">
  <title id="kairos-icon-title">Kairos</title>
  <rect width="64" height="64" ${padded ? "" : 'rx="14"'} fill="${INDIGO}"/>
  <g transform="translate(${padded ? "8" : "7"} ${padded ? "8" : "7"}) scale(${padded ? "0.75" : "0.78"})">
    ${symbol({ ink: WHITE, accent: AMBER })}
  </g>
</svg>
`;
}

function ogSvg() {
  const logoScale = 2.05;
  const logoWidth = 304 * logoScale;
  const logoX = Math.round((1200 - logoWidth) / 2);
  const sloganX = Math.round((1200 - data.slogan.width) / 2);
  const englishX = Math.round((1200 - data.english.width) / 2);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630" role="img" aria-labelledby="kairos-og-title">
  <title id="kairos-og-title">Kairos — Le bon message, au bon moment.</title>
  <rect width="1200" height="630" fill="${INDIGO}"/>
  <g fill="none" stroke="#4338CA" stroke-width="1.5">
    <circle cx="600" cy="295" r="282" opacity=".55"/>
    <circle cx="600" cy="295" r="230" opacity=".32"/>
    <path d="M600 13v16M600 561v16M318 295h16M866 295h16" opacity=".6"/>
  </g>
  <circle cx="600" cy="13" r="4" fill="${AMBER}" opacity=".85"/>
  <circle cx="866" cy="295" r="3" fill="${AMBER}" opacity=".45"/>
  <g transform="translate(${logoX} 187) scale(${logoScale})">
    ${logoBody({ ink: WHITE, accent: AMBER })}
  </g>
  <g transform="translate(${sloganX} 445)">
    <path fill="#F8FAFC" d="${data.slogan.d}"/>
  </g>
  <g transform="translate(${englishX} 492)">
    <path fill="#A5B4FC" d="${data.english.d}"/>
  </g>
  <rect x="${Math.round((1200 - 48) / 2)}" y="535" width="48" height="3" rx="1.5" fill="${AMBER}"/>
</svg>
`;
}

const files = {
  "kairos-mark.svg": markSvg({ ink: INDIGO, accent: AMBER }),
  "kairos-logo.svg": logoSvg({ ink: INDIGO, accent: AMBER }),
  "kairos-logo-dark.svg": logoSvg({ ink: WHITE, accent: AMBER }),
  "kairos-mark-mono.svg": monoMarkSvg(),
  "favicon.svg": tileSvg(),
  "apple-touch-icon.svg": tileSvg({ padded: true }),
  "og-image.svg": ogSvg(),
};

for (const dir of [publicBrand, srcBrand]) {
  fs.mkdirSync(dir, { recursive: true });
  for (const [name, contents] of Object.entries(files)) {
    fs.writeFileSync(path.join(dir, name), contents);
  }
}

// The PNG build reads these canonical SVGs.
console.log(`Wrote ${Object.keys(files).length} SVG sources to both brand asset directories.`);
