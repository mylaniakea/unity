import { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Trash2, Brain, Loader2, Server as ServerIcon, Settings as SettingsIcon } from 'lucide-react';
import api from '@/api/client';
import ReactMarkdown from 'react-markdown';
import { useNotification } from '@/contexts/NotificationContext';
import { useConfirm } from '@/contexts/ConfirmDialogContext';

import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

interface Report {
    id: number;
    server_id: number;
    report_type: string;
    start_time: string;
    end_time: string;
    aggregated_data: any;
    generated_at: string;
}

interface ServerProfile {
    id: number;
    name: string;
    ip_address: string;
}

export default function Reports() {
    const [profiles, setProfiles] = useState<ServerProfile[]>([]);
    const [selectedServerId, setSelectedServerId] = useState<number | string>("");
    const [selectedReportType, setSelectedReportType] = useState<string>("24-hour");
    const [reports, setReports] = useState<Report[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedReport, setSelectedReport] = useState<Report | null>(null);
    const [generationLoading, setGenerationLoading] = useState(false);
    const { showNotification } = useNotification();
    const { showConfirm } = useConfirm();

    const fetchProfiles = async () => {
        try {
            const res = await api.get('/profiles/');
            setProfiles(res.data);
            if (res.data.length > 0) {
                setSelectedServerId(res.data[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch profiles", error);
            showNotification("Failed to load server profiles.", "error");
        }
    };

    const fetchReports = async (serverId: number | string, reportType: string) => {
        if (!serverId) return;
        setLoading(true);
        try {
            const res = await api.get(`/reports/server/${serverId}`);
            const filteredReports = res.data.filter((r: Report) => r.report_type === reportType);
            setReports(filteredReports);
            setSelectedReport(filteredReports.length > 0 ? filteredReports[0] : null);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch reports", error);
            showNotification("Failed to load reports.", "error");
            setReports([]);
            setSelectedReport(null);
            setLoading(false);
        }
    };

    const generateReport = async () => {
        if (!selectedServerId || !selectedReportType) return;

        setGenerationLoading(true);
        try {
            await api.post(`/reports/generate/${selectedServerId}/${selectedReportType}`);
            showNotification(`${selectedReportType} report generated successfully!`, "success");
            fetchReports(selectedServerId, selectedReportType);
        } catch (error) {
            console.error("Failed to generate report", error);
            showNotification(`Failed to generate ${selectedReportType} report.`, "error");
        } finally {
            setGenerationLoading(false);
        }
    };

    useEffect(() => {
        fetchProfiles();
    }, []);

    useEffect(() => {
        if (selectedServerId) {
            fetchReports(selectedServerId, selectedReportType);
        }
    }, [selectedServerId, selectedReportType]);

    const deleteReport = async (id: number) => {
        const confirmed = await showConfirm({
            title: "Delete Report",
            message: "Are you sure you want to delete this report?"
        });
        if (!confirmed) return;
        try {
            await api.delete(`/reports/${id}`);
            setReports(reports.filter(r => r.id !== id));
            if (selectedReport?.id === id) setSelectedReport(null);
            showNotification("Report deleted successfully!", "success");
        } catch (error) {
            console.error("Failed to delete report", error);
            showNotification("Failed to delete report.", "error");
        }
    };

    const promoteToKnowledge = async (report: Report) => {
        try {
            // For reports, promote the aggregated data as JSON to knowledge for advanced AI analysis.
            await api.post('/knowledge/', {
                title: `Report: ${report.report_type} for ${profiles.find(p => p.id === report.server_id)?.name || 'Unknown'}`,
                content: JSON.stringify(report.aggregated_data, null, 2), // Store aggregated JSON
                category: "report_snapshot",
                tags: ["report_export", report.report_type, `server_id:${report.server_id}`]
            });
            showNotification("Report added to Knowledge Base!", "success");
        } catch (error) {
            console.error("Failed to promote report to knowledge", error);
            showNotification("Failed to add report to Knowledge Base.", "error");
        }
    };

    // Helper to format aggregated data for Chart.js
    const getChartData = useMemo(() => {
        if (!selectedReport || !selectedReport.aggregated_data) return null;

        const data = selectedReport.aggregated_data;
        const labels = Object.keys(data); // Assuming keys like 'cpu_usage_percent_avg', 'memory_percent_avg'

        return {
            labels: ['Aggregated'], // For single point aggregation
            datasets: [
                {
                    label: 'CPU Usage (Avg %)',
                    data: [data.cpu_usage_percent_avg],
                    borderColor: 'rgb(59, 130, 246)', // blue-500
                    backgroundColor: 'rgba(59, 130, 246, 0.5)',
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: 'Memory Usage (Avg %)',
                    data: [data.memory_percent_avg],
                    borderColor: 'rgb(34, 197, 94)', // green-500
                    backgroundColor: 'rgba(34, 197, 94, 0.5)',
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: 'Disk Usage (Avg %)',
                    data: [data.disk_percent_avg],
                    borderColor: 'rgb(249, 115, 22)', // orange-500
                    backgroundColor: 'rgba(249, 115, 22, 0.5)',
                    tension: 0.3,
                    fill: false,
                },
            ],
        };
    }, [selectedReport]);

    const chartOptions = {
        responsive: true,
        plugins: {
            legend: {
                position: 'top' as const,
            },
            title: {
                display: true,
                text: `Aggregated Metrics for ${selectedReport?.report_type} report`,
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Percentage (%)'
                },
                max: 100
            },
            x: {
                title: {
                    display: true,
                    text: 'Metric'
                }
            }
        }
    };


    const exportReport = (report: Report, format: 'csv' | 'pdf') => {
        // This will require new backend endpoints to generate CSV/PDF
        showNotification(`Exporting ${report.report_type} report for ${profiles.find(p => p.id === report.server_id)?.name || 'Unknown'} as ${format.toUpperCase()}... (Backend integration needed)`, "info");
        // Example: window.open(`/api/reports/export/${report.server_id}/${report.report_type}?format=${format}`, '_blank');
    };

    const reportTypes = ["24-hour", "7-day", "monthly"];

    const currentServer = profiles.find(p => p.id === Number(selectedServerId));

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
                    <p className="text-muted-foreground">Generated summaries and system analysis</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    <select
                        className="bg-card border border-border rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none"
                        value={selectedServerId}
                        onChange={(e) => setSelectedServerId(e.target.value)}
                        aria-label="Select Server"
                    >
                        <option value="">Select Server</option>
                        {profiles.map(p => (
                            <option key={p.id} value={p.id}>{p.name} ({p.ip_address})</option>
                        ))}
                    </select>
                    <select
                        className="bg-card border border-border rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none"
                        value={selectedReportType}
                        onChange={(e) => setSelectedReportType(e.target.value)}
                        aria-label="Select Report Type"
                    >
                        {reportTypes.map(type => (
                            <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)} Report</option>
                        ))}
                    </select>
                    <button
                        onClick={generateReport}
                        disabled={!selectedServerId || !selectedReportType || generationLoading}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                        title="Generate New Report"
                    >
                        {generationLoading ? <Loader2 size={18} className="animate-spin" /> : <SettingsIcon size={18} />}
                        {generationLoading ? "Generating..." : "Generate Report"}
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden flex-col md:flex-row">
                {/* List of Reports */}
                <div className="w-full md:w-1/3 overflow-y-auto pr-2 space-y-4">
                    <h3 className="text-lg font-semibold mb-2">Recent {selectedReportType.charAt(0).toUpperCase() + selectedReportType.slice(1)} Reports for {currentServer?.name || 'Selected Server'}</h3>
                    {loading ? (
                        <div className="text-center py-10 text-muted-foreground">
                            <Loader2 className="animate-spin mx-auto mb-2" size={24} />
                            Loading reports...
                        </div>
                    ) : (
                        reports.length > 0 ? reports.map((report) => (
                            <motion.div
                                key={report.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                onClick={() => setSelectedReport(report)}
                                className={`p-4 rounded-xl border cursor-pointer transition-colors ${selectedReport?.id === report.id ? 'bg-primary/10 border-primary' : 'bg-card border-border hover:bg-muted'}`}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        setSelectedReport(report);
                                    }
                                }}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <FileText size={18} className="text-blue-500" />
                                        <span className="font-semibold truncate">{report.report_type.charAt(0).toUpperCase() + report.report_type.slice(1)} Report</span>
                                    </div>
                                    <span className="text-xs text-muted-foreground">{new Date(report.generated_at).toLocaleDateString()}</span>
                                </div>
                                <p className="text-xs text-muted-foreground line-clamp-2 opacity-70">
                                    Generated from {new Date(report.start_time).toLocaleDateString()} to {new Date(report.end_time).toLocaleDateString()}.
                                </p>
                            </motion.div>
                        )) : (
                            <div className="text-center py-10 text-muted-foreground border-2 border-dashed rounded-xl">
                                No {selectedReportType} reports found for {currentServer?.name || 'selected server'}. Generate one above.
                            </div>
                        )
                    )}
                </div>

                {/* Report Preview / Visualization */}
                <div className="flex-1 bg-card border border-border rounded-xl flex flex-col overflow-hidden">
                    {selectedReport ? (
                        <>
                            <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30">
                                <h2 className="font-bold text-lg">{selectedReport.report_type.charAt(0).toUpperCase() + selectedReport.report_type.slice(1)} Report for {currentServer?.name || 'Unknown'}</h2>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => promoteToKnowledge(selectedReport)}
                                        className="p-2 hover:bg-background rounded text-purple-500 tooltip"
                                        title="Promote to Knowledge Base (Raw JSON)"
                                    >
                                        <Brain size={18} />
                                    </button>
                                    <button
                                        onClick={() => exportReport(selectedReport, 'csv')}
                                        className="p-2 hover:bg-background rounded text-green-500"
                                        title="Download CSV (Requires backend export)"
                                    >
                                        <Download size={18} /> CSV
                                    </button>
                                     <button
                                        onClick={() => exportReport(selectedReport, 'pdf')}
                                        className="p-2 hover:bg-background rounded text-red-500"
                                        title="Download PDF (Requires backend export)"
                                    >
                                        <Download size={18} /> PDF
                                    </button>
                                    <button
                                        onClick={() => deleteReport(selectedReport.id)}
                                        className="p-2 hover:bg-background rounded text-destructive"
                                        title="Delete Report"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            </div>
                            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                                {/* Snapshot Count Badge */}
                                {selectedReport.aggregated_data.snapshot_count !== undefined && (
                                    <div className="text-xs text-muted-foreground text-right">
                                        Based on {selectedReport.aggregated_data.snapshot_count} snapshot{selectedReport.aggregated_data.snapshot_count !== 1 ? 's' : ''}
                                    </div>
                                )}
                                
                                {/* Current Values (Primary) */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                                    <div className="bg-blue-500/10 p-4 rounded-lg border border-blue-500/30">
                                        <div className="text-sm text-blue-400">Current CPU</div>
                                        <div className="text-2xl font-bold">{selectedReport.aggregated_data.cpu_current ?? selectedReport.aggregated_data.cpu_usage_percent_avg ?? 'N/A'}%</div>
                                    </div>
                                    <div className="bg-green-500/10 p-4 rounded-lg border border-green-500/30">
                                        <div className="text-sm text-green-400">Current Memory</div>
                                        <div className="text-2xl font-bold">{selectedReport.aggregated_data.memory_current ?? selectedReport.aggregated_data.memory_percent_avg ?? 'N/A'}%</div>
                                    </div>
                                    <div className="bg-orange-500/10 p-4 rounded-lg border border-orange-500/30">
                                        <div className="text-sm text-orange-400">Current Disk</div>
                                        <div className="text-2xl font-bold">{selectedReport.aggregated_data.disk_current ?? selectedReport.aggregated_data.disk_percent_avg ?? 'N/A'}%</div>
                                    </div>
                                </div>

                                {/* Averages (Secondary - only show if we have multiple snapshots) */}
                                {selectedReport.aggregated_data.snapshot_count > 1 && (
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                                        <div className="bg-muted/20 p-3 rounded-lg border border-border/50">
                                            <div className="text-xs text-muted-foreground">Avg CPU ({selectedReport.aggregated_data.snapshot_count} samples)</div>
                                            <div className="text-lg font-semibold">{selectedReport.aggregated_data.cpu_usage_percent_avg || 'N/A'}%</div>
                                        </div>
                                        <div className="bg-muted/20 p-3 rounded-lg border border-border/50">
                                            <div className="text-xs text-muted-foreground">Avg Memory</div>
                                            <div className="text-lg font-semibold">{selectedReport.aggregated_data.memory_percent_avg || 'N/A'}%</div>
                                        </div>
                                        <div className="bg-muted/20 p-3 rounded-lg border border-border/50">
                                            <div className="text-xs text-muted-foreground">Avg Disk</div>
                                            <div className="text-lg font-semibold">{selectedReport.aggregated_data.disk_percent_avg || 'N/A'}%</div>
                                        </div>
                                    </div>
                                )}

                                {/* Storage Changes */}
                                {selectedReport.aggregated_data.storage_changes && selectedReport.aggregated_data.storage_changes.length > 0 && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-2">Storage Usage Changes</h3>
                                        <ul className="space-y-1">
                                            {selectedReport.aggregated_data.storage_changes.map((change: any, i: number) => (
                                                <li key={i} className="text-sm text-muted-foreground">
                                                    <span className="font-mono">{change.mountpoint}</span>: {change.from_used_gb} GB &rarr; {change.to_used_gb} GB ({change.change_gb > 0 ? '+' : ''}{change.change_gb} GB)
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Package Updates */}
                                {(selectedReport.aggregated_data.package_updates_available.length > 0 || selectedReport.aggregated_data.package_updates_recent.length > 0) && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-2">Package Updates</h3>
                                        {selectedReport.aggregated_data.package_updates_recent.length > 0 && (
                                            <div className="mb-3">
                                                <h4 className="text-sm font-medium mb-1 text-muted-foreground">Recent Updates:</h4>
                                                <ul className="space-y-1 text-sm">
                                                    {selectedReport.aggregated_data.package_updates_recent.map((pkg: any, i: number) => (
                                                        <li key={i} className="font-mono">{pkg.package}: {pkg.from_version} &rarr; {pkg.to_version}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {selectedReport.aggregated_data.package_updates_available.length > 0 && (
                                            <div>
                                                <h4 className="text-sm font-medium mb-1 text-muted-foreground">Available Updates:</h4>
                                                <ul className="space-y-1 text-sm">
                                                    {selectedReport.aggregated_data.package_updates_available.map((pkg: any, i: number) => (
                                                        <li key={i} className="font-mono">{pkg.package} ({pkg.version})</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Average Temperatures */}
                                {selectedReport.aggregated_data.average_temps_celsius && Object.keys(selectedReport.aggregated_data.average_temps_celsius).length > 0 && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-2">Average Temperatures ('C)</h3>
                                        <ul className="space-y-1 text-sm">
                                            {Object.entries(selectedReport.aggregated_data.average_temps_celsius).map(([sensorType, temp], i) => (
                                                <li key={i} className="flex justify-between items-center">
                                                    <span className="text-muted-foreground">{sensorType}</span>
                                                    <span className="font-bold">{String(temp)}°C</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Log Summaries (Placeholders) */}
                                {selectedReport.aggregated_data.syslog_summary && selectedReport.aggregated_data.syslog_summary !== "Not yet implemented." && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-2">Syslog Summary</h3>
                                        <p className="text-sm text-muted-foreground">{selectedReport.aggregated_data.syslog_summary}</p>
                                    </div>
                                )}
                                {selectedReport.aggregated_data.docker_log_summary && selectedReport.aggregated_data.docker_log_summary !== "Not yet implemented." && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-2">Docker Log Summary</h3>
                                        <p className="text-sm text-muted-foreground">{selectedReport.aggregated_data.docker_log_summary}</p>
                                    </div>
                                )}

                                {/* Container Updates (Placeholder) */}
                                {selectedReport.aggregated_data.container_updates_available && selectedReport.aggregated_data.container_updates_available.length > 0 && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-2">Available Container Updates</h3>
                                        <ul className="space-y-1 text-sm">
                                            {selectedReport.aggregated_data.container_updates_available.map((container: string, i: number) => (
                                                <li key={i} className="font-mono">{container}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* GPU Stats (nvidia-smi plugin) */}
                                {selectedReport.aggregated_data.plugin_data?.['nvidia-smi']?.gpus?.length > 0 && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                                            <span className="text-purple-400">⚡</span> GPU Status
                                        </h3>
                                        <div className="grid gap-3">
                                            {selectedReport.aggregated_data.plugin_data['nvidia-smi'].gpus.map((gpu: any, i: number) => (
                                                <div key={i} className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <span className="font-medium text-sm">{gpu.name}</span>
                                                        <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded">GPU {gpu.index}</span>
                                                    </div>
                                                    <div className="grid grid-cols-4 gap-3 text-center text-sm">
                                                        <div>
                                                            <div className="text-xs text-muted-foreground">Temp</div>
                                                            <div className={`font-bold ${gpu.temp_c > 80 ? 'text-red-400' : gpu.temp_c > 60 ? 'text-yellow-400' : 'text-green-400'}`}>
                                                                {gpu.temp_c}°C
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <div className="text-xs text-muted-foreground">Utilization</div>
                                                            <div className="font-bold">{gpu.utilization_pct}%</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-xs text-muted-foreground">VRAM</div>
                                                            <div className="font-bold">{Math.round(gpu.memory_used_mb / 1024 * 10) / 10}GB / {Math.round(gpu.memory_total_mb / 1024 * 10) / 10}GB</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-xs text-muted-foreground">Power</div>
                                                            <div className="font-bold">{gpu.power_draw_w}W</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Docker Container Stats (docker-stats plugin) */}
                                {selectedReport.aggregated_data.plugin_data?.['docker-stats']?.containers?.length > 0 && (
                                    <div className="bg-card border border-border rounded-xl p-4">
                                        <h3 className="font-semibold mb-3 flex items-center gap-2">
                                            <span className="text-cyan-400">🐳</span> Container Stats
                                        </h3>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm">
                                                <thead>
                                                    <tr className="border-b border-border text-left">
                                                        <th className="pb-2 font-medium text-muted-foreground">Container</th>
                                                        <th className="pb-2 font-medium text-muted-foreground text-right">CPU</th>
                                                        <th className="pb-2 font-medium text-muted-foreground text-right">Memory</th>
                                                        <th className="pb-2 font-medium text-muted-foreground text-right">Net I/O</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-border/50">
                                                    {selectedReport.aggregated_data.plugin_data['docker-stats'].containers.map((c: any, i: number) => (
                                                        <tr key={i} className="hover:bg-muted/30 transition-colors">
                                                            <td className="py-2 font-mono text-cyan-300">{c.name}</td>
                                                            <td className="py-2 text-right">{c.cpu_pct}</td>
                                                            <td className="py-2 text-right"><span className="text-muted-foreground">{c.mem_pct}</span> <span className="text-xs">({c.mem_usage.split(' / ')[0]})</span></td>
                                                            <td className="py-2 text-right text-xs text-muted-foreground">{c.net_io}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}

                                {getChartData && (
                                    <div className="h-80">
                                        <Line options={chartOptions} data={getChartData} />
                                    </div>
                                )}
                                <div className="bg-muted/10 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                                    <h3 className="font-semibold mb-2">Raw Aggregated Data</h3>
                                    <pre className="whitespace-pre-wrap">{JSON.stringify(selectedReport.aggregated_data, null, 2)}</pre>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-muted-foreground">
                            Select a report from the list to view its details and visualizations.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
