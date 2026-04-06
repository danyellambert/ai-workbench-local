import { useRef } from 'react';
import LandingHero from '@/components/landing/LandingHero';
import LandingWorkflows from '@/components/landing/LandingWorkflows';
import LandingHowItWorks from '@/components/landing/LandingHowItWorks';
import LandingWhyGrounded from '@/components/landing/LandingWhyGrounded';
import LandingAILab from '@/components/landing/LandingAILab';
import LandingArtifacts from '@/components/landing/LandingArtifacts';
import LandingFinalCTA from '@/components/landing/LandingFinalCTA';
import LandingBackground from '@/components/landing/LandingBackground';
import LandingNav from '@/components/landing/LandingNav';

export default function LandingPage() {
  const workflowsRef = useRef<HTMLDivElement>(null);

  const scrollToWorkflows = () => {
    workflowsRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-screen bg-landing-bg overflow-hidden">
      <LandingBackground />
      <LandingNav />
      <LandingHero onExploreWorkflows={scrollToWorkflows} />
      <div ref={workflowsRef}>
        <LandingWorkflows />
      </div>
      <LandingHowItWorks />
      <LandingWhyGrounded />
      <LandingAILab />
      <LandingArtifacts />
      <LandingFinalCTA />
    </div>
  );
}
