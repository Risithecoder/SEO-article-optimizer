import { motion } from 'framer-motion';
import { Eye, EyeOff } from 'lucide-react';

export default function DashboardToggle({ isMinimal, onToggle }) {
  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.95 }}
      onClick={onToggle}
      className="p-3 rounded-full transition-all duration-200 focus:outline-none"
      style={{
        background: isMinimal ? '#E8E8ED' : '#F5F5F7',
        color: isMinimal ? '#1D1D1F' : '#86868B',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = isMinimal ? '#D1D1D6' : '#E8E8ED';
        if (!isMinimal) e.currentTarget.style.color = '#1D1D1F';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = isMinimal ? '#E8E8ED' : '#F5F5F7';
        e.currentTarget.style.color = isMinimal ? '#1D1D1F' : '#86868B';
      }}
      aria-label={isMinimal ? "Show full dashboard" : "Focus viewing mode"}
      title={isMinimal ? "Show full dashboard" : "Focus viewing mode"}
    >
      {isMinimal ? (
        <EyeOff className="w-[18px] h-[18px]" strokeWidth={1.8} />
      ) : (
        <Eye className="w-[18px] h-[18px]" strokeWidth={1.8} />
      )}
    </motion.button>
  );
}
