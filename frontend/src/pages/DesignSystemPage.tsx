import { useState } from 'react';
import { ArrowRight, Check, Inbox, Settings, Trash2 } from 'lucide-react';
import { Button } from '../design-system/Button';

export default function DesignSystemPage() {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const variants = ['primary', 'secondary', 'ghost', 'destructive'] as const;
  return <main className="min-h-screen bg-kairos-bg px-6 py-10 text-kairos-text sm:px-10" data-theme-preview={theme}>
    <div className="mx-auto max-w-6xl">
      <header className="mb-10 flex items-end justify-between gap-4">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[.18em] text-brand-amber">Kairos / Catalogue</p><h1 className="text-4xl font-semibold tracking-tight">Design system</h1></div>
        <div className="flex rounded-xl border border-kairos-border bg-kairos-surface p-1">
          {(['dark', 'light'] as const).map((value) => <button key={value} onClick={() => setTheme(value)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${theme === value ? 'bg-brand-indigo text-white' : 'text-kairos-muted'}`}>{value === 'dark' ? 'Sombre' : 'Clair'}</button>)}
        </div>
      </header>
      <section className="mb-10"><h2 className="mb-4 text-sm font-bold">Boutons</h2><div className="grid gap-3 rounded-2xl border border-kairos-border bg-kairos-surface p-6 sm:grid-cols-4">
        {variants.map((variant) => <Button key={variant} variant={variant} leadingIcon={variant === 'destructive' ? <Trash2 className="size-4" /> : variant === 'secondary' ? <Settings className="size-4" /> : undefined}>{variant}</Button>)}
        <Button loading>Chargement</Button><Button disabled>Désactivé</Button><Button leadingIcon={<Check className="size-4" />}>Confirmé</Button><Button variant="primary" leadingIcon={<ArrowRight className="size-4" />} />
      </div></section>
      <section className="grid gap-4 md:grid-cols-2"><div className="rounded-2xl border border-kairos-border bg-kairos-surface p-6"><h2 className="mb-4 text-sm font-bold">Couleurs sémantiques</h2><div className="grid grid-cols-2 gap-2"><span className="rounded-lg bg-kairos-success-bg px-3 py-4 text-kairos-success">Succès</span><span className="rounded-lg bg-kairos-warning-bg px-3 py-4 text-kairos-warning">Alerte</span><span className="rounded-lg bg-kairos-danger-bg px-3 py-4 text-kairos-danger">Erreur</span><span className="rounded-lg bg-kairos-info-bg px-3 py-4 text-kairos-info">Information</span></div></div><div className="rounded-2xl border border-kairos-border bg-kairos-surface p-6"><h2 className="mb-4 text-sm font-bold">État vide</h2><div className="flex flex-col items-center py-6 text-center"><div className="mb-3 flex size-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400"><Inbox className="size-5" /></div><b>Rien à afficher</b><p className="mt-1 text-sm text-kairos-muted">Les nouveaux éléments apparaîtront ici.</p></div></div></section>
      <p className="mt-10 text-xs text-kairos-muted">Tokens, états, contrastes et composants accessibles du système Kairos.</p>
    </div>
  </main>;
}
