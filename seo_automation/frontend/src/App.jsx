import { useState } from 'react';
import StartScreen from './components/StartScreen';
import Dashboard from './pages/Dashboard';

const API = '/api';

export default function App() {
  const [started, setStarted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleStart = async (dryRun = false) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dryRun) params.set('dry_run', 'true');

      const res = await fetch(`${API}/start_pipeline?${params}`, { method: 'POST' });
      if (res.ok) {
        setStarted(true);
      } else {
        const data = await res.json();
        if (data.detail && data.detail.toLowerCase().includes('already running')) {
          setStarted(true);
        } else {
          alert(data.detail || 'Failed to start pipeline');
        }
      }
    } catch (err) {
      // If backend isn't running yet, go to dashboard anyway for monitoring
      console.error('Start failed:', err);
      setStarted(true);
    } finally {
      setLoading(false);
    }
  };

  if (!started) {
    return <StartScreen onStart={handleStart} loading={loading} />;
  }

  return <Dashboard />;
}
