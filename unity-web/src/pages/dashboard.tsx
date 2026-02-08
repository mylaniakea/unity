import { useState, useEffect, useCallback } from 'react';
import MetricChart from '@/components/dashboard/metric-chart';
import dashboardApi, { type MetricsHistory } from '@/api/dashboard';

type TimeRange = '1h' | '6h' | '24h' | '7d';

export default function Dashboard() {
    const [timeRange, setTimeRange] = useState<TimeRange>('1h');
    const [metricsData, setMetricsData] = useState<MetricsHistory | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchMetrics = useCallback(async () => {
        try {
            setError(null);
            // In a real app we'd pass timeRange to the API
            const data = await dashboardApi.getMetricsHistory(timeRange);
            setMetricsData(data);
        } catch (err) {
            console.error('Failed to fetch metrics history:', err);
            setError('Failed to load metrics data');
        } finally {
            setLoading(false);
        }
    }, [timeRange]);

    useEffect(() => {
        fetchMetrics();
        const interval = setInterval(fetchMetrics, 30000);
        return () => clearInterval(interval);
    }, [fetchMetrics]);

    const timeRangeOptions: TimeRange[] = ['1h', '6h', '24h', '7d'];
    const timeRangeLabels = {
        '1h': '1 Hour',
        '6h': '6 Hours',
        '24h': '24 Hours',
        '7d': '7 Days'
    };

    if (loading && !metricsData) {
        return (
            <div className="space-y-6">
                <div className="bg-card border border-border rounded-lg shadow p-4">
                    <div className="h-6 bg-muted rounded w-1/4 mb-4 animate-pulse"></div>
                    <div className="h-64 bg-muted rounded animate-pulse"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive">
                <p>{error}</p>
                <button
                    onClick={() => fetchMetrics()}
                    className="mt-2 text-sm underline hover:no-underline"
                >
                    Retry
                </button>
            </div>
        );
    }

    const cpuData = metricsData?.metrics['system_info.cpu_percent'] || [];
    const memoryData = metricsData?.metrics['system_info.memory_percent'] || [];
    const diskData = metricsData?.metrics['disk_monitor.disk_usage_percent'] || [];
    const networkSentData = metricsData?.metrics['network_monitor.network_bytes_sent'] || [];

    return (
        <div className="space-y-6">
            {/* Time Range Selector */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold tracking-tight text-foreground">
                    Dashboard
                </h2>
                <div className="flex space-x-2 bg-muted p-1 rounded-lg">
                    {timeRangeOptions.map((range) => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={`px-3 py-1 rounded-md text-sm font-medium transition-all ${timeRange === range
                                ? 'bg-background text-foreground shadow-sm'
                                : 'text-muted-foreground hover:text-foreground'
                                }`}
                        >
                            {timeRangeLabels[range]}
                        </button>
                    ))}
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <MetricChart
                    title="CPU Usage"
                    data={cpuData}
                    color="#3b82f6"
                    unit="%"
                    chartType="line"
                />
                <MetricChart
                    title="Memory Usage"
                    data={memoryData}
                    color="#8b5cf6"
                    unit="%"
                    chartType="line"
                />
                {/* Disk Chart */}
                <MetricChart
                    title="Disk Usage"
                    data={diskData}
                    color="#eab308"
                    unit="%"
                    chartType="line"
                    height={250}
                    className="border-yellow-500/20"
                />        <MetricChart
                    title="Network Traffic (Sent)"
                    data={networkSentData}
                    color="#10b981"
                    unit=" B"
                    chartType="line"
                />
            </div>
        </div>
    );
}
