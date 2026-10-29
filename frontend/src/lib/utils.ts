import clsx, { type ClassValue } from 'clsx';
import type { Locale } from '../types';

export const cn = (...inputs: ClassValue[]) => clsx(inputs);
export const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
export const formatDate = (value?: string | null, locale: Locale = 'fr', options?: Intl.DateTimeFormatOptions) => value ? new Intl.DateTimeFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', options ?? { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value)) : '—';
export const formatTime = (value: string, locale: Locale = 'fr') => new Intl.DateTimeFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
export function relativeTime(value: string, locale: Locale = 'fr') {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  if (Math.abs(seconds) < 60) return formatter.format(seconds, 'second');
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, 'minute');
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, 'hour');
  return formatter.format(Math.round(hours / 24), 'day');
}
export const percent = (used: number, limit: number) => limit ? Math.min(100, Math.round(used / limit * 100)) : 0;
export const signalIcon = (type: string) => ({ funding: '↗', hiring: '+', job_change: '↻', linkedin_post: '“', company_growth: '⌁', manual: '•' }[type] || '•');
export async function copyText(value: string) { await navigator.clipboard.writeText(value); }
