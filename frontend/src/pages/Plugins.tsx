import { useEffect, useState } from 'react';
import { Plug, Server, Check, X, Download, RefreshCw, Thermometer, HardDrive, Cpu, Box, AlertTriangle, Network, Activity, Battery, Monitor } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '@/api/client';
import { cn } from '@/lib/utils';
import { useNotification } from '@/contexts/NotificationContext';

interface Plugin {
    id: string;
    name: string;
    description: string;
    category: string;
    requires_sudo: boolean;
    os: string[];
}

interface ServerProfile {
    id: number;
    name: string;
    ip_address: string;
    enabled_plugins: string[];
    detected_plugins: { [key: string]: boolean };
}

interface PluginCategories {
    [key: string]: { name: string; icon: string };
}

const categoryIcons: { [key: string]: React.ReactNode } = {
    thermal: <Thermometer size={18} />,
    storage: <HardDrive size={18} />,
    gpu: <Cpu size={18} />,
    containers: <Box size={18} />,
    virtualization: <Monitor size={18} />,
    network: <Network size={18} />,
    services: <Activity size={18} />,
    power: <Battery size={18} />
};

export default function Plugins() {
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [categories, setCategories] = useState<PluginCategories>({});
    const [servers, setServers] = useState<ServerProfile[]>([]);
    const [selectedServer, setSelectedServer] = useState<ServerProfile | null>(null);
    const [checking, setChecking] = useState(false);
    const [installing, setInstalling] = useState<string | null>(null);
    const [installOutput, setInstallOutput] = useState<string>('');
    const [showInstallModal, setShowInstallModal] = useState(false);
    const [pendingInstall, setPendingInstall] = useState<{ pluginId: string; script: string } | null>(null);
    const { showNotification } = useNotification();

    useEffect(() => {
        fetchPlugins();
        fetchServers();
    }, []);

    const fetchPlugins = async () => {
        try {
            const res = await api.get('/plugins/');
            setPlugins(res.data.plugins);
            setCategories(res.data.categories);
        } catch (error) {
            console.error('Failed to fetch plugins', error);
        }
    };

    const fetchServers = async () => {
        try {
            const res = await api.get('/profiles/');
            setServers(res.data);
            if (res.data.length > 0 && !selectedServer) {
                setSelectedServer(res.data[0]);
            }
        } catch (error) {
            console.error('Failed to fetch servers', error);
        }
    };

    const checkPlugins = async () => {
        if (!selectedServer) return;
        setChecking(true);
        try {
            const res = await api.get(`/plugins/check/${selectedServer.id}`);
            setSelectedServer({
                ...selectedServer,
                detected_plugins: res.data.detected_plugins,
                enabled_plugins: res.data.enabled_plugins
            });
            showNotification('Plugin detection completed', 'success');
        } catch (error) {
            console.error('Failed to check plugins', error);
            showNotification('Failed to detect plugins', 'error');
        } finally {
            setChecking(false);
        }
    };

    const togglePlugin = async (pluginId: string, enabled: boolean) => {
        if (!selectedServer) return;
        try {
            await api.post(`/plugins/toggle/${selectedServer.id}`, {
                plugin_id: pluginId,
                enabled
            });
            setSelectedServer({
                ...selectedServer,
                enabled_plugins: enabled
                    ? [...selectedServer.enabled_plugins, pluginId]
                    : selectedServer.enabled_plugins.filter(p => p !== pluginId)
            });
            showNotification(`Plugin ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } catch (error) {
            console.error('Failed to toggle plugin', error);
            showNotification('Failed to toggle plugin', 'error');
        }
    };

    const previewInstall = async (pluginId: string) => {
        try {
            const res = await api.get(`/plugins/install-script/${pluginId}?distro=debian`);
            setPendingInstall({ pluginId, script: res.data.script });
            setShowInstallModal(true);
        } catch (error) {
            console.error('Failed to get install script', error);
            showNotification('Failed to get install script', 'error');
        }
    };

    const executeInstall = async () => {
        if (!selectedServer || !pendingInstall) return;
        setInstalling(pendingInstall.pluginId);
        setInstallOutput('Installing...\n');
        setShowInstallModal(false);
        
        try {
            const res = await api.post(`/plugins/install/${selectedServer.id}`, {
                plugin_id: pendingInstall.pluginId,
                distro: 'debian'
            });
            
            if (res.data.manual_required) {
                setInstallOutput(res.data.message);
                showNotification('Manual installation required', 'info');
            } else if (res.data.success) {
                setInstallOutput(res.data.output || 'Installation completed successfully!');
                showNotification('Plugin installed successfully', 'success');
                // Refresh detection
                checkPlugins();
            } else {
                setInstallOutput(`Error: ${res.data.stderr || res.data.output}`);
                showNotification('Installation failed', 'error');
            }
        } catch (error: any) {
            setInstallOutput(`Installation failed: ${error.message}`);
            showNotification('Installation failed', 'error');
        } finally {
            setInstalling(null);
            setPendingInstall(null);
        }
    };

    const groupedPlugins = plugins.reduce((acc, plugin) => {
        const cat = plugin.category || 'other';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(plugin);
        return acc;
    }, {} as { [key: string]: Plugin[] });

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Plug className="text-primary" />
                        Data Plugins
                    </h1>
                    <p className="text-muted-foreground">
                        Extend data collection with specialized monitoring tools
                    </p>
                </div>
            </div>

            {/* Server Selector */}
            <div className="bg-card border border-border p-4 rounded-xl">
                <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex items-center gap-2">
                        <Server size={18} className="text-muted-foreground" />
                        <span className="text-sm font-medium">Select Server:</span>
                    </div>
                    <select
                        value={selectedServer?.id || ''}
                        onChange={(e) => {
                            const server = servers.find(s => s.id === parseInt(e.target.value));
                            setSelectedServer(server || null);
                        }}
                        className="bg-background border border-border rounded-md px-3 py-2 min-w-[200px]"
                    >
                        {servers.map(s => (
                            <option key={s.id} value={s.id}>{s.name} ({s.ip_address})</option>
                        ))}
                    </select>
                    <button
                        onClick={checkPlugins}
                        disabled={checking || !selectedServer}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw size={16} className={checking ? 'animate-spin' : ''} />
                        Detect Installed
                    </button>
                </div>
            </div>

            {/* Plugin Categories */}
            {Object.entries(groupedPlugins).map(([category, categoryPlugins]) => (
                <motion.div
                    key={category}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                >
                    <div className="flex items-center gap-2 text-lg font-semibold">
                        {categoryIcons[category] || <Plug size={18} />}
                        <span>{categories[category]?.name || category}</span>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {categoryPlugins.map(plugin => {
                            const isDetected = selectedServer?.detected_plugins?.[plugin.id] ?? false;
                            const isEnabled = selectedServer?.enabled_plugins?.includes(plugin.id) ?? false;
                            
                            return (
                                <motion.div
                                    key={plugin.id}
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className={cn(
                                        "bg-card border p-4 rounded-xl transition-all",
                                        isEnabled ? "border-primary/50 shadow-sm shadow-primary/10" : "border-border"
                                    )}
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div>
                                            <h3 className="font-semibold">{plugin.name}</h3>
                                            <p className="text-xs text-muted-foreground mt-0.5">{plugin.description}</p>
                                        </div>
                                        {plugin.requires_sudo && (
                                            <span className="text-xs bg-yellow-500/20 text-yellow-500 px-2 py-0.5 rounded">
                                                sudo
                                            </span>
                                        )}
                                    </div>

                                    <div className="flex items-center justify-between mt-4">
                                        {/* Status Badge */}
                                        <div className={cn(
                                            "flex items-center gap-1.5 text-xs px-2 py-1 rounded",
                                            isDetected 
                                                ? "bg-green-500/20 text-green-400" 
                                                : "bg-muted text-muted-foreground"
                                        )}>
                                            {isDetected ? <Check size={12} /> : <X size={12} />}
                                            {isDetected ? 'Installed' : 'Not Found'}
                                        </div>

                                        {/* Actions */}
                                        <div className="flex items-center gap-2">
                                            {!isDetected && (
                                                <button
                                                    onClick={() => previewInstall(plugin.id)}
                                                    disabled={installing === plugin.id}
                                                    className={cn(
                                                        "text-xs flex items-center gap-1 px-2 py-1 rounded transition-colors",
                                                        installing === plugin.id 
                                                            ? "bg-primary/20 text-primary cursor-wait" 
                                                            : "bg-muted hover:bg-muted/80"
                                                    )}
                                                >
                                                    {installing === plugin.id ? (
                                                        <>
                                                            <RefreshCw size={12} className="animate-spin" />
                                                            Installing...
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Download size={12} />
                                                            Install
                                                        </>
                                                    )}
                                                </button>
                                            )}
                                            {isDetected && (
                                                <label className="flex items-center gap-2 cursor-pointer">
                                                    <span className="text-xs text-muted-foreground">Enable</span>
                                                    <input
                                                        type="checkbox"
                                                        checked={isEnabled}
                                                        onChange={(e) => togglePlugin(plugin.id, e.target.checked)}
                                                        className="h-4 w-4 accent-primary"
                                                    />
                                                </label>
                                            )}
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                </motion.div>
            ))}

            {/* Install Output */}
            <AnimatePresence>
                {installOutput && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-card border border-border rounded-xl p-4"
                    >
                        <div className="flex items-center justify-between mb-2">
                            <h3 className="font-semibold">Installation Output</h3>
                            <button
                                onClick={() => setInstallOutput('')}
                                className="text-xs text-muted-foreground hover:text-foreground"
                            >
                                Clear
                            </button>
                        </div>
                        <pre className="bg-muted/50 p-3 rounded-md text-xs font-mono overflow-auto max-h-48">
                            {installOutput}
                        </pre>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Install Confirmation Modal */}
            <AnimatePresence>
                {showInstallModal && pendingInstall && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                        onClick={() => setShowInstallModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-card border border-border rounded-xl p-6 max-w-lg w-full mx-4"
                        >
                            <div className="flex items-center gap-2 text-lg font-semibold mb-4">
                                <AlertTriangle className="text-yellow-500" size={20} />
                                Install Plugin
                            </div>
                            <p className="text-sm text-muted-foreground mb-4">
                                The following commands will be executed on <strong>{selectedServer?.name}</strong>:
                            </p>
                            <pre className="bg-muted/50 p-3 rounded-md text-xs font-mono overflow-auto max-h-32 mb-4">
                                {pendingInstall.script}
                            </pre>
                            <div className="flex justify-end gap-3">
                                <button
                                    onClick={() => setShowInstallModal(false)}
                                    className="px-4 py-2 rounded-md bg-muted hover:bg-muted/80 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={executeInstall}
                                    className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                                >
                                    Install
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
