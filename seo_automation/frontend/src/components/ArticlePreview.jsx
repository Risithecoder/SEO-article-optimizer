import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

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
      setMessage(res.ok ? `Article ${action}${action === 'publish' ? 'ed' : 'd'} successfully` : (data.detail || 'Action failed'));
      if (res.ok) onRefresh?.();
    } catch (err) { setMessage(`Error: ${err.message}`); }
    finally { setActionLoading(''); }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this article permanently?')) return;
    setActionLoading('delete');
    try {
      await fetch(`${API}/articles/${article.id}`, { method: 'DELETE' });
      setMessage('Article deleted');
      setTimeout(() => { onClose(); onRefresh?.(); }, 600);
    } catch (err) { setMessage(err.message); }
    finally { setActionLoading(''); }
  };

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
        className="fixed inset-0 z-50 flex items-start justify-center p-8 overflow-y-auto bg-black/20 backdrop-blur-sm"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.98 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="w-full max-w-4xl my-8 rounded-2xl shadow-xl bg-white p-8 flex flex-col break-words"
        >
          {/* Header */}
          <div className="flex justify-between items-center pb-6 border-b border-gray-100 mb-8">
            <h2 className="text-2xl font-semibold text-[#1D1D1F] leading-snug pr-8">
              {article.title}
            </h2>
            <button
              onClick={onClose}
              className="p-2.5 rounded-full hover:bg-gray-100 transition-colors flex-shrink-0"
            >
              <X className="w-5 h-5 text-gray-500" strokeWidth={2} />
            </button>
          </div>

          {/* Message Banner */}
          {message && (
            <div className="mb-8 px-4 py-3 bg-gray-50 text-sm font-medium text-gray-900 rounded-lg">
              {message}
            </div>
          )}

          {/* Grid Layout (2-column) */}
          <div className="grid grid-cols-2 gap-8 mb-8">
            {/* Left Column: Content */}
            <div className="flex flex-col gap-6">
              <div>
                <label className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-2 block">
                  SEO Title
                </label>
                <p className="text-base text-gray-900 font-medium">
                  {article.title}
                </p>
              </div>

              <div>
                <label className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-4 block">
                  Article Content
                </label>
                <div className="prose prose-neutral max-w-none prose-sm text-gray-800">
                  {article.html_content ? (
                    <div dangerouslySetInnerHTML={{ __html: article.html_content }} />
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans">
                      {article.content || 'No content provided.'}
                    </pre>
                  )}
                </div>
              </div>
            </div>

            {/* Right Column: Meta */}
            <div className="flex flex-col gap-6">
              <div>
                <label className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-2 block">
                  Meta Description
                </label>
                <p className="text-base text-gray-600 leading-relaxed">
                  {article.meta_description || 'None'}
                </p>
              </div>
              <div>
                <label className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-2 block">
                  URL Slug
                </label>
                <p className="text-base text-gray-600 leading-relaxed">
                  {article.slug || 'None'}
                </p>
              </div>
              <div>
                <label className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-2 block">
                  Status
                </label>
                <p className="text-base text-gray-600 font-medium capitalize">
                  {article.status.replace('_', ' ')}
                </p>
              </div>
            </div>
          </div>

          {/* Schema Section (Full width) */}
          {schemaMarkup && (
            <div className="w-full bg-gray-50 rounded-xl p-4 font-mono text-sm mb-8 overflow-x-auto">
              <label className="text-xs uppercase tracking-wide text-gray-400 font-sans font-semibold mb-3 block">
                Schema Markup
              </label>
              <pre className="text-gray-600 whitespace-pre-wrap">
                {JSON.stringify(schemaMarkup, null, 2)}
              </pre>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4 mt-6 pt-6 border-t border-gray-100 flex-wrap">
            <Btn label="Approve" primary onClick={() => handleAction('approve')} loading={actionLoading === 'approve'} disabled={!!actionLoading} />
            <Btn label="Publish" onClick={() => handleAction('publish')} loading={actionLoading === 'publish'} disabled={!!actionLoading} />
            <Btn label="Regenerate" onClick={() => handleAction('regenerate')} loading={actionLoading === 'regenerate'} disabled={!!actionLoading} />
            <Btn label="Reject" onClick={() => handleAction('reject')} loading={actionLoading === 'reject'} disabled={!!actionLoading} />
            <div className="flex-1" />
            <button
              onClick={handleDelete}
              disabled={!!actionLoading}
              className="px-6 py-3 rounded-full font-medium text-sm text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors disabled:opacity-50"
            >
              Delete
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function Btn({ label, primary, onClick, loading, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-6 py-3 rounded-full font-medium text-sm transition-colors disabled:opacity-50 flex items-center justify-center min-w-[120px] ${
        primary 
          ? 'bg-gray-900 text-white hover:bg-black' 
          : 'bg-white border border-gray-200 text-gray-900 hover:bg-gray-50'
      }`}
    >
      {loading ? 'Processing...' : label}
    </button>
  );
}
