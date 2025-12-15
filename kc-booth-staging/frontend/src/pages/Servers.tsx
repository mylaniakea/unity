import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Server as ServerIcon, Trash2, Edit2 } from 'lucide-react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { useConfirm } from '@/contexts/ConfirmDialogContext';

interface Server {
    id: number;
    hostname: string;
    ip_address: string;
    username: string;
}

export default function Servers() {
    const [servers, setServers] = useState<Server[]>([]);
    const [loading, setLoading] = useState(true);
    const { showNotification } = useNotification();
    const { showConfirm } = useConfirm();

    const fetchServers = async () => {
        try {
            const res = await api.get('/servers/');
            if (Array.isArray(res.data)) {
                setServers(res.data);
            } else {
                console.error("API returned unexpected data", res);
                setServers([]);
            }
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch servers", error);
            setLoading(false);
        }
    };

    const deleteServer = async (id: number) => {
        const confirmed = await showConfirm({
            title: "Delete Server",
            message: "Are you sure you want to delete this server?"
        });
        if (!confirmed) return;
        try {
            await api.delete(`/servers/${id}`);
            setServers(servers.filter(s => s.id !== id));
            showNotification("Server deleted successfully!", "success");
        } catch (error) {
            console.error("Delete failed", error);
            showNotification("Failed to delete server.", "error");
        }
    }

    useEffect(() => {
        fetchServers();
    }, []);

    const [showModal, setShowModal] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [currentServer, setCurrentServer] = useState<any>({ 
        hostname: '', 
        ip_address: '',
        username: 'root',
        password: ''
    });

    const openAddModal = () => {
        setCurrentServer({ 
            hostname: '', 
            ip_address: '',
            username: 'root',
            password: ''
        });
        setIsEditing(false);
        setShowModal(true);
    };

    const openEditModal = (server: Server) => {
        setCurrentServer({ ...server });
        setIsEditing(true);
        setShowModal(true);
    };
    
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (isEditing) {
                // kc-booth backend does not support updating servers yet
                // const res = await api.put(`/servers/${currentServer.id}`, currentServer);
                // setServers(servers.map(s => s.id === currentServer.id ? res.data : s));
                showNotification("Updating servers is not yet supported.", "info");
            } else {
                const res = await api.post('/servers/', currentServer);
                setServers([...servers, res.data]);
                showNotification("Server created successfully!", "success");
            }
            setShowModal(false);
        } catch (error) {
            console.error("Failed to save server", error);
            showNotification("Failed to save server.", "error");
        }
    };

    return (
        <div className="space-y-8 relative">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Servers</h1>
                    <p className="text-muted-foreground">Manage servers for issuing certificates</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={openAddModal}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <Plus size={18} />
                        Add Server
                    </button>
                </div>
            </div>

            {loading ? (
                <div>Loading servers...</div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {servers.map((server, i) => (
                        <motion.div
                            key={server.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: i * 0.1 }}
                            className="bg-card border border-border p-6 rounded-xl hover:border-primary/50 transition-colors group relative flex flex-col h-full"
                        >
                            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                    onClick={() => openEditModal(server)}
                                    className="text-muted-foreground hover:text-primary transition-colors"
                                    title="Edit Server"
                                >
                                    <Edit2 size={18} />
                                </button>
                                <button
                                    onClick={() => deleteServer(server.id)}
                                    className="text-muted-foreground hover:text-destructive transition-colors"
                                    title="Delete Server"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>

                            <div className="flex items-center gap-4 mb-4">
                                <div className="p-3 rounded-lg bg-blue-500/10 text-blue-500">
                                    <ServerIcon size={24} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg">{server.hostname}</h3>
                                    <div className="text-xs text-muted-foreground">{server.ip_address || 'No IP'}</div>
                                </div>
                            </div>
                            <p className="text-sm text-muted-foreground mb-4 line-clamp-2 flex-grow">
                                Username: {server.username}
                            </p>
                        </motion.div>
                    ))}

                    {servers.length === 0 && (
                        <div className="col-span-full text-center py-20 text-muted-foreground border-2 border-dashed border-border rounded-xl">
                            No servers found. Add one to get started.
                        </div>
                    )}
                </div>
            )}
            
            {showModal && (
                <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-card border border-border p-6 rounded-xl w-full max-w-lg shadow-lg my-8"
                    >
                        <h2 className="text-xl font-bold mb-4">{isEditing ? 'Edit' : 'Add'} Server</h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium">Hostname</label>
                                    <input
                                        required
                                        value={currentServer.hostname}
                                        onChange={e => setCurrentServer({ ...currentServer, hostname: e.target.value })}
                                        className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                        placeholder="e.g. my-server"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium">IP Address</label>
                                    <input
                                        required
                                        value={currentServer.ip_address}
                                        onChange={e => setCurrentServer({ ...currentServer, ip_address: e.target.value })}
                                        className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                        placeholder="192.168.1.x"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium">Username</label>
                                <input
                                    required
                                    value={currentServer.username}
                                    onChange={e => setCurrentServer({ ...currentServer, username: e.target.value })}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                    placeholder="root"
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium">Password</label>
                                <input
                                    type="password"
                                    required
                                    value={currentServer.password}
                                    onChange={e => setCurrentServer({ ...currentServer, password: e.target.value })}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                />
                            </div>

                            <div className="flex justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-4 py-2 hover:bg-muted rounded-md transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                                >
                                    {isEditing ? 'Save Changes' : 'Create Server'}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
}