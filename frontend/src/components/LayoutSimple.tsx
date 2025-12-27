import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Menu, X, LayoutDashboard, Server, Plug, Settings, HardDrive, Users, Bell, FileText, Bot, Package } from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';
import { useRole } from '@/contexts/RoleContext';
import ThemeToggle from '@/components/ThemeToggle';

export default function LayoutSimple() {
    const { isSidebarOpen, toggleSidebar } = useSidebar();
    const { user } = useRole();
    const location = useLocation();

    const navItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: Server, label: 'Homelab', path: '/homelab' },
        { icon: HardDrive, label: 'Hardware', path: '/hardware' },
        { icon: Plug, label: 'Plugins', path: '/plugins' },
        { icon: Package, label: 'Marketplace', path: '/marketplace' },
        { icon: Bot, label: 'AI Intelligence', path: '/ai' },
        { icon: FileText, label: 'Reports', path: '/reports' },
        { icon: Bell, label: 'Alerts', path: '/alerts' },
        { icon: Users, label: 'Users', path: '/users' },
        { icon: Settings, label: 'Settings', path: '/settings' },
    ];

    return (
        <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
            {/* Sidebar */}
            <aside className={`${isSidebarOpen ? 'w-64' : 'w-16'} bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 flex flex-col`}>
                {/* Header */}
                <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
                    {isSidebarOpen && <h1 className="text-xl font-bold text-gray-900 dark:text-white">Unity</h1>}
                    <button onClick={toggleSidebar} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                        {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                                    isActive
                                        ? 'bg-blue-500 text-white'
                                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                                title={!isSidebarOpen ? item.label : ''}
                            >
                                <Icon size={20} />
                                {isSidebarOpen && <span className="text-sm">{item.label}</span>}
                            </Link>
                        );
                    })}
                </nav>

                {/* User info & Theme */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                    {isSidebarOpen && (
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-semibold">
                                {user?.username?.[0]?.toUpperCase() || 'A'}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{user?.username || 'Admin'}</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{user?.role || 'admin'}</p>
                            </div>
                        </div>
                    )}
                    <ThemeToggle />
                </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 overflow-auto">
                <Outlet />
            </main>
        </div>
    );
}
