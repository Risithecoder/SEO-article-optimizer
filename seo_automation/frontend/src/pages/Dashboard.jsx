import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PipelineStatus from '../components/PipelineStatus';
import LogsPanel from '../components/LogsPanel';
import ArticleCarousel from '../components/ArticleCarousel';
import ArticlePreview from '../components/ArticlePreview';
import StatsPanel from '../components/StatsPanel';
import DashboardToggle from '../components/DashboardToggle';
import useWebSocket from '../hooks/useWebSocket';

const API = '/api';

export default function Dashboard() {
  const { connected, steps, logs, pipelineComplete } = useWebSocket();
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [stats, setStats] = useState(null);
  const [isMinimal, setIsMinimal] = useState(false);

  const fetchArticles = useCallback(async () => {
    try {
      const res = await fetch(`${API}/articles`);
      const data = await res.json();
      setArticles(data.articles || []);
    } catch (err) {
      console.error('Failed to fetch articles:', err);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  useEffect(() => {
    if (pipelineComplete) { fetchArticles(); fetchStats(); }
  }, [pipelineComplete, fetchArticles, fetchStats]);

  useEffect(() => {
    fetchArticles(); fetchStats();
    const interval = setInterval(() => { fetchArticles(); fetchStats(); }, 10000);
    return () => clearInterval(interval);
  }, [fetchArticles, fetchStats]);

  const handleSelectArticle = async (article) => {
    try {
      const res = await fetch(`${API}/articles/${article.id}`);
      const fullArticle = await res.json();
      setSelectedArticle(fullArticle);
    } catch {
      setSelectedArticle(article);
    }
  };

  return (
    <div className="min-h-screen font-sans" style={{ background: '#F5F5F7' }}>
      {/* ─── Top bar ─── */}
      <header
        className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-[#E5E5E7]"
      >
        <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
          <h1 className="text-base font-semibold tracking-tight text-[#1D1D1F]">
            Oliveboard AI Content Engine
          </h1>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ background: connected ? '#1D1D1F' : '#C7C7CC' }} />
              <span className="text-xs font-medium text-[#86868B]">
                {connected ? 'Live' : 'Offline'}
              </span>
            </div>
            <div className="h-5 w-px bg-[#E5E5E7]" />
            <DashboardToggle isMinimal={isMinimal} onToggle={() => setIsMinimal(!isMinimal)} />
          </div>
        </div>
      </header>

      {/* ─── Content ─── */}
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className={`flex ${isMinimal ? 'justify-center' : ''}`}>

          {/* Sidebar */}
          <AnimatePresence>
            {!isMinimal && (
              <motion.aside
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 256 }}
                exit={{ opacity: 0, width: 0, overflow: 'hidden' }}
                transition={{ duration: 0.3 }}
                className="w-64 flex-shrink-0 border-r border-[#E5E5E7] pr-8"
              >
                <div className="sticky top-24 space-y-8">
                  <StatsPanel data={stats} connected={connected} />
                </div>
              </motion.aside>
            )}
          </AnimatePresence>

          {/* Main */}
          <motion.main layout className={`flex-1 min-w-0 flex flex-col gap-8 ${isMinimal ? 'px-0 max-w-4xl w-full' : 'px-10'}`} transition={{ duration: 0.35 }}>
            <AnimatePresence>
              {!isMinimal && (
                <motion.section
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                  transition={{ duration: 0.3 }}
                >
                  <PipelineStatus steps={steps} />
                </motion.section>
              )}
            </AnimatePresence>

            <section>
              <ArticleCarousel articles={articles} onSelect={handleSelectArticle} />
            </section>

            <AnimatePresence>
              {!isMinimal && (
                <motion.section
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                  transition={{ duration: 0.3 }}
                >
                  <LogsPanel logs={logs} />
                </motion.section>
              )}
            </AnimatePresence>
          </motion.main>
        </div>
      </div>

      {selectedArticle && (
        <ArticlePreview
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
          onRefresh={() => { fetchArticles(); fetchStats(); }}
        />
      )}
    </div>
  );
}
