import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const levelStyle = {
  INFO:    'text-gray-900',
  WARNING: 'text-gray-600',
  ERROR:   'text-gray-900',
  DEBUG:   'text-gray-400',
};

export default function LogsPanel({ logs }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [logs]);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm uppercase tracking-wide text-gray-500 font-semibold">
          Live System Logs
        </h2>
        <span className="text-xs font-medium text-gray-400">
          {logs.length} entries
        </span>
      </div>

      <div
        ref={ref}
        className="rounded-xl bg-gray-50 p-4 h-48 overflow-y-auto font-mono text-sm w-full border border-gray-100 shadow-inner"
      >
        <AnimatePresence initial={false}>
          {logs.map((log, i) => (
            <motion.div
              key={`${log.timestamp}-${i}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-4 py-1 border-b border-gray-100/50 break-words last:border-0"
            >
              <span className="flex-shrink-0 text-gray-400 w-20">{log.timestamp.split(' ')[1] || log.timestamp}</span>
              <span className={`flex-shrink-0 font-semibold w-16 ${levelStyle[log.level] || 'text-gray-500'}`}>
                [{log.level}]
              </span>
              <span className="flex-1 break-words text-gray-800">{log.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>

        {logs.length === 0 && (
          <div className="text-center py-10 text-gray-400 font-sans">
            Waiting for pipeline events...
          </div>
        )}
      </div>
    </div>
  );
}
