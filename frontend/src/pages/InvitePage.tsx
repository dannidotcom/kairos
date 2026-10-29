import { useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, Check, Eye, EyeOff, Mail, ShieldCheck, UserPlus } from 'lucide-react';
import { Logo } from '../assets/brand/Logo';
import { api, json, session } from '../lib/api';
import { useAuth } from '../lib/auth';
import { useI18n } from '../lib/i18n';
import { Spinner } from '../components/UI';
import { useToast } from '../components/Toast';
import type { AuthResponse } from '../types';

export default function InvitePage() {
  const { token } = useParams();
  const { user, applySession } = useAuth();
  const { t, locale, setLocale } = useI18n();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [accepted, setAccepted] = useState(false);

  if (!token) return <Navigate to="/login" replace />;
  if (accepted) return <Navigate to="/" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const payload: Record<string, unknown> = { token };
      if (!user) {
        payload.full_name = fullName;
        payload.password = password;
      } else {
        payload.password = password || null;
      }
      const data = await api<AuthResponse>('/auth/accept-invite', json('POST', payload));
      if (applySession) applySession(data);
      else {
        session.setTokens(data.access_token, data.refresh_token);
        session.setOrganization(data.organizations[0]?.organization.id ?? '');
        window.location.assign('/');
      }
      toast(t('settings.invited'));
      setAccepted(true);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1fr_1.05fr]">
      <section className="relative hidden overflow-hidden bg-brand-indigo px-14 py-10 text-white lg:flex lg:flex-col xl:px-20">
        <div className="pointer-events-none absolute -right-32 -top-32 size-[440px] rounded-full border border-white/[.055]" />
        <div className="pointer-events-none absolute -bottom-40 -left-20 size-[360px] rounded-full border border-white/[.05]" />
        <Logo variant="full" theme="dark" size={39} className="relative z-10 w-fit" />
        <div className="relative z-10 my-auto max-w-md">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[.06] px-3 py-1.5 text-[11px] font-semibold tracking-[.13em] text-indigo-100">
            <span className="size-1.5 rounded-full bg-brand-amber" />
            KAIROS · {locale === 'fr' ? 'INVITATION' : 'INVITATION'}
          </div>
          <h1 className="text-balance text-[42px] font-medium leading-[1.14] tracking-[-.045em]">
            {locale === 'fr' ? 'Rejoignez une équipe qui saisit le bon moment.' : 'Join a team that seizes the right moment.'}
          </h1>
          <p className="mt-6 text-[15px] leading-7 text-slate-300">
            {locale === 'fr'
              ? 'Un espace partagé pour détecter les signaux, scorer les prospects et engager les conversations qui comptent.'
              : 'A shared workspace to spot signals, score leads and start the conversations that matter.'}
          </p>
          <div className="mt-9 space-y-4 text-sm text-slate-200">
            {[
              locale === 'fr' ? 'Pipeline et signaux partagés en temps réel' : 'Shared pipeline and signals in real time',
              locale === 'fr' ? 'Rôles owner, admin et membre' : 'Owner, admin and member roles',
              locale === 'fr' ? 'Accès MCP et clés API dédiées' : 'Dedicated MCP access and API keys',
            ].map((line) => (
              <div key={line} className="flex items-center gap-3">
                <span className="flex size-6 items-center justify-center rounded-lg border border-white/10 bg-white/[.055]">
                  <Check className="size-3.5 text-emerald-300" />
                </span>
                {line}
              </div>
            ))}
          </div>
        </div>
        <div className="relative z-10 flex items-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="size-4 text-brand-amber" />
          {t('tagline')}
        </div>
      </section>

      <section className="relative flex min-h-screen flex-col px-6 py-7 sm:px-12 lg:px-16 xl:px-24">
        <div className="flex items-center justify-between">
          <Logo variant="full" size={34} className="lg:hidden" />
          <div className="ml-auto flex rounded-lg bg-slate-100 p-0.5 text-[11px] font-semibold">
            <button
              className={`rounded-md px-2.5 py-1.5 ${locale === 'fr' ? 'bg-white text-brand-indigo shadow-sm' : 'text-slate-400'}`}
              onClick={() => setLocale('fr')}
            >
              FR
            </button>
            <button
              className={`rounded-md px-2.5 py-1.5 ${locale === 'en' ? 'bg-white text-brand-indigo shadow-sm' : 'text-slate-400'}`}
              onClick={() => setLocale('en')}
            >
              EN
            </button>
          </div>
        </div>

        <div className="mx-auto my-auto w-full max-w-[410px] py-12">
          <div className="mb-8 flex size-12 items-center justify-center rounded-2xl bg-indigo-50 text-brand-indigo">
            <UserPlus className="size-6" />
          </div>
          <h2 className="text-[30px] font-semibold tracking-[-.04em] text-ink">
            {user
              ? locale === 'fr'
                ? 'Rejoindre cet espace'
                : 'Join this workspace'
              : locale === 'fr'
                ? 'Vous avez été invité'
                : 'You have been invited'}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            {user
              ? locale === 'fr'
                ? 'Confirmez avec votre mot de passe pour accepter l’invitation.'
                : 'Confirm with your password to accept the invitation.'
              : locale === 'fr'
                ? 'Créez votre compte pour accepter l’invitation et accéder à Kairos.'
                : 'Create your account to accept the invitation and access Kairos.'}
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            {user && (
              <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3.5 text-sm text-slate-600">
                <Mail className="size-4 text-slate-400" />
                <span className="truncate">{user.email}</span>
              </div>
            )}
            {!user && (
              <div>
                <label className="label" htmlFor="invite-full-name">
                  {t('login.fullName')}
                </label>
                <input
                  id="invite-full-name"
                  className="input"
                  required
                  minLength={2}
                  autoComplete="name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Camille Martin"
                />
              </div>
            )}
            <div>
              <div className="flex items-center justify-between">
                <label className="label" htmlFor="invite-password">
                  {t('login.password')}
                </label>
                {!user && <span className="mb-1.5 text-[11px] text-slate-400">{t('login.passwordHint')}</span>}
              </div>
              <div className="relative">
                <input
                  id="invite-password"
                  type={showPassword ? 'text' : 'password'}
                  className="input pr-11"
                  required
                  minLength={user ? 1 : 10}
                  autoComplete={user ? 'current-password' : 'new-password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••••"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>
            {error && (
              <div role="alert" className="rounded-xl bg-rose-50 px-3.5 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? (
                <Spinner className="size-4" />
              ) : (
                <>
                  {locale === 'fr' ? 'Accepter l’invitation' : 'Accept invitation'}
                  <ArrowRight className="size-4" />
                </>
              )}
            </button>
          </form>
          <p className="mt-8 text-center text-xs leading-5 text-slate-400">
            {locale === 'fr'
              ? 'Invitation valable 7 jours. Vous pourrez changer d’organisation à tout moment.'
              : 'Invitation valid for 7 days. You can switch organization at any time.'}
          </p>
        </div>
        <p className="text-center text-[11px] text-slate-400 lg:hidden">{t('tagline')}</p>
      </section>
    </div>
  );
}
