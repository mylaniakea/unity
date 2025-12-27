import { createContext, useContext, useState, ReactNode } from 'react';

type Role = 'admin' | 'user' | 'viewer';

interface User {
    id: number;
    username: string;
    email: string | null;
    role: Role;
    is_active: boolean;
}

interface RoleContextType {
    user: User | null;
    role: Role | null;
    isAdmin: boolean;
    isUser: boolean;
    isViewer: boolean;
    canEdit: boolean;
    canManageUsers: boolean;
    loading: boolean;
    refreshUser: () => Promise<void>;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export function RoleProvider({ children }: { children: ReactNode }) {
    // Mock admin user for testing
    const [user] = useState<User>({
        id: 1,
        username: 'admin',
        email: 'admin@test.com',
        role: 'admin',
        is_active: true
    });

    const value: RoleContextType = {
        user,
        role: 'admin',
        isAdmin: true,
        isUser: false,
        isViewer: false,
        canEdit: true,
        canManageUsers: true,
        loading: false,
        refreshUser: async () => {}
    };

    return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole() {
    const context = useContext(RoleContext);
    if (context === undefined) {
        throw new Error('useRole must be used within a RoleProvider');
    }
    return context;
}
