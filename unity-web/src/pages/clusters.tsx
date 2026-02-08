import { useState } from 'react';
import { Server, Power, RefreshCw, MoreVertical } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ClusterNode {
    id: string;
    name: string;
    role: 'control-plane' | 'worker';
    status: 'ready' | 'not-ready' | 'unknown';
    cpu: number;
    memory: number;
    version: string;
}

export default function Clusters() {
    const [nodes] = useState<ClusterNode[]>([
        {
            id: 'n1',
            name: 'unity-cp-01',
            role: 'control-plane',
            status: 'ready',
            cpu: 12,
            memory: 45,
            version: 'v1.28.2'
        },
        {
            id: 'n2',
            name: 'unity-worker-01',
            role: 'worker',
            status: 'ready',
            cpu: 8,
            memory: 32,
            version: 'v1.28.2'
        },
        {
            id: 'n3',
            name: 'unity-worker-02',
            role: 'worker',
            status: 'not-ready',
            cpu: 0,
            memory: 0,
            version: 'v1.28.2'
        }
    ]);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Clusters</h1>
                    <p className="text-muted-foreground mt-2">
                        Manage your Kubernetes clusters and nodes.
                    </p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity">
                    <RefreshCw size={16} />
                    <span>Refresh</span>
                </button>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {nodes.map((node) => (
                    <div
                        key={node.id}
                        className="bg-card border border-border rounded-xl shadow-sm overflow-hidden"
                    >
                        <div className="p-6 border-b border-border flex justify-between items-start">
                            <div className="flex items-center gap-3">
                                <div className={cn(
                                    "p-2 rounded-lg",
                                    node.status === 'ready' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
                                )}>
                                    <Server size={24} />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-lg">{node.name}</h3>
                                    <p className="text-xs text-muted-foreground uppercase tracking-wider">{node.role}</p>
                                </div>
                            </div>
                            <div className={cn(
                                "w-3 h-3 rounded-full mt-2",
                                node.status === 'ready' ? "bg-green-500" : "bg-red-500"
                            )} />
                        </div>

                        <div className="p-6 space-y-4">
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">CPU Usage</span>
                                    <span className="font-medium">{node.cpu}%</span>
                                </div>
                                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-primary transition-all duration-500"
                                        style={{ width: `${node.cpu}%` }}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Memory Usage</span>
                                    <span className="font-medium">{node.memory}%</span>
                                </div>
                                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-500 transition-all duration-500"
                                        style={{ width: `${node.memory}%` }}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="px-6 py-4 bg-muted/50 flex justify-between items-center text-sm text-muted-foreground">
                            <div className="flex items-center gap-2">
                                <Power size={14} />
                                <span>{node.version}</span>
                            </div>
                            <button className="hover:text-foreground">
                                <MoreVertical size={16} />
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
