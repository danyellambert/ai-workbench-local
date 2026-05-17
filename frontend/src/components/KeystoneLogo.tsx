import { cn } from '@/lib/utils';

interface KeystoneLogoProps {
  className?: string;
  size?: number;
}

/**
 * Axiovance — Cut Diamond
 * Sculptural diamond-shaped lock with a central core.
 */
export default function KeystoneLogo({ className, size = 32 }: KeystoneLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('shrink-0', className)}
      aria-label="Axiovance"
    >
      <defs>
        <linearGradient id="ks-outer" x1="20" y1="2" x2="20" y2="38" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="hsl(217 91% 65%)" />
          <stop offset="50%" stopColor="hsl(224 76% 48%)" />
          <stop offset="100%" stopColor="hsl(230 70% 28%)" />
        </linearGradient>
        <linearGradient id="ks-facet-l" x1="2" y1="20" x2="20" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="hsl(230 60% 22%)" />
          <stop offset="100%" stopColor="hsl(224 70% 40%)" />
        </linearGradient>
        <linearGradient id="ks-facet-r" x1="20" y1="20" x2="38" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="hsl(217 95% 70%)" />
          <stop offset="100%" stopColor="hsl(213 90% 55%)" />
        </linearGradient>
        <radialGradient id="ks-core" cx="20" cy="20" r="5" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="hsl(0 0% 100%)" />
          <stop offset="55%" stopColor="hsl(210 100% 85%)" />
          <stop offset="100%" stopColor="hsl(220 95% 60%)" />
        </radialGradient>
        <radialGradient id="ks-glow" cx="20" cy="20" r="18" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="hsl(220 100% 60%)" stopOpacity="0.45" />
          <stop offset="100%" stopColor="hsl(220 100% 60%)" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle cx="20" cy="20" r="18" fill="url(#ks-glow)" />

      <path d="M20 2 L38 20 L20 38 L2 20 Z" fill="url(#ks-outer)" />

      <path d="M20 2 L2 20 L20 38 L20 20 Z" fill="url(#ks-facet-l)" fillOpacity="0.95" />
      <path d="M20 2 L38 20 L20 38 L20 20 Z" fill="url(#ks-facet-r)" fillOpacity="0.85" />

      <path d="M20 2 L38 20 L20 20 L2 20 Z" fill="hsl(0 0% 100%)" fillOpacity="0.08" />

      {/* Inner keystone cut — clean, no D/L signature */}
      <path
        d="M20 9 L31 20 L20 31 L9 20 Z"
        fill="hsl(224 60% 12%)"
        stroke="hsl(217 95% 70%)"
        strokeOpacity="0.55"
        strokeWidth="0.6"
      />

      <circle cx="20" cy="20" r="2.6" fill="url(#ks-core)" />
      <circle cx="20" cy="20" r="1" fill="hsl(0 0% 100%)" />
    </svg>
  );
}
