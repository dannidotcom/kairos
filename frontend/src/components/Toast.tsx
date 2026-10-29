import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

type Toast = { id: number; message: string; kind: 'success' | 'error' };
const ToastContext = createContext<{ toast: (message: string, kind?: Toast['kind']) => void } | null>(null);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setItems((current) => current.filter((item) => item.id !== id)), []);
  const toast = useCallback((message: string, kind: Toast['kind'] = 'success') => {
    const id = Date.now() + Math.random();
    setItems((current) => [...current.slice(-2), { id, message, kind }]);
    window.setTimeout(() => dismiss(id), 4500);
  }, [dismiss]);
  const value = useMemo(() => ({ toast }), [toast]);
  return <ToastContext.Provider value={value}>{children}<div className="pointer-events-none fixed bottom-5 right-5 z-[100] flex w-[min(380px,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">{items.map((item) => <div key={item.id} className="pointer-events-auto flex items-start gap-3 rounded-xl border border-white/10 bg-brand-indigo px-4 py-3 text-sm text-white shadow-lift animate-fade-up">{item.kind === 'success' ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-300" /> : <AlertCircle className="mt-0.5 size-4 shrink-0 text-amber-300" />}<span className="flex-1">{item.message}</span><button className="text-slate-400 hover:text-white" onClick={() => dismiss(item.id)} aria-label="Close"><X className="size-4" /></button></div>)}</div></ToastContext.Provider>;
}
export function useToast() { const context = useContext(ToastContext); if (!context) throw new Error('useToast must be used inside ToastProvider'); return context; }
