import { motion } from 'framer-motion';
import { Key, Package, FileText, Clock, Rocket, ClipboardList } from 'lucide-react';

const stats = [
  { key: 'keywords_fetched', label: 'Keywords', Icon: Key },
  { key: 'clusters_created', label: 'Clusters', Icon: Package },
  { key: 'articles_total', label: 'Articles', Icon: FileText },
  { key: 'articles_awaiting_approval', label: 'Awaiting', Icon: Clock },
  { key: 'articles_published', label: 'Published', Icon: Rocket },
  { key: 'articles_draft', label: 'Drafts', Icon: ClipboardList },
];

export default function StatsPanel({ data, connected }) {
  return (
    <div className="rounded-3xl p-8" style={{ background: '#FFFFFF', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.04)' }}>
      {/* Connection status */}
      <div className="flex items-center gap-2 mb-6">
        <div className="w-2 h-2 rounded-full" style={{ background: connected ? '#1D1D1F' : '#C7C7CC' }} />
        <span className="text-xs font-medium" style={{ color: '#86868B' }}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <h2 className="text-xs font-semibold tracking-wider uppercase mb-5" style={{ color: '#86868B' }}>
        System Overview
      </h2>

      <div className="space-y-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.key}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-center justify-between py-3.5 px-5 rounded-2xl transition-colors duration-200"
            style={{ background: '#F5F5F7' }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#E8E8ED'}
            onMouseLeave={(e) => e.currentTarget.style.background = '#F5F5F7'}
          >
            <div className="flex items-center gap-3">
              <stat.Icon className="w-4 h-4" style={{ color: '#86868B' }} strokeWidth={1.8} />
              <span className="text-sm font-medium" style={{ color: '#6E6E73' }}>{stat.label}</span>
            </div>
            <span className="text-sm font-bold tabular-nums" style={{ color: '#1D1D1F' }}>
              {data?.[stat.key] ?? 0}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
