// Mock dashboard API for now
export interface MetricsHistory {
    metrics: Record<string, Array<{ timestamp: string; value: number }>>;
    fetched_at: string;
}

const dashboardApi = {
    getMetricsHistory: async (timeRange: string): Promise<MetricsHistory> => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 500));

        const now = Date.now();
        const points = 20;
        const generateData = (base: number, variance: number) =>
            Array.from({ length: points }, (_, i) => ({
                timestamp: new Date(now - (points - i) * 60000 * (timeRange === '1h' ? 3 : 10)).toISOString(),
                value: base + Math.random() * variance
            }));

        return {
            metrics: {
                'system_info.cpu_percent': generateData(45, 15),
                'system_info.memory_percent': generateData(60, 10),
                'disk_monitor.disk_usage_percent': generateData(75, 2),
                'network_monitor.network_bytes_sent': generateData(1000, 5000),
                'network_monitor.network_bytes_recv': generateData(2000, 8000),
            },
            fetched_at: new Date().toISOString()
        };
    }
};

export default dashboardApi;
