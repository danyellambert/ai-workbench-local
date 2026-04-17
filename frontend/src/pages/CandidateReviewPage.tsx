import { motion } from 'framer-motion';
import { UserCheck, Sparkles, Star, AlertTriangle, Briefcase, GraduationCap, CheckCircle2, Upload, Target, Search, ShieldAlert } from 'lucide-react';
import { PageHeader, GlassCard } from '@/components/shared/ui-components';
import { candidateData } from '@/lib/mock-data';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

const roleFitRubric = [
  { requirement: 'LLM / Transformer expertise', type: 'must-have' as const, met: true, evidence: 'T5 development at Google Brain, RLHF at Anthropic, 3 NeurIPS papers' },
  { requirement: 'Production ML systems at scale', type: 'must-have' as const, met: true, evidence: '10M+ daily predictions, MLOps toolchain (Kubeflow, MLflow, W&B)' },
  { requirement: 'Team leadership experience', type: 'must-have' as const, met: true, evidence: 'Led 5-person ML team at Scale AI, mentored 3 interns at Google Brain' },
  { requirement: 'RAG / retrieval system design', type: 'must-have' as const, met: false, evidence: 'Not explicitly mentioned — probe in interview' },
  { requirement: 'Regulatory compliance (SOC2, HIPAA)', type: 'nice-to-have' as const, met: false, evidence: 'No direct compliance experience noted in CV' },
  { requirement: 'Edge / on-premise deployment', type: 'nice-to-have' as const, met: false, evidence: 'Cloud-only experience — limited transferability' },
  { requirement: 'Cross-functional collaboration', type: 'nice-to-have' as const, met: true, evidence: 'Product collaboration at Scale AI, cross-team influence at Anthropic' },
];

const interviewFocusAreas = [
  { area: 'RAG Architecture & Retrieval Design', reason: 'Core to role — no explicit CV evidence. Assess depth of vector DB, chunking and reranking knowledge.', priority: 'high' as const },
  { area: 'System Design Under Constraints', reason: 'Role requires on-premise/edge awareness. Probe experience with latency budgets and resource-constrained inference.', priority: 'high' as const },
  { area: 'Technical Leadership Scope', reason: 'CV shows IC lead roles only. Clarify management vs technical authority boundaries.', priority: 'medium' as const },
  { area: 'Compliance & Governance Awareness', reason: 'Regulatory gap may be trainable. Assess willingness and aptitude for SOC2/HIPAA contexts.', priority: 'low' as const },
];

const riskSignals = [
  { signal: 'RAG experience gap', severity: 'high' as const, detail: 'Core requirement not evidenced in CV. Mitigable if strong fundamentals confirmed in interview.' },
  { signal: 'Management scope unclear', severity: 'medium' as const, detail: 'IC lead ≠ people management. Clarify expectations if role includes direct reports.' },
  { signal: 'Tenure pattern', severity: 'low' as const, detail: '2-year average tenure across roles. Normal for ML engineering market; not a red flag.' },
];

const mustHaves = roleFitRubric.filter(r => r.type === 'must-have');
const mustHaveMet = mustHaves.filter(r => r.met).length;

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
              <p className="text-[10px] text-muted-foreground mt-1.5">
                {mustHaveMet}/{mustHaves.length} must-have requirements met. Advance to technical interview with focus on RAG architecture.
              </p>
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

          {/* Risk Signals */}
          <GlassCard delay={0.2}>
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4 h-4 text-glow-warning" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Decision Risks</h4>
            </div>
            <div className="space-y-2">
              {riskSignals.map(r => (
                <div key={r.signal} className="text-xs">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${r.severity === 'high' ? 'bg-glow-error' : r.severity === 'medium' ? 'bg-glow-warning' : 'bg-muted-foreground'}`} />
                    <span className="text-foreground font-medium">{r.signal}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground ml-3.5">{r.detail}</p>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Seniority Signals */}
          <GlassCard delay={0.25}>
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
          {/* Role-Fit Rubric */}
          <GlassCard delay={0.12}>
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-primary" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Role-Fit Rubric</h4>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">{mustHaveMet}/{mustHaves.length} must-haves met</span>
            </div>
            <div className="space-y-2">
              {roleFitRubric.map((r, i) => (
                <motion.div key={r.requirement} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + i * 0.03 }}
                  className={`flex items-start gap-3 py-2.5 px-3 rounded-lg ${r.met ? 'bg-glow-success/5' : 'bg-glow-warning/5'}`}>
                  <div className="mt-0.5 shrink-0">
                    {r.met ? <CheckCircle2 className="w-3.5 h-3.5 text-glow-success" /> : <AlertTriangle className="w-3.5 h-3.5 text-glow-warning" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground">{r.requirement}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded border font-medium ${r.type === 'must-have' ? 'bg-primary/10 text-primary border-primary/20' : 'bg-secondary text-muted-foreground border-border/50'}`}>
                        {r.type}
                      </span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{r.evidence}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>

          {/* Interview Focus Areas */}
          <GlassCard delay={0.18}>
            <div className="flex items-center gap-2 mb-4">
              <Search className="w-4 h-4 text-primary" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Interview Focus Areas</h4>
            </div>
            <div className="space-y-2">
              {interviewFocusAreas.map((f, i) => (
                <div key={f.area} className="flex items-start gap-3 py-2 px-3 rounded-lg bg-secondary/20">
                  <span className="text-[10px] font-bold text-muted-foreground w-4 mt-0.5">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground">{f.area}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-medium ${
                        f.priority === 'high' ? 'bg-glow-error/10 text-glow-error' : f.priority === 'medium' ? 'bg-glow-warning/10 text-glow-warning' : 'bg-secondary text-muted-foreground'
                      }`}>{f.priority}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{f.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Experience Timeline */}
          <GlassCard delay={0.22}>
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
