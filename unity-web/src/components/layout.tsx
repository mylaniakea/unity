import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Bot, Menu, X, Settings, FileText, Brain, Network, HardDrive, Plug, Bell, LogOut, User, Users, Boxes, Rocket } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/sidebar-context';
import { useRole } from '@/contexts/role-context';
import { useNotification } from '@/contexts/notification-context';
import { ModeToggle } from '@/components/mode-toggle';

export default function Layout() {
    const { isSidebarOpen, toggleSidebar } = useSidebar();
    const { user, canManageUsers } = useRole();
    const location = useLocation();
    const navigate = useNavigate();
    const { showNotification } = useNotification();

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        showNotification('Logged out successfully', 'success');
        navigate('/login');
    };

    // Note: Alert logic omitted for now as it requires backend
    const getAlertColor = () => '';

    const allNavItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: Boxes, label: 'Clusters', path: '/clusters' },
        { icon: Rocket, label: 'Orchestration', path: '/orchestration' },
        { icon: Network, label: 'Environment', path: '/homelab' },
        { icon: Server, label: 'Servers', path: '/profiles' },
        { icon: HardDrive, label: 'Hardware', path: '/hardware' },
        { icon: Plug, label: 'Plugins', path: '/plugins' },
        { icon: Bot, label: 'Intelligence', path: '/ai' },
        { icon: FileText, label: 'Reports', path: '/reports' },
        { icon: Brain, label: 'Knowledge', path: '/knowledge' },
        { icon: Bell, label: 'Alerts & Thresholds', path: '/alerts', dynamicColor: getAlertColor() },
        { icon: Users, label: 'Users', path: '/users', adminOnly: true },
        { icon: Settings, label: 'Settings', path: '/settings' },
    ];

    // Filter nav items based on user role
    const navItems = allNavItems.filter(item => !item.adminOnly || canManageUsers);

    return (
        <div className="min-h-screen bg-background text-foreground flex overflow-hidden">
            {/* Sidebar */}
            <aside
                className={cn(
                    "bg-card border-r border-border hidden md:flex flex-col relative z-20 transition-all duration-300",
                    isSidebarOpen ? "w-60" : "w-20"
                )}
            >
                <div className="p-4 flex items-center justify-between h-16 border-b border-border">
                    <div className={cn("font-bold text-2xl leading-tight truncate tracking-tight lowercase font-sans", !isSidebarOpen && "hidden")}>
                        unity
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Theme toggle moved to header usually, but preserved here if in original */}
                        {/* Replacing internal ThemeToggle with ModeToggle */}
                        {isSidebarOpen && <ModeToggle />}
                        <button onClick={toggleSidebar} className="p-1 hover:bg-muted rounded text-foreground" title={isSidebarOpen ? "Close Sidebar" : "Open Sidebar"}>
                            {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
                        </button>
                    </div>
                </div>

                <nav className="flex-1 p-2 space-y-2 mt-4 overflow-y-auto">
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
                                title={!isSidebarOpen ? item.label : undefined}
                            >
                                <Icon size={20} className={cn("min-w-[20px]", !isActive && hasDynamicColor ? hasDynamicColor : '')} />
                                {isSidebarOpen && <span className={cn("truncate", !isActive && hasDynamicColor ? hasDynamicColor : '')}>{item.label}</span>}
                            </Link>
                        );
                    })}
                </nav>

                {/* User Menu */}
                <div className="p-2 border-t border-border mt-auto">
                    <div className={cn("flex items-center gap-3 px-3 py-2 text-sm", !isSidebarOpen && "justify-center")}>
                        <User size={20} className="text-muted-foreground min-w-[20px]" />
                        {isSidebarOpen && user && (
                            <span className="flex-1 truncate text-muted-foreground">{user.username}</span>
                        )}
                    </div>
                    <button
                        onClick={handleLogout}
                        className={cn(
                            "w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors",
                            !isSidebarOpen && "justify-center"
                        )}
                        title="Logout"
                    >
                        <LogOut size={20} className="min-w-[20px]" />
                        {isSidebarOpen && <span>Logout</span>}
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto relative z-10 flex flex-col">
                <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-card/50 backdrop-blur sticky top-0 z-30 md:hidden">
                    <div className="font-bold text-xl leading-tight lowercase font-sans">
                        unity
                    </div>
                    {/* Mobile sidebar toggle would go here */}
                    <ModeToggle />
                </header>
                <div className="p-6 max-w-7xl mx-auto w-full">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}
