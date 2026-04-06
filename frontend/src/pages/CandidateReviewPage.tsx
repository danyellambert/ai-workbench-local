import { motion } from 'framer-motion';
import { UserCheck, Sparkles, Star, AlertTriangle, Briefcase, GraduationCap, CheckCircle2, Upload } from 'lucide-react';
import { PageHeader, GlassCard } from '@/components/shared/ui-components';
import { candidateData } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

export default function CandidateReviewPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Candidate Review" description="AI-powered hiring intelligence with grounded evaluation and scoring.">
        <Button variant="outline" className="h-9 px-4 text-xs border-border/50"><Upload className="w-3.5 h-3.5 mr-2" /> Upload CV</Button>
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"><Sparkles className="w-3.5 h-3.5 mr-2" /> Generate Deck</Button>
      </PageHeader>

      <div className="grid lg:grid-cols-12 gap-4">
        {/* Profile Hero */}
        <div className="lg:col-span-4 space-y-4">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="glass rounded-xl p-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-gradient-primary">SC</span>
            </div>
            <h3 className="text-lg font-semibold text-foreground">{candidateData.name}</h3>
            <p className="text-sm text-muted-foreground">{candidateData.title}</p>
            <p className="text-xs text-muted-foreground mt-1">{candidateData.location}</p>

            <div className="mt-5 pt-5 border-t border-border/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Overall Score</span>
                <span className="text-sm font-semibold text-primary">{candidateData.overallScore}/100</span>
              </div>
              <Progress value={candidateData.overallScore} className="h-2 bg-secondary" />
            </div>

            <div className="mt-4 bg-glow-success/5 border border-glow-success/20 rounded-lg p-3">
              <div className="flex items-center justify-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-glow-success" />
                <span className="text-sm font-semibold text-glow-success">{candidateData.recommendation}</span>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-left">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Briefcase className="w-3.5 h-3.5" />{candidateData.experience}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <GraduationCap className="w-3.5 h-3.5" />{candidateData.education}
              </div>
            </div>
          </motion.div>

          {/* Seniority Signals */}
          <GlassCard delay={0.2}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Seniority Signals</h4>
            <div className="space-y-2">
              {candidateData.senioritySignals.map(signal => (
                <div key={signal} className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Star className="w-3 h-3 text-glow-warning shrink-0" />{signal}
                </div>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-8 space-y-4">
          {/* Experience Timeline */}
          <GlassCard delay={0.15}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-4">Experience</h4>
            <div className="space-y-4">
              {candidateData.experiences.map((exp, i) => (
                <motion.div key={exp.company} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.25 + i * 0.08 }}
                  className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Briefcase className="w-4 h-4 text-primary" />
                    </div>
                    {i < candidateData.experiences.length - 1 && <div className="w-px flex-1 bg-border mt-2" />}
                  </div>
                  <div className="pb-4 flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h5 className="text-sm font-medium text-foreground">{exp.role}</h5>
                      <span className="text-[10px] text-muted-foreground">{exp.period}</span>
                    </div>
                    <p className="text-xs text-primary/80 mb-2">{exp.company}</p>
                    <div className="space-y-1">
                      {exp.highlights.map(h => (
                        <p key={h} className="text-xs text-muted-foreground flex items-start gap-1.5">
                          <span className="w-1 h-1 rounded-full bg-muted-foreground mt-1.5 shrink-0" />{h}
                        </p>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Strengths */}
            <GlassCard delay={0.3}>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-glow-success" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Strengths</h4>
              </div>
              <div className="space-y-2">
                {candidateData.strengths.map(s => (
                  <p key={s} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-glow-success mt-1.5 shrink-0" />{s}
                  </p>
                ))}
              </div>
            </GlassCard>

            {/* Gaps */}
            <GlassCard delay={0.35}>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-glow-warning" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Gaps</h4>
              </div>
              <div className="space-y-2">
                {candidateData.gaps.map(g => (
                  <p key={g} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-glow-warning mt-1.5 shrink-0" />{g}
                  </p>
                ))}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
