import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import KeystoneLogo from '@/components/KeystoneLogo';
import MeetDanyelModal from '@/components/landing/MeetDanyelModal';

export default function LandingNav() {
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);

  return (
    <>
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-12 h-16 bg-landing-bg/60 backdrop-blur-xl border-b border-border/30"
      >
        <div className="flex items-center gap-2.5">
          <Link
            to="/"
            aria-label="Open landing page"
            className="flex items-center gap-2.5 rounded-lg transition-opacity hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary/60 focus:ring-offset-2 focus:ring-offset-background"
          >
            <KeystoneLogo size={32} />
            <span className="text-sm font-semibold text-foreground tracking-tight">Axiovance</span>
          </Link>
          <button
            type="button"
            onClick={() => setIsBuilderOpen(true)}
            className="text-[10px] text-muted-foreground transition-colors hover:text-primary focus:outline-none focus:text-primary"
            aria-label="Open Meet Danyel card"
            data-usage-label="by Danyel Lambert"
          >
            by Danyel Lambert
          </button>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setIsBuilderOpen(true)}
            className="hidden sm:inline-flex text-xs font-medium text-muted-foreground hover:text-foreground border border-border/50 bg-card/20 hover:bg-card/40 px-4 py-2 rounded-lg transition-colors"
            data-usage-label="Meet Danyel"
          >
            Meet Danyel
          </button>
          <Link
            to="/app"
            className="text-xs font-medium text-primary-foreground bg-primary hover:bg-primary/90 px-4 py-2 rounded-lg transition-colors"
            data-usage-label="Enter Workbench"
          >
            Enter Workbench
          </Link>
        </div>
      </motion.header>

      <MeetDanyelModal isOpen={isBuilderOpen} onClose={() => setIsBuilderOpen(false)} />
    </>
  );
}
