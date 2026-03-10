import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const statusColors = {
  draft: { bg: '#F5F5F7', text: '#86868B' },
  optimized: { bg: '#F5F5F7', text: '#6E6E73' },
  awaiting_approval: { bg: '#F5F5F7', text: '#6E6E73' },
  approved: { bg: '#E8E8ED', text: '#1D1D1F' },
  published: { bg: '#1D1D1F', text: '#FFFFFF' },
  rejected: { bg: '#F5F5F7', text: '#86868B' },
  failed: { bg: '#F5F5F7', text: '#86868B' },
};

const statusLabels = {
  draft: 'Draft',
  optimized: 'Optimized',
  awaiting_approval: 'Awaiting',
  approved: 'Approved',
  published: 'Published',
  rejected: 'Rejected',
  failed: 'Failed',
};

export default function ArticleCard({ article, onSelect }) {
  const wordCount = article.content ? article.content.split(/\s+/).length : 0;
  const dateStr = article.created_at 
    ? new Date(article.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : 'Just now';
  const statusText = statusLabels[article.status] || 'Draft';
  const colors = statusColors[article.status] || statusColors.draft;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.03, transition: { duration: 0.2, ease: 'easeOut' } }}
      className="flex-shrink-0 w-[340px] rounded-3xl p-8 cursor-pointer snap-center flex flex-col transition-shadow duration-300 break-words"
      style={{
        background: '#FFFFFF',
        border: '1px solid rgba(0,0,0,0.06)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.04)',
      }}
      onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 8px 40px rgba(0,0,0,0.08)'}
      onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.04)'}
      onClick={() => onSelect(article)}
    >
      {/* Status + Meta */}
      <div className="flex items-center justify-between mb-6">
        <span
          className="text-[11px] font-semibold uppercase tracking-wider px-3 py-1.5 rounded-full"
          style={{ background: colors.bg, color: colors.text }}
        >
          {statusText}
        </span>
        <span className="text-[11px] font-medium" style={{ color: '#86868B' }}>
          {wordCount > 0 ? `${wordCount} words` : dateStr}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-bold text-lg leading-snug mb-3 line-clamp-2" style={{ color: '#1D1D1F' }}>
        {article.title || 'Untitled Article'}
      </h3>

      {/* Summary */}
      <p className="text-sm line-clamp-3 mb-8 leading-relaxed flex-1" style={{ color: '#6E6E73' }}>
        {article.meta_description || article.slug || 'No summary available for this article.'}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between pt-5" style={{ borderTop: '1px solid rgba(0,0,0,0.05)' }}>
        <span className="text-[11px] font-medium" style={{ color: '#86868B' }}>
          {dateStr}
        </span>
        <span className="flex items-center gap-1.5 text-[12px] font-semibold transition-colors duration-200" style={{ color: '#1D1D1F' }}>
          Preview <ArrowRight className="w-3.5 h-3.5" strokeWidth={2} />
        </span>
      </div>
    </motion.div>
  );
}
