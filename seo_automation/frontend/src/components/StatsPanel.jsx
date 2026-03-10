import { motion } from 'framer-motion';
import { Key, Package, FileText, Clock, Rocket, ClipboardList } from 'lucide-react';

const stats = [
  { key: 'keywords_fetched',        label: 'Keywords',  Icon: Key },
  { key: 'clusters_created',        label: 'Clusters',  Icon: Package },
  { key: 'articles_total',          label: 'Articles',  Icon: FileText },
  { key: 'articles_awaiting_approval', label: 'Awaiting', Icon: Clock },
  { key: 'articles_published',      label: 'Published', Icon: Rocket },
  { key: 'articles_draft',          label: 'Drafts',    Icon: ClipboardList },
];

export default function StatsPanel({ data, connected }) {
  return (
    <div className="flex flex-col">
      <h2 className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-6">
        Overview Stats
      </h2>

      <div className="flex flex-col gap-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.key}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="flex items-center justify-between group cursor-default"
          >
            <div className="flex items-center gap-3">
              <stat.Icon className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" strokeWidth={2} />
              <span className="text-base text-[#6E6E73] group-hover:text-[#1D1D1F] transition-colors font-medium">
                {stat.label}
              </span>
            </div>
            {/* Numbers align right */}
            <span className="text-base font-semibold text-[#1D1D1F] tabular-nums">
              {data?.[stat.key] ?? 0}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
