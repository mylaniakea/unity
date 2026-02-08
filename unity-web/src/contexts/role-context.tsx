import { createContext, useContext, type ReactNode } from 'react';

// Mock user type
interface User {
    id: string;
    username: string;
    role: string;
}

interface RoleContextType {
    user: User | null;
    canManageUsers: boolean;
    isAdmin: boolean;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export function RoleProvider({ children }: { children: ReactNode }) {
    // Mock user for now
    const user: User = {
        id: '1',
        username: 'admin',
        role: 'admin'
    };

    const isAdmin = user?.role === 'admin';
    const canManageUsers = isAdmin;

    return (
        <RoleContext.Provider value={{ user, canManageUsers, isAdmin }}>
            {children}
        </RoleContext.Provider>
    );
}

export function useRole() {
    const context = useContext(RoleContext);
    if (context === undefined) {
        throw new Error('useRole must be used within a RoleProvider');
    }
    return context;
}
