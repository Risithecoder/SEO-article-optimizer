import { motion } from 'framer-motion';

const statusConfig = {
  draft:              { bg: 'bg-gray-100', text: 'text-gray-500' },
  optimized:          { bg: 'bg-gray-100', text: 'text-gray-500' },
  awaiting_approval:  { bg: 'bg-gray-200', text: 'text-gray-700' },
  approved:           { bg: 'bg-gray-200', text: 'text-gray-900' },
  published:          { bg: 'bg-gray-900', text: 'text-white' },
  rejected:           { bg: 'bg-gray-100', text: 'text-gray-500' },
  failed:             { bg: 'bg-gray-100', text: 'text-gray-500' },
};

const statusLabels = {
  draft: 'Draft', optimized: 'Optimized', awaiting_approval: 'Awaiting',
  approved: 'Approved', published: 'Published', rejected: 'Rejected', failed: 'Failed',
};

export default function ArticleCard({ article, onSelect }) {
  const wordCount = article.content ? article.content.split(/\s+/).length : 0;
  const dateStr = article.created_at
    ? new Date(article.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : 'Just now';
  const cfg = statusConfig[article.status] || statusConfig.draft;
  const label = statusLabels[article.status] || 'Draft';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.03 }}
      transition={{ duration: 0.2 }}
      onClick={() => onSelect(article)}
      className="flex flex-col h-full rounded-2xl bg-white shadow-sm border border-gray-100 p-6 cursor-pointer hover:shadow-lg break-words"
    >
      <h3 className="text-base font-bold text-[#1D1D1F] leading-snug mb-2 line-clamp-2">
        {article.title || 'Untitled Article'}
      </h3>

      <p className="text-sm text-[#6E6E73] leading-relaxed line-clamp-3 mb-4 flex-1">
        {article.meta_description || article.slug || 'No summary available.'}
      </p>

      <div className="flex items-center gap-2 flex-wrap mb-6">
        <span className={`text-xs font-medium px-3 py-1 rounded-full ${cfg.bg} ${cfg.text}`}>
          {label}
        </span>
        <span className="text-xs text-gray-500 bg-gray-50 px-3 py-1 rounded-full">
          {wordCount > 0 ? `${wordCount} words` : dateStr}
        </span>
      </div>

      <div className="mt-auto pt-4 border-t border-gray-50 flex items-center justify-between">
        <span className="text-sm text-gray-500">{dateStr}</span>
        <span className="text-sm font-medium text-[#1D1D1F] hover:underline underline-offset-4">
          Preview article →
        </span>
      </div>
    </motion.div>
  );
}
