import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, json, session } from './api';
import type { AuthResponse, MeResponse, Membership, User } from '../types';
import { useI18n } from './i18n';

type LoginInput = { email: string; password: string };
type RegisterInput = LoginInput & { full_name: string; organization_name: string; locale: 'fr' | 'en' };
type AuthContextValue = {
  user: User | null; organizations: Membership[]; activeOrganization: Membership | null;
  loading: boolean; login: (input: LoginInput) => Promise<void>; demoLogin: () => Promise<void>;
  register: (input: RegisterInput) => Promise<void>; logout: () => Promise<void>; switchOrganization: (id: string) => void;
  applySession: (data: AuthResponse) => void;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { locale, setLocale } = useI18n();
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Membership[]>([]);
  const [activeId, setActiveId] = useState<string | null>(session.organization);
  const [loading, setLoading] = useState(Boolean(session.access));

  const applyAuth = useCallback((data: AuthResponse | MeResponse) => {
    session.setOrganization(session.organization && data.organizations.some((m) => m.organization.id === session.organization) ? session.organization : data.organizations[0].organization.id);
    setActiveId(session.organization);
    setUser(data.user); setOrganizations(data.organizations);
    if (data.user.locale !== locale) setLocale(data.user.locale);
    if ('access_token' in data) session.setTokens(data.access_token, data.refresh_token);
  }, [locale, setLocale]);

  useEffect(() => {
    if (!session.access) { setLoading(false); return; }
    api<MeResponse>('/auth/me').then(applyAuth).catch(() => { session.clear(); setUser(null); }).finally(() => setLoading(false));
  }, []); // initial session only

  useEffect(() => {
    const unauthorized = () => { setUser(null); setOrganizations([]); setActiveId(null); queryClient.clear(); };
    window.addEventListener('kairos:unauthorized', unauthorized);
    return () => window.removeEventListener('kairos:unauthorized', unauthorized);
  }, [queryClient]);

  const login = useCallback(async (input: LoginInput) => { const data = await api<AuthResponse>('/auth/login', json('POST', input)); applyAuth(data); }, [applyAuth]);
  const demoLogin = useCallback(async () => { const data = await api<AuthResponse>('/demo/login', json('POST')); applyAuth(data); }, [applyAuth]);
  const register = useCallback(async (input: RegisterInput) => { const data = await api<AuthResponse>('/auth/register', json('POST', input)); applyAuth(data); }, [applyAuth]);
  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('kairos.refresh');
    if (refresh) await api('/auth/logout', json('POST', { refresh_token: refresh })).catch(() => undefined);
    session.clear(); setUser(null); setOrganizations([]); setActiveId(null); queryClient.clear();
  }, [queryClient]);
  const switchOrganization = useCallback((id: string) => { session.setOrganization(id); setActiveId(id); queryClient.clear(); }, [queryClient]);
  const activeOrganization = organizations.find((item) => item.organization.id === activeId) || organizations[0] || null;
  const value = useMemo(() => ({ user, organizations, activeOrganization, loading, login, demoLogin, register, logout, switchOrganization, applySession: applyAuth as (data: AuthResponse) => void }), [user, organizations, activeOrganization, loading, login, demoLogin, register, logout, switchOrganization, applyAuth]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error('useAuth must be used within AuthProvider'); return context; }
