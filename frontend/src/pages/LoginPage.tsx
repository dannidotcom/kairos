import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { ArrowRight, Check, Eye, EyeOff, Radio, Sparkles, Target, Zap } from 'lucide-react';
import { Logo } from '../assets/brand/Logo';
import { useAuth } from '../lib/auth';
import { useI18n } from '../lib/i18n';
import { Spinner } from '../components/UI';
import { useToast } from '../components/Toast';

export default function LoginPage() {
  const { user, login, demoLogin, register, loading: sessionLoading } = useAuth();
  const { t, locale, setLocale } = useI18n(); const { toast } = useToast(); const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login'); const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState<'form' | 'demo' | null>(null); const [error, setError] = useState('');
  const [form, setForm] = useState({ email: '', password: '', full_name: '', organization_name: '' });
  if (sessionLoading) return <div className="flex min-h-screen items-center justify-center"><Spinner /></div>;
  if (user) return <Navigate to="/" replace />;
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setLoading('form');
    try { if (mode === 'login') await login({ email: form.email, password: form.password }); else await register({ ...form, locale }); toast(t('login.connected')); navigate('/'); }
    catch (err) { setError(err instanceof Error ? err.message : t('error')); }
    finally { setLoading(null); }
  };
  const demo = async () => { setError(''); setLoading('demo'); try { await demoLogin(); navigate('/'); } catch (err) { setError(err instanceof Error ? err.message : t('error')); } finally { setLoading(null); } };
  return <div className="grid min-h-screen bg-white lg:grid-cols-[1.08fr_1fr]">
    <section className="relative hidden overflow-hidden bg-brand-indigo px-14 py-10 text-white lg:flex lg:flex-col xl:px-20 xl:py-12">
      <div className="pointer-events-none absolute -right-32 -top-32 size-[440px] rounded-full border border-white/[.055]" /><div className="pointer-events-none absolute -right-16 -top-16 size-[300px] rounded-full border border-white/[.055]" /><div className="pointer-events-none absolute -bottom-52 -left-24 size-[420px] rounded-full border border-white/[.04]" />
      <Logo variant="full" theme="dark" size={39} className="relative z-10 w-fit" />
      <div className="relative z-10 my-auto max-w-xl py-16"><div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[.06] px-3 py-1.5 text-[11px] font-semibold tracking-[.13em] text-indigo-100"><span className="size-1.5 rounded-full bg-brand-amber" />{t('login.eyebrow')}</div><h1 className="text-balance text-[46px] font-medium leading-[1.12] tracking-[-.045em] xl:text-[54px]">{t('login.title')}</h1><p className="mt-6 max-w-lg text-[16px] leading-7 text-slate-300">{t('login.subtitle')}</p><div className="mt-10 space-y-5">{[[Radio, t('login.point1')], [Target, t('login.point2')], [Zap, t('login.point3')]].map(([Icon, text], index) => { const IconComponent = Icon as typeof Radio; return <div key={index} className="flex items-center gap-3.5 text-sm text-slate-200"><div className="flex size-8 items-center justify-center rounded-lg border border-white/[.08] bg-white/[.055]"><IconComponent className="size-4 text-indigo-200" /></div>{text as string}</div>; })}</div></div>
      <div className="relative z-10 flex items-center gap-3 text-xs text-slate-400"><Sparkles className="size-4 text-brand-amber" /><span>{t('tagline')}</span><span className="ml-auto">© {new Date().getFullYear()} Kairos</span></div>
    </section>
    <section className="relative flex min-h-screen flex-col px-6 py-7 sm:px-12 lg:px-16 xl:px-24"><div className="flex items-center justify-between"><Logo variant="full" size={34} className="lg:hidden" /><div className="ml-auto flex rounded-lg bg-slate-100 p-0.5 text-[11px] font-semibold"><button className={`rounded-md px-2.5 py-1.5 ${locale === 'fr' ? 'bg-white text-brand-indigo shadow-sm' : 'text-slate-400'}`} onClick={() => setLocale('fr')}>FR</button><button className={`rounded-md px-2.5 py-1.5 ${locale === 'en' ? 'bg-white text-brand-indigo shadow-sm' : 'text-slate-400'}`} onClick={() => setLocale('en')}>EN</button></div></div>
      <div className="mx-auto my-auto w-full max-w-[410px] py-12"><div className="mb-8"><h2 className="text-[30px] font-semibold tracking-[-.04em] text-ink">{t(mode === 'login' ? 'login.welcome' : 'login.registerTitle')}</h2><p className="mt-2 text-sm leading-6 text-slate-500">{t(mode === 'login' ? 'login.prompt' : 'login.registerPrompt')}</p></div>
        <form onSubmit={submit} className="space-y-4">{mode === 'register' && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2"><div><label className="label" htmlFor="full_name">{t('login.fullName')}</label><input id="full_name" className="input" value={form.full_name} onChange={(e) => update('full_name', e.target.value)} required minLength={2} autoComplete="name" placeholder="Camille Martin" /></div><div><label className="label" htmlFor="organization_name">{t('login.orgName')}</label><input id="organization_name" className="input" value={form.organization_name} onChange={(e) => update('organization_name', e.target.value)} required minLength={2} autoComplete="organization" placeholder="Acme" /></div></div>}<div><label className="label" htmlFor="email">{t('login.email')}</label><input id="email" type="email" className="input" value={form.email} onChange={(e) => update('email', e.target.value)} required autoComplete="email" placeholder="vous@entreprise.com" /></div><div><div className="flex items-center justify-between"><label className="label" htmlFor="password">{t('login.password')}</label>{mode === 'register' && <span className="mb-1.5 text-[11px] text-slate-400">{t('login.passwordHint')}</span>}</div><div className="relative"><input id="password" type={showPassword ? 'text' : 'password'} className="input pr-11" value={form.password} onChange={(e) => update('password', e.target.value)} required minLength={mode === 'register' ? 10 : 1} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder="••••••••••" /><button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" onClick={() => setShowPassword(!showPassword)} aria-label="Show password">{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></div></div>{error && <div role="alert" className="rounded-xl bg-rose-50 px-3.5 py-3 text-sm text-rose-700">{error}</div>}<button className="btn-primary mt-2 w-full" disabled={loading !== null}>{loading === 'form' ? <Spinner className="size-4" /> : <>{t(mode === 'login' ? 'login.submit' : 'login.createAccount')}<ArrowRight className="size-4" /></>}</button></form>
        {mode === 'login' && <><div className="my-6 flex items-center gap-4"><div className="h-px flex-1 bg-slate-200" /><span className="text-[11px] uppercase tracking-wider text-slate-400">Kairos demo</span><div className="h-px flex-1 bg-slate-200" /></div><button className="btn-secondary w-full" onClick={demo} disabled={loading !== null}>{loading === 'demo' ? <Spinner className="size-4" /> : <><Sparkles className="size-4 text-brand-amber" />{t('login.demo')}</>}</button><p className="mt-3 text-center text-[11px] leading-5 text-slate-400">{t('login.demoHint')}</p></>}
        <p className="mt-8 text-center text-sm text-slate-500">{t(mode === 'login' ? 'login.noAccount' : 'login.hasAccount')} <button className="font-semibold text-brand-indigo hover:underline" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>{t(mode === 'login' ? 'login.createAccount' : 'login.signIn')}</button></p>
        <div className="mt-10 flex items-center justify-center gap-2 text-[11px] text-slate-400"><Check className="size-3.5 text-emerald-500" />JWT · Argon2 · PostgreSQL</div>
      </div><p className="text-center text-[11px] text-slate-400 lg:hidden">{t('tagline')}</p>
    </section>
  </div>;
}
