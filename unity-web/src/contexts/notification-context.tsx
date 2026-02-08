import { createContext, useContext, type ReactNode } from 'react';

interface NotificationContextType {
    showNotification: (message: string, type: 'success' | 'error' | 'info') => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
    const showNotification = (message: string, type: 'success' | 'error' | 'info') => {
        console.log(`[Notification: ${type}] ${message}`);
        // To be implemented with a toast library later
    };

    return (
        <NotificationContext.Provider value={{ showNotification }}>
            {children}
        </NotificationContext.Provider>
    );
}

export function useNotification() {
    const context = useContext(NotificationContext);
    if (context === undefined) {
        throw new Error('useNotification must be used within a NotificationProvider');
    }
    return context;
}
