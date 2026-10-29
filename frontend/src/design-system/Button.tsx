import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { LoaderCircle } from 'lucide-react';
import { cn } from '../lib/utils';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  leadingIcon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, leadingIcon, className, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all duration-[250ms]',
        'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-amber/25',
        'disabled:pointer-events-none disabled:opacity-50',
        variant === 'primary' && 'border border-brand-amber/30 bg-brand-amber text-brand-indigo shadow-[0_10px_30px_rgba(245,158,11,.16)] hover:-translate-y-0.5 hover:bg-[#F6A51F]',
        variant === 'secondary' && 'border border-kairos-border bg-kairos-surface text-kairos-text shadow-soft hover:border-electric-violet/30 hover:bg-white/80',
        variant === 'ghost' && 'text-kairos-muted hover:bg-kairos-glass hover:text-kairos-text',
        variant === 'destructive' && 'border border-kairos-danger/20 bg-kairos-danger-bg text-kairos-danger hover:border-kairos-danger/40',
        size === 'sm' && 'min-h-9 px-3 text-xs',
        size === 'md' && 'min-h-11 px-4 text-sm',
        size === 'lg' && 'min-h-12 px-5 text-[15px]',
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : leadingIcon}
      {children}
    </button>
  );
});
