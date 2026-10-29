import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Bell, Building2, Check, ChevronDown, Inbox, LayoutDashboard, LogOut, Menu, Palette, Plus, Radio, Settings, Sparkles, Target, UsersRound, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Logo } from '../assets/brand/Logo';
import { useAuth } from '../lib/auth';
import { useI18n } from '../lib/i18n';
import { api, json } from '../lib/api';
import type { ConversationListResponse } from '../types';
import { Avatar, Modal } from './UI';
import { useToast } from './Toast';

const mainNav = [
  { to: '/app', key: 'dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/leads', key: 'leads', icon: UsersRound },
  { to: '/app/signals', key: 'signals', icon: Radio },
  { to: '/app/campaigns', key: 'campaigns', icon: BarChart3 },
];
export default function Layout() {
  const { t, locale, setLocale } = useI18n();
  const { user, organizations, activeOrganization, switchOrganization, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [orgOpen, setOrgOpen] = useState(false);
  const [newOrgOpen, setNewOrgOpen] = useState(false);
  const [orgName, setOrgName] = useState('');
  const [creating, setCreating] = useState(false);
  const location = useLocation(); const navigate = useNavigate(); const { toast } = useToast();
  const { data: inbox } = useQuery({ queryKey: ['nav-unread'], queryFn: () => api<ConversationListResponse>('/conversations?status=open&page_size=100'), refetchInterval: 20_000 });
  const unread = inbox?.items.reduce((total, item) => total + item.unread_count, 0) || 0;
  const org = activeOrganization?.organization;
  const createOrg = async (event: React.FormEvent) => {
    event.preventDefault(); setCreating(true);
    try { const membership = await api<import('../types').Membership>('/auth/organizations', json('POST', { name: orgName, locale, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone })); switchOrganization(membership.organization.id); window.location.reload(); }
    catch (error) { toast(error instanceof Error ? error.message : t('error'), 'error'); }
    finally { setCreating(false); }
  };
  const sidebar = <div className="flex h-full flex-col bg-brand-indigo">
    <div className="flex h-[76px] items-center justify-between px-6"><NavLink to="/app" aria-label="Kairos dashboard"><Logo variant="full" theme="dark" size={34} /></NavLink><button className="text-slate-400 lg:hidden" onClick={() => setMobileOpen(false)} aria-label={t('close')}><X /></button></div>
    <div className="px-4 pb-5"><div className="relative"><button onClick={() => setOrgOpen(!orgOpen)} className="flex w-full items-center gap-3 rounded-xl border border-white/[.08] bg-white/[.055] p-3 text-left transition hover:bg-white/[.09]"><div className="flex size-8 items-center justify-center rounded-lg bg-white/10 text-indigo-100"><Building2 className="size-4" /></div><div className="min-w-0 flex-1"><div className="truncate text-sm font-medium text-white">{org?.name || t('workspace')}</div><div className="mt-0.5 text-[11px] capitalize text-slate-400">{org?.plan || 'MVP'} · {activeOrganization?.role}</div></div><ChevronDown className="size-4 text-slate-400" /></button>{orgOpen && <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-30 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lift">{organizations.map((membership) => <button key={membership.id} onClick={() => { switchOrganization(membership.organization.id); setOrgOpen(false); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50"><span className="flex-1 truncate">{membership.organization.name}</span>{membership.organization.id === org?.id && <Check className="size-4 text-brand-indigo" />}</button>)}<button onClick={() => { setNewOrgOpen(true); setOrgOpen(false); }} className="flex w-full items-center gap-2 border-t border-slate-100 px-3 py-2.5 text-sm font-medium text-brand-indigo"><Plus className="size-4" />{t('login.createAccount')}</button></div>}</div></div>
    <nav className="scrollbar-thin flex-1 overflow-y-auto px-4 pb-4">
      <p className="mb-2 px-3 pt-3 text-[10px] font-semibold tracking-[.16em] text-slate-500">{t('nav.prospecting')}</p>
      <div className="space-y-1">{mainNav.map(({ to, key, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon className="size-[18px]" strokeWidth={1.8} /><span className="flex-1">{t(key)}</span>{key === 'signals' && <span className="size-1.5 rounded-full bg-brand-amber" />}</NavLink>)}</div>
      <p className="mb-2 mt-7 px-3 text-[10px] font-semibold tracking-[.16em] text-slate-500">{t('nav.conversations')}</p>
      <NavLink to="/app/unibox" onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Inbox className="size-[18px]" strokeWidth={1.8} /><span className="flex-1">{t('unibox')}</span>{unread > 0 && <span className="rounded-full bg-brand-amber px-2 py-0.5 text-[10px] font-bold text-brand-indigo">{unread}</span>}</NavLink>
      <p className="mb-2 mt-7 px-3 text-[10px] font-semibold tracking-[.16em] text-slate-500">{t('nav.configuration')}</p>
      <div className="space-y-1"><NavLink to="/app/icp" onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Target className="size-[18px]" strokeWidth={1.8} />{t('icp')}</NavLink><NavLink to="/app/settings" onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Settings className="size-[18px]" strokeWidth={1.8} />{t('settings')}</NavLink>{import.meta.env.DEV && <NavLink to="/app/brand" onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Palette className="size-[18px]" strokeWidth={1.8} />{t('brand')}</NavLink>}</div>
    </nav>
    <div className="m-4 rounded-xl border border-white/[.07] bg-white/[.045] p-3.5"><div className="flex items-center gap-2 text-xs font-medium text-indigo-100"><Sparkles className="size-3.5 text-brand-amber" />{t('tagline')}</div><p className="mt-2 text-[11px] leading-5 text-slate-400">Kairos · /ˈkaɪ.rɒs/ · καιρός</p></div>
    <div className="flex items-center gap-3 border-t border-white/[.07] px-5 py-4"><Avatar name={user?.full_name || 'Kairos'} src={user?.avatar_url} size="sm" className="ring-white/10" /><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium text-white">{user?.full_name}</p><p className="truncate text-[11px] text-slate-400">{user?.email}</p></div><button className="text-slate-400 transition hover:text-white" onClick={() => void logout().then(() => navigate('/login'))} title={t('logout')}><LogOut className="size-4" /></button></div>
  </div>;
  const title = [...mainNav.map((item) => ({ ...item, to: item.to })), { to: '/app/unibox', key: 'unibox' }, { to: '/app/icp', key: 'icp' }, { to: '/app/settings', key: 'settings' }].find((item) => item.to === '/app' ? location.pathname === '/app' : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`));
  return <div className="min-h-screen bg-canvas">
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] lg:block">{sidebar}</aside>
    {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button className="absolute inset-0 bg-brand-indigo/50" onClick={() => setMobileOpen(false)} aria-label={t('close')} /><aside className="absolute inset-y-0 left-0 w-[280px] shadow-lift">{sidebar}</aside></div>}
    <div className="lg:pl-[248px]">
      <header className="sticky top-0 z-30 flex h-[64px] items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-7 lg:px-9"><button className="icon-btn lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Menu"><Menu className="size-5" /></button><div className="hidden items-center gap-2 text-sm text-slate-400 sm:flex"><span>{org?.name}</span><span>/</span><span className="font-medium text-slate-700">{title ? t(title.key) : 'Kairos'}</span></div><div className="ml-auto flex items-center gap-1.5"><div className="mr-2 hidden items-center gap-1.5 text-[11px] font-medium text-emerald-600 md:flex"><span className="size-1.5 animate-pulse-soft rounded-full bg-emerald-500" />{t('live')}</div><button className="icon-btn relative" onClick={() => navigate('/signals')} aria-label={t('signals')}><Bell className="size-[18px]" /></button><div className="ml-1 flex rounded-lg bg-slate-100 p-0.5 text-[11px] font-semibold"><button onClick={() => setLocale('fr')} className={`rounded-md px-2 py-1.5 ${locale === 'fr' ? 'bg-white text-brand-indigo shadow-sm' : 'text-slate-400'}`}>FR</button><button onClick={() => setLocale('en')} className={`rounded-md px-2 py-1.5 ${locale === 'en' ? 'bg-white text-brand-indigo shadow-sm' : 'text-slate-400'}`}>EN</button></div></div></header>
      <main className="mx-auto max-w-[1560px] p-4 sm:p-7 lg:p-9"><Outlet /></main>
    </div>
    <Modal open={newOrgOpen} onClose={() => setNewOrgOpen(false)} title={t('login.createAccount')}><form onSubmit={createOrg} className="space-y-5"><div><label className="label" htmlFor="new-org-name">{t('login.orgName')}</label><input id="new-org-name" className="input" required minLength={2} value={orgName} onChange={(e) => setOrgName(e.target.value)} /></div><button className="btn-primary w-full" disabled={creating}>{creating ? t('saving') : t('create')}</button></form></Modal>
  </div>;
}
