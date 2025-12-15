import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '@/api/client';

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
    canEdit: boolean; // true for admin/user, false for viewer
    canManageUsers: boolean; // true only for admin
    loading: boolean;
    refreshUser: () => Promise<void>;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export function RoleProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchUser = async () => {
        try {
            const res = await api.get('/auth/me');
            setUser(res.data);
        } catch (error) {
            console.error('Failed to fetch user', error);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUser();
    }, []);

    const value: RoleContextType = {
        user,
        role: user?.role || null,
        isAdmin: user?.role === 'admin',
        isUser: user?.role === 'user',
        isViewer: user?.role === 'viewer',
        canEdit: user?.role === 'admin' || user?.role === 'user',
        canManageUsers: user?.role === 'admin',
        loading,
        refreshUser: fetchUser
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
