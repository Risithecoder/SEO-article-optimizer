import { motion } from 'framer-motion';
import { Play } from 'lucide-react';

export default function StartScreen({ onStart, loading }) {
  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden" style={{ background: '#FFFFFF' }}>
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="text-center z-10 px-8"
      >
        {/* Title */}
        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-5xl md:text-6xl font-bold tracking-tight mb-4"
          style={{ color: '#1D1D1F' }}
        >
          Oliveboard AI
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-xl font-medium mb-6"
          style={{ color: '#6E6E73' }}
        >
          Content Engine
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-base mb-10 max-w-lg mx-auto leading-relaxed"
          style={{ color: '#86868B' }}
        >
          Automated SEO &amp; AEO content generation pipeline.
          Discover trends, generate articles, publish automatically.
        </motion.p>

        {/* Start Button */}
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onStart()}
          disabled={loading}
          className="px-8 py-4 rounded-full text-white font-semibold text-base cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200"
          style={{ background: '#1D1D1F', boxShadow: '0 4px 16px rgba(0,0,0,0.1)' }}
        >
          {loading ? (
            <span className="flex items-center gap-3">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Starting...
            </span>
          ) : (
            <span className="flex items-center gap-3">
              <Play className="w-5 h-5" strokeWidth={2} />
              Start Pipeline
            </span>
          )}
        </motion.button>

        {/* Dry run option */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="mt-8"
        >
          <button
            onClick={() => onStart(true)}
            disabled={loading}
            className="text-sm font-medium cursor-pointer disabled:cursor-not-allowed transition-colors duration-200"
            style={{ color: '#86868B' }}
            onMouseEnter={(e) => e.target.style.color = '#1D1D1F'}
            onMouseLeave={(e) => e.target.style.color = '#86868B'}
          >
            or run in dry-run mode →
          </button>
        </motion.div>
      </motion.div>
    </div>
  );
}
