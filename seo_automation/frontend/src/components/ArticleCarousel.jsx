import { useRef, useState } from 'react';
import ArticleCard from './ArticleCard';
import { FileText } from 'lucide-react';

export default function ArticleCarousel({ articles, onSelect }) {
  const scrollRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);

  if (!articles || articles.length === 0) {
    return (
      <div
        className="rounded-3xl p-10 text-center flex flex-col items-center justify-center min-h-[300px]"
        style={{ background: '#FFFFFF', boxShadow: '0 4px 24px rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.04)' }}
      >
        <FileText className="w-10 h-10 mb-5" style={{ color: '#C7C7CC' }} strokeWidth={1.5} />
        <div className="text-xl font-semibold mb-3" style={{ color: '#1D1D1F' }}>No articles generated yet</div>
        <div className="text-base" style={{ color: '#86868B' }}>Start the pipeline to generate content.</div>
      </div>
    );
  }

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setStartX(e.pageX - scrollRef.current.offsetLeft);
    setScrollLeft(scrollRef.current.scrollLeft);
  };
  const handleMouseLeave = () => setIsDragging(false);
  const handleMouseUp = () => setIsDragging(false);
  const handleMouseMove = (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    const walk = (x - startX) * 2;
    scrollRef.current.scrollLeft = scrollLeft - walk;
  };

  return (
    <div className="w-full py-4">
      <div className="flex items-center justify-between mb-6 px-2">
        <h2 className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#86868B' }}>
          Generated Articles
        </h2>
        <span className="text-xs font-medium" style={{ color: '#86868B' }}>{articles.length} articles</span>
      </div>

      <div 
        ref={scrollRef}
        className={`flex gap-10 overflow-x-auto pb-8 pt-4 px-2 snap-x snap-mandatory hide-scrollbar ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
        onMouseDown={handleMouseDown}
        onMouseLeave={handleMouseLeave}
        onMouseUp={handleMouseUp}
        onMouseMove={handleMouseMove}
        style={{ scrollBehavior: isDragging ? 'auto' : 'smooth' }}
      >
        {articles.map((article, i) => (
          <ArticleCard key={article.id || i} article={article} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}
