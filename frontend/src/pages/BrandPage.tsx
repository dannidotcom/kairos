import { Check, Copy, Download, MinusCircle, Palette, Ruler, Sparkles } from 'lucide-react';
import { useI18n } from '../lib/i18n';
import { Logo } from '../assets/brand/Logo';
import { PageHeader } from '../components/UI';
import { copyText } from '../lib/utils';
import { useToast } from '../components/Toast';

const palette = [
  { name: 'Indigo profond', token: 'brand-indigo', hex: '#1E1B4B', usage: 'Couleur principale, fonds, typographie' },
  { name: 'Ambre signal', token: 'brand-amber', hex: '#F59E0B', usage: 'Uniquement le point-signal' },
  { name: 'Ardoise', token: 'brand-slate', hex: '#64748B', usage: 'Texte secondaire' },
  { name: 'Blanc', token: 'brand-white', hex: '#FFFFFF', usage: 'Fonds, symbole sur fond sombre' },
];

const assets = [
  { file: 'kairos-mark.svg', label: 'Symbole', kind: 'svg' },
  { file: 'kairos-mark-mono.svg', label: 'Symbole monochrome', kind: 'svg' },
  { file: 'kairos-wordmark.svg', label: 'Wordmark', kind: 'svg' },
  { file: 'kairos-logo.svg', label: 'Logo clair', kind: 'svg' },
  { file: 'kairos-logo-dark.svg', label: 'Logo sombre', kind: 'svg' },
  { file: 'kairos-logo-mono.svg', label: 'Logo monochrome', kind: 'svg' },
  { file: 'favicon.svg', label: 'Favicon', kind: 'svg' },
  { file: 'favicon-16.png', label: 'Favicon 16', kind: 'png' },
  { file: 'favicon-32.png', label: 'Favicon 32', kind: 'png' },
  { file: 'apple-touch-icon.png', label: 'Apple 180', kind: 'png' },
  { file: 'icon-192.png', label: 'Icône 192', kind: 'png' },
  { file: 'icon-512.png', label: 'Icône 512', kind: 'png' },
  { file: 'og-image.png', label: 'Open Graph 1200×630', kind: 'png' },
];

