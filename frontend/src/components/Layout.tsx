import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Bot, Menu, X, Settings, FileText, Brain, Network, HardDrive, Clock, Plug, AlertTriangle, Bell, LogOut, User, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { useSidebar } from '@/contexts/SidebarContext';
import { useRole } from '@/contexts/RoleContext';
import ThemeToggle from '@/components/ThemeToggle';
import { useState, useEffect, useRef } from 'react';
import api from '@/api/client';
import { updateFaviconBadge, initializeFaviconManager } from '@/lib/favicon';
import { useNotification } from '@/contexts/NotificationContext';

export default function Layout() {
    const { isSidebarOpen, toggleSidebar } = useSidebar();
    const { user, canManageUsers } = useRole();
    const location = useLocation();
    const navigate = useNavigate();
    const { showNotification } = useNotification();
    const [alertStats, setAlertStats] = useState({ critical: 0, warning: 0, info: 0 });
    const faviconLinkRef = useRef<HTMLLinkElement | null>(null);

    useEffect(() => {
        // Initialize favicon link element if it doesn't exist
        faviconLinkRef.current = initializeFaviconManager();

        fetchAlertStats();
        const interval = setInterval(fetchAlertStats, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        // Update favicon badge whenever alertStats changes
        if (faviconLinkRef.current) {
            updateFaviconBadge({
                criticalCount: alertStats.critical,
                warningCount: alertStats.warning,
                originalFaviconUrl: '/vite.svg' // Specify the path to your original favicon
            }).then(dataUrl => {
                if (faviconLinkRef.current) {
                    faviconLinkRef.current.href = dataUrl;
                }
            }).catch(error => {
                console.error("Failed to update favicon badge:", error);
            });
        }
    }, [alertStats]);

    const fetchAlertStats = async () => {
        try {
            const res = await api.get('/alerts/stats');
            setAlertStats(res.data);
        } catch (error) {
            console.error('Failed to fetch alert stats', error);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        showNotification('Logged out successfully', 'success');
        navigate('/login');
    };

    const getAlertColor = () => {
        if (alertStats.critical > 0) return 'text-red-500';
        if (alertStats.warning > 0) return 'text-yellow-500';
        if (alertStats.info > 0) return 'text-blue-500';
        return 'text-green-500';
    };

    const allNavItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: Network, label: 'Environment', path: '/homelab' },
        { icon: Server, label: 'Servers', path: '/profiles' },
        { icon: HardDrive, label: 'Hardware', path: '/hardware' },
        { icon: Plug, label: 'Plugins', path: '/plugins' },
        { icon: Bot, label: 'Intelligence', path: '/ai' },
        { icon: FileText, label: 'Reports', path: '/reports' },
        { icon: Brain, label: 'Knowledge', path: '/knowledge' },
        { icon: AlertTriangle, label: 'Thresholds', path: '/thresholds' },
        { icon: Bell, label: 'Alerts', path: '/alerts', dynamicColor: getAlertColor() },
        { icon: Clock, label: 'Automations', path: '/automations' },
        { icon: Users, label: 'Users', path: '/users' },
        { icon: Settings, label: 'Settings', path: '/settings' },
    ];

    // Filter nav items based on user role
    const navItems = allNavItems.filter(item => !item.adminOnly || canManageUsers);

    return (
        <div className="min-h-screen bg-background text-foreground flex overflow-hidden">
            {/* Sidebar */}
            <motion.aside
                initial={false}
                animate={{ width: isSidebarOpen ? 240 : 80 }}
                className="bg-card border-r border-border hidden md:flex flex-col relative z-20"
            >
                <div className="p-4 flex items-center justify-between h-16 border-b border-border">
                    <div className={cn("font-bold text-lg leading-tight", !isSidebarOpen && "hidden")}>
                        <div>Homelab</div>
                        <div>Intelligence</div>
                    </div>
                    <div className="flex items-center gap-2">
                        {isSidebarOpen && <ThemeToggle />}
                        <button onClick={toggleSidebar} className="p-1 hover:bg-muted rounded" title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}>
                            {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
                        </button>
                    </div>
                </div>

                <nav className="flex-1 p-2 space-y-2 mt-4">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.path;
                        const hasDynamicColor = item.dynamicColor;

                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
                                    isActive
                                        ? "bg-primary text-primary-foreground"
                                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                                )}
                            >
                                <Icon size={20} className={!isActive && hasDynamicColor ? hasDynamicColor : ''} />
                                {isSidebarOpen && <span className={!isActive && hasDynamicColor ? hasDynamicColor : ''}>{item.label}</span>}
                            </Link>
                        );
                    })}
                </nav>

                {/* User Menu */}
                <div className="p-2 border-t border-border">
                    <div className="flex items-center gap-3 px-3 py-2 text-sm">
                        <User size={20} className="text-muted-foreground" />
                        {isSidebarOpen && user && (
                            <span className="flex-1 truncate text-muted-foreground">{user.username}</span>
                        )}
                    </div>
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                        title="Logout"
                    >
                        <LogOut size={20} />
                        {isSidebarOpen && <span>Logout</span>}
                    </button>
                </div>
            </motion.aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto relative z-10">
                <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-card/50 backdrop-blur sticky top-0 md:hidden">
                    <div className="font-bold text-base leading-tight">
                        <div>Homelab</div>
                        <div>Intelligence</div>
                    </div>
                    <ThemeToggle />
                </header>
                <div className="p-6 max-w-7xl mx-auto">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}
