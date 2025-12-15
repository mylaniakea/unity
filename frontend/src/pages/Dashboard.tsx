import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { HardDrive, Cpu, Server as ServerIcon, MemoryStick, FileText, Activity, Layers, Clock, Users, Clipboard } from 'lucide-react';
import api from '@/api/client';
import { cn } from '@/lib/utils';

interface SystemStats {
    hardware: {
        cpu: { usage_percent: number; physical_cores: number; frequency: number };
        memory: { total: number; used: number; percent: number };
        disk: { total: number; used: number; percent: number };
    };
    os: { hostname: string; system: string; release: string };
    network: { bytes_sent: number; bytes_recv: number };
    
    // New Metrics
    memory: {
        total_bytes: number;
        used_bytes: number;
        available_bytes: number;
        swap_total_bytes: number;
        swap_used_bytes: number;
        swap_percent: number;
    };
    load_average: {
        '1min': number;
        '5min': number;
        '15min': number;
    };
    processes: {
        count: number;
    };
    file_descriptors: {
        open: number;
        max: number;
    };
    uptime_seconds: number;
}


export default function Dashboard() {
    const [stats, setStats] = useState<SystemStats | null>(null);
    const [dashStats, setDashStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [pollingInterval, setPollingInterval] = useState<number>(30); // Default to 30 seconds

    const fetchStats = async () => {
        try {
            const [sysRes, dashRes] = await Promise.all([
                api.get('/system/full'),
                api.get('/system/dashboard-stats')
            ]);
            setStats(sysRes.data);
            setDashStats(dashRes.data);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch stats", error);
            setLoading(false);
        }
    };

    const fetchPollingInterval = async () => {
        try {
            const res = await api.get('/settings/');
            setPollingInterval(res.data.polling_interval || 30);
        } catch (error) {
            console.error("Failed to fetch polling interval", error);
        }
    };

    useEffect(() => {
        fetchPollingInterval();
        fetchStats();
    }, []);

    useEffect(() => {
        const interval = setInterval(fetchStats, pollingInterval * 1000); // Convert to milliseconds
        return () => clearInterval(interval);
    }, [pollingInterval]);

    if (loading) return <div className="p-10 text-center">Loading System Intelligence...</div>;

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">System Overview</h1>
                <p className="text-muted-foreground">Real-time telemetry from {stats?.os.hostname}</p>
            </div>

            {/* System Telemetry */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <StatCard
                    title="CPU Usage"
                    value={`${stats?.hardware.cpu.usage_percent}%`}
                    subtext={`${stats?.hardware.cpu.physical_cores} Cores @ ${stats?.hardware.cpu.frequency}MHz`}
                    icon={Cpu}
                    color="text-blue-500"
                />
                <StatCard
                    title="Memory"
                    value={`${stats?.memory?.used_bytes && stats?.memory?.total_bytes ? ((stats.memory.used_bytes / stats.memory.total_bytes) * 100).toFixed(1) : stats?.hardware?.memory?.percent?.toFixed(1) || 0}%`}
                    subtext={`${stats?.memory?.used_bytes ? (stats.memory.used_bytes / 1024 / 1024 / 1024).toFixed(1) : stats?.hardware?.memory ? (stats.hardware.memory.used / 1024 / 1024 / 1024).toFixed(1) : 0} GB / ${stats?.memory?.total_bytes ? (stats.memory.total_bytes / 1024 / 1024 / 1024).toFixed(1) : stats?.hardware?.memory ? (stats.hardware.memory.total / 1024 / 1024 / 1024).toFixed(1) : 0} GB`}
                    icon={MemoryStick} color="text-green-500"
                />
                <StatCard
                    title="Swap Usage"
                    value={`${stats?.memory?.swap_percent?.toFixed(1) || 0}%`}
                    subtext={`${stats?.memory?.swap_used_bytes ? (stats.memory.swap_used_bytes / 1024 / 1024 / 1024).toFixed(1) : 0} GB / ${stats?.memory?.swap_total_bytes ? (stats.memory.swap_total_bytes / 1024 / 1024 / 1024).toFixed(1) : 0} GB`}
                    icon={Layers}
                    color="text-teal-500"
                />
                <StatCard
                    title="Disk Space"
                    value={`${stats?.hardware.disk.percent}%`}
                    subtext={`${(stats?.hardware.disk.used! / 1024 / 1024 / 1024).toFixed(1)} GB Used`}
                    icon={HardDrive}
                    color="text-orange-500"
                />
                <StatCard
                    title="Load Average (1min)"
                    value={stats?.load_average?.['1min']?.toFixed(2) || 'N/A'}
                    subtext={`5min: ${stats?.load_average?.['5min']?.toFixed(2) || 'N/A'}, 15min: ${stats?.load_average?.['15min']?.toFixed(2) || 'N/A'}`}
                    icon={Activity}
                    color="text-red-500"
                />
                <StatCard
                    title="Processes"
                    value={stats?.processes?.count || 'N/A'}
                    subtext="Running processes"
                    icon={Users}
                    color="text-indigo-500"
                />
                <StatCard
                    title="Open File Descriptors"
                    value={stats?.file_descriptors?.open || 'N/A'}
                    subtext={`Max: ${stats?.file_descriptors?.max || 'N/A'}`}
                    icon={Clipboard}
                    color="text-pink-500"
                />
                <StatCard
                    title="Uptime"
                    value={stats?.uptime_seconds ? `${Math.floor(stats.uptime_seconds / 3600 / 24)}d ${Math.floor((stats.uptime_seconds / 3600) % 24)}h ${Math.floor((stats.uptime_seconds / 60) % 60)}m` : 'N/A'}
                    subtext="Total system uptime"
                    icon={Clock}
                    color="text-purple-500"
                />
                <StatCard
                    title="OS Info"
                    value={stats?.os.system}
                    subtext={`${stats?.os.release}`}
                    icon={ServerIcon}
                    color="text-purple-500"
                />
            </div>

            {/* Homelab Overview */}
            <div>
                <h2 className="text-xl font-semibold mb-4">Homelab Fleet</h2>
                <div className="grid gap-6 md:grid-cols-3">
                    <StatCard
                        title="Managed Servers"
                        value={dashStats?.counts?.profiles || 0}
                        subtext="Active Profiles"
                        icon={ServerIcon}
                        color="text-indigo-500"
                    />
                    <StatCard
                        title="Generated Reports"
                        value={dashStats?.counts?.reports || 0}
                        subtext="System Analyses"
                        icon={FileText}
                        color="text-pink-500"
                    />
                    <StatCard
                        title="Knowledge Base"
                        value={dashStats?.counts?.knowledge || 0}
                        subtext="Context Items"
                        icon={HardDrive}
                        color="text-teal-500"
                    />
                </div>
            </div>

            {/* Recent Reports */}
            <div className="grid gap-6 md:grid-cols-2">
                <div className="bg-card border border-border p-6 rounded-xl">
                    <h3 className="font-semibold mb-4">Recent Reports</h3>
                    <div className="space-y-2">
                        {dashStats?.recent_reports?.map((report: any) => (
                            <div 
                                key={report.id} 
                                className="flex justify-between items-center p-2 hover:bg-muted rounded text-sm"
                                role="button"
                                tabIndex={0} // Make it keyboard focusable
                                // Optionally add onKeyDown for Enter key press
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        // Handle report click action here if needed
                                        // For now, it's just a visual hover, so no direct action needed yet
                                    }
                                }}
                            >
                                <span className="font-medium">{report.title}</span>
                                <span className="text-muted-foreground">{new Date(report.created_at).toLocaleDateString()}</span>
                            </div>
                        ))}
                        {(!dashStats?.recent_reports || dashStats.recent_reports.length === 0) && (
                            <div className="text-muted-foreground text-sm">No reports generated yet.</div>
                        )}
                    </div>
                </div>
                <div className="bg-card border border-border p-6 rounded-xl flex items-center justify-center text-muted-foreground">
                    Network Activity Chart Placeholder
                </div>
            </div>
        </div>
    );
}

const StatCard = ({ title, value, subtext, icon: Icon, color }: any) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-card border border-border p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
    >
        <div className={cn("absolute right-0 top-0 p-4 opacity-10", color)}>
            <Icon size={100} />
        </div>
        <div className="flex items-center gap-4 mb-4">
            <div className={cn("p-3 rounded-lg bg-muted text-foreground", color && "bg-opacity-20 text-opacity-100")}>
                <Icon size={24} />
            </div>
            <h3 className="font-medium text-muted-foreground">{title}</h3>
        </div>
        <div className="relative z-10">
            <div className="text-3xl font-bold mb-1">{value}</div>
            <div className="text-sm text-muted-foreground">{subtext}</div>
        </div>
    </motion.div>
);
