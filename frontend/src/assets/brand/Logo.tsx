import markUrl from './kairos-mark.svg';
import monoUrl from './kairos-mark-mono.svg';
import logoUrl from './kairos-logo.svg';
import darkLogoUrl from './kairos-logo-dark.svg';

export type LogoProps = {
  variant?: 'full' | 'mark';
  theme?: 'light' | 'dark' | 'mono';
  size?: number;
  className?: string;
};

/** Kairos brand lockup. SVG wordmark paths need no web font. */
export function Logo({ variant = 'full', theme = 'light', size = 36, className }: LogoProps) {
  const src = variant === 'mark'
    ? theme === 'mono' ? monoUrl : markUrl
    : theme === 'dark' ? darkLogoUrl : logoUrl;
  const width = variant === 'full' ? size * 3.8 : size;
  return (
    <img
      src={src}
      width={width}
      height={size}
      className={className}
      role="img"
      title="Kairos"
      aria-label="Kairos"
      alt="Kairos"
      draggable={false}
    />
  );
}

export default Logo;
