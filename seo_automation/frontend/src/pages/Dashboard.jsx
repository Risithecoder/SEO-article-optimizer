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
    if (pipelineComplete) {
      fetchArticles();
      fetchStats();
    }
  }, [pipelineComplete, fetchArticles, fetchStats]);

  useEffect(() => {
    fetchArticles();
    fetchStats();
    const interval = setInterval(() => {
      fetchArticles();
      fetchStats();
    }, 10000);
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
    <div className="min-h-screen" style={{ background: '#F5F5F7' }}>
      {/* Top bar — frosted glass */}
      <header className="sticky top-0 z-40 border-b" style={{ background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', borderColor: 'rgba(0,0,0,0.06)' }}>
        <div className="max-w-7xl mx-auto px-10 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold tracking-tight" style={{ color: '#1D1D1F' }}>Oliveboard AI Content Engine</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ background: connected ? '#1D1D1F' : '#C7C7CC' }} />
              <span className="text-xs font-medium" style={{ color: '#86868B' }}>{connected ? 'Live' : 'Offline'}</span>
            </div>
            <div className="h-5 w-px" style={{ background: 'rgba(0,0,0,0.08)' }} />
            <DashboardToggle isMinimal={isMinimal} onToggle={() => setIsMinimal(!isMinimal)} />
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="max-w-7xl mx-auto px-10 py-10">
        <div className={`grid grid-cols-1 ${isMinimal ? 'lg:grid-cols-1 place-items-center min-h-[50vh]' : 'lg:grid-cols-4'} gap-10`}>
          
          {/* Sidebar */}
          <AnimatePresence>
            {!isMinimal && (
              <motion.div 
                initial={{ opacity: 0, width: 0, scale: 0.95 }}
                animate={{ opacity: 1, width: 'auto', scale: 1 }}
                exit={{ opacity: 0, width: 0, scale: 0.95, padding: 0, margin: 0, overflow: 'hidden' }}
                transition={{ duration: 0.3 }}
                className="lg:col-span-1 space-y-10"
              >
                <StatsPanel data={stats} connected={connected} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Main content */}
          <motion.div 
            layout
            className={`${isMinimal ? 'w-full max-w-7xl' : 'lg:col-span-3'} space-y-10 origin-top`}
            transition={{ duration: 0.4, ease: "easeInOut" }}
          >
            <AnimatePresence>
              {!isMinimal && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                  transition={{ duration: 0.3 }}
                >
                  <PipelineStatus steps={steps} />
                </motion.div>
              )}
            </AnimatePresence>

            <motion.div layout>
              <ArticleCarousel articles={articles} onSelect={handleSelectArticle} />
            </motion.div>

            <AnimatePresence>
              {!isMinimal && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                  transition={{ duration: 0.3 }}
                >
                  <LogsPanel logs={logs} />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
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
