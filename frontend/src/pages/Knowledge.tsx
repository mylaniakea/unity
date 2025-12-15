import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Search, Server, X, ExternalLink, Hash, Trash2 } from 'lucide-react';
import api from '@/api/client';
import { cn } from '@/lib/utils';
import { useConfirm } from '@/contexts/ConfirmDialogContext';
// import ReactMarkdown from 'react-markdown'; // Assuming user might add later

interface KnowledgeItem {
    id: number;
    title: string;
    content: string;
    category: string;
    tags: string[];
    created_at: string;
}

interface GroupedKnowledge {
    [serverName: string]: KnowledgeItem[];
}

export default function Knowledge() {
    const [items, setItems] = useState<KnowledgeItem[]>([]);
    const [groupedItems, setGroupedItems] = useState<GroupedKnowledge>({});
    const [loading, setLoading] = useState(true);
    const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);
    const [filter, setFilter] = useState('');
    const { showConfirm } = useConfirm();

    const fetchKnowledge = async () => {
        try {
            const res = await api.get('/knowledge/');
            setItems(res.data);
            groupItems(res.data);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch knowledge", error);
            setLoading(false);
        }
    };

    const deleteItem = async (id: number, e: React.MouseEvent) => {
        e.stopPropagation();
        const confirmed = await showConfirm({
            title: "Delete Knowledge Item",
            message: "Are you sure you want to delete this knowledge item?"
        });
        if (!confirmed) return;
        try {
            await api.delete(`/knowledge/${id}`);
            fetchKnowledge();
            if (selectedItem?.id === id) setSelectedItem(null);
        } catch (error) {
            console.error("Delete failed", error);
        }
    };

    const groupItems = (data: KnowledgeItem[]) => {
        const groups: GroupedKnowledge = { "General": [] };
        
        data.forEach(item => {
            // Find server_name tag
            const serverTag = item.tags?.find(t => t.startsWith("server_name:"));
            const groupName = serverTag ? serverTag.split(":")[1] : "General";
            
            if (!groups[groupName]) groups[groupName] = [];
            groups[groupName].push(item);
        });
        
        // Remove empty General if unused (optional)
        if (groups["General"].length === 0) delete groups["General"];
        
        setGroupedItems(groups);
    };

    useEffect(() => {
        fetchKnowledge();
    }, []);

    // Filter logic
    const filteredGroups = Object.entries(groupedItems).reduce((acc, [server, serverItems]) => {
        const filtered = serverItems.filter(item => 
            item.title.toLowerCase().includes(filter.toLowerCase()) ||
            item.content.toLowerCase().includes(filter.toLowerCase())
        );
        if (filtered.length > 0) acc[server] = filtered;
        return acc;
    }, {} as GroupedKnowledge);

    return (
        <div className="space-y-8 relative">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
                    <p className="text-muted-foreground">AI-generated documentation and manual insights.</p>
                </div>
                <div className="relative w-full md:w-64">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <input
                        placeholder="Search knowledge..."
                        className="pl-8 w-full bg-card border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                    />
                </div>
            </div>

            {loading ? (
                <div>Loading knowledge base...</div>
            ) : (
                <div className="space-y-8">
                    {Object.keys(filteredGroups).length === 0 && (
                        <div className="text-center py-20 text-muted-foreground border-2 border-dashed border-border rounded-xl">
                            No knowledge items found. Add some via the Hardware tab or Homelab settings.
                        </div>
                    )}

                    {Object.entries(filteredGroups).map(([serverName, serverItems]) => (
                        <motion.div 
                            key={serverName}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-card/50 border border-border/50 rounded-xl overflow-hidden"
                        >
                            <div className="bg-muted/30 px-6 py-3 border-b border-border/50 flex items-center gap-2">
                                <Server size={18} className="text-primary" />
                                <h2 className="font-semibold text-lg">{serverName}</h2>
                                <span className="text-xs bg-background border border-border px-2 py-0.5 rounded-full text-muted-foreground">
                                    {serverItems.length} Items
                                </span>
                            </div>
                            <div className="p-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                                {serverItems.map((item) => (
                                    <div 
                                        key={item.id}
                                        onClick={() => setSelectedItem(item)}
                                        className="bg-background border border-border p-4 rounded-lg hover:border-primary/50 cursor-pointer transition-colors group relative"
                                        role="button"
                                        tabIndex={0} // Make it keyboard focusable
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                setSelectedItem(item);
                                            }
                                        }}
                                    >
                                        <button
                                            onClick={(e) => deleteItem(item.id, e)}
                                            className="absolute top-2 right-2 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity p-1"
                                            title="Delete Item"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                        <div className="flex items-start justify-between mb-2 pr-6">
                                            <div className="flex items-center gap-2">
                                                <Brain size={16} className="text-purple-500 shrink-0" />
                                                <span className="font-medium truncate" title={item.title}>
                                                    {item.title}
                                                </span>
                                            </div>
                                        </div>
                                        <p className="text-xs text-muted-foreground line-clamp-3 mb-3">
                                            {item.content.slice(0, 150)}...
                                        </p>
                                        <div className="flex flex-wrap gap-1">
                                            <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded border border-border/50">
                                                {item.category}
                                            </span>
                                            <span className="text-[10px] text-muted-foreground ml-auto">
                                                {new Date(item.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}

            {/* View Modal */}
            <AnimatePresence>
                {selectedItem && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col"
                        >
                            <div className="flex items-center justify-between p-6 border-b border-border">
                                <div>
                                    <h2 className="text-2xl font-bold">{selectedItem.title}</h2>
                                    <div className="flex gap-2 mt-1 text-sm text-muted-foreground">
                                        <span className="flex items-center gap-1"><Server size={12} /> {selectedItem.tags.find(t => t.startsWith('server_name'))?.split(':')[1] || 'General'}</span>
                                        <span>•</span>
                                        <span>{new Date(selectedItem.created_at).toLocaleString()}</span>
                                    </div>
                                </div>
                                <button 
                                    onClick={() => setSelectedItem(null)}
                                    className="p-2 hover:bg-muted rounded-full transition-colors"
                                    title="Close"
                                >
                                    <X size={24} />
                                </button>
                            </div>
                            
                            <div className="flex-1 overflow-y-auto p-6">
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <pre className="whitespace-pre-wrap font-sans">{selectedItem.content}</pre>
                                </div>
                            </div>
                            
                            <div className="p-4 border-t border-border bg-muted/20 flex gap-2">
                                {selectedItem.tags.map(tag => (
                                    <span key={tag} className="text-xs flex items-center gap-1 bg-background border border-border px-2 py-1 rounded">
                                        <Hash size={10} /> {tag}
                                    </span>
                                ))}
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}