import { useEffect, useState } from 'react';
import { HardDrive, Cpu, Server as ServerIcon, RefreshCw, Network, Zap, BookPlus, Clock, Database, Layers } from 'lucide-react';
import api from '@/api/client';
import { motion } from 'framer-motion';
import { useNotification } from '@/contexts/NotificationContext';
import CustomDropdown from '@/components/CustomDropdown';

interface HardwareData {
    pci: { Slot: string; Class: string; Vendor: string; Device: string }[];
    disks: { 
        name: string; 
        size: string; 
        type: string; 
        model: string; 
        tran?: string;
        rota?: string;
        children?: { name: string; size: string; mountpoint: string }[] 
    }[];
    raid: string;
    zfs_pools?: { name: string; size: string; health: string; alloc: string; free: string }[];
    zfs_status?: string;
    network?: { 
        ifname: string; 
        address: string; 
        operstate: string; 
        mtu: number;
        addr_info?: { local: string; family: string }[];
    }[];
    gpu?: { Vendor?: string; Device?: string; Model?: string; Class?: string }[];
    timestamp?: string;
}

interface Profile {
    id: number;
    name: string;
    ip_address: string;
    hardware_info: {
        detailed?: HardwareData;
        cpu?: any;
        memory?: any;
    };
}

export default function ServerHardware() {
    const [profiles, setProfiles] = useState<Profile[]>([]);
    const [selectedId, setSelectedId] = useState<number | string>("");
    const [loading, setLoading] = useState(false);
    const [knowledgeLoading, setKnowledgeLoading] = useState(false);
    const { showNotification } = useNotification();

    useEffect(() => {
        api.get('/profiles/').then(res => {
            setProfiles(res.data);
            if (res.data.length > 0) setSelectedId(res.data[0].id);
        });
    }, []);

    const selectedProfile = profiles.find(p => p.id === Number(selectedId));
    const detailed = selectedProfile?.hardware_info?.detailed;

    const scanHardware = async () => {
        if (!selectedId) return;
        setLoading(true);
        try {
            await api.post(`/profiles/${selectedId}/scan-hardware`);
            // Give backend time to finish writing to DB
            await new Promise(resolve => setTimeout(resolve, 500));
            // Refetch all profiles to update UI
            const res = await api.get('/profiles/');
            setProfiles(res.data);
            showNotification("Hardware scan completed!", "success");
        } catch (error) {
            console.error("Scan failed", error);
            showNotification("Hardware scan failed. Check SSH connection.", "error");
        } finally {
            setLoading(false);
        }
    };

    const addToKnowledge = async () => {
        if (!selectedProfile || !detailed) return;
        setKnowledgeLoading(true);
        try {
            await api.post('/ai/ingest-hardware-knowledge', {
                profile_id: selectedProfile.id,
                hardware_data: detailed
            });
            showNotification("Success! Hardware spec added to Knowledge Base.", "success");
        } catch (error) {
            console.error("Ingest failed", error);
            showNotification("Failed to add to knowledge base.", "error");
        } finally {
            setKnowledgeLoading(false);
        }
    };

    // Helper to identify if a disk is part of a RAID/ZFS pool
    const isRaidMember = (disk: any) => {
        if (!disk.children) return false;
        return disk.children.some((child: any) => {
            const fs = child.fstype?.toLowerCase() || '';
            const type = child.type?.toLowerCase() || '';
            return fs.includes('zfs_member') || fs.includes('raid') || type.includes('raid');
        });
    };

    // Robust SSD Check
    const isSSD = (d: any) => {
        const rota = String(d.rota).trim();
        const model = (d.model || '').toLowerCase();
        // Non-rotational (0) OR model says SSD
        return (rota === '0' || rota === 'false') || model.includes('ssd');
    };

    const isHDD = (d: any) => {
        const rota = String(d.rota).trim();
        // Rotational (1)
        return rota === '1' || rota === 'true';
    };

    // Grouping Logic for Disks
    const allDisks = detailed?.disks || [];
    
    const raidMembers = allDisks.filter(d => isRaidMember(d));
    const nonRaidDisks = allDisks.filter(d => !isRaidMember(d));

    const diskGroups = {
        nvme: nonRaidDisks.filter(d => d.name?.startsWith('nvme')),
        ssd: nonRaidDisks.filter(d => !d.name?.startsWith('nvme') && isSSD(d) && d.tran !== 'usb'),
        hdd: nonRaidDisks.filter(d => isHDD(d) && d.tran !== 'usb'),
        usb: nonRaidDisks.filter(d => d.tran === 'usb'),
        other: nonRaidDisks.filter(d => !d.name?.startsWith('nvme') && !isSSD(d) && !isHDD(d) && d.tran !== 'usb')
    };

    // Grouping Logic for PCI
    const pciGroups: { [key: string]: typeof detailed.pci } = {};
    detailed?.pci?.forEach(dev => {
        const cls = dev.Class.split(' ')[0]; // Simple grouping by first word of class
        if (!pciGroups[cls]) pciGroups[cls] = [];
        pciGroups[cls].push(dev);
    });

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Server Hardware</h1>
                    <p className="text-muted-foreground">Deep dive into hardware components and storage configuration.</p>
                </div>
                <div className="flex gap-4 items-center flex-wrap">
                    <CustomDropdown
                        options={profiles.map(p => ({ value: p.id, label: `${p.name} (${p.ip_address})` }))}
                        value={selectedId}
                        onChange={(value) => setSelectedId(value)}
                        placeholder="Select a server"
                        disabled={profiles.length === 0}
                    />
                    {detailed && (
                        <button
                            onClick={addToKnowledge}
                            disabled={knowledgeLoading}
                            className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors disabled:opacity-50"
                        >
                            <BookPlus size={18} className={knowledgeLoading ? "animate-pulse" : ""} />
                            {knowledgeLoading ? "Analyzing..." : "Add to Knowledge"}
                        </button>
                    )}
                    <button
                        onClick={scanHardware}
                        disabled={loading || !selectedId}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
                        Scan Hardware
                    </button>
                </div>
            </div>

            {!detailed ? (
                <div className="text-center py-20 text-muted-foreground border-2 border-dashed border-border rounded-xl">
                    No detailed hardware data found. Click "Scan Hardware" to collect information.
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Header with Timestamp */}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/20 p-2 rounded-lg border border-border/50">
                        <Clock size={14} />
                        <span className="font-mono">
                            Snapshot: {selectedProfile.name}_HardwareScan_{(() => {
                                const d = detailed.timestamp ? new Date(detailed.timestamp) : new Date();
                                const year = d.getFullYear();
                                const month = String(d.getMonth() + 1).padStart(2, '0');
                                const day = String(d.getDate()).padStart(2, '0');
                                return `${year}${month}${day}`;
                            })()}
                        </span>
                        <span className="ml-auto">
                            Scanned: {detailed.timestamp ? new Date(detailed.timestamp).toLocaleString() : 'Unknown Date'}
                        </span>
                    </div>

                    {/* GPU Section - Stacked Layout (2 Columns) */}
                    {detailed.gpu && detailed.gpu.length > 0 && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-card border border-border rounded-xl overflow-hidden">
                            <div className="p-4 bg-muted/30 border-b border-border flex items-center gap-2 font-semibold text-purple-500">
                                <Zap size={20} /> GPU & Accelerators
                            </div>
                            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                                {detailed.gpu.map((gpu, i) => (
                                    <div key={i} className="border border-border rounded-lg p-4 bg-gradient-to-r from-muted/5 to-transparent flex flex-col justify-between h-full">
                                        <div>
                                            <div className="font-bold text-lg leading-tight mb-2">{gpu.Model || gpu.Device || "Unknown Device"}</div>
                                            <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mb-1">
                                                {gpu.Vendor}
                                            </div>
                                            {gpu.Class && <div className="text-xs text-muted-foreground">{gpu.Class}</div>}
                                        </div>
                                        <div className="mt-3 pt-3 border-t border-border/50 text-right">
                                            <span className="bg-background border border-border px-2 py-1 rounded text-[10px] font-mono text-muted-foreground">
                                                {gpu.Type || "PCIe Device"}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {/* Network Section */}
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-card border border-border rounded-xl overflow-hidden">
                        <div className="p-4 bg-muted/30 border-b border-border flex items-center gap-2 font-semibold text-blue-500">
                            <Network size={20} /> Network Interfaces
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-muted/50">
                                    <tr>
                                        <th className="p-3 text-left">Interface</th>
                                        <th className="p-3 text-left">State</th>
                                        <th className="p-3 text-left">IP Address(es)</th>
                                        <th className="p-3 text-left">MAC / Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {detailed.network?.length ? detailed.network.map((net, i) => (
                                        <tr key={i} className="border-b border-border/50 hover:bg-muted/20">
                                            <td className="p-3 font-mono font-semibold">{net.ifname || 'Unknown'}</td>
                                            <td className="p-3">
                                                <span className={`px-2 py-0.5 rounded text-xs ${net.operstate === 'UP' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                                                    {net.operstate || 'UNKNOWN'}
                                                </span>
                                            </td>
                                            <td className="p-3 font-mono">
                                                {net.addr_info?.map(a => a.local).join(', ') || '-'}
                                            </td>
                                            <td className="p-3 text-muted-foreground text-xs">
                                                {net.address} (MTU: {net.mtu})
                                            </td>
                                        </tr>
                                    )) : (
                                        <tr><td colSpan={4} className="p-4 text-center italic text-muted-foreground">No physical interfaces detected.</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </motion.div>

                    {/* Storage & RAID Section */}
                    <div className="grid gap-6 md:grid-cols-2">
                        {/* Storage Pools (RAID/ZFS) */}
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-card border border-border rounded-xl overflow-hidden h-full flex flex-col">
                            <div className="p-4 bg-muted/30 border-b border-border flex items-center gap-2 font-semibold text-orange-500">
                                <Database size={20} /> Storage Pools & RAID
                            </div>
                            <div className="p-4 space-y-6 flex-1">
                                {/* ZFS Pools */}
                                {detailed.zfs_pools && detailed.zfs_pools.length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-semibold mb-2 uppercase tracking-wide text-muted-foreground">ZFS Pools</h3>
                                        <div className="space-y-2">
                                            {detailed.zfs_pools.map(pool => (
                                                <div key={pool.name} className="flex justify-between items-center bg-muted/20 p-2 rounded border border-border/50">
                                                    <span className="font-bold">{pool.name}</span>
                                                    <span className="text-xs font-mono">{formatBytes(pool.size)}</span>
                                                    <span className={`text-xs px-2 py-0.5 rounded ${pool.health === 'ONLINE' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                                                        {pool.health}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                
                                {/* Member Disks */}
                                {raidMembers.length > 0 && (
                                    <div>
                                        <h3 className="text-sm font-semibold mb-2 uppercase tracking-wide text-muted-foreground">Pool Member Disks</h3>
                                        <div className="space-y-2">
                                            {raidMembers.map((disk, i) => (
                                                <div key={i} className="flex justify-between items-center bg-muted/10 p-2 rounded border border-border/50 opacity-80">
                                                    <div>
                                                        <div className="font-bold font-mono text-xs">{disk.name}</div>
                                                        <div className="text-[10px] text-muted-foreground">{disk.model}</div>
                                                    </div>
                                                    <div className="text-xs font-mono">{disk.size}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                
                                {/* Raw Status */}
                                {detailed.zfs_status && (
                                    <div className="mt-4 pt-4 border-t border-border/50">
                                        <h4 className="text-xs font-semibold mb-1 text-muted-foreground">ZFS Status</h4>
                                        <pre className="bg-black/50 p-2 rounded text-[10px] font-mono overflow-auto max-h-32 whitespace-pre-wrap">{detailed.zfs_status}</pre>
                                    </div>
                                )}
                                
                                {detailed.raid && (
                                    <div className="mt-4 pt-4 border-t border-border/50">
                                        <h3 className="text-sm font-semibold mb-2">MDRAID Status</h3>
                                        <pre className="bg-black/50 p-2 rounded text-[10px] font-mono overflow-auto max-h-32 whitespace-pre-wrap">
                                            {detailed.raid}
                                        </pre>
                                    </div>
                                )}
                                
                                {!detailed.raid && (!detailed.zfs_pools || detailed.zfs_pools.length === 0) && (
                                    <div className="text-sm text-muted-foreground italic">No RAID or ZFS pools detected.</div>
                                )}
                            </div>
                        </motion.div>

                        {/* Physical Disks - Grouped */}
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-card border border-border rounded-xl overflow-hidden h-full flex flex-col">
                            <div className="p-4 bg-muted/30 border-b border-border flex items-center gap-2 font-semibold">
                                <HardDrive size={20} /> Physical Disks (Non-RAID)
                            </div>
                            <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto flex-1">
                                <DiskGroup title="NVMe SSDs" disks={diskGroups.nvme} />
                                <DiskGroup title="SATA/SAS SSDs" disks={diskGroups.ssd} />
                                <DiskGroup title="HDDs (Rotational)" disks={diskGroups.hdd} />
                                <DiskGroup title="USB / Removable" disks={diskGroups.usb} />
                                <DiskGroup title="Other / Unclassified" disks={diskGroups.other} />
                                
                                {Object.values(diskGroups).every(g => g.length === 0) && (
                                    <div className="text-center text-muted-foreground italic py-10">All disks are part of RAID pools or none detected.</div>
                                )}
                            </div>
                        </motion.div>
                    </div>

                    {/* PCI Devices - Grouped */}
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-card border border-border rounded-xl overflow-hidden">
                        <div className="p-4 bg-muted/30 border-b border-border flex items-center gap-2 font-semibold">
                            <Cpu size={20} /> PCI Devices (Add-in Cards)
                        </div>
                        <div className="p-4 grid gap-4 md:grid-cols-2">
                            {Object.entries(pciGroups).map(([cls, devices]) => (
                                <div key={cls} className="border border-border rounded-lg overflow-hidden">
                                    <div className="bg-muted/20 px-3 py-2 text-xs font-bold border-b border-border/50 uppercase tracking-wide">
                                        {cls}
                                    </div>
                                    <div className="divide-y divide-border/50">
                                        {devices.map((dev, i) => (
                                            <div key={i} className="p-3 text-sm">
                                                <div className="font-semibold">{dev.Vendor}</div>
                                                <div className="text-muted-foreground">{dev.Device}</div>
                                                <div className="text-[10px] text-muted-foreground font-mono mt-1">{dev.Slot}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    );
}

const DiskGroup = ({ title, disks }: { title: string, disks: any[] }) => {
    if (disks.length === 0) return null;
    return (
        <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 border-b border-border pb-1">{title}</h4>
            <div className="space-y-2">
                {disks.map((disk, i) => (
                    <div key={i} className="flex justify-between items-center bg-muted/10 p-2 rounded border border-border/50">
                        <div>
                            <div className="font-bold font-mono text-sm">{disk.name}</div>
                            <div className="text-xs text-muted-foreground">{disk.model}</div>
                        </div>
                        <div className="text-sm font-mono">{disk.size}</div>
                    </div>
                ))}
            </div>
        </div>
    );
};