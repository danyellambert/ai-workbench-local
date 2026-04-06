import { memo } from 'react';

const LandingBackground = memo(() => (
  <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none" aria-hidden>
    {/* Aurora orbs */}
    <div className="absolute -top-[40%] -left-[20%] w-[900px] h-[900px] rounded-full opacity-[0.07]"
      style={{ background: 'radial-gradient(circle, hsl(217 91% 60%), transparent 60%)', animation: 'aurora 30s ease-in-out infinite' }} />
    <div className="absolute -bottom-[30%] -right-[15%] w-[700px] h-[700px] rounded-full opacity-[0.05]"
      style={{ background: 'radial-gradient(circle, hsl(260 60% 65%), transparent 60%)', animation: 'aurora 35s ease-in-out infinite reverse' }} />
    <div className="absolute top-[30%] right-[20%] w-[500px] h-[500px] rounded-full opacity-[0.03]"
      style={{ background: 'radial-gradient(circle, hsl(200 80% 55%), transparent 60%)', animation: 'aurora 25s ease-in-out infinite 3s' }} />
    
    {/* Subtle grid */}
    <div className="absolute inset-0 opacity-[0.02]"
      style={{
        backgroundImage: 'linear-gradient(hsl(217 91% 60% / 0.3) 1px, transparent 1px), linear-gradient(90deg, hsl(217 91% 60% / 0.3) 1px, transparent 1px)',
        backgroundSize: '80px 80px',
        animation: 'grid-fade 8s ease-in-out infinite',
      }} />

    {/* Floating particles */}
    {Array.from({ length: 20 }).map((_, i) => (
      <div key={i} className="absolute w-[2px] h-[2px] rounded-full bg-primary/40"
        style={{
          left: `${5 + (i * 4.7) % 90}%`,
          top: `${100 + (i * 13) % 20}%`,
          animation: `particle-float ${15 + (i % 5) * 4}s linear infinite`,
          animationDelay: `${i * 1.2}s`,
        }} />
    ))}
  </div>
));
LandingBackground.displayName = 'LandingBackground';
export default LandingBackground;
