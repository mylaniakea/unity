import { useEffect, useState } from 'react';
import { Network, Plus, Trash2, Edit2, Save } from 'lucide-react';
import api from '@/api/client';
import { motion } from 'framer-motion';
import { useConfirm } from '@/contexts/ConfirmDialogContext';

interface HomelabItem {
    id: number;
    title: string;
    content: string;
    category: string;
}

export default function Homelab() {
    const [items, setItems] = useState<HomelabItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [newItem, setNewItem] = useState({ title: '', content: '' });
    const [editingId, setEditingId] = useState<number | null>(null);
    const { showConfirm } = useConfirm();

    const fetchItems = async () => {
        try {
            // We reuse the knowledge endpoint but filter client-side or assume we might add server-side filtering later.
            // Ideally backend supports filtering. 
            // Currently backend GET /knowledge returns all. We filter here for category='homelab'.
            const res = await api.get('/knowledge/');
            const homelabItems = res.data.filter((k: HomelabItem) => k.category === 'homelab');
            setItems(homelabItems);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch homelab info", error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchItems();
    }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/knowledge/', {
                title: newItem.title,
                content: newItem.content,
                category: 'homelab',
                tags: []
            });
            setNewItem({ title: '', content: '' });
            fetchItems();
        } catch (error) {
            console.error("Failed to add item", error);
        }
    };

    const handleDelete = async (id: number) => {
        const confirmed = await showConfirm({
            title: "Delete Item",
            message: "Are you sure you want to delete this homelab item?"
        });
        if (!confirmed) return;
        try {
            await api.delete(`/knowledge/${id}`);
            fetchItems();
        } catch (error) {
            console.error("Failed to delete", error);
        }
    };

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Homelab Environment</h1>
                <p className="text-muted-foreground">Define your infrastructure context (DNS, Subnets, Credentials) for the AI agent.</p>
            </div>

            {/* Add New Item Card */}
            <div className="bg-card border border-border p-6 rounded-xl">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <Plus size={18} /> Add Environment Variable
                </h3>
                <form onSubmit={handleAdd} className="grid md:grid-cols-3 gap-4">
                    <div>
                        <label className="text-xs font-medium text-muted-foreground">Key / Name</label>
                        <input
                            required
                            value={newItem.title}
                            onChange={e => setNewItem({ ...newItem, title: e.target.value })}
                            placeholder="e.g. Primary DNS"
                            className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1"
                        />
                    </div>
                    <div className="md:col-span-2">
                        <label className="text-xs font-medium text-muted-foreground">Value / Details</label>
                        <div className="flex gap-2">
                            <input
                                required
                                value={newItem.content}
                                onChange={e => setNewItem({ ...newItem, content: e.target.value })}
                                placeholder="e.g. 192.168.1.1"
                                className="w-full bg-background border border-border rounded-md px-3 py-2 mt-1 flex-1"
                            />
                            <button
                                type="submit"
                                className="mt-1 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                            >
                                Add
                            </button>
                        </div>
                    </div>
                </form>
            </div>

            {/* List */}
            {loading ? (
                <div>Loading...</div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {items.map((item) => (
                        <motion.div
                            key={item.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-card border border-border p-4 rounded-xl flex flex-col group relative"
                        >
                            <button
                                onClick={() => handleDelete(item.id)}
                                className="absolute top-2 right-2 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Delete Item"
                            >
                                <Trash2 size={16} />
                            </button>
                            
                            <div className="flex items-center gap-2 mb-2 text-primary">
                                <Network size={18} />
                                <span className="font-semibold">{item.title}</span>
                            </div>
                            <div className="bg-muted/50 p-2 rounded text-sm font-mono break-all">
                                {item.content}
                            </div>
                        </motion.div>
                    ))}
                    
                    {items.length === 0 && (
                        <div className="col-span-full text-center py-10 text-muted-foreground">
                            No environment variables defined. Add one above.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
