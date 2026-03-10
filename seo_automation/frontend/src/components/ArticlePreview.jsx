import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Check, Send, RefreshCw, Ban, Trash2 } from 'lucide-react';

const API = '/api';

export default function ArticlePreview({ article, onClose, onRefresh }) {
  const [actionLoading, setActionLoading] = useState('');
  const [message, setMessage] = useState('');

  if (!article) return null;

  const handleAction = async (action) => {
    setActionLoading(action);
    setMessage('');
    try {
      const res = await fetch(`${API}/articles/${article.id}/${action}`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setMessage(`Article ${action}${action === 'publish' ? 'ed' : 'd'} successfully`);
        onRefresh?.();
      } else {
        setMessage(`${data.detail || 'Action failed'}`);
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setActionLoading('');
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this article permanently?')) return;
    setActionLoading('delete');
    try {
      await fetch(`${API}/articles/${article.id}`, { method: 'DELETE' });
      setMessage('Article deleted');
      setTimeout(() => { onClose(); onRefresh?.(); }, 800);
    } catch (err) {
      setMessage(`${err.message}`);
    } finally {
      setActionLoading('');
    }
  };

  const wordCount = article.content ? article.content.split(/\s+/).length : 0;
  let schemaMarkup = article.schema_markup;
  if (typeof schemaMarkup === 'string') {
    try { schemaMarkup = JSON.parse(schemaMarkup); } catch { schemaMarkup = null; }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-start justify-center p-8 overflow-y-auto"
        style={{ background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 30, scale: 0.97 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="w-full max-w-4xl my-8 rounded-3xl overflow-hidden shadow-2xl"
          style={{ background: '#FFFFFF', border: '1px solid rgba(0,0,0,0.06)' }}
        >
          {/* Header */}
          <div className="flex items-start justify-between p-10" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
            <div className="flex-1 mr-6 break-words">
              <h2 className="text-3xl font-bold leading-snug mb-3" style={{ color: '#1D1D1F' }}>{article.title}</h2>
              <p className="text-base font-medium" style={{ color: '#86868B' }}>{article.slug} · {wordCount} words</p>
            </div>
            <button
              onClick={onClose}
              className="p-3.5 flex-shrink-0 rounded-full cursor-pointer transition-colors duration-200"
              style={{ background: '#F5F5F7' }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#E8E8ED'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#F5F5F7'}
            >
              <X className="w-5 h-5" style={{ color: '#1D1D1F' }} strokeWidth={2} />
            </button>
          </div>

          {/* Meta info */}
          <div className="px-10 py-8 grid grid-cols-1 md:grid-cols-2 gap-8" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
            <div className="break-words">
              <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#86868B' }}>SEO Title</label>
              <p className="text-base font-medium mt-2" style={{ color: '#1D1D1F' }}>{article.title}</p>
            </div>
            <div className="break-words">
              <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#86868B' }}>Meta Description</label>
              <p className="text-base mt-2 leading-relaxed" style={{ color: '#6E6E73' }}>{article.meta_description || 'None'}</p>
            </div>
          </div>

          {/* Article content */}
          <div className="px-10 py-10 max-h-[500px] overflow-y-auto" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
            <label className="text-xs font-semibold uppercase tracking-wider mb-6 block" style={{ color: '#86868B' }}>Article Content</label>
            {article.html_content ? (
              <div
                className="prose prose-base max-w-none break-words"
                style={{ color: '#1D1D1F' }}
                dangerouslySetInnerHTML={{ __html: article.html_content }}
              />
            ) : (
              <pre
                className="text-base whitespace-pre-wrap font-mono rounded-2xl p-8 break-words"
                style={{ color: '#6E6E73', background: '#FAFAFA', border: '1px solid rgba(0,0,0,0.04)' }}
              >
                {article.content || 'No content'}
              </pre>
            )}
          </div>

          {/* Schema markup */}
          {schemaMarkup && (
            <div className="px-10 py-8" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
              <label className="text-xs font-semibold uppercase tracking-wider mb-5 block" style={{ color: '#86868B' }}>Schema Markup</label>
              <pre
                className="text-sm rounded-2xl p-8 overflow-x-auto max-h-48 break-words whitespace-pre-wrap"
                style={{ color: '#86868B', background: '#FAFAFA', border: '1px solid rgba(0,0,0,0.04)' }}
              >
                {JSON.stringify(schemaMarkup, null, 2)}
              </pre>
            </div>
          )}

          {/* Message */}
          {message && (
            <div className="px-10 py-5 text-base font-medium" style={{ color: '#1D1D1F', background: '#F5F5F7' }}>
              {message}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-4 p-10 bg-[#FAFAFA]">
            <ActionButton label="Approve" Icon={Check} bg="#1D1D1F" hoverBg="#000000" textColor="#FFFFFF" border="transparent" onClick={() => handleAction('approve')} loading={actionLoading === 'approve'} disabled={!!actionLoading} />
            <ActionButton label="Publish" Icon={Send} bg="#FFFFFF" hoverBg="#F5F5F7" textColor="#1D1D1F" border="rgba(0,0,0,0.1)" onClick={() => handleAction('publish')} loading={actionLoading === 'publish'} disabled={!!actionLoading} />
            <ActionButton label="Regenerate" Icon={RefreshCw} bg="#FFFFFF" hoverBg="#F5F5F7" textColor="#1D1D1F" border="rgba(0,0,0,0.1)" onClick={() => handleAction('regenerate')} loading={actionLoading === 'regenerate'} disabled={!!actionLoading} />
            <ActionButton label="Reject" Icon={Ban} bg="#FFFFFF" hoverBg="#F5F5F7" textColor="#1D1D1F" border="rgba(0,0,0,0.1)" onClick={() => handleAction('reject')} loading={actionLoading === 'reject'} disabled={!!actionLoading} />
            <div className="flex-1" />
            <button
              onClick={handleDelete}
              disabled={!!actionLoading}
              className="flex items-center gap-2 text-base cursor-pointer transition-colors duration-200 disabled:opacity-40 font-medium px-4 py-2 rounded-full"
              style={{ color: '#86868B' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#1D1D1F'; e.currentTarget.style.background = '#E8E8ED'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#86868B'; e.currentTarget.style.background = 'transparent'; }}
            >
              <Trash2 className="w-4 h-4" strokeWidth={2} />
              Delete
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function ActionButton({ label, Icon, bg, hoverBg, textColor, border, onClick, loading, disabled }) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      disabled={disabled}
      className="px-8 py-3.5 rounded-full text-base font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2.5 transition-colors duration-200"
      style={{ background: bg, color: textColor, border: `1px solid ${border}` }}
      onMouseEnter={(e) => !disabled && (e.currentTarget.style.background = hoverBg)}
      onMouseLeave={(e) => !disabled && (e.currentTarget.style.background = bg)}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {label}...
        </span>
      ) : (
        <>
          <Icon className="w-4 h-4" strokeWidth={2} />
          {label}
        </>
      )}
    </motion.button>
  );
}
