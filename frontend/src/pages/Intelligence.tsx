import React from 'react';
import { useState, useEffect } from 'react';
import { Bot, Send, Sparkles, Server, Save } from 'lucide-react';
import api from '@/api/client';
import { cn } from '@/lib/utils';
import { useNotification } from '@/contexts/NotificationContext';
import { useConfirm } from '@/contexts/ConfirmDialogContext';

export default function Intelligence() {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState<string | null>(null);
    const [profiles, setProfiles] = useState<any[]>([]);
    const [reports, setReports] = useState<any[]>([]);
    const [selectedProfileId, setSelectedProfileId] = useState<number | string>(""); 
    const [scanLoading, setScanLoading] = useState(false);
    const { showNotification } = useNotification();
    const { showConfirm } = useConfirm();
    
    // Fetch profiles and reports on mount
    useEffect(() => {
        api.get('/profiles/').then(res => setProfiles(res.data)).catch(console.error);
        fetchReports();
    }, []);

    const fetchReports = () => {
        api.get('/reports/').then(res => setReports(res.data)).catch(console.error);
    };

    const getSelectedProfile = () => {
        if (!selectedProfileId) return null;
        return profiles.find(p => p.id === Number(selectedProfileId));
    };

    const scanHardware = async () => {
        if (!selectedProfileId) return;
        setScanLoading(true);
        try {
            await api.post(`/profiles/${selectedProfileId}/scan-hardware`);
            showNotification("Hardware scan complete! View details in the Hardware tab.", "success");
        } catch (error) {
            console.error("Scan failed", error);
            showNotification("Hardware scan failed. Check SSH connection.", "error");
        } finally {
            setScanLoading(false);
        }
    };

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const history = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }));
            
            // Pass profile_id if selected
            const payload: any = { messages: history };
            if (selectedProfileId) {
                payload.profile_id = Number(selectedProfileId);
            }

            const res = await api.post('/ai/chat', payload);
            const aiMsg = { role: 'assistant', content: res.data.response };

            setMessages(prev => [...prev, aiMsg]);
        } catch (error) {
            console.error("Chat failed", error);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error connecting to the intelligence engine.' }]);
        } finally {
            setLoading(false);
        }
    };

    const generateSummary = async () => {
        setLoading(true);
        try {
            const payload: any = {};
            if (selectedProfileId) {
                payload.profile_id = Number(selectedProfileId);
            }
            const res = await api.post('/ai/generate-summary', payload);
            setSummary(res.data.summary);
        } catch (error) {
            console.error("Summary failed", error);
        } finally {
            setLoading(false);
        }
    };

    const saveReport = async () => {
        if (!summary) return;
        
        const profile = getSelectedProfile();
        const serverName = profile ? profile.name : 'LocalSystem';
        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, ''); // YYYYMMDD
        
        const reportName = prompt("Enter report name:", "System_Audit"); // Keep browser prompt for now until a custom input dialog is built
        if (!reportName) return;
        
        let fullTitle = `${serverName}_${reportName}_${dateStr}`;
        const existingReport = reports.find(r => r.title === fullTitle);
        
        try {
            if (existingReport) {
                const choice = await showConfirm({
                    title: "Report Exists",
                    message: `Report '${fullTitle}' already exists. Do you want to OVERWRITE it? Click Cancel to save as a NEW report (with timestamp suffix).`
                });
                
                if (choice) {
                    // Overwrite (Update)
                    await api.put(`/reports/${existingReport.id}`, {
                        title: fullTitle,
                        content: summary,
                        type: 'system_summary'
                    });
                    showNotification("Report updated successfully!", "success");
                } else {
                    // Keep (Save New)
                    fullTitle = `${fullTitle}_${new Date().getTime()}`;
                    await api.post('/reports/', {
                        title: fullTitle,
                        content: summary,
                        type: 'system_summary'
                    });
                    showNotification(`Report saved as '${fullTitle}'!`, "success");
                }
            } else {
                // New Report
                await api.post('/reports/', {
                    title: fullTitle,
                    content: summary,
                    type: 'system_summary'
                });
                showNotification("Report saved successfully!", "success");
            }
            fetchReports(); // Refresh list
        } catch (error) {
            console.error("Failed to save report", error);
            showNotification("Failed to save report.", "error");
        }
    };

    return (
        <div className="space-y-8 h-[calc(100vh-140px)] flex flex-col">
            <div className="flex items-center justify-between shrink-0">
                <div className="flex flex-col gap-2">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Intelligence Engine</h1>
                        <p className="text-muted-foreground">Interact with your local LLM (Ollama)</p>
                    </div>
                    
                    {/* Server Selector */}
                    <div className="flex items-center gap-2 mt-2">
                        <Server size={16} className="text-muted-foreground" />
                        <select 
                            className="bg-card border border-border rounded-md px-2 py-1 text-sm focus:ring-1 focus:ring-primary outline-none"
                            value={selectedProfileId}
                            onChange={(e) => setSelectedProfileId(e.target.value)}
                            aria-label="Select Server Profile"
                        >
                            <option value="">Local System (Host)</option>
                            {profiles.map(p => (
                                <option key={p.id} value={p.id}>{p.name} ({p.ip_address})</option>
                            ))}
                        </select>
                    </div>
                </div>
                
                <div className="flex gap-2">
                    {summary && (
                        <button
                            onClick={saveReport}
                            className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors"
                        >
                            <Save size={18} />
                            Save Report
                        </button>
                    )}
                    <button
                        onClick={scanHardware}
                        disabled={scanLoading || !selectedProfileId}
                        className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
                        title="Run deep hardware scan (LSPCI, Disks, RAID)"
                    >
                        <Server size={18} className={scanLoading ? "animate-spin" : ""} />
                        Scan Hardware
                    </button>
                    <button
                        onClick={generateSummary}
                        disabled={loading}
                        className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50"
                    >
                        <Sparkles size={18} />
                        Generate Report
                    </button>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6 min-h-0">
                {/* Chat Area */}
                <div className="md:col-span-2 bg-card border border-border rounded-xl flex flex-col overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.length === 0 && (
                            <div className="text-center text-muted-foreground mt-20">
                                <Bot size={48} className="mx-auto mb-4 opacity-20" />
                                <p>Start a conversation about {getSelectedProfile()?.name || "your system"}.</p>
                            </div>
                        )}
                        {messages.map((m, i) => (
                            <div key={i} className={cn("flex", m.role === 'user' ? "justify-end" : "justify-start")}>
                                <div className={cn(
                                    "max-w-[80%] rounded-2xl px-4 py-2",
                                    m.role === 'user' ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                                )}>
                                    {m.content}
                                </div>
                            </div>
                        ))}
                        {loading && <div className="text-sm text-muted-foreground animate-pulse">Thinking...</div>}
                    </div>
                    <div className="p-4 border-t border-border flex gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                            placeholder={`Ask about ${getSelectedProfile()?.name || "local system"}...`}
                            className="flex-1 bg-background border border-border rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                        <button
                            onClick={sendMessage}
                            disabled={loading || !input.trim()}
                            className="p-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                            title="Send Message"
                        >
                            <Send size={20} />
                        </button>
                    </div>
                </div>

                {/* Context / Summary Area */}
                <div className="bg-card border border-border rounded-xl p-6 overflow-y-auto">
                    <h3 className="font-bold mb-4 flex items-center gap-2">
                        <Activity size={20} />
                        Analysis: {getSelectedProfile()?.name || "Local System"}
                    </h3>
                    {summary ? (
                        <div className="prose prose-sm dark:prose-invert">
                            <p className="whitespace-pre-wrap">{summary}</p>
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">
                            Click "Generate Report" to analyze telemetry for the selected server.
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}

// Icon helper
function Activity({ size }: { size: number }) { return <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg> }