export default function BrandPage() {
  const { t, locale } = useI18n();
  const { toast } = useToast();
  const copy = (value: string) => void copyText(value).then(() => toast(t('copied')));

  return (
    <div className="animate-fade-up pb-10">
      <PageHeader
        eyebrow="BRAND SYSTEM · DEV"
        title={t('brand.title')}
        subtitle={t('brand.subtitle')}
        actions={
          <span className="badge bg-amber-50 text-amber-700">
            <Sparkles className="size-3" />
            {locale === 'fr' ? 'Page développement uniquement' : 'Development-only page'}
          </span>
        }
      />

      <section className="grid gap-5 xl:grid-cols-2">
        <article className="card overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4 sm:px-6">
            <h2 className="font-semibold text-ink">{t('brand.concept')}</h2>
            <p className="mt-1 text-xs leading-5 text-slate-400">{t('brand.conceptText')}</p>
          </div>
          <div className="flex min-h-[220px] items-center justify-center bg-white p-10">
            <Logo variant="full" theme="light" size={64} />
          </div>
          <div className="flex min-h-[220px] items-center justify-center bg-brand-indigo p-10">
            <Logo variant="full" theme="dark" size={64} />
          </div>
        </article>

        <article className="card overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4 sm:px-6">
            <h2 className="font-semibold text-ink">{t('brand.variants')}</h2>
            <p className="mt-1 text-xs text-slate-400">SVG · paths · no web font</p>
          </div>
          <div className="grid grid-cols-2 divide-x divide-y divide-slate-100 sm:grid-cols-3">
            {[
              { label: 'Mark · clair', node: <Logo variant="mark" theme="light" size={44} />, bg: 'bg-white' },
              { label: 'Mark · sombre', node: <Logo variant="mark" theme="dark" size={44} />, bg: 'bg-brand-indigo' },
              { label: 'Mark · mono', node: <Logo variant="mark" theme="mono" size={44} />, bg: 'bg-slate-100' },
              { label: 'Logo · clair', node: <Logo variant="full" theme="light" size={34} />, bg: 'bg-white' },
              { label: 'Logo · sombre', node: <Logo variant="full" theme="dark" size={34} />, bg: 'bg-brand-indigo' },
              { label: 'Logo · mono', node: <img src="/brand/kairos-logo-mono.svg" alt="Kairos" height={34} className="h-[34px] w-auto" />, bg: 'bg-slate-100' },
            ].map(({ label, node, bg }) => (
              <div key={label} className={`flex flex-col items-center justify-center gap-3 p-6 ${bg}`}>
                {node}
                <span className={`text-[10px] uppercase tracking-wider ${bg === 'bg-white' ? 'text-slate-400' : 'text-slate-300'}`}>{label}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
        <article className="card p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <Palette className="size-4 text-indigo-500" />
            <h2 className="font-semibold text-ink">{t('brand.colors')}</h2>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {palette.map((color) => (
              <button
                key={color.token}
                onClick={() => copy(color.hex)}
                className="group flex items-center gap-3 rounded-xl border border-slate-100 p-3 text-left transition hover:border-indigo-100 hover:bg-slate-50/60"
              >
                <span
                  className="size-11 shrink-0 rounded-lg ring-1 ring-inset ring-black/5"
                  style={{ background: color.hex }}
                />
                <span className="min-w-0 flex-1">
                  <span className="block text-xs font-semibold text-slate-700">{color.name}</span>
                  <span className="mt-0.5 block font-mono text-[10px] text-slate-400">{color.token} · {color.hex}</span>
                  <span className="mt-1 block text-[10px] leading-4 text-slate-400">{color.usage}</span>
                </span>
                <Copy className="size-3.5 text-slate-300 opacity-0 transition group-hover:opacity-100" />
              </button>
            ))}
          </div>
          <div className="mt-5 rounded-xl bg-slate-50 p-4 font-mono text-[10px] leading-5 text-slate-500">
            <p>--brand-indigo: #1E1B4B;</p>
            <p>--brand-amber: #F59E0B;</p>
            <p>--brand-slate: #64748B;</p>
          </div>
        </article>

        <article className="card p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <Ruler className="size-4 text-indigo-500" />
            <h2 className="font-semibold text-ink">{t('brand.clearspace')}</h2>
          </div>
          <div className="mt-5 flex items-center justify-center rounded-xl border border-dashed border-indigo-200 bg-indigo-50/40 p-8">
            <div className="border border-dashed border-brand-amber/70 p-5">
              <Logo variant="full" theme="light" size={40} />
            </div>
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500">{t('brand.clearspaceText')}</p>
          <div className="mt-5 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-semibold text-ink">{t('brand.minimum')}</h3>
            <p className="mt-2 text-xs leading-5 text-slate-500">{t('brand.minimumText')}</p>
            <div className="mt-4 flex items-end gap-6">
              {[16, 24, 32, 48].map((size) => (
                <div key={size} className="flex flex-col items-center gap-2">
                  <Logo variant="mark" theme="light" size={size} />
                  <span className="text-[10px] text-slate-400">{size}px</span>
                </div>
              ))}
            </div>
          </div>
        </article>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1fr_.8fr]">
        <article className="card p-5 sm:p-6">
          <h2 className="font-semibold text-ink">{t('brand.donts')}</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              locale === 'fr' ? 'Déformer ou incliner' : 'Stretch or rotate',
              locale === 'fr' ? 'Recolorer le point-signal' : 'Recolor the signal dot',
              locale === 'fr' ? 'Ajouter ombre ou contour' : 'Add shadows or outlines',
              locale === 'fr' ? 'Placer sur un fond saturé' : 'Place on saturated backgrounds',
            ].map((item) => (
              <div key={item} className="flex items-center gap-2 rounded-xl bg-rose-50/70 px-3 py-2.5 text-xs text-rose-700">
                <MinusCircle className="size-3.5 shrink-0" />
                {item}
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500">{t('brand.dontsText')}</p>
        </article>

        <article className="card p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <Download className="size-4 text-indigo-500" />
            <h2 className="font-semibold text-ink">{locale === 'fr' ? 'Fichiers' : 'Files'}</h2>
          </div>
          <ul className="mt-4 divide-y divide-slate-100">
            {assets.map((asset) => (
              <li key={asset.file}>
                <a
                  href={`/brand/${asset.file}`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-3 py-2.5 text-xs text-slate-600 transition hover:text-brand-indigo"
                >
                  <Check className="size-3.5 text-emerald-500" />
                  <span className="flex-1 truncate font-mono">{asset.file}</span>
                  <span className="text-[10px] text-slate-400">{asset.label}</span>
                </a>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <img src="/brand/og-image.png" alt="Kairos — Le bon message, au bon moment." className="w-full" />
      </div>
    </div>
  );
}
