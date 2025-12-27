import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface UpdatesContextType {
  updatesPaused: boolean;
  toggleUpdates: () => void;
  pauseUpdates: () => void;
  resumeUpdates: () => void;
}

const UpdatesContext = createContext<UpdatesContextType | undefined>(undefined);

export function UpdatesProvider({ children }: { children: ReactNode }) {
  // Load from localStorage, default to false (updates enabled)
  const [updatesPaused, setUpdatesPaused] = useState(() => {
    const saved = localStorage.getItem('updatesPaused');
    return saved === 'true';
  });

  // Save to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('updatesPaused', String(updatesPaused));
  }, [updatesPaused]);

  const toggleUpdates = () => {
    setUpdatesPaused(prev => !prev);
  };

  const pauseUpdates = () => {
    setUpdatesPaused(true);
  };

  const resumeUpdates = () => {
    setUpdatesPaused(false);
  };

  return (
    <UpdatesContext.Provider
      value={{
        updatesPaused,
        toggleUpdates,
        pauseUpdates,
        resumeUpdates,
      }}
    >
      {children}
    </UpdatesContext.Provider>
  );
}

export function useUpdates() {
  const context = useContext(UpdatesContext);
  if (context === undefined) {
    throw new Error('useUpdates must be used within an UpdatesProvider');
  }
  return context;
}

