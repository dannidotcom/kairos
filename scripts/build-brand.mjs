import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const publicBrand = path.join(root, "frontend", "public", "brand");
const srcBrand = path.join(root, "frontend", "src", "assets", "brand");

// Les SVG de public/brand sont les sources vectorielles manuscrites canoniques.
const svgSources = [
  "kairos-mark.svg",
  "kairos-mark-mono.svg",
  "kairos-wordmark.svg",
  "kairos-logo.svg",
  "kairos-logo-dark.svg",
  "kairos-logo-mono.svg",
  "favicon.svg",
  "apple-touch-icon.svg",
  "og-image.svg",
];

const pngTargets = [
  { source: "favicon.svg", name: "favicon-16.png", width: 16, height: 16 },
  { source: "favicon.svg", name: "favicon-32.png", width: 32, height: 32 },
  { source: "apple-touch-icon.svg", name: "apple-touch-icon.png", width: 180, height: 180 },
  { source: "apple-touch-icon.svg", name: "icon-192.png", width: 192, height: 192 },
  { source: "apple-touch-icon.svg", name: "icon-512.png", width: 512, height: 512 },
  { source: "kairos-mark.svg", name: "kairos-mark-512.png", width: 512, height: 512 },
  { source: "og-image.svg", name: "og-image.png", width: 1200, height: 630 },
];

fs.mkdirSync(publicBrand, { recursive: true });
fs.mkdirSync(srcBrand, { recursive: true });

for (const name of svgSources) {
  const sourcePath = path.join(publicBrand, name);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Source SVG manquante : ${sourcePath}`);
  }

  const svg = fs.readFileSync(sourcePath, "utf8");
  if (/<(?:text|image|script)\b|@font-face|font-family\s*[:=]/i.test(svg)) {
    throw new Error(`${name} doit rester vectoriel, autonome et sans police chargée.`);
  }
  fs.copyFileSync(sourcePath, path.join(srcBrand, name));
}

for (const target of pngTargets) {
  const sourcePath = path.join(publicBrand, target.source);
  const outputPath = path.join(publicBrand, target.name);

  await sharp(sourcePath, { density: 384 })
    .resize(target.width, target.height, {
      fit: "contain",
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toFile(outputPath);

  const meta = await sharp(outputPath).metadata();
  if (meta.width !== target.width || meta.height !== target.height) {
    throw new Error(
      `${target.name} mesure ${meta.width}×${meta.height}, dimensions attendues ${target.width}×${target.height}.`,
    );
  }

  fs.copyFileSync(outputPath, path.join(srcBrand, target.name));
}

console.log(
  `Identité construite : ${svgSources.length} SVG synchronisés et ${pngTargets.length} PNG générés dans chaque dossier brand.`,
);
