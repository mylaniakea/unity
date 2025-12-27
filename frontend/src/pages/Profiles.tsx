import React from 'react';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Server, Trash2, RefreshCw, Terminal as TerminalIcon, Activity, Edit2, Play, KeyRound } from 'lucide-react';
import api from '@/api/client';
import { cn } from '@/lib/utils';
import Terminal from '@/components/Terminal';
import { useSidebar } from '@/contexts/SidebarContext';
import { useNotification } from '@/contexts/NotificationContext';
import { useConfirm } from '@/contexts/ConfirmDialogContext';

interface Profile {
    id: number;
    name: string;
    description: string;
    ip_address: string;
    ssh_port: number;
    ssh_username: string;
    ssh_key_path: string;
    os_info: any;
    hardware_info: any;
    created_at: string;
}

export default function Profiles() {
    const { setSidebarOpen } = useSidebar();
    const [profiles, setProfiles] = useState<Profile[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<number | null>(null);
    const [activeTerminal, setActiveTerminal] = useState<number | null>(null);
    const { showNotification } = useNotification();
    const { showConfirm } = useConfirm();

    const openTerminal = (id: number) => {
        setSidebarOpen(false);
        setActiveTerminal(id);
    };

    const closeTerminal = () => {
        setSidebarOpen(true);
        setActiveTerminal(null);
    };

    const fetchProfiles = async () => {
        try {
            const res = await api.get('/profiles/');
            if (Array.isArray(res.data)) {
                setProfiles(res.data);
            } else {
                console.error("API returned unexpected data", res);
                setProfiles([]);
            }
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch profiles", error);
            setLoading(false);
        }
    };

    const scanLocal = async () => {
        try {
            setLoading(true);
            await api.post('/profiles/scan-local');
            await fetchProfiles();
        } catch (error) {
            console.error("Scan failed", error);
            setLoading(false);
        }
    };

    const deleteProfile = async (id: number) => {
        const confirmed = await showConfirm({
            title: "Delete Profile",
            message: "Are you sure you want to delete this server profile?"
        });
        if (!confirmed) return;
        try {
            await api.delete(`/profiles/${id}`);
            setProfiles(profiles.filter(p => p.id !== id));
            showNotification("Profile deleted successfully!", "success");
        } catch (error) {
            console.error("Delete failed", error);
            showNotification("Failed to delete profile.", "error");
        }
    }

    const testSSH = async (id: number) => {
        setActionLoading(id);
        try {
            const res = await api.post(`/profiles/${id}/ssh/test`);
            if (res.data.success) {
                showNotification(`Connection Successful: ${res.data.message}`, "success");
            } else {
                showNotification(`Connection Failed: ${res.data.message}`, "error");
            }
        } catch (error: any) {
             showNotification(`Error: ${error.response?.data?.detail || "Backend error"}`, "error");
        } finally {
            setActionLoading(null);
        }
    }

    const refreshStats = async (id: number) => {
        setActionLoading(id);
        try {
            const res = await api.post(`/profiles/${id}/refresh`);
            setProfiles(profiles.map(p => p.id === id ? res.data : p));
            showNotification("Stats refreshed successfully!", "success");
        } catch (error: any) {
            console.error(error);
            showNotification(`Failed to refresh: ${error.response?.data?.detail || "Unknown error"}`, "error");
        } finally {
            setActionLoading(null);
        }
    }

    useEffect(() => {
        fetchProfiles();
    }, []);

    const [showModal, setShowModal] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [currentProfile, setCurrentProfile] = useState<any>({ 
        name: '', 
        description: '', 
        ip_address: '',
        ssh_username: 'root',
        ssh_port: 22,
        ssh_key_path: ''
    });

    // Key Setup Modal State
    const [showKeyModal, setShowKeyModal] = useState(false);
    const [keyPassword, setKeyPassword] = useState("");
    const [keyProfileId, setKeyProfileId] = useState<number | null>(null);
    const [keySetupLoading, setKeySetupLoading] = useState(false);

    const openAddModal = () => {
        setCurrentProfile({ 
            name: '', 
            description: '', 
            ip_address: '',
            ssh_username: 'root',
            ssh_port: 22,
            ssh_key_path: ''
        });
        setIsEditing(false);
        setShowModal(true);
    };

    const openEditModal = (profile: Profile) => {
        setCurrentProfile({ ...profile });
        setIsEditing(true);
        setShowModal(true);
    };
    
    const openKeySetupModal = (id: number) => {
        setKeyProfileId(id);
        setKeyPassword("");
        setShowKeyModal(true);
    }

    const handleKeySetup = async (e: React.FormEvent) => {
        e.preventDefault();
        if(!keyProfileId) return;
        
        setKeySetupLoading(true);
        try {
            const res = await api.post(`/profiles/${keyProfileId}/setup-keys`, {
                password: keyPassword
            });
            if(res.data.success) {
                showNotification("Keys installed successfully! You can now connect without a password.", "success");
                // Refresh profile to show updated key path if we wanted to
                fetchProfiles();
                setShowKeyModal(false);
            }
        } catch (error: any) {
            console.error("Key setup failed", error);
            showNotification(`Failed to setup keys: ${error.response?.data?.detail || error.message}`, "error");
        } finally {
            setKeySetupLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (isEditing) {
                const res = await api.put(`/profiles/${currentProfile.id}`, currentProfile);
                setProfiles(profiles.map(p => p.id === currentProfile.id ? res.data : p));
                showNotification("Profile updated successfully!", "success");
            } else {
                const res = await api.post('/profiles/', {
                    ...currentProfile,
                    hardware_info: {},
                    os_info: { system: "Unknown" },
                    packages: []
                });
                setProfiles([...profiles, res.data]);
                showNotification("Profile created successfully!", "success");
            }
            setShowModal(false);
        } catch (error) {
            console.error("Failed to save profile", error);
            showNotification("Failed to save profile.", "error");
        }
    };

    return (
        <div className="space-y-8 relative">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Server Profiles</h1>
                    <p className="text-muted-foreground">Manage and document your homelab fleet</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={openAddModal}
                        className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors"
                    >
                        <Plus size={18} />
                        Add Manual
                    </button>
                    <button
                        onClick={scanLocal}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <RefreshCw size={18} />
                        Scan Local
                    </button>
                </div>
            </div>

            {loading ? (
                <div>Loading profiles...</div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {profiles.map((profile, i) => (
                        <motion.div
                            key={profile.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: i * 0.1 }}
                            className="bg-card border border-border p-6 rounded-xl hover:border-primary/50 transition-colors group relative flex flex-col h-full"
                        >
                            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                    onClick={() => openKeySetupModal(profile.id)}
                                    className="text-muted-foreground hover:text-yellow-500 transition-colors"
                                    title="Setup SSH Keys"
                                >
                                    <KeyRound size={18} />
                                </button>
                                <button
                                    onClick={() => openEditModal(profile)}
                                    className="text-muted-foreground hover:text-primary transition-colors"
                                    title="Edit Profile"
                                >
                                    <Edit2 size={18} />
                                </button>
                                <button
                                    onClick={() => deleteProfile(profile.id)}
                                    className="text-muted-foreground hover:text-destructive transition-colors"
                                    title="Delete Profile"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>

                            <div className="flex items-center gap-4 mb-4">
                                <div className="p-3 rounded-lg bg-blue-500/10 text-blue-500">
                                    <Server size={24} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg">{profile.name}</h3>
                                    <div className="text-xs text-muted-foreground">{profile.ip_address || 'No IP'}</div>
                                </div>
                            </div>
                            <p className="text-sm text-muted-foreground mb-4 line-clamp-2 flex-grow">
                                {profile.description || 'No description'}
                            </p>
                            
                            {/* Stats Preview */}
                            <div className="grid grid-cols-2 gap-2 mb-4 text-xs text-muted-foreground bg-muted/50 p-2 rounded">
                                <div className="flex flex-col">
                                    <span className="font-semibold">OS</span>
                                    <span className="truncate" title={profile.os_info?.system}>{profile.os_info?.system || 'Unknown'}</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="font-semibold">Memory</span>
                                    <span>{profile.hardware_info?.memory?.percent ? `${profile.hardware_info.memory.percent}%` : 'N/A'}</span>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-border flex justify-between items-center mt-auto">
                                <div className="text-xs text-muted-foreground">
                                    {new Date(profile.created_at).toLocaleDateString()}
                                </div>
                                <div className="flex gap-1">
                                    <button 
                                        onClick={() => openTerminal(profile.id)}
                                        className="p-2 hover:bg-secondary rounded-full text-muted-foreground hover:text-foreground transition-colors"
                                        title="Open Terminal"
                                    >
                                        <Play size={16} />
                                    </button>
                                    <button 
                                        onClick={() => testSSH(profile.id)}
                                        disabled={actionLoading === profile.id}
                                        className="p-2 hover:bg-secondary rounded-full text-muted-foreground hover:text-foreground transition-colors"
                                        title="Test SSH Connection"
                                    >
                                        <TerminalIcon size={16} />
                                    </button>
                                    <button 
                                        onClick={() => refreshStats(profile.id)}
                                        disabled={actionLoading === profile.id}
                                        className={cn("p-2 hover:bg-secondary rounded-full text-muted-foreground hover:text-foreground transition-colors", actionLoading === profile.id && "animate-spin")}
                                        title="Refresh Stats"
                                    >
                                        {actionLoading === profile.id ? <RefreshCw size={16} /> : <Activity size={16} />}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}

                    {profiles.length === 0 && (
                        <div className="col-span-full text-center py-20 text-muted-foreground border-2 border-dashed border-border rounded-xl">
                            No profiles found. Scan the local server or add one manually.
                        </div>
                    )}
                </div>
            )}

            {/* Terminal Modal */}
            {activeTerminal && (
                <Terminal profileId={activeTerminal} onClose={closeTerminal} />
            )}
            
            {/* Key Setup Modal */}
            {showKeyModal && (
                <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                     <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-card border border-border p-6 rounded-xl w-full max-w-sm shadow-lg"
                    >
                        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                             <KeyRound size={20} /> Setup SSH Keys
                        </h2>
                        <p className="text-sm text-muted-foreground mb-4">
                            Enter the root/user password for this server. 
                            We will generate a keypair and install it automatically, allowing passwordless access.
                        </p>
                        <form onSubmit={handleKeySetup} className="space-y-4">
                            <div>
                                <label className="text-sm font-medium">Password</label>
                                <input
                                    type="password"
                                    required
                                    autoFocus
                                    value={keyPassword}
                                    onChange={e => setKeyPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                    placeholder="Server Password"
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowKeyModal(false)}
                                    className="px-4 py-2 hover:bg-muted rounded-md transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={keySetupLoading}
                                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                                >
                                    {keySetupLoading ? 'Installing...' : 'Install Keys'}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}

            {/* Add/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-card border border-border p-6 rounded-xl w-full max-w-lg shadow-lg my-8"
                    >
                        <h2 className="text-xl font-bold mb-4">{isEditing ? 'Edit' : 'Add'} Server Profile</h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium">Server Name</label>
                                    <input
                                        required
                                        value={currentProfile.name}
                                        onChange={e => setCurrentProfile({ ...currentProfile, name: e.target.value })}
                                        className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                        placeholder="e.g. Proxithor"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium">IP Address</label>
                                    <input
                                        required
                                        value={currentProfile.ip_address}
                                        onChange={e => setCurrentProfile({ ...currentProfile, ip_address: e.target.value })}
                                        className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                                        placeholder="192.168.1.x"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium">Description</label>
                                <textarea
                                    value={currentProfile.description || ''}
                                    onChange={e => setCurrentProfile({ ...currentProfile, description: e.target.value })}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1 min-h-[60px]"
                                    placeholder="Primary virtualization node..."
                                />
                            </div>

                            <div className="bg-muted/30 p-4 rounded-lg space-y-4 border border-border/50">
                                <h3 className="text-sm font-semibold flex items-center gap-2">
                                    <TerminalIcon size={14} /> SSH Configuration
                                </h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs font-medium text-muted-foreground">Username</label>
                                        <input
                                            value={currentProfile.ssh_username || ''}
                                            onChange={e => setCurrentProfile({ ...currentProfile, ssh_username: e.target.value })}
                                            className="w-full bg-background border border-border rounded-md px-3 py-1.5 mt-1 text-sm"
                                            placeholder="root"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs font-medium text-muted-foreground">Port</label>
                                        <input
                                            type="number"
                                            value={currentProfile.ssh_port || 22}
                                            onChange={e => setCurrentProfile({ ...currentProfile, ssh_port: parseInt(e.target.value) || 22 })}
                                            className="w-full bg-background border border-border rounded-md px-3 py-1.5 mt-1 text-sm"
                                            placeholder="22"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="text-xs font-medium text-muted-foreground">Identity File Path (Optional)</label>
                                    <input
                                        value={currentProfile.ssh_key_path || ''}
                                        onChange={e => setCurrentProfile({ ...currentProfile, ssh_key_path: e.target.value })}
                                        className="w-full bg-background border border-border rounded-md px-3 py-1.5 mt-1 text-sm"
                                        placeholder="/home/user/.ssh/id_rsa"
                                    />
                                    <p className="text-[10px] text-muted-foreground mt-1">Path to the private key on the container/host running the backend.</p>
                                </div>
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
                                    {isEditing ? 'Save Changes' : 'Create Profile'}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
}
