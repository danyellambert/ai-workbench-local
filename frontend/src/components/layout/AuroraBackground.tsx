import { memo } from 'react';

const AuroraBackground = memo(() => (
  <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none" aria-hidden>
    <div className="absolute -top-1/2 -left-1/4 w-[800px] h-[800px] rounded-full opacity-[0.03]"
      style={{ background: 'radial-gradient(circle, hsl(187 90% 70%), transparent 70%)', animation: 'aurora 25s ease-in-out infinite' }} />
    <div className="absolute -bottom-1/3 -right-1/4 w-[600px] h-[600px] rounded-full opacity-[0.025]"
      style={{ background: 'radial-gradient(circle, hsl(260 60% 65%), transparent 70%)', animation: 'aurora 30s ease-in-out infinite reverse' }} />
    <div className="absolute top-1/4 right-1/3 w-[400px] h-[400px] rounded-full opacity-[0.02]"
      style={{ background: 'radial-gradient(circle, hsl(160 70% 50%), transparent 70%)', animation: 'aurora 20s ease-in-out infinite 5s' }} />
  </div>
));
AuroraBackground.displayName = 'AuroraBackground';
export default AuroraBackground;
