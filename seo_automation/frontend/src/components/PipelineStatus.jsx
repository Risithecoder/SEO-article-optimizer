import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const statusConfig = {
  idle: { bg: '#F5F5F7', text: '#86868B', label: 'Idle', dot: '#C7C7CC' },
  running: { bg: '#E8E8ED', text: '#1D1D1F', label: 'Running', dot: '#1D1D1F' },
  completed: { bg: '#F5F5F7', text: '#6E6E73', label: 'Completed', dot: '#86868B' },
  failed: { bg: '#F5F5F7', text: '#86868B', label: 'Failed', dot: '#86868B' },
};

function StepCard({ step, index }) {
  const cfg = statusConfig[step.status] || statusConfig.idle;
  const isRunning = step.status === 'running';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06 }}
      className="flex items-center gap-4 px-6 py-4 rounded-2xl transition-all duration-300 break-words"
      style={{
        background: isRunning ? '#F5F5F7' : '#FAFAFA',
        border: '1px solid rgba(0,0,0,0.04)',
        boxShadow: isRunning ? '0 2px 8px rgba(0,0,0,0.06)' : 'none',
      }}
    >
      <div className="relative flex-shrink-0">
        <div className="w-3 h-3 rounded-full" style={{ background: cfg.dot }} />
        {isRunning && (
          <div className="absolute inset-0 w-3 h-3 rounded-full animate-ping opacity-40" style={{ background: '#1D1D1F' }} />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium text-sm truncate" style={{ color: '#1D1D1F' }}>{step.label}</span>
          <span className="text-xs font-medium px-3 py-1 rounded-full whitespace-nowrap" style={{ background: cfg.bg, color: cfg.text }}>
            {cfg.label}
          </span>
        </div>
        {step.detail && (
          <p className="text-xs mt-1 truncate" style={{ color: '#86868B' }}>{step.detail}</p>
        )}
      </div>

      {isRunning && (
        <Loader2 className="animate-spin h-4 w-4 flex-shrink-0" style={{ color: '#1D1D1F' }} strokeWidth={2} />
      )}
    </motion.div>
  );
}

export default function PipelineStatus({ steps }) {
  if (!steps || steps.length === 0) return null;

  const completed = steps.filter((s) => s.status === 'completed').length;
  const progress = steps.length > 0 ? (completed / steps.length) * 100 : 0;

  return (
    <div className="rounded-3xl p-8" style={{ background: '#FFFFFF', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.04)' }}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#86868B' }}>Pipeline Progress</h2>
        <span className="text-xs font-medium" style={{ color: '#86868B' }}>{completed}/{steps.length} steps</span>
      </div>

      <div className="h-2 rounded-full overflow-hidden mb-8" style={{ background: '#F5F5F7' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: '#1D1D1F' }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <div className="space-y-4">
        {steps.map((step, i) => (
          <StepCard key={step.id} step={step} index={i} />
        ))}
      </div>
    </div>
  );
}
