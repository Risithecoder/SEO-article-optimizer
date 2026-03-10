import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Square } from 'lucide-react';

const statusConfig = {
  idle:      { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Idle' },
  running:   { bg: 'bg-gray-200', text: 'text-gray-900', label: 'Running' },
  completed: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Completed' },
  failed:    { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Failed' },
};

function StepRow({ step, index }) {
  const cfg = statusConfig[step.status] || statusConfig.idle;
  const isRunning = step.status === 'running';

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className={`grid grid-cols-[220px_1fr_120px] items-center gap-4 py-3 px-4 rounded-xl transition-colors duration-150 ${isRunning ? 'bg-gray-50' : ''}`}
    >
      {/* Left: Step name */}
      <div className="flex items-center gap-3 min-w-0 pr-4 border-r border-gray-100 h-full">
        {isRunning ? (
          <Loader2 className="animate-spin w-4 h-4 text-gray-900 flex-shrink-0" strokeWidth={2} />
        ) : (
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${step.status === 'completed' ? 'bg-gray-400' : 'bg-gray-200'}`} />
        )}
        <span className="text-sm font-semibold text-[#1D1D1F] truncate">{step.label}</span>
      </div>

      {/* Center: Description */}
      <span className="text-sm text-[#6E6E73] truncate">
        {step.detail || '—'}
      </span>

      {/* Right: Status indicator */}
      <div className="flex items-center justify-end">
        <span className={`text-xs font-medium px-3 py-1 rounded-full whitespace-nowrap ${cfg.bg} ${cfg.text}`}>
          {cfg.label}
        </span>
      </div>
    </motion.div>
  );
}

export default function PipelineStatus({ steps }) {
  const [stopping, setStopping] = useState(false);
  const isRunning = steps?.some(s => s.status === 'running');

  useEffect(() => {
    if (!isRunning) setStopping(false);
  }, [isRunning]);

  const handleStop = async () => {
    if (!isRunning) return;
    setStopping(true);
    try {
      await fetch('/api/stop_pipeline', { method: 'POST' });
    } catch (err) {
      console.error('Failed to stop pipeline:', err);
      setStopping(false);
    }
  };

  if (!steps || steps.length === 0) return null;

  return (
    <div className="rounded-2xl bg-white shadow-sm border border-[#E5E5E7] p-6">
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-2">
            Pipeline Status
          </h2>
          <p className="text-sm text-[#6E6E73]">
            Live progression of the content generation engine.
          </p>
        </div>
        
        {isRunning && (
          <button
            onClick={handleStop}
            disabled={stopping}
            title="Stop Pipeline"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {stopping ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Square className="w-4 h-4" fill="currentColor" />
            )}
            {stopping ? 'Stopping...' : 'Stop'}
          </button>
        )}
      </div>

      <div className="flex flex-col gap-2">
        {/* Header row (optional, helps structure visually) */}
        <div className="grid grid-cols-[220px_1fr_120px] items-center gap-4 px-4 pb-2 border-b border-gray-100">
          <span className="text-xs uppercase tracking-wide text-gray-400 font-semibold">Step</span>
          <span className="text-xs uppercase tracking-wide text-gray-400 font-semibold">Detail</span>
          <span className="text-xs uppercase tracking-wide text-gray-400 font-semibold text-right">Status</span>
        </div>

        {/* Rows */}
        {steps.map((step, i) => (
          <StepRow key={step.id} step={step} index={i} />
        ))}
      </div>
    </div>
  );
}
