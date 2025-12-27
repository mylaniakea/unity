import { Pause, Play } from 'lucide-react';
import { useUpdates } from '@/contexts/UpdatesContext';
import { cn } from '@/lib/utils';

export default function UpdatesToggle() {
  const { updatesPaused, toggleUpdates } = useUpdates();

  return (
    <button
      onClick={toggleUpdates}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
        updatesPaused
          ? "bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 hover:bg-yellow-500/30"
          : "bg-green-500/20 text-green-600 dark:text-green-400 hover:bg-green-500/30"
      )}
      title={updatesPaused ? "Resume updates" : "Pause updates"}
    >
      {updatesPaused ? (
        <>
          <Pause size={16} />
          <span className="hidden sm:inline">Paused</span>
        </>
      ) : (
        <>
          <Play size={16} />
          <span className="hidden sm:inline">Live</span>
        </>
      )}
    </button>
  );
}

