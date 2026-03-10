import ArticleCard from './ArticleCard';
import { FileText } from 'lucide-react';

export default function ArticleCarousel({ articles, onSelect }) {
  if (!articles || articles.length === 0) {
    return (
      <div className="w-full">
        <div className="mb-4">
          <h2 className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-2">
            Generated Articles
          </h2>
        </div>
        <div className="rounded-2xl bg-white shadow-sm border border-gray-100 p-8 flex flex-col items-center justify-center min-h-[240px]">
          <FileText className="w-8 h-8 text-gray-300 mb-4" strokeWidth={1.5} />
          <div className="text-base font-semibold text-[#1D1D1F] mb-1">No articles yet</div>
          <div className="text-sm text-[#86868B]">Start the pipeline to generate content.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-sm uppercase tracking-wide text-gray-500 font-semibold">
          Generated Articles
        </h2>
        <span className="text-sm font-medium text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
          {articles.length} article{articles.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {articles.map((article, i) => (
          <ArticleCard key={article.id || i} article={article} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}
