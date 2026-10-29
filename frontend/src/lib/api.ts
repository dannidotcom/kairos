const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const ACCESS_KEY = 'kairos.access';
const REFRESH_KEY = 'kairos.refresh';
const ORG_KEY = 'kairos.organization';

let accessToken = localStorage.getItem(ACCESS_KEY);
let refreshToken = localStorage.getItem(REFRESH_KEY);
let organizationId = localStorage.getItem(ORG_KEY);
let refreshing: Promise<boolean> | null = null;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const session = {
  get access() { return accessToken; },
  get organization() { return organizationId; },
  setTokens(access: string, refresh: string) {
    accessToken = access; refreshToken = refresh;
    localStorage.setItem(ACCESS_KEY, access); localStorage.setItem(REFRESH_KEY, refresh);
  },
  setOrganization(id: string) { organizationId = id; localStorage.setItem(ORG_KEY, id); },
  clear() {
    accessToken = null; refreshToken = null; organizationId = null;
    localStorage.removeItem(ACCESS_KEY); localStorage.removeItem(REFRESH_KEY); localStorage.removeItem(ORG_KEY);
  },
};

async function tryRefresh() {
  if (!refreshToken) return false;
  refreshing ??= (async () => {
    try {
      const response = await fetch(`${API_URL}/api/auth/refresh`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      session.setTokens(data.access_token, data.refresh_token);
      return true;
    } catch { return false; }
    finally { refreshing = null; }
  })();
  return refreshing;
}

export async function api<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  if (organizationId) headers.set('X-Organization-ID', organizationId);
  const response = await fetch(`${API_URL}/api${path}`, { ...options, headers });
  if (response.status === 401 && retry && !path.startsWith('/auth/') && await tryRefresh()) return api<T>(path, options, false);
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/') && !path.startsWith('/demo/')) {
      session.clear();
      window.dispatchEvent(new Event('kairos:unauthorized'));
    }
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map((e: { msg?: string }) => e.msg).join(', ') : message;
    } catch { /* response may not contain JSON */ }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const json = (method: string, body?: unknown): RequestInit => ({ method, body: body === undefined ? undefined : JSON.stringify(body) });
export const queryString = (params: Record<string, string | number | boolean | null | undefined>) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value !== '' && value != null) query.set(key, String(value)); });
  const value = query.toString();
  return value ? `?${value}` : '';
};
