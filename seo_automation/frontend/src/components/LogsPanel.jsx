import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Radio } from 'lucide-react';

const levelColors = {
  INFO: '#1D1D1F',
  WARNING: '#6E6E73',
  ERROR: '#1D1D1F',
  DEBUG: '#86868B',
};

export default function LogsPanel({ logs }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="rounded-3xl p-8 flex flex-col" style={{ background: '#FFFFFF', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.04)' }}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#86868B' }}>Live Logs</h2>
        <div className="flex items-center gap-2">
          <Radio className="w-3 h-3 animate-pulse" style={{ color: '#1D1D1F' }} strokeWidth={2.5} />
          <span className="text-xs font-medium" style={{ color: '#86868B' }}>{logs.length} entries</span>
        </div>
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto max-h-72 font-mono text-xs space-y-2 rounded-2xl p-6"
        style={{ background: '#FAFAFA', border: '1px solid rgba(0,0,0,0.03)' }}
      >
        <AnimatePresence initial={false}>
          {logs.map((log, i) => (
            <motion.div
              key={`${log.timestamp}-${i}`}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
              className="flex gap-4 leading-relaxed py-1 break-words"
            >
              <span className="flex-shrink-0" style={{ color: '#86868B' }}>{log.timestamp}</span>
              <span className="flex-shrink-0 font-semibold" style={{ color: levelColors[log.level] || '#6E6E73' }}>
                [{log.level}]
              </span>
              <span className="break-words flex-1" style={{ color: '#1D1D1F' }}>{log.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>

        {logs.length === 0 && (
          <div className="text-center py-10 text-sm" style={{ color: '#86868B' }}>
            Waiting for pipeline to start...
          </div>
        )}
      </div>
    </div>
  );
}
