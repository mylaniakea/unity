import { useState, useEffect } from 'react';
import api from '@/api/client';
import { Plug, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { useNotification } from '@/contexts/notification-context';

interface Plugin {
    id: string;
    name: string;
    version: string;
    description: string;
    category: string;
    enabled: boolean;
    author: string;
    config: Record<string, any>;
}

export default function Plugins() {
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState<string | null>(null);
    const { showNotification } = useNotification();

    useEffect(() => {
        fetchPlugins();
    }, []);

    const fetchPlugins = async () => {
        try {
            setLoading(true);
            const res = await api.get('/plugins');
            // Ensure we have an array
            const data = Array.isArray(res.data) ? res.data : [];
            setPlugins(data);
        } catch (err: any) {
            console.error('Failed to load plugins:', err);
            showNotification(err.message || 'Failed to load plugins', 'error');
            setPlugins([]);
        } finally {
            setLoading(false);
        }
    };

    const togglePlugin = async (pluginId: string, currentState: boolean) => {
        try {
            setToggling(pluginId);
            // The backend endpoint might be /plugins/:id/enable or similar.
            // Original code used: api.post(`/plugins/${pluginId}/enable`, { enabled: !currentState })
            await api.post(`/plugins/${pluginId}/enable`, {
                enabled: !currentState
            });

            // Update local state
            setPlugins(prev => prev.map(p =>
                p.id === pluginId ? { ...p, enabled: !currentState } : p
            ));

            showNotification(`Plugin ${!currentState ? 'enabled' : 'disabled'} successfully`, "success");
        } catch (err: any) {
            console.error('Failed to toggle plugin:', err);
            showNotification('Failed to toggle plugin: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setToggling(null);
        }
    };

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h1 className="text-3xl font-bold tracking-tight">Plugins</h1>
                </div>
                <div className="text-muted-foreground">Loading plugins...</div>
            </div>
        );
    }

    const enabledCount = plugins.filter(p => p.enabled).length;

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Plugins</h1>
                    <p className="text-muted-foreground">Manage system extensions and integrations.</p>
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground bg-muted/50 px-3 py-1 rounded-full">
                        {enabledCount} / {plugins.length} active
                    </span>
                    <button
                        onClick={fetchPlugins}
                        className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw size={18} />
                        Refresh
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {plugins.map((plugin) => (
                    <div key={plugin.id} className="bg-card border border-border rounded-xl p-6 hover:shadow-lg transition-all group flex flex-col h-full">
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3 flex-1 overflow-hidden">
                                <div className="p-2 bg-primary/10 rounded-lg text-primary shrink-0">
                                    <Plug size={24} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-semibold text-lg truncate" title={plugin.name}>{plugin.name}</h3>
                                    <p className="text-xs text-muted-foreground font-mono">v{plugin.version}</p>
                                </div>
                            </div>
                            <button
                                onClick={() => togglePlugin(plugin.id, plugin.enabled)}
                                disabled={toggling === plugin.id}
                                className={`p-2 rounded-lg transition-colors shrink-0 ${plugin.enabled
                                    ? 'bg-green-500/10 text-green-500 hover:bg-green-500/20'
                                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                                    }`}
                                title={plugin.enabled ? 'Disable' : 'Enable'}
                            >
                                {toggling === plugin.id ? (
                                    <RefreshCw className="animate-spin" size={20} />
                                ) : plugin.enabled ? (
                                    <CheckCircle size={20} />
                                ) : (
                                    <XCircle size={20} />
                                )}
                            </button>
                        </div>

                        <p className="text-sm text-muted-foreground mb-4 line-clamp-3 flex-grow">{plugin.description}</p>

                        <div className="flex items-center justify-between pt-4 border-t border-border mt-auto">
                            <span className="px-2 py-1 text-[10px] font-medium bg-secondary text-secondary-foreground rounded uppercase tracking-wider">
                                {plugin.category}
                            </span>
                            <span className="text-xs text-muted-foreground">{plugin.author}</span>
                        </div>
                    </div>
                ))}

                {plugins.length === 0 && (
                    <div className="col-span-full text-center py-20 text-muted-foreground border-2 border-dashed border-border rounded-xl">
                        <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
                            <Plug className="text-muted-foreground" size={24} />
                        </div>
                        <p>No plugins available.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
